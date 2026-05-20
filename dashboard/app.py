from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard.components.data import app_stats
from dashboard.components.layout import configure_page


configure_page("Home")

st.markdown(
    """
    <div class="hero">
      <h1>Growth Analytics Platform</h1>
      <p>A warehouse-first TikTok Ads analytics platform for multi-objective attribution,
      funnel and cohort analysis, and governed natural-language data discovery.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

stats = app_stats()
cols = st.columns(4)
for col, (label, value) in zip(cols, stats.items(), strict=True):
    col.metric(label, value)

st.subheader("Architecture")
st.graphviz_chart(
    """
    digraph {
      graph [rankdir=LR, bgcolor="transparent", pad=0.2, nodesep=0.45, ranksep=0.65]
      node [shape=box, style="rounded,filled", color="#b9c9d8", fillcolor="#f7f9fb", fontname="Helvetica", fontsize=11]
      edge [color="#67839b"]
      Simulator [label="Python simulator\\nTikTok Ads journeys"]
      Kafka [label="Kafka\\nraw event topics"]
      Spark [label="PySpark streaming\\nbronze ingestion"]
      BigQuery [label="BigQuery\\nbronze warehouse"]
      dbt [label="dbt\\nsilver + gold marts"]
      MetricFlow [label="MetricFlow\\ngoverned metrics"]
      OpenAI [label="OpenAI agent\\ntext-to-metric"]
      Dashboard [label="Streamlit\\ndemo surface"]
      Simulator -> Kafka -> Spark -> BigQuery -> dbt -> MetricFlow -> OpenAI -> Dashboard
      MetricFlow -> Dashboard
    }
    """,
    use_container_width=True,
)

st.subheader("Demo Paths")
left, middle, right = st.columns(3)
with left:
    st.markdown(
        """
        <div class="panel">
          <h3>Attribution Comparison</h3>
          <p class="quiet">Compare first-touch, last-touch, linear, time-decay, and position-based revenue by channel.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_Attribution_Comparison.py", label="Open attribution page")
with middle:
    st.markdown(
        """
        <div class="panel">
          <h3>Funnel + Cohort</h3>
          <p class="quiet">Inspect objective-specific funnel drop-off and weekly retention behavior.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_Funnel_and_Cohort.py", label="Open funnel page")
with right:
    st.markdown(
        """
        <div class="panel">
          <h3>Ask The Data</h3>
          <p class="quiet">Ask business questions in English and see the governed MetricFlow SQL behind each answer.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/3_Ask_The_Data.py", label="Open NL page")

st.info(
    "Interview framing: this is not text-to-SQL. The assistant routes questions to governed MetricFlow metrics, "
    "then exposes the generated SQL for auditability."
)
