from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

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

st.subheader("Interactive Architecture")
components.html(
    """
    <style>
      body { margin: 0; font-family: Inter, Arial, sans-serif; color: #15171a; }
      .arch-wrap {
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 18px;
        background:
          radial-gradient(circle at top left, rgba(37,244,238,.16), transparent 30%),
          radial-gradient(circle at bottom right, rgba(254,44,85,.13), transparent 32%),
          #ffffff;
      }
      .arch-grid {
        display: grid;
        grid-template-columns: repeat(5, minmax(150px, 1fr));
        gap: 14px;
        align-items: stretch;
      }
      .arch-node {
        position: relative;
        min-height: 118px;
        border: 1px solid #d9dee7;
        border-top: 4px solid #25F4EE;
        border-radius: 8px;
        padding: 13px 13px 12px 13px;
        background: rgba(255,255,255,.94);
        box-shadow: 0 8px 22px rgba(16,24,40,.06);
        transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease;
      }
      .arch-node:hover {
        transform: translateY(-3px);
        border-color: #25F4EE;
        box-shadow: 0 14px 30px rgba(16,24,40,.12);
        z-index: 5;
      }
      .arch-node.red { border-top-color: #FE2C55; }
      .arch-node.black { border-top-color: #010101; }
      .arch-title {
        font-size: 14px;
        font-weight: 800;
        margin-bottom: 7px;
      }
      .arch-sub {
        color: #667085;
        font-size: 12px;
        line-height: 1.35;
      }
      .arch-stat {
        display: inline-block;
        margin-top: 10px;
        padding: 4px 8px;
        border-radius: 999px;
        background: #f3f4f6;
        color: #111827;
        font-size: 11px;
        font-weight: 700;
      }
      .arch-details {
        display: none;
        position: absolute;
        left: 10px;
        right: 10px;
        top: calc(100% - 8px);
        padding: 11px 12px;
        border: 1px solid #dbeafe;
        border-radius: 8px;
        background: #ffffff;
        color: #374151;
        font-size: 12px;
        line-height: 1.42;
        box-shadow: 0 12px 28px rgba(16,24,40,.16);
      }
      .arch-node:hover .arch-details { display: block; }
      .flow-arrow {
        text-align: center;
        color: #98a2b3;
        font-size: 18px;
        padding: 4px 0;
      }
      .arch-caption {
        margin-top: 14px;
        color: #667085;
        font-size: 12px;
      }
      @media (max-width: 900px) {
        .arch-grid { grid-template-columns: repeat(2, minmax(150px, 1fr)); }
      }
    </style>
    <div class="arch-wrap">
      <div class="arch-grid">
        <div class="arch-node">
          <div class="arch-title">Advertiser Objectives</div>
          <div class="arch-sub">App, commerce, lead, subscription, marketplace, awareness, offline.</div>
          <div class="arch-stat">7 objectives</div>
          <div class="arch-details">The model supports different TikTok ad outcomes instead of forcing every product through the same app-install funnel.</div>
        </div>
        <div class="arch-node red">
          <div class="arch-title">Synthetic Journey Simulator</div>
          <div class="arch-sub">Creates user paths with channels, campaigns, devices, countries, and conversion values.</div>
          <div class="arch-stat">10k users / 30 days</div>
          <div class="arch-details">The dummy data is generated from configurable conversion rates, objective distribution, channel shares, ad spend, and time gaps between touchpoints.</div>
        </div>
        <div class="arch-node">
          <div class="arch-title">Kafka Event Stream</div>
          <div class="arch-sub">Raw event topics for impressions, clicks, installs, signups, purchases, leads, and more.</div>
          <div class="arch-stat">event-level raw data</div>
          <div class="arch-details">Kafka represents the streaming boundary: producers emit raw events, and downstream jobs process the same log into warehouse tables.</div>
        </div>
        <div class="arch-node black">
          <div class="arch-title">PySpark Processing</div>
          <div class="arch-sub">Parses events, adds ingestion metadata, checkpoints streams, and lands bronze data.</div>
          <div class="arch-stat">streaming ingestion</div>
          <div class="arch-details">Spark handles schema enforcement, event timestamps, Kafka offsets, and the deterministic device-to-user identity mapping job.</div>
        </div>
        <div class="arch-node">
          <div class="arch-title">BigQuery Bronze</div>
          <div class="arch-sub">Raw tables preserve event payloads and ingestion metadata for replay/debugging.</div>
          <div class="arch-stat">growth_raw</div>
          <div class="arch-details">Bronze is intentionally close to source data. It supports backfills, schema checks, and row-count reconciliation against Kafka.</div>
        </div>
        <div class="arch-node red">
          <div class="arch-title">dbt Silver + Gold</div>
          <div class="arch-sub">Cleans events, resolves users, builds sessions, facts, dimensions, funnels, cohorts.</div>
          <div class="arch-stat">15+ marts</div>
          <div class="arch-details">This layer turns raw events into analysis-ready warehouse models: touchpoints, conversions, user events, campaigns, users, attribution, funnel, and cohort tables.</div>
        </div>
        <div class="arch-node">
          <div class="arch-title">Attribution Engine</div>
          <div class="arch-sub">First-touch, last-touch, linear, time-decay, and position-based credit assignment.</div>
          <div class="arch-stat">5 models</div>
          <div class="arch-details">Each model assigns conversion credit differently, then validates that credit fractions sum to one per conversion.</div>
        </div>
        <div class="arch-node black">
          <div class="arch-title">MetricFlow Semantic Layer</div>
          <div class="arch-sub">Canonical metrics for DAU, CAC, ROAS, retention, attributed revenue, and funnel conversion.</div>
          <div class="arch-stat">34 metrics</div>
          <div class="arch-details">MetricFlow prevents metric drift by defining business meaning and query logic in governed YAML instead of ad hoc dashboard SQL.</div>
        </div>
        <div class="arch-node">
          <div class="arch-title">LLM Data Discovery</div>
          <div class="arch-sub">OpenAI answers questions by selecting governed metrics, not by inventing SQL.</div>
          <div class="arch-stat">auditable SQL</div>
          <div class="arch-details">The assistant routes natural language to MetricFlow queries and exposes generated SQL so the answer can be inspected.</div>
        </div>
        <div class="arch-node red">
          <div class="arch-title">Dashboard Surface</div>
          <div class="arch-sub">Attribution comparison, funnel/cohort analysis, and natural-language exploration.</div>
          <div class="arch-stat">3 workflows</div>
          <div class="arch-details">The dashboard is the product surface for growth teams to diagnose budget allocation, drop-off, retention, and metric questions.</div>
        </div>
      </div>
      <div class="arch-caption">Hover over each component to see what it does, what data it touches, and why it exists in the platform.</div>
    </div>
    """,
    height=520,
    scrolling=False,
)

st.subheader("Project Highlights")
highlight_cols = st.columns(2)
with highlight_cols[0]:
    st.markdown(
        """
        - Models multiple TikTok advertiser objectives instead of assuming every product has the same funnel.
        - Preserves raw event streams before transforming them into analysis-ready warehouse tables.
        - Resolves anonymous device behavior into user-level journeys after signup or conversion.
        - Separates attribution, funnel, cohort, and spend logic so each analysis has a clear source table.
        """
    )
with highlight_cols[1]:
    st.markdown(
        """
        - Compares five attribution rules and surfaces when model choice changes channel credit.
        - Defines metrics in a governed semantic layer so CAC, ROAS, retention, and revenue stay consistent.
        - Lets analysts ask plain-English questions while still showing the generated MetricFlow SQL.
        - Uses dummy data to mirror real operational problems without exposing customer or platform data.
        """
    )

st.subheader("Explore The Product")
workflow = st.tabs(["1. Diagnose channel credit", "2. Find funnel drop-off", "3. Ask governed metrics"])
with workflow[0]:
    st.markdown(
        "Compare channel revenue under different attribution rules and see whether model choice changes the story."
    )
    st.page_link("pages/1_Attribution_Comparison.py", label="Open Attribution Comparison")
with workflow[1]:
    st.markdown(
        "Review objective-level funnel completion and weekly cohort retention to understand where users drop off."
    )
    st.page_link("pages/2_Funnel_and_Cohort.py", label="Open Funnel and Cohort")
with workflow[2]:
    st.markdown(
        "Ask questions against governed MetricFlow metrics and inspect the generated SQL for auditability."
    )
    st.page_link("pages/3_Ask_The_Data.py", label="Open Ask The Data")

st.info(
    "Design principle: the natural-language assistant uses governed MetricFlow metrics instead of free-form text-to-SQL, "
    "so answers are tied to the same definitions used by the dashboard."
)
