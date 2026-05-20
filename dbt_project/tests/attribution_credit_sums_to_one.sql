with attribution_models as (
    select 'first_touch' as attribution_model, conversion_id, sum(credit_fraction) as total_credit
    from {{ ref('fact_attribution_first_touch') }}
    group by 1, 2

    union all

    select 'last_touch' as attribution_model, conversion_id, sum(credit_fraction) as total_credit
    from {{ ref('fact_attribution_last_touch') }}
    group by 1, 2

    union all

    select 'linear' as attribution_model, conversion_id, sum(credit_fraction) as total_credit
    from {{ ref('fact_attribution_linear') }}
    group by 1, 2

    union all

    select 'time_decay' as attribution_model, conversion_id, sum(credit_fraction) as total_credit
    from {{ ref('fact_attribution_time_decay') }}
    group by 1, 2

    union all

    select 'position_based' as attribution_model, conversion_id, sum(credit_fraction) as total_credit
    from {{ ref('fact_attribution_position_based') }}
    group by 1, 2
)

select *
from attribution_models
where abs(total_credit - 1.0) > 0.000001
