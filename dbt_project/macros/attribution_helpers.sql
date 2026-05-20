{% macro touchpoint_event_list() -%}
('ad_impression', 'video_view', 'ad_click', 'engagement')
{%- endmacro %}

{% macro conversion_event_list() -%}
(
  'purchase',
  'repeat_purchase',
  'qualified_lead',
  'subscription_started',
  'renewal',
  'booking_or_order',
  'repeat_order',
  'offline_conversion'
)
{%- endmacro %}

{% macro attribution_lookback_days() -%}
30
{%- endmacro %}
