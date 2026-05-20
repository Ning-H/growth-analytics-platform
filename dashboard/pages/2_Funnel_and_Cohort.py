from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dashboard.components.charts import funnel_table, retention_pivot
from dashboard.components.data import metric_query
from dashboard.components.layout import configure_page, page_intro, show_sql


configure_page("Funnel and Cohort")
page_intro(
    "Funnel and Cohort",
    "Track objective-specific drop-off and how weekly signup cohorts retain after acquisition.",
)

objective = st.sidebar.selectbox(
    "Objective",
    ["All", "app_install", "ecommerce_purchase", "lead_generation", "subscription", "marketplace", "offline_sales"],
)

funnel_result = metric_query(
    "funnel_step_users",
    ("funnel_completion__objective", "funnel_completion__step_name"),
    limit=200,
)
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
    if objective != "All":
        funnel = funnel[funnel["objective"] == objective]

    st.subheader("Funnel Step Completion")
    prepared = funnel_table(funnel, "objective", "step", "users")
    if prepared.empty:
        st.info("No funnel rows returned.")
    else:
        first_objective = prepared["objective"].iloc[0]
        chart_frame = prepared[prepared["objective"] == first_objective].set_index("step")["users"]
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
retention_result = metric_query(
    "retention_rate",
    ("cohort_week__signup_week", "cohort_week__weeks_since_signup"),
    limit=200,
)
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
