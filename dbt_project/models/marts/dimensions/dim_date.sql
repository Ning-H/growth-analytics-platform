select
    date_day,
    extract(year from date_day) as year,
    extract(quarter from date_day) as quarter,
    extract(month from date_day) as month,
    extract(week from date_day) as week_of_year,
    date_trunc(date_day, week(monday)) as week_start_date,
    date_trunc(date_day, month) as month_start_date,
    format_date('%A', date_day) as day_name,
    extract(dayofweek from date_day) in (1, 7) as is_weekend
from unnest(
    generate_date_array(
        date_sub(current_date(), interval 1 year),
        date_add(current_date(), interval 1 year),
        interval 1 day
    )
) as date_day
