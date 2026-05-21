from __future__ import annotations

import csv
import json
import os
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


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


def _metricflow_command(*args: str) -> list[str]:
    return ["uv", "run", *_dotenv_prefix(), "mf", *args]


@lru_cache(maxsize=1)
def _ensure_semantic_manifest() -> None:
    dbt_packages_dir = DBT_PROJECT_DIR / "dbt_packages"
    if not dbt_packages_dir.exists() or not any(dbt_packages_dir.iterdir()):
        _run_command(
            [
                "uv",
                "run",
                *_dotenv_prefix(),
                "dbt",
                "deps",
                "--project-dir",
                str(DBT_PROJECT_DIR),
                "--profiles-dir",
                str(DBT_PROJECT_DIR),
            ],
            cwd=REPO_ROOT,
        )
    _run_command(
        [
            "uv",
            "run",
            *_dotenv_prefix(),
            "dbt",
            "parse",
            "--project-dir",
            str(DBT_PROJECT_DIR),
            "--profiles-dir",
            str(DBT_PROJECT_DIR),
            "--no-partial-parse",
        ],
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

    command = _metricflow_command("query", "--metrics", metric_name, "--csv", str(csv_path))
    explain_command = _metricflow_command("query", "--metrics", metric_name, "--explain")

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
