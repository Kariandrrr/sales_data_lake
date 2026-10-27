{{ config(materialized='table', order_by='customer_id') }}

with source as (select *
                from {{ source('ch_raw', 'customers') }}),

     deduped as (select *
                 from source
                 where customer_id is not null
                 limit 1 by customer_id)

select customer_id,
       customer_unique_id,
       {{ hash_pii('toString(customer_zip_code_prefix)') }} as zip_code_hash,
       initcapUTF8(trimBoth(customer_city))                 as city,
       upper(trimBoth(customer_state))                      as state
from deduped