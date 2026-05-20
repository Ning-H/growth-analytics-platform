from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DBT_PROJECT_DIR = REPO_ROOT / "dbt_project"
METRICS_DIR = DBT_PROJECT_DIR / "models" / "metrics"
ENV_PATH = REPO_ROOT / ".env"


class MetricFlowToolError(ValueError):
    """Raised when a requested MetricFlow query is outside the governed catalog."""


def _run_command(args: list[str], cwd: Path = DBT_PROJECT_DIR) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise MetricFlowToolError((result.stderr or result.stdout).strip())
    return result.stdout


def _metricflow_command(*args: str) -> list[str]:
    return ["uv", "run", "dotenv", "-f", str(ENV_PATH), "run", "--", "mf", *args]


def _ensure_semantic_manifest() -> None:
    _run_command(
        [
            "uv",
            "run",
            "dotenv",
            "-f",
            str(ENV_PATH),
            "run",
            "--",
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


def _available_dimensions_from_mf() -> dict[str, list[str]]:
    _ensure_semantic_manifest()
    output = _run_command(_metricflow_command("list", "metrics"))
    dimensions: dict[str, list[str]] = {}
    for line in output.splitlines():
        match = re.search(r"•\s+([^:]+):\s+(.*)", line.strip())
        if not match:
            continue
        metric_name = match.group(1).strip()
        raw_dimensions = match.group(2).strip()
        if raw_dimensions.endswith(" more"):
            # `mf list metrics` truncates long lists; keep the visible names and always allow metric_time.
            raw_dimensions = raw_dimensions.rsplit(" and ", 1)[0]
        dimensions[metric_name] = [
            item.strip()
            for item in raw_dimensions.split(",")
            if item.strip() and item.strip() != "metric_time"
        ]
        if "metric_time" not in dimensions[metric_name]:
            dimensions[metric_name].append("metric_time")
    return dimensions


def list_metrics() -> list[dict[str, Any]]:
    """Return the governed metric catalog with visible MetricFlow dimensions."""
    metrics = _load_metric_yaml()
    try:
        dimensions = _available_dimensions_from_mf()
    except MetricFlowToolError:
        dimensions = {}

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
