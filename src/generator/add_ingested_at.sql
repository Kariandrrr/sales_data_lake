ALTER TABLE order_items
    ADD COLUMN IF NOT EXISTS _ingested_at TIMESTAMPTZ;
ALTER TABLE order_payments
    ADD COLUMN IF NOT EXISTS _ingested_at TIMESTAMPTZ;
ALTER TABLE order_reviews
    ADD COLUMN IF NOT EXISTS _ingested_at TIMESTAMPTZ;

UPDATE order_items
SET _ingested_at = '2026-01-01'
WHERE _ingested_at IS NULL;
UPDATE order_payments
SET _ingested_at = '2026-01-01'
WHERE _ingested_at IS NULL;
UPDATE order_reviews
SET _ingested_at = '2026-01-01'
WHERE _ingested_at IS NULL;
