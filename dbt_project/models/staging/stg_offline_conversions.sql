select * from {{ ref('stg_events') }}
where event_type in ('call_or_directions', 'offline_conversion')
