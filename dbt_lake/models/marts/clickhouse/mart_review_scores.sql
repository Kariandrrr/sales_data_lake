{{ config(
    materialized='table',
    engine='MergeTree',
    order_by='(delay_bucket)'
) }}

with base as (select d.order_id,
                     d.late_days,
                     argMax(r.review_score, r.created_at) AS review_score
              from {{  ref('int_orders_delivery_per_order') }} d
                       INNER JOIN {{ ref('stg_ch__order_reviews') }} r on d.order_id = r.order_id
              group by d.order_id, d.late_days),
     bucketed as (select review_score,
                         case
                             when late_days = 0 then '0'
                             when late_days between 1 and 3 then '1-3'
                             when late_days between 4 and 7 then '4-7'
                             when late_days >= 8 then '8+'
                             else 'unknown'
                             end as delay_bucket
                  from base),
     aggregated as (select delay_bucket,
                           avg(review_score)                    AS avg_review_score,
                           countIf(review_score <= 2) / count() AS share_low_scores,
                           count()                              AS review_count
                    from bucketed
                    group by delay_bucket)
select delay_bucket,
       avg_review_score,
       share_low_scores,
       review_count,
       review_count / sum(review_count) over () as bucket_share, rank() over (order by avg_review_score asc) as score_rank
from aggregated
order by delay_bucket

