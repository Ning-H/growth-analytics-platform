with event_dates as (
    select
        min(event_date) as min_event_date,
        max(event_date) as max_event_date
    from {{ ref('fact_user_events') }}
),

date_spine as (
    select date_day as spend_date
    from {{ ref('dim_date') }}
    cross join event_dates
    where date_day between min_event_date and max_event_date
),

campaigns as (
    select distinct
        campaign_id,
        advertiser_id,
        product_id,
        channel,
        objective,
        daily_spend
    from {{ ref('dim_campaign') }}
)

select
    to_hex(md5(concat(
        campaign_id,
        '|',
        advertiser_id,
        '|',
        product_id,
        '|',
        channel,
        '|',
        objective,
        '|',
        cast(spend_date as string)
    ))) as campaign_spend_day_id,
    spend_date,
    campaign_id,
    advertiser_id,
    product_id,
    channel,
    objective,
    daily_spend
from campaigns
cross join date_spine
