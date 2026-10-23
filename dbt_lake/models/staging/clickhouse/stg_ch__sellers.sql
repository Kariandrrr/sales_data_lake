{{ config(materialized='table', order_by='seller_id') }}

with source as (select *
                from {{ source('ch_raw', 'sellers') }}),

     deduped as (select *
                 from source
                 where seller_id is not null
                 limit 1 by seller_id)

select seller_id,
       initcapUTF8(trimBoth(seller_city)) as city,
       upper(trimBoth(seller_state))      as state
from deduped