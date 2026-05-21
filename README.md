# Growth Analytics Platform

A warehouse-first growth analytics platform for multi-objective advertising journeys: attribution, funnel/cohort analysis, governed metrics, and natural-language data discovery.

> Current status: end-to-end local build is implemented. The Streamlit dashboard is deployable on Streamlit Community Cloud with BigQuery-backed hosted metrics.

## Problem Statement

Growth teams rarely have one clean funnel. A mobile app campaign may need `impression -> click -> install -> signup -> activation -> purchase`. An ecommerce campaign may skip install and go directly from ad click to product page to purchase. Lead generation, subscription, marketplace, awareness, and offline-sales campaigns each produce different conversion paths.

This project simulates those raw journeys, resolves identity across anonymous and logged-in events, models the data in a warehouse, and lets teams compare attribution, funnel drop-off, cohorts, CAC, ROAS, and governed metric answers.

The demo uses TikTok-style paid media journeys as the example event source, but the design is platform-neutral: the same pattern applies to any paid-growth channel, marketplace, ecommerce business, subscription product, or app-install funnel.

## What Is Built

- Multi-objective event simulator for app install, ecommerce purchase, lead generation, subscription, marketplace order, brand awareness, and offline conversion flows.
- Kafka topics for raw event families such as impressions, clicks, installs, signups, activations, purchases, leads, subscriptions, marketplace events, and offline conversions.
- PySpark Structured Streaming jobs for bronze ingestion and deterministic identity mapping.
- BigQuery warehouse with raw bronze tables, dbt silver models, and gold marts.
- Five attribution models: first-touch, last-touch, linear, 7-day half-life time-decay, and 40/20/40 position-based.
- Funnel and cohort marts separated from attribution marts.
- dbt MetricFlow semantic layer with 34 governed metrics.
- Natural-language interface that routes questions to governed metrics instead of free-form text-to-SQL.
- Streamlit dashboard with Attribution Comparison, Funnel and Cohort, and Ask The Data pages.

## Architecture

```mermaid
flowchart TD
    A["Objective-specific journey rules"] --> B["Python simulator"]
    B --> C["Kafka raw event topics"]
    C --> D["PySpark Structured Streaming"]
    D --> E["BigQuery bronze tables"]
    E --> F["dbt staging and intermediate models"]
    F --> G["dbt gold facts and dimensions"]
    G --> H["Attribution, funnel, and cohort marts"]
    H --> I["MetricFlow semantic layer"]
    I --> J["Natural-language metric agent"]
    I --> K["Streamlit dashboard"]
    H --> L["Hosted BigQuery fallback queries"]
    L --> K
```

The hosted Streamlit app still uses the same governed metric names and dbt marts. Because MetricFlow CLI currently has a runtime issue on Streamlit Cloud, the dashboard includes a BigQuery fallback for hosted metrics while preserving the same metric contract and showing auditable SQL.

## Tech Stack

| Layer | Tooling |
|---|---|
| Language/runtime | Python 3.13, uv |
| Event generation | Custom Python simulator |
| Streaming log | Kafka + Kafka UI |
| Stream processing | PySpark Structured Streaming |
| Warehouse | BigQuery |
| Transformation | dbt Core |
| Semantic layer | dbt MetricFlow YAML |
| NL interface | OpenAI API + governed metric routing |
| Dashboard | Streamlit |
| Hosted demo path | Streamlit Community Cloud |

## Dashboard Pages

- **Home:** product problem, data flow, interactive architecture, and project highlights.
- **Attribution Comparison:** compares channel revenue under all five attribution models and highlights where model choice changes channel credit.
- **Funnel and Cohort:** objective-specific funnel completion, step drop-off, weekly signup cohorts, and retention curves.
- **Ask The Data:** chat-style interface that answers using governed metrics and exposes the generated SQL.

## Metrics

Metric definitions live in version-controlled YAML under `dbt_project/models/metrics/`, with business explanations in `docs/metrics_catalog.md`.

Implemented metric groups:

- Active users: `dau`, `wau`, `mau`
- Acquisition and conversion: `new_signups`, `activated_users`, `purchasing_users`, `conversions`, `conversion_value`
- Spend: `total_spend`
- Funnel/cohort: `funnel_step_users`, `retained_users`, `cohort_users`, `retention_rate`, `signup_to_activation_rate`
- Attribution: attributed conversions and revenue for first-touch, last-touch, linear, time-decay, and position-based models
- Efficiency: CAC and ROAS variants for each attribution model

## Local Quick Start

Prerequisites:

- Python 3.13
- Docker Desktop
- GCP project with BigQuery datasets `growth_raw` and `growth_analytics`
- Service-account JSON with BigQuery access
- OpenAI API key for the NL answer synthesis page

```bash
make setup
cp .env.example .env
```

Fill `.env`:

```bash
GCP_PROJECT_ID=your-project-id
GCP_SERVICE_ACCOUNT_JSON_PATH=/absolute/path/to/service-account.json
BIGQUERY_DATASET_RAW=growth_raw
BIGQUERY_DATASET_ANALYTICS=growth_analytics
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

Generate and load data:

```bash
make kafka-up
make simulate-historical
make backfill-bigquery
make dbt-deps
make dbt-seed
make dbt-run
make dbt-test
```

Run the dashboard:

```bash
make dashboard
```

Open `http://localhost:8501`.

## Streamlit Cloud Deployment

Use these app settings:

- Main file path: `dashboard/app.py`
- Python version: `3.13`
- Dependency file: `dashboard/requirements.txt`

Use Streamlit secrets for cloud credentials. Do not paste a local file path into `GCP_SERVICE_ACCOUNT_JSON_PATH`; that path only exists on your laptop. In Streamlit Cloud, put the JSON content into `GCP_SERVICE_ACCOUNT_JSON`.

```toml
GCP_PROJECT_ID = "your-project-id"
BIGQUERY_DATASET_RAW = "growth_raw"
BIGQUERY_DATASET_ANALYTICS = "growth_analytics"
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"

GCP_SERVICE_ACCOUNT_JSON = """
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
  "client_email": "...",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
"""
```

More details: `docs/streamlit_cloud_deploy.md`.

## Common Commands

```bash
make simulate-dry-run      # generate sample events without Kafka
make simulate-historical   # publish historical events to Kafka
make stream-up             # start Spark bronze + identity jobs
make stream-down           # stop local Spark jobs and clear checkpoints
make backfill-bigquery     # load generated data directly to BigQuery for demo use
make dbt-run               # build warehouse models
make dbt-test              # run dbt tests
make mf-validate           # validate MetricFlow configs
make mf-query-test         # run sample MetricFlow queries
make nl-eval               # run golden-question NL eval
make dashboard             # start Streamlit
make test                  # run Python tests
```

## Repository Structure

```text
growth-analytics-platform/
├── simulator/                 # Multi-objective event generator
├── streaming/                 # PySpark Kafka -> BigQuery jobs
├── scripts/                   # BigQuery demo backfill utilities
├── dbt_project/               # dbt models, seeds, tests, metrics, semantic models
├── nl_interface/              # Governed metric agent and eval harness
├── dashboard/                 # Streamlit app and hosted requirements
├── docs/                      # Data model, metrics catalog, deployment notes
├── infra/                     # Deployment placeholders
├── docker-compose.yml         # Local Kafka stack
├── Makefile                   # Local workflow commands
└── pyproject.toml             # Python 3.13 project dependencies
```

## Design Choices

- **Warehouse-first:** raw events are preserved in BigQuery, then cleaned and modeled through dbt.
- **Multi-objective funnels:** campaign objectives define different conversion paths instead of forcing every journey into one app-install funnel.
- **Auditable attribution:** every attribution model outputs conversion-level credit fractions and attributed revenue.
- **Governed metrics:** MetricFlow YAML is the canonical metric contract.
- **LLM over metrics, not SQL:** the assistant selects governed metrics and dimensions; it does not invent metric definitions or write arbitrary SQL.
- **Cloud fallback:** hosted dashboard queries can bypass a MetricFlow CLI runtime bug by querying the same dbt marts directly in BigQuery.

## Validation Snapshot

Recent local validation:

- Python tests: `6 passed`
- dbt build path implemented for bronze, silver, gold, attribution, funnel, and cohort layers
- Metric catalog: 34 metrics
- Attribution models: 5
- Dashboard pages: 3 feature pages plus home

## Project Docs

- `docs/data_model.md` — event taxonomy, identity model, schemas, attribution/funnel/cohort design
- `docs/dbt_transformations.md` — dbt silver and gold transformation overview
- `docs/attribution_methodology.md` — attribution rules and worked examples
- `docs/metrics_catalog.md` — business meaning, formulas, and caveats for metrics
- `docs/nl_interface_design.md` — governed natural-language interface design
- `docs/streamlit_cloud_deploy.md` — Streamlit Cloud setup and secrets
