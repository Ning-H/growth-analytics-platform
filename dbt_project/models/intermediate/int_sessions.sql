with ordered_events as (
    select
        *,
        lag(event_timestamp) over (
            partition by resolved_user_id
            order by event_timestamp, event_id
        ) as previous_event_timestamp
    from {{ ref('int_identity_resolved') }}
),

session_flags as (
    select
        *,
        case
            when previous_event_timestamp is null then 1
            when timestamp_diff(event_timestamp, previous_event_timestamp, minute) > 30 then 1
            else 0
        end as new_session_flag
    from ordered_events
),

sessionized as (
    select
        *,
        sum(new_session_flag) over (
            partition by resolved_user_id
            order by event_timestamp, event_id
            rows between unbounded preceding and current row
        ) as session_number
    from session_flags
)

select
    to_hex(md5(concat(resolved_user_id, '-', cast(session_number as string)))) as session_key,
    resolved_user_id,
    min(event_timestamp) as session_start_at,
    max(event_timestamp) as session_end_at,
    timestamp_diff(max(event_timestamp), min(event_timestamp), second) as session_duration_seconds,
    count(*) as event_count,
    countif(is_touchpoint) as touchpoint_count,
    countif(is_conversion) as conversion_count,
    array_agg(channel order by event_timestamp limit 1)[offset(0)] as first_channel,
    array_agg(objective order by event_timestamp limit 1)[offset(0)] as first_objective
from sessionized
group by 1, 2
