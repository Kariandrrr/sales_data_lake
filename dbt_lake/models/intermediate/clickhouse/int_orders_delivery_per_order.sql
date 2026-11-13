{{ config(materialized='table', order_by='tuple()') }}

with base as (select *
              from {{ ref('int_orders_delivery') }}),

     final as (select order_id,
                      max(delivered_at),
                      max(estimated_delivery_at) as estimated_at,
                      max(
                              greatest(dateDiff('day', estimated_delivery_at, delivered_at), 0)
                      )                          as late_days,
                      max(customer_state)        as
                                                    customer_state,
                      max(customer_city)         as customer_city

               from base
               group by order_id)

select *
from final