select
    *,
    event_type in {{ touchpoint_event_list() }} as is_touchpoint,
    (
        event_type in {{ conversion_event_list() }}
        or (
            event_type = 'video_view'
            and objective = 'brand_awareness'
            and conversion_id is not null
        )
    ) as is_conversion,
    coalesce(revenue, qualified_value, lead_value, event_value, price, 0.0) as event_value_canonical,
    event_type as funnel_step
from {{ ref('stg_events') }}
