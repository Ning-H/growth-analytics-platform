with weighted_touchpoints as (
    select
        conversions.conversion_id,
        conversions.resolved_user_id,
        conversions.conversion_value,
        conversions.conversion_timestamp,
        touchpoints.touchpoint_id,
        touchpoints.channel,
        touchpoints.campaign_id,
        touchpoints.touchpoint_timestamp,
        pow(
            0.5,
            timestamp_diff(conversions.conversion_timestamp, touchpoints.touchpoint_timestamp, second)
            / (7 * 24 * 60 * 60)
        ) as decay_weight
    from {{ ref('fact_conversions') }} as conversions
    join {{ ref('fact_touchpoints') }} as touchpoints
        on conversions.resolved_user_id = touchpoints.resolved_user_id
       and conversions.advertiser_id = touchpoints.advertiser_id
       and conversions.product_id = touchpoints.product_id
       and touchpoints.touchpoint_timestamp < conversions.conversion_timestamp
       and touchpoints.touchpoint_timestamp >= timestamp_sub(conversions.conversion_timestamp, interval {{ attribution_lookback_days() }} day)
       and touchpoints.touchpoint_id != conversions.conversion_event_id
),

normalized as (
    select
        *,
        sum(decay_weight) over (partition by conversion_id) as total_decay_weight
    from weighted_touchpoints
)

select
    conversion_id,
    resolved_user_id,
    touchpoint_id,
    channel,
    campaign_id,
    decay_weight / total_decay_weight as credit_fraction,
    conversion_value * decay_weight / total_decay_weight as attributed_revenue
from normalized
