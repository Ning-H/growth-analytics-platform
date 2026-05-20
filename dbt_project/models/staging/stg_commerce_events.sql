select * from {{ ref('stg_events') }}
where event_type in ('product_view', 'add_to_cart', 'checkout_started', 'purchase', 'repeat_purchase')
