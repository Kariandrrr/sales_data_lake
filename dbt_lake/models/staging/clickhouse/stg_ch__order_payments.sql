{{ config(materialized='table', order_by='(order_id, payment_sequential)') }}
{{ config(
    engine='MergeTree',
    order_by=['(order_id, payment_sequential)'],
    settings={'allow_nullable_key': 1}
) }}

with source as (select *
                from {{ source('ch_raw', 'order_payments') }}),

     cleaned as (select order_id,
                        toInt32(payment_sequential)                as payment_sequential,
                        lower(trimBoth(payment_type))              as payment_type,
                        toInt32(coalesce(payment_installments, 0)) as installments,
                        toDecimal64(coalesce(payment_value, 0), 2) as payment_value
                 from source
                 where order_id is not null
                   and payment_sequential is not null),

     deduped as (select *
                 from cleaned
                 order by payment_value desc
    limit 1 by (order_id, payment_sequential))

select *
from deduped