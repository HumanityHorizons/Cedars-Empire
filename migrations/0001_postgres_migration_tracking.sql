-- CEDARS EMPIRE PostgreSQL migration 0001
-- Safe, additive migration. Does not drop or rewrite application data.
-- Apply only to the isolated development PostgreSQL database first.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS database_health_checks (
    check_id TEXT PRIMARY KEY,
    check_type TEXT NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);
