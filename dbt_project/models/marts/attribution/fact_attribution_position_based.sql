with ranked_touchpoints as (
    select
        conversions.conversion_id,
        conversions.resolved_user_id,
        conversions.conversion_value,
        touchpoints.touchpoint_id,
        touchpoints.channel,
        touchpoints.campaign_id,
        row_number() over (
            partition by conversions.conversion_id
            order by touchpoints.touchpoint_timestamp, touchpoints.touchpoint_id
        ) as touch_rank,
        count(*) over (partition by conversions.conversion_id) as touchpoint_count
    from {{ ref('fact_conversions') }} as conversions
    join {{ ref('fact_touchpoints') }} as touchpoints
        on conversions.resolved_user_id = touchpoints.resolved_user_id
       and conversions.advertiser_id = touchpoints.advertiser_id
       and conversions.product_id = touchpoints.product_id
       and touchpoints.touchpoint_timestamp < conversions.conversion_timestamp
       and touchpoints.touchpoint_timestamp >= timestamp_sub(conversions.conversion_timestamp, interval {{ attribution_lookback_days() }} day)
       and touchpoints.touchpoint_id != conversions.conversion_event_id
),

credited as (
    select
        *,
        case
            when touchpoint_count = 1 then 1.0
            when touchpoint_count = 2 then 0.5
            when touch_rank = 1 then 0.4
            when touch_rank = touchpoint_count then 0.4
            else 0.2 / (touchpoint_count - 2)
        end as credit_fraction
    from ranked_touchpoints
)

select
    conversion_id,
    resolved_user_id,
    touchpoint_id,
    channel,
    campaign_id,
    credit_fraction,
    conversion_value * credit_fraction as attributed_revenue
from credited
