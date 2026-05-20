from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from nl_interface.agent import answer_question, plan_question


EVAL_PATH = Path(__file__).with_name("golden_questions.yml")


def _load_cases() -> list[dict[str, Any]]:
    with EVAL_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)["questions"]


def score_case(case: dict[str, Any]) -> dict[str, Any]:
    question = case["question"]

    if case.get("expected_refusal"):
        result = answer_question(question, use_openai=False)
        passed = result["metric_used"] is None and "cannot write raw SQL" in result["answer"]
        return {
            "question": question,
            "passed": passed,
            "expected": "refusal",
            "actual": result,
        }

    plan = plan_question(question)
    expected_group_by = case.get("expected_group_by", [])
    passed = (
        plan.metric_name == case["expected_metric"]
        and plan.group_by == expected_group_by
        and bool(plan.needs_clarification) == bool(case.get("expected_clarification", False))
    )
    return {
        "question": question,
        "passed": passed,
        "expected_metric": case["expected_metric"],
        "actual_metric": plan.metric_name,
        "expected_group_by": expected_group_by,
        "actual_group_by": plan.group_by,
        "expected_clarification": bool(case.get("expected_clarification", False)),
        "actual_clarification": bool(plan.needs_clarification),
    }


def main() -> None:
    results = [score_case(case) for case in _load_cases()]
    passed = sum(1 for result in results if result["passed"])
    total = len(results)
    confusion = Counter(
        (result.get("expected_metric", result.get("expected")), result.get("actual_metric", "refusal"))
        for result in results
    )
    print(json.dumps({"pass_rate": passed / total, "passed": passed, "total": total}, indent=2))
    print("Confusion matrix:")
    for (expected, actual), count in sorted(confusion.items()):
        print(f"  expected={expected} actual={actual}: {count}")
    failures = [result for result in results if not result["passed"]]
    if failures:
        print(json.dumps(failures, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
