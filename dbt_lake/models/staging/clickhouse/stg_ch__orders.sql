{{ config(materialized='table', order_by='order_id') }}

{{ config(
    engine='MergeTree',
    order_by=['order_id'],
    settings={'allow_nullable_key': 1}
) }}

with source as (select *
                from {{ source('ch_raw', 'orders') }}),

     cleaned as (select order_id,
                        customer_id,
                        lower(trimBoth(order_status))                                          as order_status,
                        parseDateTimeBestEffortOrNull(toString(order_purchase_timestamp))      as ordered_at,
                        parseDateTimeBestEffortOrNull(toString(order_approved_at))             as approved_at,
                        parseDateTimeBestEffortOrNull(toString(order_delivered_carrier_date))  as handed_to_carrier_at,
                        parseDateTimeBestEffortOrNull(toString(order_delivered_customer_date)) as delivered_to_customer_at,
                        parseDateTimeBestEffortOrNull(toString(order_estimated_delivery_date)) as estimated_delivery_at
                 from source
                 where order_id is not null
                   and parseDateTimeBestEffortOrNull(toString(order_purchase_timestamp)) is not null),

     deduped as (select *
                 from cleaned
                 order by ordered_at desc
    limit 1 by order_id)

select *
from deduped