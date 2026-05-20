from __future__ import annotations

import pandas as pd
import streamlit as st


FUNNEL_ORDER = [
    "ad_impression",
    "ad_click",
    "landing_page_view",
    "app_install",
    "signup",
    "activation",
    "purchase",
    "repeat_purchase",
    "lead_submit",
    "subscription_start",
    "offline_purchase",
]


def bar_chart(frame: pd.DataFrame, x: str, y: str, *, color: str | None = None) -> None:
    if frame.empty or x not in frame.columns or y not in frame.columns:
        st.info("No rows returned for this chart yet.")
        return
    chart = frame.set_index(x)[y]
    st.bar_chart(chart, use_container_width=True)


def line_chart(frame: pd.DataFrame, x: str, y: str) -> None:
    if frame.empty or x not in frame.columns or y not in frame.columns:
        st.info("No rows returned for this chart yet.")
        return
    st.line_chart(frame.set_index(x)[y], use_container_width=True)


def funnel_table(frame: pd.DataFrame, objective_column: str, step_column: str, value_column: str) -> pd.DataFrame:
    if frame.empty:
        return frame
    table = frame.copy()
    table["_step_order"] = table[step_column].apply(
        lambda value: FUNNEL_ORDER.index(value) if value in FUNNEL_ORDER else len(FUNNEL_ORDER)
    )
    table = table.sort_values([objective_column, "_step_order"]).drop(columns=["_step_order"])
    table["previous_step_users"] = table.groupby(objective_column)[value_column].shift(1)
    table["step_conversion_rate"] = table[value_column] / table["previous_step_users"]
    table["dropoff_rate"] = 1 - table["step_conversion_rate"]
    table.loc[table["previous_step_users"].isna(), ["step_conversion_rate", "dropoff_rate"]] = None
    return table


def retention_pivot(frame: pd.DataFrame, cohort_column: str, week_column: str, value_column: str) -> pd.DataFrame:
    if frame.empty:
        return frame
    pivot = frame.pivot_table(
        index=cohort_column,
        columns=week_column,
        values=value_column,
        aggfunc="mean",
    ).sort_index()
    return pivot

