INSERT INTO order_reviews (
    review_id, order_id, review_score,
    review_comment_title, review_comment_message,
    review_creation_date, review_answer_timestamp, _ingested_at
)
SELECT
    gen_random_uuid()::text,
    o.order_id,
    1 + floor(random() * 5)::int,
    NULL,
    NULL,
    to_char(o.order_delivered_customer_date::timestamptz + interval '1 day',
            'YYYY-MM-DD HH24:MI:SS'),
    to_char(o.order_delivered_customer_date::timestamptz + interval '3 days',
            'YYYY-MM-DD HH24:MI:SS'),
    CAST(:ds AS timestamptz)
FROM orders o
WHERE o._ingested_at::date = CAST(:ds AS date)
  AND o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND random() < 0.5;
