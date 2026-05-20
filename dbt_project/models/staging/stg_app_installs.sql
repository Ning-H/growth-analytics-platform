select * from {{ ref('stg_events') }}
where event_type = 'app_install'
