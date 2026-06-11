ALTER TABLE users
    ADD COLUMN IF NOT EXISTS age INTEGER,
    ADD COLUMN IF NOT EXISTS favorite_sport VARCHAR(128);

ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(128);

ALTER TABLE tickets
    DROP CONSTRAINT IF EXISTS uq_tickets_campaign_source_reason;

UPDATE tickets
SET idempotency_key = CONCAT('legacy-ticket-', id)
WHERE idempotency_key IS NULL;

ALTER TABLE tickets
    ALTER COLUMN idempotency_key SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_tickets_idempotency_key'
    ) THEN
        ALTER TABLE tickets
            ADD CONSTRAINT uq_tickets_idempotency_key UNIQUE (idempotency_key);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_tickets_idempotency_key ON tickets (idempotency_key);
