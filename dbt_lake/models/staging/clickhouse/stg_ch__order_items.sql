{{ config(materialised='table', order_by='(order_id, order_item_id)') }}

{{ config(
    engine='MergeTree',
    order_by=['(order_id, order_item_id)'],
    settings={'allow_nullable_key': 1}
) }}

with source as (select *
                from {{ source('ch_raw', 'order_items') }}),

     cleaned as (select order_id,
                        toInt32(order_item_id)                                       as order_item_id,
                        product_id,
                        seller_id,
                        toDecimal64(coalesce(price, 0), 2)                           as item_price,
                        toDecimal64(coalesce(freight_value, 0), 2)                   as freight_amount,
                        parseDateTimeBestEffortOrNull(toString(shipping_limit_date)) as shipping_limit_at
                 from source
                 where order_id is not null
                   and order_item_id is not null),

     valid as (select *
               from cleaned
               where item_price >= 0
                 and freight_amount >= 0),

     dedupted as (select *
                  from valid
                  order by item_price DESC
                  limit 1 by (order_id, order_item_id))

select *
from dedupted
