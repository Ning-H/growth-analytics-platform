select * from {{ ref('stg_events') }}
where event_type = 'video_view'
