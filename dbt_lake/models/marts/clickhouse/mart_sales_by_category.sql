{{ config(materialized='table', engine='MergeTree', order_by='total_orders') }}

select category_name_en     as product_category_name_english,
       uniqExact(order_id)  as total_orders,
       count(order_item_id) as total_items_sold,
       sum(item_price)      as total_revenue,
       sum(freight_amount)  as total_freight,
       avg(item_price)      as avg_item_price
from {{ ref('int_sales_base') }}
group by category_name_en
order by total_orders desc
