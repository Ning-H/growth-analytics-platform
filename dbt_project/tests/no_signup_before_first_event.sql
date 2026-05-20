select *
from {{ ref('dim_user') }}
where signup_date is not null
  and signup_date < first_event_date
