INSERT INTO order_payments (order_id, payment_sequential, payment_type, payment_installments, payment_value,
                            _ingested_at)
SELECT order_id,
       n,
       payment_type,
       CASE WHEN payment_type = 'credit_card' THEN 1 + floor(random() * 12)::INT ELSE 1 END,
    round((random() * 190 + 10)::NUMERIC, 2),
    CAST(:ds AS timestamptz)
FROM (
    SELECT
    o.order_id, g.n, (ARRAY['credit_card', 'boleto', 'voucher', 'debit_card'])[1 + floor(random() * 4):: INT] AS payment_type
    FROM orders o
    CROSS JOIN LATERAL generate_series(1, 1 + floor(random() * 2):: INT) AS g(n)
    WHERE o._ingested_at:: DATE = CAST (:ds AS DATE)
    ) AS s;
