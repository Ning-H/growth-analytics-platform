from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dashboard.components.data import MODEL_CONFIG, available_values, metric_query, revenue_by_model
from dashboard.components.layout import configure_page, page_intro, show_sql


MATERIAL_REVENUE_DELTA = 1.0


def example_attribution_shift() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"model": "First touch", "channel": "tiktok_ads", "credited_revenue": 100.00},
            {"model": "First touch", "channel": "google_ads", "credited_revenue": 0.00},
            {"model": "First touch", "channel": "email", "credited_revenue": 0.00},
            {"model": "Last touch", "channel": "tiktok_ads", "credited_revenue": 0.00},
            {"model": "Last touch", "channel": "google_ads", "credited_revenue": 0.00},
            {"model": "Last touch", "channel": "email", "credited_revenue": 100.00},
            {"model": "Linear", "channel": "tiktok_ads", "credited_revenue": 33.33},
            {"model": "Linear", "channel": "google_ads", "credited_revenue": 33.33},
            {"model": "Linear", "channel": "email", "credited_revenue": 33.33},
            {"model": "Time decay", "channel": "tiktok_ads", "credited_revenue": 14.00},
            {"model": "Time decay", "channel": "google_ads", "credited_revenue": 29.00},
            {"model": "Time decay", "channel": "email", "credited_revenue": 57.00},
            {"model": "Position based", "channel": "tiktok_ads", "credited_revenue": 40.00},
            {"model": "Position based", "channel": "google_ads", "credited_revenue": 20.00},
            {"model": "Position based", "channel": "email", "credited_revenue": 40.00},
        ]
    )


configure_page("Attribution Comparison")
page_intro(
    "Attribution Comparison",
    "See where channel credit changes when the same conversions are scored by different attribution rules.",
)

model = st.sidebar.selectbox("Attribution model", list(MODEL_CONFIG.keys()), index=3)
st.sidebar.caption("Filters are applied to returned governed MetricFlow results.")
channel_filter = "All"

config = MODEL_CONFIG[model]
with st.spinner("Loading attributed revenue by channel..."):
    result = metric_query(config["metric"], (config["dimension"],), limit=50)

with st.spinner("Comparing all attribution models..."):
    comparison = revenue_by_model()

if result.error:
    st.error(result.error)
elif result.data.empty:
    st.info("No attributed revenue rows returned for this model.")
else:
    selected = result.data.rename(columns={config["dimension"]: "channel", config["metric"]: "revenue"})
    channel_options = ["All", *available_values(selected, "channel")]
    channel_filter = st.sidebar.selectbox(
        "Channel",
        channel_options,
        help="These options come from the current query result, so filters cannot point at missing channels.",
    )
    if channel_filter != "All":
        selected = selected[selected["channel"].astype(str) == channel_filter]
        comparison = comparison[comparison["channel"].astype(str) == channel_filter]

    top = selected.sort_values("revenue", ascending=False).head(10) if not selected.empty else selected
    left, right = st.columns([1.5, 1])
    with left:
        st.subheader(f"Attributed Revenue By Channel: {model}")
        if top.empty:
            st.info("No rows match the current filter.")
        else:
            selected_chart = (
                alt.Chart(top)
                .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color="#25F4EE")
                .encode(
                    x=alt.X("revenue:Q", title="Attributed revenue"),
                    y=alt.Y("channel:N", sort="-x", title="Channel"),
                    tooltip=[
                        alt.Tooltip("channel:N", title="Channel"),
                        alt.Tooltip("revenue:Q", title="Revenue", format="$,.0f"),
                    ],
                )
                .properties(height=320)
            )
            st.altair_chart(selected_chart, use_container_width=True)
    with right:
        st.subheader("Selected Model Ranking")
        if top.empty:
            st.info("No rows returned.")
        else:
            ranking = top.copy()
            ranking["rank"] = ranking["revenue"].rank(method="dense", ascending=False).astype(int)
            ranking = ranking[["rank", "channel", "revenue"]].sort_values("rank")
            st.dataframe(ranking.style.format({"revenue": "${:,.0f}"}), hide_index=True, use_container_width=True)

    show_sql(result.sql)

st.divider()
st.subheader("Where Attribution Model Choice Changes Credit")

if comparison.empty:
    st.info("No attribution comparison rows match the current filters.")
else:
    pivot = comparison.pivot_table(index="channel", columns="model", values="revenue", aggfunc="sum").fillna(0)
    ranks = pivot.rank(method="dense", ascending=False).astype(int)
    selected_model_revenue = pivot[model]
    baseline = pivot["Last touch"] if "Last touch" in pivot.columns else selected_model_revenue
    selected_rank = ranks[model]
    baseline_rank = ranks["Last touch"] if "Last touch" in ranks.columns else selected_rank

    impact = pd.DataFrame(
        {
            "channel": pivot.index,
            f"{model} revenue": selected_model_revenue.to_numpy(),
            "last touch revenue": baseline.to_numpy(),
            "revenue change vs last touch": (selected_model_revenue - baseline).to_numpy(),
            f"{model} rank": selected_rank.to_numpy(),
            "rank change vs last touch": (baseline_rank - selected_rank).to_numpy(),
            "model sensitivity": (pivot.max(axis=1) - pivot.min(axis=1)).to_numpy(),
        }
    ).sort_values("model sensitivity", ascending=False)

    metric_cols = st.columns(3)
    total_selected = float(selected_model_revenue.sum()) if not selected_model_revenue.empty else 0.0
    total_sensitivity = float(impact["model sensitivity"].sum()) if not impact.empty else 0.0
    most_sensitive = (
        impact.iloc[0]["channel"]
        if not impact.empty and total_sensitivity > MATERIAL_REVENUE_DELTA
        else "No material shift"
    )
    metric_cols[0].metric(f"{model} revenue", f"${total_selected:,.0f}")
    metric_cols[1].metric("Total model sensitivity", f"${total_sensitivity:,.0f}")
    metric_cols[2].metric("Most sensitive channel", most_sensitive)

    if total_sensitivity <= MATERIAL_REVENUE_DELTA:
        st.markdown(
            """
            <div class="comparison-note">
            <b>No material model shift in this warehouse run.</b><br/>
            The attribution models are returning the same channel totals because the current generated
            conversions do not create enough cross-channel disagreement. This is useful as a data-quality
            diagnostic: the next simulator improvement should increase multi-channel journeys where first,
            middle, and closing touches come from different channels.
            </div>
            """,
            unsafe_allow_html=True,
        )
        example = example_attribution_shift()
        st.subheader("Example: Where Model Choice Would Change Credit")
        st.caption(
            "One $100 conversion path: TikTok impression → Google click → Email click → purchase."
        )
        example_chart = (
            alt.Chart(example)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("model:N", title="Attribution model"),
                y=alt.Y("credited_revenue:Q", title="Credited revenue"),
                color=alt.Color(
                    "channel:N",
                    scale=alt.Scale(
                        domain=["tiktok_ads", "google_ads", "email"],
                        range=["#25F4EE", "#111827", "#FE2C55"],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("model:N"),
                    alt.Tooltip("channel:N"),
                    alt.Tooltip("credited_revenue:Q", format="$,.2f"),
                ],
            )
            .properties(height=320)
        )
        st.altair_chart(example_chart, use_container_width=True)
    else:
        st.markdown(
            """
            <div class="comparison-note">
            <b>How to read this:</b> the top chart shows the selected attribution model. This section shows
            how much each channel's credit moves compared with last-touch, plus how sensitive each channel is
            across all five models.
            </div>
            """,
            unsafe_allow_html=True,
        )
        delta_chart = (
            alt.Chart(impact)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                x=alt.X("revenue change vs last touch:Q", title="Revenue change vs last-touch"),
                y=alt.Y("channel:N", sort="-x", title="Channel"),
                color=alt.condition(
                    alt.datum["revenue change vs last touch"] >= 0,
                    alt.value("#25F4EE"),
                    alt.value("#FE2C55"),
                ),
                tooltip=[
                    alt.Tooltip("channel:N"),
                    alt.Tooltip(f"{model} revenue:Q", format="$,.0f"),
                    alt.Tooltip("last touch revenue:Q", format="$,.0f"),
                    alt.Tooltip("revenue change vs last touch:Q", format="$,.0f"),
                    alt.Tooltip("rank change vs last touch:Q"),
                ],
            )
            .properties(height=320)
        )
        st.altair_chart(delta_chart, use_container_width=True)

    st.dataframe(
        impact.style.format(
            {
                f"{model} revenue": "${:,.0f}",
                "last touch revenue": "${:,.0f}",
                "revenue change vs last touch": "${:,.0f}",
                "model sensitivity": "${:,.0f}",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )

    with st.expander("Raw revenue matrix across all five models"):
        st.dataframe(pivot.style.format("${:,.0f}"), use_container_width=True)

    if {"First touch", "Last touch"}.issubset(pivot.columns):
        shift = (pivot["First touch"] - pivot["Last touch"]).sort_values(ascending=False)
        channel = shift.index[0]
        gap = pivot.loc[channel, "First touch"] - pivot.loc[channel, "Last touch"]
        if gap > 0:
            interpretation = "This suggests the channel is stronger at starting journeys than closing them."
        elif gap < 0:
            interpretation = "This suggests the channel is stronger near the closing touch than at initial discovery."
        else:
            interpretation = "This channel receives the same credit under first-touch and last-touch for the current data."
        st.markdown(
            f"""
            <div class="panel">
            <b>Insight</b><br/>
            {channel} receives ${pivot.loc[channel, "First touch"]:,.0f} under first-touch and
            ${pivot.loc[channel, "Last touch"]:,.0f} under last-touch attribution. {interpretation}
            </div>
            """,
            unsafe_allow_html=True,
        )
