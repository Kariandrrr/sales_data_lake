INSERT INTO order_items (order_id, product_id, seller_id, price, freight_value, _ingested_at)
SELECT o.order_id,
       (SELECT product_id FROM products ORDER BY RANDOM() LIMIT 1),
       (SELECT seller_id FROM sellers ORDER BY RANDOM() LIMIT 1),
       ROUND((RANDOM() * 190 + 10)::NUMERIC, 2),
       ROUND((RANDOM() * 40)::NUMERIC, 2),
       CAST(:ds AS TIMESTAMPTZ)
FROM orders o
         CROSS JOIN LATERAL GENERATE_SERIES(1, 1 + FLOOR(RANDOM() * 3):: INT) AS g(n)
WHERE o._ingested_at:: DATE = CAST(:ds AS DATE);
