# Natural-Language Interface

The NL interface answers business questions by selecting governed MetricFlow metrics. It does not generate raw SQL.

## Commands

```bash
make nl-chat
make nl-eval
```

You can also ask one question directly:

```bash
uv run python -m nl_interface.agent "What was our DAU last week?"
```

## Guardrails

- Metrics must exist in the MetricFlow catalog.
- Dimensions must be valid for the selected metric.
- Raw SQL requests are refused.
- Every successful answer returns generated MetricFlow SQL for auditability.
