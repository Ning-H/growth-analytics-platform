from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st

from nl_interface.agent import answer_question
from nl_interface.metricflow_tool import MetricFlowToolError, list_metrics, query_metric


MODEL_CONFIG = {
    "First touch": {
        "metric": "attributed_revenue_first_touch",
        "dimension": "attribution_record__channel",
    },
    "Last touch": {
        "metric": "attributed_revenue_last_touch",
        "dimension": "attribution_record_last_touch__channel",
    },
    "Linear": {
        "metric": "attributed_revenue_linear",
        "dimension": "attribution_record_linear__channel",
    },
    "Time decay": {
        "metric": "attributed_revenue_time_decay",
        "dimension": "attribution_record_time_decay__channel",
    },
    "Position based": {
        "metric": "attributed_revenue_position_based",
        "dimension": "attribution_record_position_based__channel",
    },
}


@dataclass(frozen=True)
class QueryResult:
    data: pd.DataFrame
    sql: str
    error: str | None = None


def _coerce_numbers(frame: pd.DataFrame) -> pd.DataFrame:
    for column in frame.columns:
        if column == "metric_time":
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
            continue
        converted = pd.to_numeric(frame[column], errors="coerce")
        if converted.notna().any():
            frame[column] = converted
    return frame


@st.cache_data(ttl=900, show_spinner=False)
def metric_query(
    metric_name: str,
    group_by: tuple[str, ...] = (),
    limit: int | None = 100,
    order_by: str | None = None,
) -> QueryResult:
    try:
        result = query_metric(
            metric_name,
            group_by=list(group_by),
            limit=limit,
            order_by=order_by,
        )
    except MetricFlowToolError as error:
        return QueryResult(pd.DataFrame(), "", str(error))

    frame = _coerce_numbers(pd.DataFrame(result["data"]))
    return QueryResult(frame, result.get("query_sql", ""), None)


@st.cache_data(ttl=900, show_spinner=False)
def metric_catalog() -> list[dict[str, Any]]:
    try:
        return list_metrics()
    except MetricFlowToolError:
        return []


def ask_agent(question: str, use_openai: bool = True) -> dict[str, Any]:
    return answer_question(question, use_openai=use_openai)


def revenue_by_model() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for label, config in MODEL_CONFIG.items():
        result = metric_query(config["metric"], (config["dimension"],), limit=50)
        if result.error or result.data.empty:
            continue
        frame = result.data.rename(columns={config["dimension"]: "channel", config["metric"]: "revenue"})
        frame["model"] = label
        frames.append(frame[["model", "channel", "revenue"]])
    if not frames:
        return pd.DataFrame(columns=["model", "channel", "revenue"])
    return pd.concat(frames, ignore_index=True)


def app_stats() -> dict[str, str]:
    catalog = metric_catalog()
    return {
        "Metrics": str(len(catalog)),
        "Attribution models": "5",
        "dbt marts": "15+",
        "NL eval": "17/17",
    }
