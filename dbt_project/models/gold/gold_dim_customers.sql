{{ config(
    materialized='table'
) }}

with silver_customers as (
    select *
    from {{ ref('silver_customers') }}
),

gold_dimension as (
    select
        {{ dbt_utils.generate_surrogate_key(['customer_id']) }} as customer_sk,

        customer_id,

        first_name,
        last_name,
        first_name || '-' || last_name as full_name,
        email,
        phone,
        country,
        
        case 
            when email like '%@%' and email like '%.%' then true 
            else false 
        end as is_valid_email,
        
        case 
            when upper(country) = 'ARGENTINA' then 'Domestic'
            else 'International'
        end as market_segment,
        
        _loaded_at as effective_from_timestamp

    from silver_customers
)

select * from gold_dimension