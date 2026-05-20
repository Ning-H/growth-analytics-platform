select * from {{ ref('stg_events') }}
where event_type in ('trial_started', 'subscription_started', 'renewal')
