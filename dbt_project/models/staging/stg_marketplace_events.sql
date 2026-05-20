select * from {{ ref('stg_events') }}
where event_type in ('search_or_browse', 'booking_or_order', 'repeat_order')
