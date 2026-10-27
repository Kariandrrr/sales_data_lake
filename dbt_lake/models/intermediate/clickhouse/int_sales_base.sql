{{ config(materialized='table', order_by='tuple()') }}

with items as (select * from {{ ref('stg_ch__order_items') }}),
     orders as (select * from {{ ref('stg_ch__orders') }}),
     customers as (select * from {{ ref('stg_ch__customers') }}),
     products as (select * from {{ ref('stg_ch__products') }}),
     translations as (select * from {{ ref('stg_ch__category_translation') }}),

     joined as (select i.order_id                            as order_id,
                       i.order_item_id                       as order_item_id,
                       i.product_id                          as product_id,
                       i.seller_id                           as seller_id,
                       o.customer_id                         as customer_id,
                       c.customer_unique_id                  as customer_unique_id,
                       i.item_price                          as item_price,
                       i.freight_amount                      as freight_amount,
                       i.item_price + i.freight_amount       as total_value,
                       o.order_status                        as order_status,
                       o.ordered_at                          as ordered_at,
                       o.delivered_to_customer_at            as delivered_to_customer_at,
                       c.city                                as customer_city,
                       c.state                               as customer_state,
                       c.zip_code_hash                       as zip_code_hash,
                       p.category_name                       as category_name,
                       coalesce(t.category_name_en, 'other') as category_name_en,
                       p.weight_g                            as weight_g

                from items i
                         inner join orders o on o.order_id = i.order_id
                         left join customers c on c.customer_id = o.customer_id
                         left join products p on p.product_id = i.product_id
                         left join translations t on t.category_name = p.category_name)

select *
from joined
