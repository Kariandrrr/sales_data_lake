{{ config(
     materialized='table',
     engine='MergeTree',
     order_by='seller_id',
     settings={'allow_nullable_key': 1})
}}

with base as (select * from {{ ref('int_sales_base') }}),

     final as (select seller_id,
                      uniqExact(order_id)  as total_orders_fulfilled,
                      count(order_item_id) as total_items_sold,
                      sum(item_price)      as total_gross_revenue,
                      min(ordered_at)      as first_order_at,
                      max(ordered_at)      as last_order_at
               from base
               group by seller_id)

select *
from final
order by total_gross_revenue desc
