INSERT INTO orders (
    order_id, customer_id, order_status,
    order_purchase_timestamp, order_approved_at,
    order_delivered_carrier_date, order_delivered_customer_date,
    order_estimated_delivery_date, _ingested_at
)
SELECT
    gen_random_uuid()::text,
    (SELECT customer_id FROM customers ORDER BY random() LIMIT 1),
    'delivered',
    to_char(purchase, 'YYYY-MM-DD HH24:MI:SS'),
    to_char(purchase + interval '2 hours', 'YYYY-MM-DD HH24:MI:SS'),
    to_char(purchase + interval '1 day', 'YYYY-MM-DD HH24:MI:SS'),
    to_char(delivered, 'YYYY-MM-DD HH24:MI:SS'),
    to_char(estimated, 'YYYY-MM-DD HH24:MI:SS'),
    CAST(:ds AS timestamptz)
FROM (
    SELECT
        purchase,
        purchase + (interval '1 day' * (2 + floor(random() * 12)::int))  AS delivered,
        purchase + (interval '1 day' * (10 + floor(random() * 10)::int)) AS estimated
    FROM (
        SELECT CAST(:ds AS timestamptz)
               - (interval '1 day' * floor(random() * 20)::int) AS purchase
        FROM generate_series(1, :rows)
    ) p
) s;
