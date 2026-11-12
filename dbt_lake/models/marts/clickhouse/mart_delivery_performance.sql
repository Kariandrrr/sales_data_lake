{{ config(
    materialized='table',
    order_by='(customer_state, seller_id, ordered_at)',
    settings={'allow_nullable_key': 1}
) }}

with base as (select *
              from {{ ref('int_orders_delivery') }}),

     intermediate as (select order_id,
                             order_item_id,
                             customer_state,
                             seller_id,
                             seller_state,
                             ordered_at,
                             estimated_delivery_at,
                             assumeNotNull(delivered_at) as delivered_at
                      from src),

     final as (select order_id,
                      ordered_at,
                      order_item_id,
                      customer_state,
                      seller_id,
                      seller_state,

                      dateDiff('day', ordered_at, delivered_at)                         as purchase_days,
                      dateDiff('day', ordered_at, estimated_delivery_at)                as estimated_days,
                      greatest(dateDiff('day', estimated_delivery_at, delivered_at), 0) as late_days,
                      toUInt8(dateDiff('day', estimated_delivery_at, delivered_at) > 0) as is_late
               from base)

select *
from final