# dbt Transformations

The dbt layer turns raw TikTok Ads simulator events into warehouse-ready analytics tables.

## Layers

- Staging: cleans and deduplicates `growth_raw.bronze_events_union`, then exposes topic-family views.
- Intermediate: unifies events, resolves deterministic identity, and sessionizes users with a 30-minute inactivity window.
- Gold dimensions: users, campaigns, channels, and dates.
- Gold facts: user events, touchpoints, conversions, attribution, funnel completion, and cohort retention.

## Multi-Objective Design

The marts preserve `objective` throughout the model so app installs, commerce purchases, lead generation, subscriptions, marketplace orders, brand awareness, and offline conversions can use different funnel shapes while sharing one governed analytics layer.

## Run

```bash
make dbt-deps
make dbt-seed
make dbt-run
make dbt-test
```
