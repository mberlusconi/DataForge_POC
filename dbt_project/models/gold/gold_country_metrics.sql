{{ config(
    materialized='table'
) }}

with dim_customers as (
    select *
    from {{ ref('gold_dim_customers') }}
)

select
    country,
    market_segment,
    count(distinct customer_sk) as total_customers,
    
    count(case when is_valid_email = true then 1 end) as total_valid_emails,
    
    current_timestamp() as _calculated_at
from dim_customers
group by 1, 2