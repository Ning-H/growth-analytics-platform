with daily_steps as (
    select
        first_completed_date as funnel_date,
        objective,
        step_name,
        step_order,
        count(distinct resolved_user_id) as users_completed
    from {{ ref('funnel_step_completion') }}
    group by 1, 2, 3, 4
),

with_previous as (
    select
        *,
        lag(users_completed) over (
            partition by funnel_date, objective
            order by step_order, step_name
        ) as previous_step_users
    from daily_steps
)

select
    funnel_date,
    objective,
    step_name,
    step_order,
    users_completed,
    previous_step_users,
    safe_divide(users_completed, previous_step_users) as step_to_step_conversion_rate
from with_previous
