{{ config(materialized='table', order_by='category_name') }}

with source as (select *
                from {{ source('ch_raw', 'product_category_name_translation') }}),

     unioned as (select trimBoth(product_category_name)         as category_name,
                        trimBoth(product_category_name_english) as category_name_en
                 from source

                 union all

                 select trimBoth(product_category_name),
                        trimBoth(product_category_name_english)
                 from {{ ref('category_translations_extra') }})

select category_name,
       any(category_name_en) as category_name_en
from unioned
where category_name is not null
group by category_name
