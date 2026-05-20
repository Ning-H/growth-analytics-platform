# Natural-Language Interface Design

The NL interface uses a text-to-metric design, not text-to-SQL.

The agent maps a user question to a governed MetricFlow metric and valid dimensions, executes MetricFlow, then asks OpenAI to explain the returned rows in business language. The LLM is not allowed to write SQL or invent metric definitions.

## Why Text-To-Metric

- Metric definitions are version-controlled in dbt YAML.
- MetricFlow validates available dimensions and join paths.
- Generated SQL is exposed for auditability.
- The same definitions power dashboards, analysts, and the LLM interface.

## Flow

```text
question -> guarded planner -> MetricFlow query -> generated SQL + rows -> OpenAI explanation
```

## Evaluation

`nl_interface/eval/golden_questions.yml` defines expected metrics, dimensions, and refusal behavior. `make nl-eval` runs the planner against those cases and reports pass rate plus a confusion matrix.
