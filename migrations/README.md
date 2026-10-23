# PostgreSQL migrations — CEDARS EMPIRE

Status: **NOT VERIFIED** until an isolated PostgreSQL instance completes the connection and migration checks.

## Safety rules
- Run on a dedicated development database first; do not point development at production.
- Configure `DATABASE_URL` only in the hosting provider's secret manager. Never commit or paste it into issues, logs, or chat.
- Use TLS/SSL as required by the database provider and a least-privilege database role.
- Back up any existing database before applying migrations.
- Never drop tables or silently fall back to ephemeral SQLite when PostgreSQL is unavailable.
- Keep deposits, credits, and withdrawals disabled until durable persistence and payment verification pass.

## Migration 0001
`0001_postgres_migration_tracking.sql` creates only two additive tables:
- `schema_migrations`: records migration versions and timestamps.
- `database_health_checks`: records non-sensitive diagnostic check results.

Both statements use `CREATE TABLE IF NOT EXISTS`; this migration does not alter or delete existing application data.

## Verification checklist
1. Confirm `psycopg[binary]` installs from `requirements.txt`.
2. In the development app only, configure a PostgreSQL `DATABASE_URL` in secrets.
3. Connect using a short timeout and run `SELECT current_database(), current_user, version()`; do not print the connection string.
4. Apply migration 0001 in a transaction; insert its version into `schema_migrations` only after all statements succeed.
5. Query both tables and confirm the migration version is present.
6. Write a synthetic, non-financial test record, close the connection, reconnect, and confirm it persists.
7. Restart/redeploy the development app and repeat the read.
8. Test transaction rollback, duplicate primary-key rejection, and required application tables/columns.
9. Confirm the app fails closed on connection/migration errors and does not use SQLite as a fallback.
10. Record results as PASS/FAIL/NOT RUN. Do not label the database verified until all required checks pass.

## Important integration note
This file establishes the first additive migration, not proof of a live connection. The current application initializes many tables through `init_db()`; the next code change must route startup through a versioned migration runner and ensure each migration is recorded transactionally. Until that runner is implemented and tested against development PostgreSQL, status remains **NOT VERIFIED**.
