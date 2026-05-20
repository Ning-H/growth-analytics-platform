with eligible_touchpoints as (
    select
        conversions.conversion_id,
        conversions.resolved_user_id,
        conversions.conversion_value,
        touchpoints.touchpoint_id,
        touchpoints.channel,
        touchpoints.campaign_id,
        count(*) over (partition by conversions.conversion_id) as touchpoint_count
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
    1.0 / touchpoint_count as credit_fraction,
    conversion_value / touchpoint_count as attributed_revenue
from eligible_touchpoints
