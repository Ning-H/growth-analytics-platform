select
    resolved_user_id,
    signup_date,
    date_trunc(signup_date, week(monday)) as signup_week,
    first_objective,
    acquisition_channel_first_touch,
    acquisition_channel_last_touch,
    country,
    device_type,
    ltv_to_date
from {{ ref('dim_user') }}
where signup_date is not null
