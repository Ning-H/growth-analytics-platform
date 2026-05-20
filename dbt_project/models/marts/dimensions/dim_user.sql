with events as (
    select *
    from {{ ref('int_identity_resolved') }}
),

user_rollup as (
    select
        resolved_user_id,
        min(event_date) as first_event_date,
        min(if(event_type = 'signup', event_date, null)) as signup_date,
        array_agg(country ignore nulls order by event_timestamp limit 1)[offset(0)] as country,
        array_agg(device_type ignore nulls order by event_timestamp limit 1)[offset(0)] as device_type,
        array_agg(objective ignore nulls order by event_timestamp limit 1)[offset(0)] as first_objective,
        array_agg(if(is_touchpoint, channel, null) ignore nulls order by event_timestamp limit 1)[safe_offset(0)] as acquisition_channel_first_touch,
        array_agg(if(is_touchpoint, channel, null) ignore nulls order by event_timestamp desc limit 1)[safe_offset(0)] as acquisition_channel_last_touch,
        sum(if(is_conversion, event_value_canonical, 0)) as ltv_to_date,
        countif(is_conversion) as conversion_count,
        countif(event_type = 'activation') > 0 as has_activated
    from events
    group by 1
)

select
    *,
    case
        when conversion_count > 1 then 'repeat_converter'
        when conversion_count = 1 then 'converter'
        when has_activated then 'activated'
        when signup_date is not null then 'signed_up'
        else 'anonymous'
    end as lifecycle_stage
from user_rollup
