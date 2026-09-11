{{ config(
    materialized='view'
) }}

with bronze_data as (
    select *
    from {{ ref('stg_bronze_customers') }}
),

cleaned_and_typed as (
    select
        try_cast(customer_id as integer) as customer_id,
        
        trim(first_name) as first_name,
        trim(last_name) as last_name,
        upper(trim(email)) as email,
        
        coalesce(trim(phone), 'N/A') as phone,
        upper(coalesce(trim(country), 'UNKNOWN')) as country,
        
        _loaded_at,
        _loaded_by
        
    from bronze_data
    where customer_id is not null 
),

deduplicated as (
    select
        *,
        row_number() over (
            partition by customer_id 
            order by _loaded_at desc
        ) as row_num
    from cleaned_and_typed
)

select
    customer_id,
    first_name,
    last_name,
    email,
    phone,
    country,
    _loaded_at,
    _loaded_by
from deduplicated
where row_num = 1