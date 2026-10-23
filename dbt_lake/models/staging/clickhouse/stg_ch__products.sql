{{ config(materialized='table', order_by='product_id') }}

with source as (select *
                from {{ source('ch_raw', 'products') }}),

     deduped as (select *
                 from source
                 where product_id is not null
                 limit 1 by product_id)

select product_id,
       coalesce(nullIf(trimBoth(product_category_name), ''), 'unknown') as category_name,
       product_name_lenght                                              as name_length,
       product_description_lenght                                       as description_length,
       product_photos_qty                                               as photos_qty,
       product_weight_g                                                 as weight_g,
       product_length_cm                                                as length_cm,
       product_height_cm                                                as height_cm,
       product_width_cm                                                 as width_cm
from deduped 