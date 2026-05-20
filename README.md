# Growth Analytics Platform

Warehouse-first TikTok Ads growth analytics for multi-objective attribution, funnel/cohort analysis, audience quality, and governed natural-language metric discovery.

## What This Is

Growth Analytics Platform is a portfolio-grade data engineering project that simulates TikTok Ads advertiser journeys and turns them into trustworthy growth metrics. It supports multiple campaign objectives, including app installs, e-commerce purchases, subscriptions, lead generation, marketplace orders, brand awareness, and offline conversions.

The finished system is designed around a modern warehouse-first stack:

Python 3.13+ simulator -> Kafka -> PySpark Structured Streaming -> BigQuery -> dbt Core + MetricFlow -> OpenAI-powered data discovery -> Streamlit dashboard.

Current status: Phase 3 PySpark streaming ingestion to BigQuery bronze.

## Architecture

```mermaid
flowchart LR
    A["Python event simulator"] --> B["Kafka topics"]
    B --> C["PySpark Structured Streaming"]
    C --> D["BigQuery raw bronze"]
    D --> E["dbt silver and gold models"]
    E --> F["MetricFlow semantic layer"]
    F --> G["OpenAI NL interface"]
    F --> H["Streamlit dashboard"]
```

## Quick Start

```bash
make setup
cp .env.example .env
make kafka-up
make simulate-historical
make stream-up
```

Kafka UI runs at `http://localhost:8080`.

## Project Structure

```text
growth-analytics-platform/
├── simulator/
├── streaming/
├── dbt_project/
├── nl_interface/
├── dashboard/
├── infra/
└── docs/
```
