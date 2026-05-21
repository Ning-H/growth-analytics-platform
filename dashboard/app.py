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
      <h1>TikTok Ads Growth Analytics Platform</h1>
      <p>Measure which ads, channels, and campaign objectives actually drive users from first
      exposure to conversion across app installs, ecommerce purchases, subscriptions, leads,
      marketplace actions, awareness, and offline sales.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="problem">
      <div class="label">Problem statement</div>
      TikTok advertisers do not all share one clean funnel. A mobile app campaign may need
      impression → click → install → signup → activation → purchase. An ecommerce campaign may
      skip install and go directly from ad click to product page to purchase. Lead-gen,
      subscription, marketplace, awareness, and offline-sales campaigns each create different
      conversion paths. This platform simulates those raw journeys, resolves identity, builds
      warehouse models, and lets growth teams compare attribution, funnel drop-off, cohorts,
      CAC, ROAS, and governed metric answers.
    </div>
    """,
    unsafe_allow_html=True,
)

stats = app_stats()
cols = st.columns(4)
for col, (label, value) in zip(cols, stats.items(), strict=True):
    col.metric(label, value)

st.subheader("Data Product Flow")
flow_cols = st.columns(4)
flow_cards = [
    (
        "Data generated",
        "A Python simulator creates synthetic TikTok Ads journeys for multiple advertiser objectives, channels, campaigns, devices, countries, and conversion types.",
    ),
    (
        "Raw event stream",
        "Events are published to Kafka topics such as impressions, clicks, app installs, signups, activations, purchases, leads, subscriptions, marketplace, and offline conversions.",
    ),
    (
        "Processing",
        "PySpark lands bronze data in BigQuery. dbt cleans, deduplicates, resolves users, sessionizes events, and builds facts, dimensions, attribution, funnel, and cohort marts.",
    ),
    (
        "Analysis surface",
        "MetricFlow defines governed metrics. Streamlit visualizes them, and the OpenAI assistant answers questions by querying metrics instead of writing raw SQL.",
    ),
]
for col, (title, body) in zip(flow_cols, flow_cards, strict=True):
    with col:
        st.markdown(
            f"""
            <div class="panel">
              <div class="label">{title}</div>
              <p class="quiet">{body}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.subheader("Architecture")
st.graphviz_chart(
    """
    digraph {
      graph [rankdir=LR, bgcolor="transparent", pad=0.2, nodesep=0.45, ranksep=0.65]
      node [shape=box, style="rounded,filled", color="#b9c9d8", fillcolor="#f7f9fb", fontname="Helvetica", fontsize=11]
      edge [color="#67839b"]
      Objectives [label="Advertiser objectives\\napp, commerce, lead, subscription, marketplace, offline"]
      Simulator [label="Python simulator\\nsynthetic TikTok Ads journeys"]
      Events [label="Event taxonomy\\nimpression, click, install, signup, activation, purchase"]
      Kafka [label="Kafka\\nraw event topics"]
      Spark [label="PySpark\\nstream parsing + bronze ingestion"]
      Bronze [label="BigQuery bronze\\nraw event tables"]
      dbt [label="dbt silver/gold\\nresolved users, sessions, facts, dims"]
      Attribution [label="Attribution marts\\nfirst, last, linear, time decay, position"]
      MetricFlow [label="MetricFlow\\nDAU, CAC, ROAS, retention, revenue"]
      OpenAI [label="OpenAI agent\\ngoverned text-to-metric"]
      Dashboard [label="Streamlit\\nportfolio demo"]
      Objectives -> Simulator -> Events -> Kafka -> Spark -> Bronze -> dbt
      dbt -> Attribution -> MetricFlow
      dbt -> MetricFlow
      MetricFlow -> Dashboard
      MetricFlow -> OpenAI -> Dashboard
    }
    """,
    use_container_width=True,
)

st.subheader("What A Reviewer Should Notice")
notice_left, notice_right = st.columns(2)
with notice_left:
    st.markdown(
        """
        - Multi-objective event design, not a one-funnel toy dataset
        - Kafka and Spark used for the resume-relevant streaming path
        - BigQuery/dbt warehouse modeling with bronze, silver, and gold layers
        - Five attribution models with auditable credit assignment
        """
    )
with notice_right:
    st.markdown(
        """
        - Funnel and cohort marts separated from attribution marts
        - MetricFlow as the semantic layer and business metric contract
        - LLM interface constrained to governed metrics, not free-form SQL
        - SQL shown for auditability on every NL answer
        """
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
