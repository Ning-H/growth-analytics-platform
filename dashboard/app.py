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
      <p>Measure which campaigns, channels, and customer journeys actually drive users from first
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
      Growth teams rarely have one clean funnel. A mobile app campaign may need
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

st.markdown(
    """
    <div class="panel">
      <div class="label">Example scenario</div>
      This demo uses TikTok-style paid media journeys as the example event source, but the
      architecture applies to any growth platform, advertiser dataset, marketplace, ecommerce
      business, subscription product, or app-install funnel.
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
        "A Python simulator creates synthetic paid-media journeys for multiple objectives, channels, campaigns, devices, countries, and conversion types.",
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
st.markdown(
    """
    <style>
      body { margin: 0; font-family: Inter, Arial, sans-serif; color: #15171a; }
      .arch-wrap {
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 18px;
        color: #15171a;
        background:
          radial-gradient(circle at top left, rgba(37,244,238,.16), transparent 30%),
          radial-gradient(circle at bottom right, rgba(254,44,85,.13), transparent 32%),
          #ffffff;
      }
      .arch-lede {
        display: flex;
        justify-content: space-between;
        gap: 16px;
        align-items: flex-start;
        margin-bottom: 16px;
      }
      .arch-lede h3 {
        margin: 0 0 6px 0;
        font-size: 20px;
      }
      .arch-lede p {
        margin: 0;
        color: #667085;
        font-size: 13px;
        line-height: 1.45;
        max-width: 760px;
      }
      .arch-pill {
        flex: 0 0 auto;
        display: inline-block;
        padding: 7px 10px;
        border-radius: 999px;
        background: #010101;
        color: #ffffff;
        font-size: 12px;
        font-weight: 800;
      }
      .pipeline {
        display: grid;
        grid-template-columns: 1fr;
        gap: 10px;
      }
      .arch-scroll {
        max-height: 560px;
        overflow-y: auto;
        padding: 2px 10px 2px 2px;
        border-radius: 8px;
        scrollbar-color: #25F4EE #f3f4f6;
        scrollbar-width: thin;
      }
      .arch-scroll::-webkit-scrollbar { width: 10px; }
      .arch-scroll::-webkit-scrollbar-track {
        background: #f3f4f6;
        border-radius: 999px;
      }
      .arch-scroll::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #25F4EE, #FE2C55);
        border-radius: 999px;
      }
      .arch-node {
        position: relative;
        min-height: 92px;
        border: 1px solid #d9dee7;
        border-left: 5px solid #25F4EE;
        border-radius: 8px;
        padding: 13px 16px 12px 16px;
        background: rgba(255,255,255,.94);
        box-shadow: 0 8px 22px rgba(16,24,40,.06);
        display: grid;
        grid-template-columns: 48px minmax(180px, 1.1fr) minmax(240px, 1.5fr) minmax(150px, .8fr);
        gap: 14px;
        align-items: center;
        transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease, background .16s ease;
      }
      .arch-node:hover {
        transform: translateX(4px);
        border-color: #25F4EE;
        background: #fbfeff;
        box-shadow: 0 14px 30px rgba(16,24,40,.12);
        z-index: 5;
      }
      .arch-node.red { border-left-color: #FE2C55; }
      .arch-node.black { border-left-color: #010101; }
      .step-num {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: grid;
        place-items: center;
        color: #010101;
        background: #25F4EE;
        font-weight: 900;
        font-size: 14px;
      }
      .arch-node.red .step-num { background: #FE2C55; color: #fff; }
      .arch-node.black .step-num { background: #010101; color: #fff; }
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
      .io {
        color: #344054;
        font-size: 12px;
        line-height: 1.45;
      }
      .io b {
        color: #111827;
      }
      .arch-stat {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 999px;
        background: #f3f4f6;
        color: #111827;
        font-size: 11px;
        font-weight: 700;
        width: fit-content;
      }
      .arch-details {
        grid-column: 2 / 5;
        max-height: 0;
        overflow: hidden;
        padding: 0 12px;
        border: 0 solid #dbeafe;
        border-radius: 8px;
        background: #f8fafc;
        color: #374151;
        font-size: 12px;
        line-height: 1.42;
        transition: max-height .18s ease, padding .18s ease, border-width .18s ease;
      }
      .arch-node:hover .arch-details {
        max-height: 150px;
        padding: 10px 12px;
        border-width: 1px;
      }
      .flow-arrow {
        text-align: center;
        color: #010101;
        font-size: 20px;
        line-height: 1;
        opacity: .45;
      }
      .arch-caption {
        margin-top: 14px;
        color: #667085;
        font-size: 12px;
      }
      @media (max-width: 900px) {
        .arch-lede { display: block; }
        .arch-pill { margin-top: 10px; }
        .arch-node {
          grid-template-columns: 42px 1fr;
        }
        .arch-scroll { max-height: 620px; }
        .io, .arch-stat, .arch-details {
          grid-column: 2 / 3;
        }
      }
    </style>
    <div class="arch-wrap">
      <div class="arch-lede">
        <div>
          <h3>End-to-end data flow</h3>
          <p>Read this top to bottom. Each numbered step consumes the output of the previous step and produces the next layer used by the dashboard.</p>
        </div>
        <div class="arch-pill">Hover on a step for details</div>
      </div>
      <div class="arch-caption" style="margin: -4px 0 12px 0;">Scroll inside this box to follow the pipeline from source data to dashboard.</div>
      <div class="arch-scroll">
      <div class="pipeline">
        <div class="arch-node">
          <div class="step-num">1</div>
          <div>
            <div class="arch-title">Define Growth Objectives</div>
            <div class="arch-sub">App, commerce, lead, subscription, marketplace, awareness, offline.</div>
          </div>
          <div class="io"><b>Input:</b> campaign objective rules<br><b>Output:</b> objective-specific funnel definitions</div>
          <div class="arch-stat" title="app_install, ecommerce_purchase, lead_generation, subscription, marketplace_order, brand_awareness, offline_conversion">7 objectives</div>
          <div class="arch-details">Objectives: app install, ecommerce purchase, lead generation, subscription, marketplace order, brand awareness, and offline conversion. Each objective has its own funnel steps and conversion rates.</div>
        </div>
        <div class="flow-arrow">↓</div>
        <div class="arch-node red">
          <div class="step-num">2</div>
          <div>
            <div class="arch-title">Generate Dummy Journeys</div>
            <div class="arch-sub">Synthetic user paths across channels, campaigns, devices, countries, and conversion values.</div>
          </div>
          <div class="io"><b>Input:</b> simulator config + seeded random behavior<br><b>Output:</b> chronological user events</div>
          <div class="arch-stat" title="10,000 simulated users over a 30-day historical window">10k users / 30 days</div>
          <div class="arch-details">The dummy data is generated from configurable conversion rates, objective distribution, channel shares, ad spend, time gaps, and cross-channel touchpoint behavior.</div>
        </div>
        <div class="flow-arrow">↓</div>
        <div class="arch-node">
          <div class="step-num">3</div>
          <div>
            <div class="arch-title">Publish Raw Events To Kafka</div>
            <div class="arch-sub">Topics for impressions, clicks, installs, signups, purchases, leads, and more.</div>
          </div>
          <div class="io"><b>Input:</b> generated events<br><b>Output:</b> raw event topics by event family</div>
          <div class="arch-stat" title="Topics include impressions, video views, clicks, engagements, landing pages, installs, signups, activations, commerce, leads, subscriptions, marketplace, and offline conversions.">13 topics</div>
          <div class="arch-details">Topics include ad impressions, video views, clicks, engagements, landing page views, app installs, signups, activations, commerce, leads, subscriptions, marketplace, and offline conversions.</div>
        </div>
        <div class="flow-arrow">↓</div>
        <div class="arch-node black">
          <div class="step-num">4</div>
          <div>
            <div class="arch-title">Process Streams With PySpark</div>
            <div class="arch-sub">Parse JSON, enforce schemas, add ingestion metadata, and checkpoint offsets.</div>
          </div>
          <div class="io"><b>Input:</b> Kafka topics<br><b>Output:</b> parsed bronze-ready event frames</div>
          <div class="arch-stat" title="Structured Streaming parses schemas, keeps Kafka offsets, adds metadata, and writes recoverably.">streaming ingestion</div>
          <div class="arch-details">Spark handles schema enforcement, event timestamps, Kafka offsets, and the deterministic device-to-user identity mapping job.</div>
        </div>
        <div class="flow-arrow">↓</div>
        <div class="arch-node">
          <div class="step-num">5</div>
          <div>
            <div class="arch-title">Land Bronze Data In BigQuery</div>
            <div class="arch-sub">Raw warehouse tables preserve event payloads and ingestion metadata.</div>
          </div>
          <div class="io"><b>Input:</b> parsed Spark streams<br><b>Output:</b> partitioned raw event tables</div>
          <div class="arch-stat" title="Raw BigQuery dataset: bronze_events_union plus per-event-family bronze tables and device_to_user mapping.">growth_raw</div>
          <div class="arch-details">Bronze is intentionally close to source data. It supports backfills, schema checks, and row-count reconciliation against Kafka.</div>
        </div>
        <div class="flow-arrow">↓</div>
        <div class="arch-node red">
          <div class="step-num">6</div>
          <div>
            <div class="arch-title">Build Silver + Gold Models</div>
            <div class="arch-sub">Clean events, resolve users, build sessions, facts, dimensions, funnels, cohorts.</div>
          </div>
          <div class="io"><b>Input:</b> bronze tables<br><b>Output:</b> analysis-ready dbt marts</div>
          <div class="arch-stat" title="Includes staging, unified events, identity resolution, sessions, user/campaign/channel/date dimensions, touchpoints, conversions, user events, attribution, funnel, and cohort marts.">15+ marts</div>
          <div class="arch-details">Models include staging, unified events, identity resolution, sessions, user/campaign/channel/date dimensions, touchpoints, conversions, user events, attribution, funnel, and cohort tables.</div>
        </div>
        <div class="flow-arrow">↓</div>
        <div class="arch-node">
          <div class="step-num">7</div>
          <div>
            <div class="arch-title">Assign Attribution Credit</div>
            <div class="arch-sub">First-touch, last-touch, linear, time-decay, and position-based rules.</div>
          </div>
          <div class="io"><b>Input:</b> touchpoints + conversions<br><b>Output:</b> credited revenue and conversion facts</div>
          <div class="arch-stat" title="first-touch, last-touch, linear, time-decay, position-based">5 models</div>
          <div class="arch-details">Attribution models: first-touch, last-touch, linear, 7-day half-life time-decay, and 40/20/40 position-based. Tests validate credit sums to one per conversion.</div>
        </div>
        <div class="flow-arrow">↓</div>
        <div class="arch-node black">
          <div class="step-num">8</div>
          <div>
            <div class="arch-title">Define Governed Metrics</div>
            <div class="arch-sub">Canonical DAU, CAC, ROAS, retention, attributed revenue, and funnel conversion.</div>
          </div>
          <div class="io"><b>Input:</b> dbt marts<br><b>Output:</b> reusable metric definitions</div>
          <div class="arch-stat" title="Includes DAU, WAU, MAU, signups, conversions, conversion value, spend, retention, CAC, ROAS, and attributed revenue variants.">34 metrics</div>
          <div class="arch-details">Metrics include active users, signups, conversions, conversion value, spend, retention, CAC, ROAS, attributed conversions, and attributed revenue by model.</div>
        </div>
        <div class="flow-arrow">↓</div>
        <div class="arch-node">
          <div class="step-num">9</div>
          <div>
            <div class="arch-title">Answer Questions With LLM</div>
            <div class="arch-sub">OpenAI selects governed metrics rather than inventing raw SQL.</div>
          </div>
          <div class="io"><b>Input:</b> analyst question + metric catalog<br><b>Output:</b> MetricFlow query and auditable SQL</div>
          <div class="arch-stat" title="The assistant returns the governed metric, data preview, and generated MetricFlow SQL.">auditable SQL</div>
          <div class="arch-details">The assistant routes natural language to MetricFlow queries and exposes generated SQL so the answer can be inspected.</div>
        </div>
        <div class="flow-arrow">↓</div>
        <div class="arch-node red">
          <div class="step-num">10</div>
          <div>
            <div class="arch-title">Explore In Dashboard</div>
            <div class="arch-sub">Attribution comparison, funnel/cohort analysis, and natural-language exploration.</div>
          </div>
          <div class="io"><b>Input:</b> governed metrics and generated SQL<br><b>Output:</b> product analytics decisions</div>
          <div class="arch-stat" title="Attribution comparison, funnel and cohort analysis, Ask The Data.">3 workflows</div>
          <div class="arch-details">Workflows: Attribution Comparison for channel credit, Funnel and Cohort for drop-off and retention, and Ask The Data for governed natural-language exploration.</div>
        </div>
      </div>
      </div>
      <div class="arch-caption">The sequence runs top to bottom. Hover over any step to expand implementation details.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Project Highlights")
highlight_cols = st.columns(2)
with highlight_cols[0]:
    st.markdown(
        """
        - Models multiple growth objectives instead of assuming every product has the same funnel.
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
st.markdown(
    """
    <style>
      .product-button {
        display: inline-block;
        margin-top: 10px;
        padding: 10px 14px;
        border-radius: 8px;
        background: #010101;
        color: #ffffff !important;
        font-weight: 800;
        text-decoration: none !important;
        border: 1px solid #010101;
        box-shadow: 4px 4px 0 #25F4EE;
        transition: transform .14s ease, box-shadow .14s ease;
      }
      .product-button:hover {
        transform: translate(2px, 2px);
        box-shadow: 2px 2px 0 #FE2C55;
      }
    </style>
    """,
    unsafe_allow_html=True,
)
workflow = st.tabs(["1. Diagnose channel credit", "2. Find funnel drop-off", "3. Ask governed metrics"])
with workflow[0]:
    st.markdown(
        "Compare channel revenue under different attribution rules and see whether model choice changes the story."
    )
    st.markdown(
        '<a class="product-button" href="/Attribution_Comparison" target="_self">Open Attribution Comparison</a>',
        unsafe_allow_html=True,
    )
with workflow[1]:
    st.markdown(
        "Review objective-level funnel completion and weekly cohort retention to understand where users drop off."
    )
    st.markdown(
        '<a class="product-button" href="/Funnel_and_Cohort" target="_self">Open Funnel and Cohort</a>',
        unsafe_allow_html=True,
    )
with workflow[2]:
    st.markdown(
        "Ask questions against governed MetricFlow metrics and inspect the generated SQL for auditability."
    )
    st.markdown(
        '<a class="product-button" href="/Ask_The_Data" target="_self">Open Ask The Data</a>',
        unsafe_allow_html=True,
    )

st.info(
    "Design principle: the natural-language assistant uses governed MetricFlow metrics instead of free-form text-to-SQL, "
    "so answers are tied to the same definitions used by the dashboard."
)
