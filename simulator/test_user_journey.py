from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from simulator.events import generate
from simulator.user_journey import EVENT_TOPICS, SimulationConfig, summarize_events


CONFIG_PATH = Path(__file__).with_name("config.yml")


def test_generator_is_deterministic_for_same_seed() -> None:
    first = generate(CONFIG_PATH, n_users=100)
    second = generate(CONFIG_PATH, n_users=100)

    comparable_first = [
        (event["event_type"], event["objective"], event["device_id"], event["event_date"])
        for event in first
    ]
    comparable_second = [
        (event["event_type"], event["objective"], event["device_id"], event["event_date"])
        for event in second
    ]

    assert comparable_first == comparable_second


def test_events_are_chronological_per_device() -> None:
    events = generate(CONFIG_PATH, n_users=500)
    by_device: dict[str, list[str]] = defaultdict(list)
    for event in events:
        by_device[event["device_id"]].append(event["event_timestamp"])

    for timestamps in by_device.values():
        assert timestamps == sorted(timestamps)


def test_all_objectives_and_topics_are_represented() -> None:
    events = generate(CONFIG_PATH, n_users=3000)
    objectives = {event["objective"] for event in events}
    topics = {event["topic"] for event in events}

    expected_objectives = set(SimulationConfig.from_yaml(CONFIG_PATH).raw["objective_distribution"])
    assert objectives == expected_objectives
    assert {"ad_impressions", "ad_clicks", "commerce_events", "lead_events"}.issubset(topics)
    assert all(event["event_type"] in EVENT_TOPICS for event in events)


def test_core_conversion_rates_stay_close_to_config() -> None:
    events = generate(CONFIG_PATH, n_users=10000)
    config = SimulationConfig.from_yaml(CONFIG_PATH).raw
    counts_by_objective: dict[str, Counter[str]] = defaultdict(Counter)
    devices_by_objective: dict[str, set[str]] = defaultdict(set)

    for event in events:
        counts_by_objective[event["objective"]][event["event_type"]] += 1
        devices_by_objective[event["objective"]].add(event["device_id"])

    checks = [
        ("ecommerce_purchase", "purchase", "checkout_started", "checkout_started_to_purchase"),
        ("lead_generation", "lead_submit", "form_start", "form_start_to_lead_submit"),
        ("subscription", "subscription_started", "trial_started", "trial_started_to_subscription_started"),
        ("marketplace_order", "booking_or_order", "search_or_browse", "search_or_browse_to_booking_or_order"),
        ("offline_conversion", "offline_conversion", "call_or_directions", "call_or_directions_to_offline_conversion"),
    ]

    for objective, numerator_event, denominator_event, config_key in checks:
        denominator = counts_by_objective[objective][denominator_event]
        assert denominator > 0
        observed = counts_by_objective[objective][numerator_event] / denominator
        expected = config["objective_funnels"][objective]["conversion_rates"][config_key]
        assert abs(observed - expected) <= 0.15


def test_multi_touch_converters_exist_at_expected_rate() -> None:
    events = generate(CONFIG_PATH, n_users=10000)
    summary = summarize_events(events)

    assert summary["total_converters"] > 0
    assert 0.25 <= summary["multi_touch_converter_rate"] <= 0.50


def test_converters_have_cross_channel_touchpoint_paths() -> None:
    events = generate(CONFIG_PATH, n_users=10000)
    summary = summarize_events(events)

    assert summary["total_converters"] > 0
    assert summary["cross_channel_converter_rate"] >= 0.20
