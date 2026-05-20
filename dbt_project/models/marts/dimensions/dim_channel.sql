select
    channel,
    channel_group,
    channel_type,
    cast(is_paid as bool) as is_paid
from {{ ref('channel_hierarchy') }}
