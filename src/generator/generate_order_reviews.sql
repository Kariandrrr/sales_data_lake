INSERT INTO order_reviews (review_id, order_id, review_score, review_comment_title, review_comment_message,
                           review_creation_date, review_answer_timestamp, _ingested_at)
SELECT gen_random_uuid()::text, o.order_id,
       1 + floor(random() * 5)::int, NULL,
       NULL,
       o.order_delivered_at + INTERVAL '1 day', o.order_delivered_at + INTERVAL '3 days', CAST (:ds AS timestamptz)
FROM orders o
WHERE o._ingested_at:: DATE = CAST (:ds AS DATE)
  AND o.order_status = 'delivered'
  AND random()
    < 0.5;
