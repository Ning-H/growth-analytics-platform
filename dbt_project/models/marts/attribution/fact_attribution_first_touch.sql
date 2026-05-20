with eligible_touchpoints as (
    select
        conversions.conversion_id,
        conversions.resolved_user_id,
        conversions.conversion_timestamp,
        conversions.conversion_value,
        touchpoints.touchpoint_id,
        touchpoints.channel,
        touchpoints.campaign_id,
        touchpoints.touchpoint_timestamp,
        row_number() over (
            partition by conversions.conversion_id
            order by touchpoints.touchpoint_timestamp, touchpoints.touchpoint_id
        ) as touch_rank
    from {{ ref('fact_conversions') }} as conversions
    join {{ ref('fact_touchpoints') }} as touchpoints
        on conversions.resolved_user_id = touchpoints.resolved_user_id
       and conversions.advertiser_id = touchpoints.advertiser_id
       and conversions.product_id = touchpoints.product_id
       and touchpoints.touchpoint_timestamp < conversions.conversion_timestamp
       and touchpoints.touchpoint_timestamp >= timestamp_sub(conversions.conversion_timestamp, interval {{ attribution_lookback_days() }} day)
       and touchpoints.touchpoint_id != conversions.conversion_event_id
)

select
    conversion_id,
    resolved_user_id,
    touchpoint_id,
    channel,
    campaign_id,
    1.0 as credit_fraction,
    conversion_value as attributed_revenue
from eligible_touchpoints
where touch_rank = 1
