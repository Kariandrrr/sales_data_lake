INSERT INTO order_items (
    order_id, order_item_id, product_id, seller_id,
    shipping_limit_date, price, freight_value, _ingested_at
)
SELECT
    o.order_id,
    g.n,
    (SELECT product_id FROM products ORDER BY random() LIMIT 1),
    (SELECT seller_id FROM sellers ORDER BY random() LIMIT 1),
    to_char(o.order_purchase_timestamp::timestamptz + interval '3 days',
            'YYYY-MM-DD HH24:MI:SS'),
    round((random() * 190 + 10)::numeric, 2),
    round((random() * 40)::numeric, 2),
    CAST(:ds AS timestamptz)
FROM orders o
CROSS JOIN LATERAL generate_series(1, 1 + floor(random() * 3)::int) AS g(n)
WHERE o._ingested_at::date = CAST(:ds AS date);
