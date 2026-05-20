with conversions as (
    select *
    from {{ ref('int_identity_resolved') }}
    where is_conversion
)

select
    coalesce(conversion_id, event_id) as conversion_id,
    event_id as conversion_event_id,
    resolved_user_id,
    device_id,
    user_id,
    advertiser_id,
    product_id,
    campaign_id,
    objective,
    channel as conversion_channel,
    event_type as conversion_type,
    event_timestamp as conversion_timestamp,
    event_date as conversion_date,
    event_value_canonical as conversion_value,
    revenue,
    currency,
    purchase_id,
    order_id,
    lead_id,
    subscription_id,
    offline_conversion_id
from conversions
