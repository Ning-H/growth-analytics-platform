select * from {{ ref('stg_events') }}
where event_type in ('form_start', 'lead_submit', 'qualified_lead')
