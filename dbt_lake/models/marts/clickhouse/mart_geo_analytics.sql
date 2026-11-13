{{ config(
    materialized='table',
    engine='MergeTree',
    order_by='(customer_state, customer_city)',
    settings={'allow_nullable_key': 1}
) }}

with base as (select *
              from {{ ref('int_sales_base') }}),
     final as (select customer_state,
                      customer_city,
                      uniqExact(order_id)    as total_orders,
                      uniqExact(customer_id) as unique_customers,
                      sum(total_value)       as total_spent,
                      avg(freight_amount)    as avg_freight_cost
-- , avg(freight_amount) as avg_freiht_cost   -- might be wrong #TODO
               from base
               group by customer_state, customer_city)

select *
from final
order by total_spent desc