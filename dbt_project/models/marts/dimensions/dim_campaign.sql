with campaigns as (
    select
        campaign_id,
        advertiser_id,
        product_id,
        objective,
        channel,
        min(event_date) as first_seen_date,
        max(event_date) as last_seen_date,
        count(*) as observed_event_count
    from {{ ref('int_identity_resolved') }}
    group by 1, 2, 3, 4, 5
)

select
    campaigns.*,
    concat(replace(initcap(replace(campaigns.objective, '_', ' ')), ' ', ''), ' ', right(campaigns.campaign_id, 3)) as campaign_name,
    coalesce(spend.daily_spend, 0) as daily_spend
from campaigns
left join {{ ref('campaign_spend') }} as spend
    on campaigns.channel = spend.channel
   and campaigns.objective = spend.objective
