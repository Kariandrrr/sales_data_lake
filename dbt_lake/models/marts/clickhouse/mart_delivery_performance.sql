{{ config(
    materialized='table',
    order_by='(customer_state, seller_id)',
    settings={'allow_nullable_key': 1}
) }}

with base as (select *
              from {{ ref('int_orders_delivery') }}),

     final as (select order_id,
                      order_item_id,
                      customer_state,
                      seller_id,
                      seller_state,

                      dateDiff('day', ordered_at, delivered_at)                                      as puchase_days,
                      dateDiff('day', ordered_at, estimated_delivery_at)                             as estimated_days,
                      greatest(dateDiff('day', estimated_delivery_at, delivered_at), 0)              as late_days,
                      toUInt8(greatest(dateDiff('day', estimated_delivery_at, delivered_at), 0) > 0) as is_late
               from base)

select *
from final
