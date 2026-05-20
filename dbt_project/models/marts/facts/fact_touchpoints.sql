with touchpoints as (
    select *
    from {{ ref('int_identity_resolved') }}
    where is_touchpoint
)

select
    event_id as touchpoint_id,
    resolved_user_id,
    device_id,
    user_id,
    advertiser_id,
    product_id,
    campaign_id,
    ad_group_id,
    creative_id,
    objective,
    channel,
    event_type as touchpoint_type,
    event_timestamp as touchpoint_timestamp,
    event_date as touchpoint_date,
    impression_id,
    click_id,
    view_id,
    engagement_id,
    cost_micros / 1000000.0 as touchpoint_cost,
    row_number() over (
        partition by resolved_user_id, advertiser_id, product_id
        order by event_timestamp, event_id
    ) as touchpoint_position,
    row_number() over (
        partition by resolved_user_id, advertiser_id, product_id
        order by event_timestamp desc, event_id desc
    ) as reverse_touchpoint_position
from touchpoints
