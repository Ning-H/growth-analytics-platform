from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from nl_interface.metricflow_tool import MetricFlowToolError, list_metrics, query_metric


load_dotenv()


REFUSAL = (
    "I can only answer using governed MetricFlow metrics. I cannot write raw SQL or "
    "invent metric definitions."
)


@dataclass(frozen=True)
class QueryPlan:
    metric_name: str
    group_by: list[str]
    order_by: str | None = None
    limit: int | None = 10
    needs_clarification: str | None = None


def _contains_raw_sql_request(question: str) -> bool:
    lowered = question.lower()
    return any(
        phrase in lowered
        for phrase in [
            "write sql",
            "raw sql",
            "select *",
            "sql query",
            "query the table directly",
        ]
    )


def plan_question(question: str) -> QueryPlan:
    """Small deterministic router used for eval and as a guardrail around the LLM."""
    q = question.lower()

    if "cac" in q and not any(model in q for model in ["first", "last", "linear", "time", "position"]):
        return QueryPlan(
            metric_name="cac_last_touch",
            group_by=[],
            needs_clarification="Did you mean CAC by first-touch, last-touch, linear, time-decay, or position-based attribution?",
        )

    if "dau" in q or "daily active" in q:
        return QueryPlan("dau", ["metric_time"], limit=7)
    if "wau" in q or "weekly active" in q:
        return QueryPlan("wau", ["metric_time"], limit=8)
    if "mau" in q or "monthly active" in q:
        return QueryPlan("mau", ["metric_time"], limit=6)
    if "retention" in q:
        return QueryPlan("retention_rate", ["cohort_week__weeks_since_signup"], limit=10)
    if "signup" in q and "activation" in q and ("rate" in q or "conversion" in q):
        return QueryPlan("signup_to_activation_rate", ["event__channel"], limit=10)
    if "signup" in q:
        return QueryPlan("new_signups", ["event__channel"], limit=10)
    if "funnel" in q or "drop" in q:
        return QueryPlan("funnel_step_users", ["funnel_completion__objective", "funnel_completion__step_name"], limit=20)

    attribution_group = {
        "first": ("attributed_revenue_first_touch", "attribution_record__channel"),
        "last": ("attributed_revenue_last_touch", "attribution_record_last_touch__channel"),
        "linear": ("attributed_revenue_linear", "attribution_record_linear__channel"),
        "time": ("attributed_revenue_time_decay", "attribution_record_time_decay__channel"),
        "decay": ("attributed_revenue_time_decay", "attribution_record_time_decay__channel"),
        "position": ("attributed_revenue_position_based", "attribution_record_position_based__channel"),
    }
    if "revenue" in q or "roas" in q:
        for key, (metric, dimension) in attribution_group.items():
            if key in q:
                if "roas" in q:
                    metric = metric.replace("attributed_revenue", "roas")
                    return QueryPlan(metric, [], limit=10)
                return QueryPlan(metric, [dimension], limit=10)
        return QueryPlan("conversion_value", ["conversion__objective"], limit=10)

    if "conversion" in q:
        if "time" in q or "decay" in q:
            return QueryPlan("attributed_conversions_time_decay", ["attribution_record_time_decay__channel"], limit=10)
        if "last" in q:
            return QueryPlan("attributed_conversions_last_touch", ["attribution_record_last_touch__channel"], limit=10)
        if "first" in q:
            return QueryPlan("attributed_conversions_first_touch", ["attribution_record__channel"], limit=10)
        return QueryPlan("conversions", ["conversion__objective"], limit=10)

    if "spend" in q:
        return QueryPlan("total_spend", ["campaign_spend_day__channel"], limit=10)

    return QueryPlan(
        metric_name="dau",
        group_by=["metric_time"],
        needs_clarification=(
            "I am not sure which governed metric you want. Try asking about DAU, signups, "
            "attributed revenue, CAC, ROAS, funnel step users, or retention."
        ),
    )


def _summarize_data(metric_name: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return f"No rows returned for `{metric_name}`."
    preview = rows[:5]
    return f"`{metric_name}` returned {len(rows)} rows. Preview: {preview}"


def _openai_answer(question: str, result: dict[str, Any]) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _summarize_data(result["metric_name"], result["data"])

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    prompt = (
        "You are a growth analytics assistant. Explain the MetricFlow query result in plain "
        "business language. Do not write SQL. Do not invent metrics. Be concise.\n\n"
        f"Question: {question}\n"
        f"Metric: {result['metric_name']}\n"
        f"Group by: {result['group_by']}\n"
        f"Rows: {json.dumps(result['data'][:10], default=str)}"
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You answer only from governed MetricFlow results."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    return response.choices[0].message.content or _summarize_data(result["metric_name"], result["data"])


def answer_question(question: str, use_openai: bool = True) -> dict[str, Any]:
    if _contains_raw_sql_request(question):
        return {
            "answer": REFUSAL,
            "metric_used": None,
            "data_preview": [],
            "underlying_sql": "",
            "needs_clarification": None,
        }

    plan = plan_question(question)
    if plan.needs_clarification:
        return {
            "answer": plan.needs_clarification,
            "metric_used": plan.metric_name,
            "data_preview": [],
            "underlying_sql": "",
            "needs_clarification": plan.needs_clarification,
            "planned_group_by": plan.group_by,
        }

    try:
        result = query_metric(
            plan.metric_name,
            group_by=plan.group_by,
            order_by=plan.order_by,
            limit=plan.limit,
        )
    except MetricFlowToolError as error:
        return {
            "answer": f"{REFUSAL} MetricFlow error: {error}",
            "metric_used": plan.metric_name,
            "data_preview": [],
            "underlying_sql": "",
            "needs_clarification": None,
            "planned_group_by": plan.group_by,
        }

    answer = _openai_answer(question, result) if use_openai else _summarize_data(plan.metric_name, result["data"])
    return {
        "answer": answer,
        "metric_used": plan.metric_name,
        "data_preview": result["data"][:10],
        "underlying_sql": result["query_sql"],
        "needs_clarification": None,
        "planned_group_by": plan.group_by,
    }


def chat() -> None:
    print("Growth Analytics NL Interface. Type 'exit' to quit.")
    while True:
        question = input("> ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        print(json.dumps(answer_question(question), indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask governed MetricFlow metrics in natural language.")
    parser.add_argument("question", nargs="*", help="Question to ask. Omit for interactive chat.")
    parser.add_argument("--no-openai", action="store_true", help="Skip OpenAI answer synthesis.")
    parser.add_argument("--list-metrics", action="store_true", help="List governed metric catalog.")
    args = parser.parse_args()

    if args.list_metrics:
        print(json.dumps(list_metrics(), indent=2))
        return
    if args.question:
        print(json.dumps(answer_question(" ".join(args.question), use_openai=not args.no_openai), indent=2))
        return
    chat()


if __name__ == "__main__":
    main()
