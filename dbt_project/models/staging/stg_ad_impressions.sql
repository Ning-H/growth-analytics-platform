select * from {{ ref('stg_events') }}
where event_type = 'ad_impression'
