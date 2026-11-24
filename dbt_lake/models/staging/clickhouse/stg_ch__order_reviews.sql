{{ config(
    order_by=['review_id']
) }}

with source as (select *
                from {{ source('ch_raw', 'order_reviews') }}),

     cleaned as (select review_id,
                        order_id,
                        toInt32(coalesce(review_score, 0))                               as review_score,
                        review_comment_title,
                        review_comment_message,
                        parseDateTimeBestEffortOrNull(toString(review_creation_date))    as created_at,
                        parseDateTimeBestEffortOrNull(toString(review_answer_timestamp)) as answered_at
                 from source
                 where review_id is not null),

     deduped as (select *
                 from cleaned
                 order by answered_at desc nulls last
    limit 1 by review_id)

select *
from deduped