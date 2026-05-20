with device_map as (
    select
        device_id,
        advertiser_id,
        product_id,
        array_agg(user_id order by last_seen_at desc limit 1)[offset(0)] as mapped_user_id
    from {{ source('growth_raw', 'device_to_user') }}
    group by 1, 2, 3
),

events as (
    select *
    from {{ ref('int_events_unified') }}
)

select
    events.*,
    coalesce(
        events.user_id,
        device_map.mapped_user_id,
        concat('anonymous_', events.device_id)
    ) as resolved_user_id,
    events.user_id is null and device_map.mapped_user_id is null as is_anonymous_event
from events
left join device_map
    on events.device_id = device_map.device_id
   and events.advertiser_id = device_map.advertiser_id
   and events.product_id = device_map.product_id
