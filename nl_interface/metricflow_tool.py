from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account


REPO_ROOT = Path(__file__).resolve().parents[1]
DBT_PROJECT_DIR = REPO_ROOT / "dbt_project"
METRICS_DIR = DBT_PROJECT_DIR / "models" / "metrics"
ENV_PATH = REPO_ROOT / ".env"


def _bootstrap_environment() -> None:
    """One-time process-level setup that must run before any subprocess calls.

    Placed here so it fires on import, regardless of which Streamlit page loads
    first (app.py is only executed when the home page is visited).
    """
    # Required for uv on Streamlit Cloud's mounted filesystem, which does not
    # support hardlinks.
    os.environ.setdefault("UV_LINK_MODE", "copy")

    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=False)

    # Streamlit Cloud exposes root-level secrets as env vars. This fallback also
    # supports nested secrets if the user pasted a TOML table for readability.
    try:
        import streamlit as st

        for key in (
            "GCP_PROJECT_ID",
            "BIGQUERY_DATASET_RAW",
            "BIGQUERY_DATASET_ANALYTICS",
            "OPENAI_API_KEY",
            "OPENAI_MODEL",
        ):
            value = st.secrets.get(key)
            if value and not os.getenv(key):
                os.environ[key] = str(value)

        if not os.getenv("GCP_SERVICE_ACCOUNT_JSON"):
            service_account = st.secrets.get("GCP_SERVICE_ACCOUNT_JSON")
            if service_account:
                os.environ["GCP_SERVICE_ACCOUNT_JSON"] = str(service_account)
            elif "gcp_service_account" in st.secrets:
                os.environ["GCP_SERVICE_ACCOUNT_JSON"] = json.dumps(dict(st.secrets["gcp_service_account"]))
    except Exception:
        # CLI use, local tests, and imports outside Streamlit should not depend
        # on Streamlit's secrets runtime being present.
        pass

    # Write GCP credentials to a temp file when only the JSON content is provided
    # (Streamlit Cloud cannot store files, only env-var strings).
    json_content = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    if json_content:
        path = os.getenv("GCP_SERVICE_ACCOUNT_JSON_PATH", "")
        if not path or not Path(path).exists():
            try:
                json.loads(json_content)
            except json.JSONDecodeError:
                return
            cred_path = Path(tempfile.gettempdir()) / "gcp_sa.json"
            cred_path.write_text(json_content)
            os.environ["GCP_SERVICE_ACCOUNT_JSON_PATH"] = str(cred_path)


_bootstrap_environment()


class MetricFlowToolError(ValueError):
    """Raised when a requested MetricFlow query is outside the governed catalog."""


def _run_command(args: list[str], cwd: Path = DBT_PROJECT_DIR) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise MetricFlowToolError((result.stderr or result.stdout).strip())
    return result.stdout


def _dotenv_prefix() -> list[str]:
    """Return the dotenv wrapper when a .env file exists; empty list otherwise.

    On Streamlit Cloud there is no .env file — environment variables are injected
    directly into the process, so subprocesses inherit them without dotenv.
    """
    if ENV_PATH.exists():
        return ["dotenv", "-f", str(ENV_PATH), "run", "--"]
    return []


def _tool_command(tool: str, *args: str) -> list[str]:
    """Build a command that works both locally and on Streamlit Cloud.

    Local development usually runs the app through `uv run`, while Streamlit
    Cloud installs dependencies into its own environment. In Cloud, `mf` and
    `dbt` should be called directly from PATH instead of assuming `uv` exists at
    app runtime.
    """
    if shutil.which(tool):
        return [tool, *args]
    if shutil.which("uv"):
        return ["uv", "run", *_dotenv_prefix(), tool, *args]
    return [tool, *args]


def _metricflow_command(*args: str) -> list[str]:
    return _tool_command("mf", *args)


@lru_cache(maxsize=1)
def _ensure_semantic_manifest() -> None:
    dbt_packages_dir = DBT_PROJECT_DIR / "dbt_packages"
    if not dbt_packages_dir.exists() or not any(dbt_packages_dir.iterdir()):
        _run_command(
            _tool_command(
                "dbt",
                "deps",
                "--project-dir",
                str(DBT_PROJECT_DIR),
                "--profiles-dir",
                str(DBT_PROJECT_DIR),
            ),
            cwd=REPO_ROOT,
        )
    _run_command(
        _tool_command(
            "dbt",
            "parse",
            "--project-dir",
            str(DBT_PROJECT_DIR),
            "--profiles-dir",
            str(DBT_PROJECT_DIR),
            "--no-partial-parse",
        ),
        cwd=REPO_ROOT,
    )


@lru_cache(maxsize=1)
def _load_metric_yaml() -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    for path in sorted(METRICS_DIR.glob("*.yml")):
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        for metric in data.get("metrics", []):
            metrics[metric["name"]] = {
                "name": metric["name"],
                "description": metric.get("description", ""),
                "type": metric.get("type", ""),
                "label": metric.get("label", metric["name"]),
                "file": str(path.relative_to(REPO_ROOT)),
            }
    return metrics


@lru_cache(maxsize=1)
def _build_metric_dimensions() -> dict[str, list[str]]:
    """Build metric → available MetricFlow dimensions from semantic model YAML files.

    MetricFlow dimension names follow the convention {primary_entity}__{dim_name}.
    All metrics also expose metric_time. This replaces CLI-output parsing, which is
    fragile and returns only metric_time when the output format doesn't match.
    """
    semantic_dir = DBT_PROJECT_DIR / "models" / "semantic_models"

    # Step 1: measure name → list of entity-prefixed dimension names
    measure_dims: dict[str, list[str]] = {}
    if semantic_dir.exists():
        for path in sorted(semantic_dir.glob("*.yml")):
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            for sem_model in data.get("semantic_models", []):
                primary_entity = next(
                    (e["name"] for e in sem_model.get("entities", []) if e.get("type") == "primary"),
                    None,
                )
                if not primary_entity:
                    continue
                dims = ["metric_time"]
                for dim in sem_model.get("dimensions", []):
                    dims.append(f"{primary_entity}__{dim['name']}")
                for measure in sem_model.get("measures", []):
                    measure_dims[measure["name"]] = dims

    # Step 2: metric name → dimensions via measure lookup
    metric_dims: dict[str, list[str]] = {}
    for path in sorted(METRICS_DIR.glob("*.yml")):
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        for metric in data.get("metrics", []):
            name = metric["name"]
            tp = metric.get("type_params", {})
            measure = tp.get("measure")
            if measure:
                metric_dims[name] = measure_dims.get(measure, ["metric_time"])
                continue
            # Ratio metrics: union of numerator and denominator dimensions
            dims_set: set[str] = {"metric_time"}
            for key in ("numerator", "denominator"):
                m = tp.get(key)
                if m and m in measure_dims:
                    dims_set.update(measure_dims[m])
            metric_dims[name] = sorted(dims_set)

    return metric_dims


@lru_cache(maxsize=1)
def list_metrics() -> list[dict[str, Any]]:
    """Return the governed metric catalog with available MetricFlow dimensions."""
    metrics = _load_metric_yaml()
    dimensions = _build_metric_dimensions()
    return [
        {
            **metric,
            "available_dimensions": dimensions.get(name, ["metric_time"]),
        }
        for name, metric in sorted(metrics.items())
    ]


def _metric_names() -> set[str]:
    return {metric["name"] for metric in list_metrics()}


def _validate_query(metric_name: str, group_by: list[str] | None) -> None:
    catalog = {metric["name"]: metric for metric in list_metrics()}
    if metric_name not in catalog:
        raise MetricFlowToolError(
            f"Metric '{metric_name}' is not in the governed MetricFlow catalog."
        )

    available_dimensions = set(catalog[metric_name].get("available_dimensions", []))
    for dimension in group_by or []:
        if dimension not in available_dimensions:
            raise MetricFlowToolError(
                f"Dimension '{dimension}' is not valid for metric '{metric_name}'. "
                f"Available examples: {sorted(available_dimensions)[:10]}"
            )


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return reader.fieldnames or [], rows


def _extract_sql(explain_output: str) -> str:
    marker = "SELECT"
    index = explain_output.find(marker)
    if index == -1:
        return ""
    return explain_output[index:].strip()


def _bq_client() -> bigquery.Client:
    project = os.getenv("GCP_PROJECT_ID")
    keyfile = os.getenv("GCP_SERVICE_ACCOUNT_JSON_PATH")
    if keyfile and Path(keyfile).exists():
        credentials = service_account.Credentials.from_service_account_file(keyfile)
        return bigquery.Client(project=project or credentials.project_id, credentials=credentials)
    return bigquery.Client(project=project)


def _table(name: str) -> str:
    project = os.getenv("GCP_PROJECT_ID")
    dataset = os.getenv("BIGQUERY_DATASET_ANALYTICS", "growth_analytics")
    if not project:
        raise MetricFlowToolError("GCP_PROJECT_ID is required for BigQuery fallback queries.")
    return f"`{project}.{dataset}.{name}`"


ATTRIBUTION_TABLES = {
    "first_touch": ("fact_attribution_first_touch", "attribution_record__channel"),
    "last_touch": ("fact_attribution_last_touch", "attribution_record_last_touch__channel"),
    "linear": ("fact_attribution_linear", "attribution_record_linear__channel"),
    "time_decay": ("fact_attribution_time_decay", "attribution_record_time_decay__channel"),
    "position_based": (
        "fact_attribution_position_based",
        "attribution_record_position_based__channel",
    ),
}


def _attribution_model(metric_name: str) -> str | None:
    for model in ATTRIBUTION_TABLES:
        if metric_name.endswith(model):
            return model
    return None


def _limit_clause(limit: int | None) -> str:
    return f"\nLIMIT {int(limit)}" if limit else ""


def _fallback_sql(metric_name: str, group_by: list[str], limit: int | None) -> str | None:
    """Equivalent governed SQL for hosted dashboards when MetricFlow CLI fails.

    MetricFlow remains the canonical definition source in the repo. This fallback
    uses the dbt marts those metrics point to, with aliases matching MetricFlow's
    output names so the dashboard and NL layer keep the same contract.
    """
    group_by = group_by or []
    first_group = group_by[0] if group_by else None

    model = _attribution_model(metric_name)
    if model:
        table_name, channel_alias = ATTRIBUTION_TABLES[model]
        if metric_name.startswith("attributed_revenue_"):
            measure = "sum(attributed_revenue)"
        elif metric_name.startswith("attributed_conversions_"):
            measure = "sum(credit_fraction)"
        elif metric_name.startswith("roas_"):
            spend = f"(select sum(daily_spend) from {_table('fact_campaign_spend_daily')})"
            measure = f"safe_divide(sum(attributed_revenue), {spend})"
        elif metric_name.startswith("cac_"):
            spend = f"(select sum(daily_spend) from {_table('fact_campaign_spend_daily')})"
            measure = f"safe_divide({spend}, sum(credit_fraction))"
        else:
            return None

        if first_group:
            if first_group != channel_alias:
                return None
            return f"""
SELECT
  channel AS `{channel_alias}`,
  {measure} AS `{metric_name}`
FROM {_table(table_name)}
GROUP BY 1
ORDER BY `{metric_name}` DESC{_limit_clause(limit)}
""".strip()
        return f"""
SELECT
  {measure} AS `{metric_name}`
FROM {_table(table_name)}{_limit_clause(limit)}
""".strip()

    if metric_name in {"dau", "wau", "mau"} and first_group == "metric_time":
        date_expr = {
            "dau": "event_date",
            "wau": "date_trunc(event_date, week(monday))",
            "mau": "date_trunc(event_date, month)",
        }[metric_name]
        return f"""
SELECT
  {date_expr} AS metric_time__day,
  count(distinct resolved_user_id) AS `{metric_name}`
FROM {_table('fact_user_events')}
GROUP BY 1
ORDER BY `{metric_name}` DESC{_limit_clause(limit)}
""".strip()

    if metric_name == "new_signups" and first_group == "event__channel":
        return f"""
SELECT
  channel AS event__channel,
  count(*) AS new_signups
FROM {_table('fact_user_events')}
WHERE event_type = 'signup'
GROUP BY 1
ORDER BY new_signups DESC{_limit_clause(limit)}
""".strip()

    if metric_name == "funnel_step_users":
        if group_by != ["funnel_completion__objective", "funnel_completion__step_name"]:
            return None
        return f"""
SELECT
  objective AS funnel_completion__objective,
  step_name AS funnel_completion__step_name,
  count(distinct resolved_user_id) AS funnel_step_users
FROM {_table('funnel_step_completion')}
GROUP BY 1, 2
ORDER BY 1, 2{_limit_clause(limit)}
""".strip()

    if metric_name == "retention_rate":
        if group_by == ["cohort_week__signup_week", "cohort_week__weeks_since_signup"]:
            return f"""
SELECT
  signup_week AS cohort_week__signup_week,
  weeks_since_signup AS cohort_week__weeks_since_signup,
  safe_divide(sum(retained_users), sum(cohort_users)) AS retention_rate
FROM {_table('cohort_retention_matrix')}
GROUP BY 1, 2
ORDER BY 1, 2{_limit_clause(limit)}
""".strip()
        if group_by == ["cohort_week__weeks_since_signup"]:
            return f"""
SELECT
  weeks_since_signup AS cohort_week__weeks_since_signup,
  safe_divide(sum(retained_users), sum(cohort_users)) AS retention_rate
FROM {_table('cohort_retention_matrix')}
GROUP BY 1
ORDER BY 1{_limit_clause(limit)}
""".strip()

    if metric_name == "conversions" and first_group == "conversion__objective":
        return f"""
SELECT
  objective AS conversion__objective,
  count(*) AS conversions
FROM {_table('fact_conversions')}
GROUP BY 1
ORDER BY conversions DESC{_limit_clause(limit)}
""".strip()

    if metric_name == "conversion_value" and first_group == "conversion__objective":
        return f"""
SELECT
  objective AS conversion__objective,
  sum(conversion_value) AS conversion_value
FROM {_table('fact_conversions')}
GROUP BY 1
ORDER BY conversion_value DESC{_limit_clause(limit)}
""".strip()

    if metric_name == "total_spend" and first_group == "campaign_spend_day__channel":
        return f"""
SELECT
  channel AS campaign_spend_day__channel,
  sum(daily_spend) AS total_spend
FROM {_table('fact_campaign_spend_daily')}
GROUP BY 1
ORDER BY total_spend DESC{_limit_clause(limit)}
""".strip()

    if metric_name == "signup_to_activation_rate" and first_group == "event__channel":
        return f"""
SELECT
  channel AS event__channel,
  safe_divide(
    count(distinct if(event_type = 'activation', resolved_user_id, null)),
    count(distinct if(event_type = 'signup', resolved_user_id, null))
  ) AS signup_to_activation_rate
FROM {_table('fact_user_events')}
WHERE event_type IN ('signup', 'activation')
GROUP BY 1
ORDER BY signup_to_activation_rate DESC{_limit_clause(limit)}
""".strip()

    return None


def _query_bigquery_fallback(metric_name: str, group_by: list[str], limit: int | None) -> dict[str, Any]:
    sql = _fallback_sql(metric_name, group_by, limit)
    if not sql:
        raise MetricFlowToolError(
            f"MetricFlow failed, and no hosted-dashboard fallback exists for `{metric_name}` "
            f"grouped by {group_by}."
        )
    rows = [dict(row.items()) for row in _bq_client().query(sql).result()]
    columns = list(rows[0].keys()) if rows else []
    return {
        "metric_name": metric_name,
        "group_by": group_by,
        "columns": columns,
        "data": rows,
        "row_count": len(rows),
        "query_sql": sql,
    }


def query_metric(
    metric_name: str,
    group_by: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    time_range: dict[str, str] | None = None,
    order_by: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Run a governed MetricFlow query and return rows plus generated SQL."""
    if filters:
        raise MetricFlowToolError("Structured filters are not implemented yet; use governed dimensions.")

    group_by = group_by or []
    _validate_query(metric_name, group_by)
    _ensure_semantic_manifest()

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_file:
        csv_path = Path(temp_file.name)

    command = _metricflow_command(
        "query",
        "--metrics",
        metric_name,
        "--csv",
        str(csv_path),
        "--quiet",
    )
    explain_command = _metricflow_command(
        "query",
        "--metrics",
        metric_name,
        "--explain",
        "--quiet",
    )

    if group_by:
        group_by_arg = ",".join(group_by)
        command.extend(["--group-by", group_by_arg])
        explain_command.extend(["--group-by", group_by_arg])
    if time_range:
        if time_range.get("start"):
            command.extend(["--start-time", time_range["start"]])
            explain_command.extend(["--start-time", time_range["start"]])
        if time_range.get("end"):
            command.extend(["--end-time", time_range["end"]])
            explain_command.extend(["--end-time", time_range["end"]])
    if order_by:
        command.extend(["--order", order_by])
        explain_command.extend(["--order", order_by])
    if limit:
        command.extend(["--limit", str(limit)])
        explain_command.extend(["--limit", str(limit)])

    try:
        _run_command(command)
        columns, rows = _read_csv(csv_path)
        explain_output = _run_command(explain_command)
    except MetricFlowToolError as error:
        if "'NoneType' object has no attribute 'close'" in str(error):
            return _query_bigquery_fallback(metric_name, group_by, limit)
        raise
    finally:
        csv_path.unlink(missing_ok=True)

    return {
        "metric_name": metric_name,
        "group_by": group_by,
        "columns": columns,
        "data": rows,
        "row_count": len(rows),
        "query_sql": _extract_sql(explain_output),
    }


if __name__ == "__main__":
    print(json.dumps(list_metrics(), indent=2))
