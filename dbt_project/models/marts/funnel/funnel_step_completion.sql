with step_events as (
    select
        resolved_user_id,
        advertiser_id,
        product_id,
        objective,
        channel,
        event_type as step_name,
        event_timestamp,
        event_date,
        case event_type
            when 'ad_impression' then 1
            when 'video_view' then 2
            when 'ad_click' then 3
            when 'engagement' then 4
            when 'landing_page_view' then 5
            when 'app_install' then 6
            when 'signup' then 7
            when 'product_view' then 8
            when 'form_start' then 8
            when 'trial_started' then 8
            when 'search_or_browse' then 8
            when 'call_or_directions' then 8
            when 'add_to_cart' then 9
            when 'activation' then 9
            when 'lead_submit' then 9
            when 'checkout_started' then 10
            when 'subscription_started' then 10
            when 'booking_or_order' then 10
            when 'purchase' then 11
            when 'qualified_lead' then 11
            when 'offline_conversion' then 11
            when 'repeat_purchase' then 12
            when 'renewal' then 12
            when 'repeat_order' then 12
            else 99
        end as step_order
    from {{ ref('fact_user_events') }}
),

completed as (
    select
        resolved_user_id,
        advertiser_id,
        product_id,
        objective,
        step_name,
        min(step_order) as step_order,
        min(event_timestamp) as first_completed_at,
        min(event_date) as first_completed_date,
        array_agg(channel order by event_timestamp limit 1)[offset(0)] as first_step_channel
    from step_events
    group by 1, 2, 3, 4, 5
)

select
    to_hex(md5(concat(resolved_user_id, '|', advertiser_id, '|', product_id, '|', objective, '|', step_name))) as funnel_completion_id,
    *,
    true as reached_step
from completed
