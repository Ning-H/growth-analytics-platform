from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml


TOUCHPOINT_EVENTS = {"ad_impression", "video_view", "ad_click", "engagement"}
COMMERCE_EVENTS = {"product_view", "add_to_cart", "checkout_started", "purchase"}
LEAD_EVENTS = {"form_start", "lead_submit", "qualified_lead"}
SUBSCRIPTION_EVENTS = {"trial_started", "subscription_started", "renewal"}
MARKETPLACE_EVENTS = {"search_or_browse", "booking_or_order"}
OFFLINE_EVENTS = {"call_or_directions", "offline_conversion"}

EVENT_TOPICS = {
    "ad_impression": "ad_impressions",
    "video_view": "video_views",
    "ad_click": "ad_clicks",
    "engagement": "engagements",
    "landing_page_view": "landing_page_views",
    "app_install": "app_installs",
    "signup": "signups",
    "activation": "activations",
    "product_view": "commerce_events",
    "add_to_cart": "commerce_events",
    "checkout_started": "commerce_events",
    "purchase": "commerce_events",
    "repeat_purchase": "commerce_events",
    "form_start": "lead_events",
    "lead_submit": "lead_events",
    "qualified_lead": "lead_events",
    "trial_started": "subscription_events",
    "subscription_started": "subscription_events",
    "renewal": "subscription_events",
    "search_or_browse": "marketplace_events",
    "booking_or_order": "marketplace_events",
    "repeat_order": "marketplace_events",
    "call_or_directions": "offline_conversions",
    "offline_conversion": "offline_conversions",
}


@dataclass(frozen=True)
class SimulationConfig:
    raw: dict[str, Any]

    @classmethod
    def from_yaml(cls, path: str | Path) -> "SimulationConfig":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls(yaml.safe_load(handle))

    @property
    def seed(self) -> int:
        return int(self.raw.get("seed", 42))

    @property
    def n_users(self) -> int:
        return int(self.raw["n_users"])

    @property
    def simulation_days(self) -> int:
        return int(self.raw["simulation_days"])

    @property
    def start_at(self) -> datetime:
        value = self.raw.get("historical_start_date", "2026-04-01T00:00:00+00:00")
        return datetime.fromisoformat(value)


def weighted_choice(weights: dict[str, float], rng: random.Random) -> str:
    items = list(weights.items())
    total = sum(weight for _, weight in items)
    point = rng.random() * total
    cumulative = 0.0
    for item, weight in items:
        cumulative += weight
        if point <= cumulative:
            return item
    return items[-1][0]


class JourneyGenerator:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.rng = random.Random(config.seed)

    def generate_all(self, n_users: int | None = None) -> list[dict[str, Any]]:
        journeys = [self.generate_user_journey(index) for index in range(n_users or self.config.n_users)]
        events = [event for journey in journeys for event in journey]
        return sorted(events, key=lambda event: (event["event_timestamp"], event["event_id"]))

    def generate_user_journey(self, user_index: int) -> list[dict[str, Any]]:
        objective = weighted_choice(self.config.raw["objective_distribution"], self.rng)
        advertiser = self._advertiser_for_objective(objective)
        product_id = f"prod_{objective}_{self.rng.randint(1, 8):03d}"
        campaign_id = f"cmp_{objective}_{self.rng.randint(1, 12):03d}"
        ad_group_id = f"adg_{self.rng.randint(1, 30):03d}"
        creative_id = f"cr_{objective}_{self.rng.randint(1, 50):03d}"
        device_id = f"dev_{uuid.uuid5(uuid.NAMESPACE_DNS, f'device-{user_index}').hex[:16]}"
        user_id: str | None = None
        session_id = self._id("sess", 16)
        channel = weighted_choice(self.config.raw["channel_acquisition_share"], self.rng)
        audience_segment_id = self.rng.choice(self.config.raw["audience_segments"])
        targeting_tags = self._targeting_tags(objective)
        base_at = self.config.start_at + timedelta(
            seconds=self.rng.randint(0, self.config.simulation_days * 24 * 60 * 60)
        )

        context = {
            "advertiser_id": advertiser["advertiser_id"],
            "product_id": product_id,
            "campaign_id": campaign_id,
            "ad_group_id": ad_group_id,
            "creative_id": creative_id,
            "objective": objective,
            "channel": channel,
            "device_id": device_id,
            "session_id": session_id,
            "audience_segment_id": audience_segment_id,
            "targeting_tag_ids": "|".join(targeting_tags),
            "country": self.rng.choice(["US", "CA", "GB", "AU"]),
            "region": self.rng.choice(["CA", "NY", "TX", "WA", "IL", "ON", "ENG"]),
            "city": self.rng.choice(["Los Angeles", "New York", "Austin", "Seattle", "Chicago", "Toronto"]),
            "device_type": self.rng.choice(["ios", "android", "web"]),
        }

        events: list[dict[str, Any]] = []
        impression_id = self._id("imp")
        events.append(
            self._event(
                "ad_impression",
                base_at,
                context,
                impression_id=impression_id,
                placement=self.rng.choice(["for_you_feed", "search", "shop_tab", "profile_feed"]),
                bid_type=self.rng.choice(["cpm", "cpc", "ocpm"]),
                cost_micros=self._cost_micros(channel, 3000, 18000),
                is_viewable=self.rng.random() < 0.93,
            )
        )

        touchpoint_count = self._touchpoint_count()
        latest_at = base_at
        click_id: str | None = None
        for touch_index in range(1, touchpoint_count):
            latest_at += timedelta(minutes=self.rng.randint(2, 3600))
            event_type = "video_view" if self.rng.random() < 0.45 else "ad_click"
            if event_type == "video_view":
                events.append(
                    self._event(
                        "video_view",
                        latest_at,
                        context,
                        view_id=self._id("view"),
                        watch_seconds=round(self.rng.uniform(2.0, 45.0), 2),
                        video_duration_seconds=self.rng.choice([15, 30, 45, 60]),
                        view_percent=round(self.rng.uniform(0.15, 1.0), 2),
                        is_engaged_view=self.rng.random() < 0.38,
                    )
                )
            else:
                click_id = self._id("clk")
                events.append(
                    self._event(
                        "ad_click",
                        latest_at,
                        context,
                        click_id=click_id,
                        impression_id=impression_id,
                        destination_url=f"https://example.com/{objective}/{product_id}",
                        click_type=self.rng.choice(["cta", "product_card", "profile", "lead_form"]),
                        cost_micros=self._cost_micros(channel, 12000, 95000),
                    )
                )

        funnel_events, user_id = self._objective_events(objective, latest_at, context, click_id)
        events.extend(funnel_events)
        if user_id:
            for event in events:
                if event["event_timestamp"] >= funnel_events[0]["event_timestamp"]:
                    event["user_id"] = user_id

        return sorted(events, key=lambda event: event["event_timestamp"])

    def _objective_events(
        self,
        objective: str,
        latest_at: datetime,
        context: dict[str, Any],
        click_id: str | None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        rates = self.config.raw["objective_funnels"][objective]["conversion_rates"]
        events: list[dict[str, Any]] = []
        user_id: str | None = None
        cursor = latest_at + timedelta(hours=self.rng.randint(1, 12))

        def advance() -> datetime:
            nonlocal cursor
            cursor += timedelta(hours=self.rng.randint(1, 48))
            return cursor

        def passes(step_rate: str) -> bool:
            return self.rng.random() < float(rates[step_rate])

        clicked = any(key.endswith("_to_click") and passes(key) for key in rates)
        if not clicked and "impression_to_video_view" not in rates:
            return events, None

        if clicked and click_id is None:
            click_id = self._id("clk")
            events.append(
                self._event(
                    "ad_click",
                    advance(),
                    context,
                    click_id=click_id,
                    destination_url=f"https://example.com/{objective}/{context['product_id']}",
                    click_type="cta",
                    cost_micros=self._cost_micros(context["channel"], 12000, 95000),
                )
            )

        if objective == "app_install":
            if not passes("click_to_app_install"):
                return events, None
            events.append(self._event("app_install", advance(), context, install_id=self._id("ins"), app_version="1.0.0", os_version="17.0", attributed_click_id=click_id, install_source="paid"))
            if not passes("app_install_to_signup"):
                return events, None
            user_id = self._id("user", 16)
            events.append(self._event("signup", advance(), context, user_id=user_id, signup_id=self._id("su"), signup_method=self.rng.choice(["email", "phone", "social_login"]), marketing_opt_in=self.rng.random() < 0.65, referral_code=None))
            if not passes("signup_to_activation"):
                return events, user_id
            events.append(self._event("activation", advance(), context, user_id=user_id, activation_id=self._id("act"), activation_event_name="first_meaningful_app_action", activation_value=1, hours_since_signup=round(self.rng.uniform(1, 24), 2)))
            if passes("activation_to_purchase"):
                events.extend(self._purchase_events(objective, context, advance(), user_id, "purchase_to_repeat_purchase"))

        elif objective == "ecommerce_purchase":
            if not passes("click_to_product_view"):
                return events, None
            events.append(self._commerce_event("product_view", advance(), context, None))
            if not passes("product_view_to_add_to_cart"):
                return events, None
            events.append(self._commerce_event("add_to_cart", advance(), context, None))
            if not passes("add_to_cart_to_checkout_started"):
                return events, None
            events.append(self._commerce_event("checkout_started", advance(), context, None))
            if passes("checkout_started_to_purchase"):
                user_id = self._id("cust", 16)
                events.extend(self._purchase_events(objective, context, advance(), user_id, "purchase_to_repeat_purchase"))

        elif objective == "lead_generation":
            if not passes("click_to_landing_page_view"):
                return events, None
            events.append(self._event("landing_page_view", advance(), context, page_view_id=self._id("lpv"), url="https://example.com/lead", referrer="tiktok", load_time_ms=self.rng.randint(100, 2200)))
            if not passes("landing_page_view_to_form_start"):
                return events, None
            lead_id = self._id("lead")
            events.append(self._event("form_start", advance(), context, form_id=f"form_{self.rng.randint(1, 5)}", lead_type="demo_request", landing_page_id="lp_growth"))
            if not passes("form_start_to_lead_submit"):
                return events, None
            user_id = self._id("lead_user", 16)
            events.append(self._event("lead_submit", advance(), context, user_id=user_id, lead_id=lead_id, lead_type="demo_request", lead_value=self._value(objective), form_id="form_growth"))
            if passes("lead_submit_to_qualified_lead"):
                events.append(self._event("qualified_lead", advance(), context, user_id=user_id, lead_id=lead_id, qualification_score=round(self.rng.uniform(0.5, 1.0), 2), qualified_value=self._value(objective), qualified_at=advance().isoformat()))

        elif objective == "subscription":
            if not passes("click_to_signup"):
                return events, None
            user_id = self._id("sub_user", 16)
            events.append(self._event("signup", advance(), context, user_id=user_id, signup_id=self._id("su"), signup_method="email", marketing_opt_in=True, referral_code=None))
            if not passes("signup_to_trial_started"):
                return events, user_id
            trial_id = self._id("trial")
            events.append(self._event("trial_started", advance(), context, user_id=user_id, trial_id=trial_id, plan_id=self.rng.choice(["monthly", "annual"]), trial_length_days=7))
            if not passes("trial_started_to_subscription_started"):
                return events, user_id
            subscription_id = self._id("sub")
            events.append(self._event("subscription_started", advance(), context, user_id=user_id, subscription_id=subscription_id, plan_id="monthly", revenue=self._value(objective), billing_period="monthly", currency="USD", conversion_id=self._id("conv")))
            if passes("subscription_started_to_renewal"):
                events.append(self._event("renewal", advance(), context, user_id=user_id, subscription_id=subscription_id, renewal_number=1, revenue=self._value(objective), currency="USD", conversion_id=self._id("conv")))

        elif objective == "marketplace_order":
            if not passes("click_to_signup"):
                return events, None
            user_id = self._id("mkt_user", 16)
            events.append(self._event("signup", advance(), context, user_id=user_id, signup_id=self._id("su"), signup_method="phone", marketing_opt_in=self.rng.random() < 0.55, referral_code=None))
            if not passes("signup_to_search_or_browse"):
                return events, user_id
            events.append(self._event("search_or_browse", advance(), context, user_id=user_id, query=self.rng.choice(["dinner", "hotel", "cleaning", "tickets"]), category=self.rng.choice(["food", "travel", "services", "events"]), result_count=self.rng.randint(3, 80)))
            if passes("search_or_browse_to_booking_or_order"):
                events.append(self._event("booking_or_order", advance(), context, user_id=user_id, order_id=self._id("ord"), booking_type=self.rng.choice(["delivery", "reservation", "service"]), revenue=self._value(objective), currency="USD", conversion_id=self._id("conv")))
                if passes("booking_or_order_to_repeat_order"):
                    events.append(self._event("repeat_order", advance(), context, user_id=user_id, order_id=self._id("ord"), booking_type="delivery", revenue=self._value(objective), currency="USD", conversion_id=self._id("conv")))

        elif objective == "brand_awareness":
            if not passes("impression_to_video_view"):
                return events, None
            events.append(self._event("video_view", advance(), context, view_id=self._id("view"), watch_seconds=round(self.rng.uniform(3, 60), 2), video_duration_seconds=60, view_percent=round(self.rng.uniform(0.25, 1.0), 2), is_engaged_view=True, conversion_id=self._id("conv"), event_value=self._value(objective)))
            if passes("video_view_to_engagement"):
                events.append(self._event("engagement", advance(), context, engagement_id=self._id("eng"), engagement_type=self.rng.choice(["like", "share", "follow", "save"]), content_id=f"content_{self.rng.randint(1, 999)}", is_key_engagement=True))
            if passes("engagement_to_landing_page_view"):
                events.append(self._event("landing_page_view", advance(), context, page_view_id=self._id("lpv"), url="https://example.com/brand", referrer="tiktok", load_time_ms=self.rng.randint(100, 2200)))

        elif objective == "offline_conversion":
            if not passes("click_to_call_or_directions"):
                return events, None
            events.append(self._event("call_or_directions", advance(), context, cta_id=self._id("cta"), cta_type=self.rng.choice(["call", "directions"]), business_location_id=f"loc_{self.rng.randint(1, 30)}"))
            if passes("call_or_directions_to_offline_conversion"):
                events.append(self._event("offline_conversion", advance(), context, offline_conversion_id=self._id("off"), conversion_id=self._id("conv"), conversion_type=self.rng.choice(["store_purchase", "appointment", "visit"]), revenue=self._value(objective), match_confidence=round(self.rng.uniform(0.65, 1.0), 2)))

        return events, user_id

    def _event(self, event_type: str, event_at: datetime, context: dict[str, Any], **properties: Any) -> dict[str, Any]:
        event = {
            "event_id": self._id("evt"),
            "event_type": event_type,
            "event_timestamp": event_at.astimezone(timezone.utc).isoformat(),
            "event_date": event_at.date().isoformat(),
            "schema_version": 1,
            "user_id": None,
            "platform": "tiktok" if event_type in TOUCHPOINT_EVENTS else self._platform_for_event(event_type),
            "ingest_source": "simulator",
            **context,
            **properties,
        }
        event["topic"] = EVENT_TOPICS[event_type]
        return event

    def _commerce_event(self, event_type: str, event_at: datetime, context: dict[str, Any], user_id: str | None) -> dict[str, Any]:
        sku = f"sku_{self.rng.randint(1000, 9999)}"
        return self._event(
            event_type,
            event_at,
            context,
            user_id=user_id,
            product_sku=sku,
            category=self.rng.choice(["beauty", "fashion", "gadgets", "home"]),
            price=self._value("ecommerce_purchase"),
            cart_id=self._id("cart") if event_type != "product_view" else None,
            quantity=self.rng.randint(1, 3) if event_type in {"add_to_cart", "checkout_started"} else None,
            currency="USD",
        )

    def _purchase_events(self, objective: str, context: dict[str, Any], event_at: datetime, user_id: str, repeat_rate_key: str) -> list[dict[str, Any]]:
        events = [
            self._event(
                "purchase",
                event_at,
                context,
                user_id=user_id,
                purchase_id=self._id("pur"),
                conversion_id=self._id("conv"),
                order_id=self._id("ord"),
                purchase_type="first_purchase",
                revenue=self._value(objective),
                currency="USD",
                product_sku=f"sku_{self.rng.randint(1000, 9999)}",
                payment_method=self.rng.choice(["card", "paypal", "wallet"]),
            )
        ]
        rate = self.config.raw["objective_funnels"][objective]["conversion_rates"].get(repeat_rate_key, 0)
        if self.rng.random() < float(rate):
            repeat_at = event_at + timedelta(days=self.rng.randint(2, 21))
            events.append(
                self._event(
                    "repeat_purchase",
                    repeat_at,
                    context,
                    user_id=user_id,
                    purchase_id=self._id("pur"),
                    conversion_id=self._id("conv"),
                    order_id=self._id("ord"),
                    purchase_type="repeat_purchase",
                    revenue=self._value(objective),
                    currency="USD",
                    product_sku=f"sku_{self.rng.randint(1000, 9999)}",
                    payment_method=self.rng.choice(["card", "paypal", "wallet"]),
                )
            )
        return events

    def _advertiser_for_objective(self, objective: str) -> dict[str, Any]:
        candidates = [
            advertiser
            for advertiser in self.config.raw["advertisers"]
            if objective in advertiser["objectives"]
        ]
        return self.rng.choice(candidates or self.config.raw["advertisers"])

    def _touchpoint_count(self) -> int:
        bucket = weighted_choice(self.config.raw["multi_touch_journey_distribution"], self.rng)
        return {"one_touch": 1, "two_touch": 2, "three_touch": 3, "four_plus_touch": self.rng.randint(4, 6)}[bucket]

    def _targeting_tags(self, objective: str) -> list[str]:
        tags = {
            "app_install": ["interest_mobile_apps", "behavior_app_installers"],
            "ecommerce_purchase": ["interest_shopping", "purchase_intent_high"],
            "lead_generation": ["interest_learning", "behavior_form_submitters"],
            "subscription": ["interest_subscription_apps", "lookalike_paid_users"],
            "marketplace_order": ["interest_local_services", "behavior_recent_searchers"],
            "brand_awareness": ["broad_reach", "engaged_viewers"],
            "offline_conversion": ["geo_near_store", "local_intent"],
        }
        return tags.get(objective, ["broad_reach"])

    def _id(self, prefix: str, chars: int = 32) -> str:
        return f"{prefix}_{self.rng.getrandbits(128):032x}"[: len(prefix) + 1 + chars]

    def _cost_micros(self, channel: str, low: int, high: int) -> int:
        if channel in {"organic", "email"}:
            return 0
        return self.rng.randint(low, high)

    def _value(self, objective: str) -> float:
        low, high = self.config.raw["objective_funnels"][objective]["conversion_value_range"]
        return round(self.rng.uniform(float(low), float(high)), 2)

    def _platform_for_event(self, event_type: str) -> str:
        if event_type in {"app_install", "signup", "activation", "trial_started", "subscription_started", "renewal"}:
            return "mobile_app"
        if event_type in OFFLINE_EVENTS:
            return "offline"
        return "mobile_web"


def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    event_counts: dict[str, int] = {}
    objective_counts: dict[str, int] = {}
    conversions: list[dict[str, Any]] = []
    touchpoints_by_device: dict[str, list[str]] = {}

    conversion_events = {
        "purchase",
        "repeat_purchase",
        "qualified_lead",
        "subscription_started",
        "renewal",
        "booking_or_order",
        "repeat_order",
        "video_view",
        "offline_conversion",
    }
    for event in events:
        event_counts[event["event_type"]] = event_counts.get(event["event_type"], 0) + 1
        objective_counts[event["objective"]] = objective_counts.get(event["objective"], 0) + 1
        if event["event_type"] in TOUCHPOINT_EVENTS:
            touchpoints_by_device.setdefault(event["device_id"], []).append(event["event_timestamp"])
        if event["event_type"] in conversion_events:
            conversions.append(event)

    multi_touch_converters = 0
    for conversion in conversions:
        prior_touchpoints = [
            timestamp
            for timestamp in touchpoints_by_device.get(conversion["device_id"], [])
            if timestamp < conversion["event_timestamp"]
        ]
        if len(prior_touchpoints) >= 3:
            multi_touch_converters += 1

    return {
        "event_counts": event_counts,
        "objective_counts": objective_counts,
        "total_events": len(events),
        "total_converters": len(conversions),
        "multi_touch_converter_rate": (
            multi_touch_converters / len(conversions) if conversions else 0.0
        ),
    }
