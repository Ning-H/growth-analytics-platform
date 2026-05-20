from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from confluent_kafka import Producer

from simulator.user_journey import EVENT_TOPICS, JourneyGenerator, SimulationConfig, summarize_events


DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.yml")


def delivery_report(error: Any, message: Any) -> None:
    if error is not None:
        raise RuntimeError(f"Delivery failed for record {message.key()}: {error}")


def create_producer(bootstrap_servers: str) -> Producer:
    return Producer(
        {
            "bootstrap.servers": bootstrap_servers,
            "client.id": "growth-analytics-simulator",
            "acks": "all",
        }
    )


def publish_events(events: list[dict[str, Any]], bootstrap_servers: str, live_rate: float | None = None) -> None:
    producer = create_producer(bootstrap_servers)
    delay = 1.0 / live_rate if live_rate and live_rate > 0 else 0.0

    for index, event in enumerate(events, start=1):
        topic = event.pop("topic")
        payload = json.dumps(event, sort_keys=True).encode("utf-8")
        key = event["device_id"].encode("utf-8")
        producer.produce(topic=topic, key=key, value=payload, callback=delivery_report)
        producer.poll(0)
        if delay:
            time.sleep(delay)
        if index % 1000 == 0:
            producer.flush()
            print(f"published {index:,} events")

    producer.flush()


def generate(config_path: Path, n_users: int | None = None) -> list[dict[str, Any]]:
    config = SimulationConfig.from_yaml(config_path)
    generator = JourneyGenerator(config)
    return generator.generate_all(n_users=n_users)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate TikTok Ads event streams.")
    parser.add_argument("--mode", choices=["historical", "live"], default="historical")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--n-users", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Generate and summarize without Kafka.")
    args = parser.parse_args()

    config = SimulationConfig.from_yaml(args.config)
    events = JourneyGenerator(config).generate_all(n_users=args.n_users)
    summary = summarize_events(events)
    print(json.dumps(summary, indent=2, sort_keys=True))

    if args.dry_run:
        return

    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    live_rate = float(config.raw["live_events_per_second"]) if args.mode == "live" else None
    publish_events(events, bootstrap_servers, live_rate=live_rate)
    print(f"published {len(events):,} events across {len(set(EVENT_TOPICS.values()))} topics")


if __name__ == "__main__":
    main()
