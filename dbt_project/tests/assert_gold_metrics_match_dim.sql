-- Custom Data Test:
-- Validates that the total customer count aggregated in the Gold metrics table 
-- matches the exact total count in the Gold Customer Dimension.
-- The test FAILS if any row is returned.

with dim_total as (
    select count(*) as total_dim
    from {{ ref('gold_dim_customers') }}
),

metrics_total as (
    select sum(total_customers) as total_metrics
    from {{ ref('gold_country_metrics') }}
)

select 
    dim_total.total_dim,
    metrics_total.total_metrics
from dim_total
cross join metrics_total
where dim_total.total_dim != metrics_total.total_metrics