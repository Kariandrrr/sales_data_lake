{{ config(materialized='table', engine='MergeTree', order_by='seller_id') }}

select seller_id,
       uniqExact(order_id)  as total_orders_fulfilled,
       count(order_item_id) as total_items_sold,
       sum(item_price)      as total_gross_revenue,
       min(ordered_at)      as first_order_at,
       max(ordered_at)      as last_order_at
from {{ ref('int_sales_base') }}
group by seller_id
order by total_gross_revenue desc
