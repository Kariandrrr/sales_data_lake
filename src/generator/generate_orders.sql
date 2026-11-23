DELETE
FROM orders
WHERE _ingested_at::DATE = CAST(:ds AS DATE);

WITH g AS (SELECT MD5(RANDOM()::TEXT || CLOCK_TIMESTAMP()::TEXT)                AS order_id,
                  (SELECT customer_id FROM customers ORDER BY RANDOM() LIMIT 1) AS customer_id,
                  CAST(:ds AS TIMESTAMPTZ) + (RANDOM() * INTERVAL '20 hours')   AS purchase
           FROM GENERATE_SERIES(1, (:rows)::INT))
INSERT
INTO orders (order_id, customer_id, order_status,
             order_purchase_timestamp, order_approved_at,
             order_delivered_carrier_date, order_delivered_customer_date,
             order_estimated_delivery_date, _ingested_at)
SELECT order_id,
       customer_id,
       'delivered',
       purchase,
       purchase + (RANDOM() * INTERVAL '2 hours'),
       purchase + (RANDOM() * INTERVAL '2 days'),
       purchase + INTERVAL '2 days' + (RANDOM() * INTERVAL '12 days'),
       purchase + INTERVAL '10 days' + (RANDOM() * INTERVAL '10 days'),
       CAST(:ds AS TIMESTAMPTZ) + (RANDOM() * INTERVAL '23 hours')
FROM g;