{{ config(
    materialized='table',
) }}

with raw_source as (
    select * 
    from {{ source('landing_raw', 'raw_customers') }}
),

renamed_and_enriched as (
    select
        id as customer_id,
        first_name,
        last_name,
        email,
        phone,
        country,
        
        -- Metadata
        current_timestamp() as _loaded_at,
        current_user() as _loaded_by

    from raw_source
)

select * from renamed_and_enriched