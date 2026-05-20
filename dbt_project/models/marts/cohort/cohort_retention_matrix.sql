with signup_cohorts as (
    select *
    from {{ ref('cohort_user_signup_week') }}
),

activity as (
    select
        resolved_user_id,
        event_date,
        date_trunc(event_date, week(monday)) as activity_week
    from {{ ref('fact_user_events') }}
    where event_type not in ('ad_impression', 'video_view', 'ad_click')
),

retained_users as (
    select
        signup_cohorts.signup_week,
        date_diff(activity.activity_week, signup_cohorts.signup_week, week) as weeks_since_signup,
        signup_cohorts.acquisition_channel_first_touch,
        signup_cohorts.first_objective,
        count(distinct activity.resolved_user_id) as retained_users
    from signup_cohorts
    join activity
        on signup_cohorts.resolved_user_id = activity.resolved_user_id
       and activity.event_date >= signup_cohorts.signup_date
    group by 1, 2, 3, 4
),

cohort_sizes as (
    select
        signup_week,
        acquisition_channel_first_touch,
        first_objective,
        count(distinct resolved_user_id) as cohort_users
    from signup_cohorts
    group by 1, 2, 3
)

select
    retained_users.signup_week,
    retained_users.weeks_since_signup,
    retained_users.acquisition_channel_first_touch,
    retained_users.first_objective,
    cohort_sizes.cohort_users,
    retained_users.retained_users,
    safe_divide(retained_users.retained_users, cohort_sizes.cohort_users) as retention_rate
from retained_users
join cohort_sizes
    on retained_users.signup_week = cohort_sizes.signup_week
   and coalesce(retained_users.acquisition_channel_first_touch, '__null__') = coalesce(cohort_sizes.acquisition_channel_first_touch, '__null__')
   and retained_users.first_objective = cohort_sizes.first_objective
