select * from {{ ref('stg_events') }}
where event_type = 'landing_page_view'
