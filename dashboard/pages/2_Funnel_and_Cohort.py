from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dashboard.components.charts import funnel_table, retention_pivot
from dashboard.components.data import available_values, metric_query
from dashboard.components.layout import configure_page, page_intro, show_sql


OBJECTIVE_OPTIONS = [
    "All",
    "app_install",
    "brand_awareness",
    "ecommerce_purchase",
    "lead_generation",
    "marketplace_order",
    "offline_conversion",
    "subscription",
]


configure_page("Funnel and Cohort")
page_intro(
    "Funnel and Cohort",
    "Track objective-specific drop-off and how weekly signup cohorts retain after acquisition.",
)

selected_objective = st.sidebar.selectbox(
    "Objective",
    OBJECTIVE_OPTIONS,
    help="Choose one growth objective, or keep All to compare every objective in the funnel table.",
)
st.sidebar.caption("The filter is applied after the governed MetricFlow query returns.")

with st.status("Loading funnel completion metrics...", expanded=False) as funnel_status:
    st.write("Querying governed funnel_step_users metric")
    funnel_result = metric_query(
        "funnel_step_users",
        ("funnel_completion__objective", "funnel_completion__step_name"),
        limit=200,
    )
    funnel_status.update(label="Funnel metrics loaded", state="complete", expanded=False)
if funnel_result.error:
    st.error(funnel_result.error)
else:
    funnel = funnel_result.data.rename(
        columns={
            "funnel_completion__objective": "objective",
            "funnel_completion__step_name": "step",
            "funnel_step_users": "users",
        }
    )
    returned_objectives = set(available_values(funnel, "objective"))
    if selected_objective != "All" and selected_objective not in returned_objectives:
        st.warning(f"No funnel rows were returned for `{selected_objective}`.")
    if selected_objective != "All":
        funnel = funnel[funnel["objective"].astype(str) == selected_objective]

    st.subheader("Funnel Step Completion")
    prepared = funnel_table(funnel, "objective", "step", "users")
    if prepared.empty:
        st.info("No funnel rows returned.")
    else:
        if selected_objective == "All":
            chart_frame = prepared.groupby("step", as_index=True)["users"].sum().sort_values(ascending=False)
        else:
            chart_frame = prepared.set_index("step")["users"]
        st.bar_chart(chart_frame, use_container_width=True)
        st.dataframe(
            prepared.assign(
                step_conversion_rate=lambda frame: frame["step_conversion_rate"].map(
                    lambda value: "" if value != value else f"{value:.1%}"
                ),
                dropoff_rate=lambda frame: frame["dropoff_rate"].map(
                    lambda value: "" if value != value else f"{value:.1%}"
                ),
            ),
            hide_index=True,
            use_container_width=True,
        )
    show_sql(funnel_result.sql)

st.divider()
st.subheader("Weekly Cohort Retention")
with st.status("Loading weekly cohort retention...", expanded=False) as retention_status:
    st.write("Querying governed retention_rate metric")
    retention_result = metric_query(
        "retention_rate",
        ("cohort_week__signup_week", "cohort_week__weeks_since_signup"),
        limit=200,
    )
    retention_status.update(label="Retention metrics loaded", state="complete", expanded=False)
if retention_result.error:
    st.error(retention_result.error)
else:
    retention = retention_result.data.rename(
        columns={
            "cohort_week__signup_week": "signup_week",
            "cohort_week__signup_week__week": "signup_week",
            "cohort_week__weeks_since_signup": "weeks_since_signup",
            "retention_rate": "retention_rate",
        }
    )
    if retention.empty:
        st.info("No retention rows returned.")
    else:
        pivot = retention_pivot(retention, "signup_week", "weeks_since_signup", "retention_rate")
        st.dataframe(pivot.style.format("{:.1%}"), use_container_width=True)
        st.line_chart(pivot.T, use_container_width=True)
    show_sql(retention_result.sql)
