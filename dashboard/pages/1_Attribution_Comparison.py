from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dashboard.components.charts import bar_chart
from dashboard.components.data import MODEL_CONFIG, metric_query, revenue_by_model
from dashboard.components.layout import configure_page, page_intro, show_sql


configure_page("Attribution Comparison")
page_intro(
    "Attribution Comparison",
    "See how channel value shifts when the same conversions are credited by different attribution rules.",
)

model = st.sidebar.selectbox("Attribution model", list(MODEL_CONFIG.keys()), index=3)
channel_filter = st.sidebar.multiselect(
    "Channels",
    ["tiktok_ads", "google_ads", "meta_ads", "email", "organic_search", "app_store_organic", "referral"],
)

config = MODEL_CONFIG[model]
result = metric_query(config["metric"], (config["dimension"],), limit=50)
if result.error:
    st.error(result.error)
else:
    selected = result.data.rename(columns={config["dimension"]: "channel", config["metric"]: "revenue"})
    if channel_filter:
        selected = selected[selected["channel"].isin(channel_filter)]

    top = selected.sort_values("revenue", ascending=False).head(10) if not selected.empty else selected
    left, right = st.columns([2, 1])
    with left:
        st.subheader(f"Attributed Revenue By Channel: {model}")
        bar_chart(top, "channel", "revenue")
    with right:
        st.subheader("Channel Ranking")
        if top.empty:
            st.info("No rows returned.")
        else:
            st.dataframe(top, hide_index=True, use_container_width=True)

    show_sql(result.sql)

st.divider()
st.subheader("Same Channels Across All Five Models")
comparison = revenue_by_model()
if channel_filter:
    comparison = comparison[comparison["channel"].isin(channel_filter)]

if comparison.empty:
    st.info("No attribution comparison rows returned yet.")
else:
    pivot = comparison.pivot_table(index="channel", columns="model", values="revenue", aggfunc="sum").fillna(0)
    st.dataframe(pivot.style.format("${:,.0f}"), use_container_width=True)
    st.bar_chart(pivot, use_container_width=True)

    if {"First touch", "Last touch"}.issubset(pivot.columns):
        shift = (pivot["First touch"] - pivot["Last touch"]).sort_values(ascending=False)
        channel = shift.index[0]
        st.markdown(
            f"""
            <div class="panel">
            <b>Insight</b><br/>
            {channel} receives ${pivot.loc[channel, "First touch"]:,.0f} under first-touch and
            ${pivot.loc[channel, "Last touch"]:,.0f} under last-touch attribution. A positive gap means the
            channel is stronger at starting journeys than closing them.
            </div>
            """,
            unsafe_allow_html=True,
        )
