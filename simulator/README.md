# Event Simulator

The simulator generates objective-specific TikTok Ads journeys from `simulator/config.yml`.

Supported campaign objectives:

- `app_install`
- `ecommerce_purchase`
- `lead_generation`
- `subscription`
- `marketplace_order`
- `brand_awareness`
- `offline_conversion`

Run a dry summary without Kafka:

```bash
uv run python -m simulator.events --dry-run --n-users 1000
```

Publish a historical backfill to local Kafka:

```bash
make kafka-up
make simulate-historical
```

Publish in live mode:

```bash
make simulate-live
```

Events are serialized as JSON for portfolio readability and easy local debugging. A production version would use Avro or Protobuf with a schema registry, explicit compatibility rules, and replay-safe producer semantics.
