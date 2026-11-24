-- Insert :rows new delivered orders for logical date :ds.
-- Cleanup of the previous batch is done by generate.py (FK-safe order).
INSERT INTO orders (order_id, customer_id, order_status,
                    order_purchase_timestamp, order_approved_at,
                    order_delivered_at, order_estimated_delivery_date,
                    _ingested_at)
SELECT gen_random_uuid()::TEXT,
       (SELECT customer_id FROM customers ORDER BY RANDOM() LIMIT 1),
       'delivered',
       purchase,
       purchase + INTERVAL '2 hours',
       purchase + (INTERVAL '1 day' * (2 + FLOOR(RANDOM() * 12)::INT)),
       purchase + (INTERVAL '1 day' * (10 + FLOOR(RANDOM() * 10)::INT)),
       CAST(:ds AS TIMESTAMPTZ)
FROM (SELECT CAST(:ds AS TIMESTAMPTZ) - (INTERVAL '1 day' * FLOOR(RANDOM() * 20)::INT) AS purchase
      FROM GENERATE_SERIES(1, :rows)) AS s;
