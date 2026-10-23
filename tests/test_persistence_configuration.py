from pathlib import Path

APP_SOURCE = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")


def test_production_does_not_silently_fall_back_to_sqlite():
    assert "Durable storage is not configured." in APP_SOURCE
    assert "Local SQLite fallback is disabled in production." in APP_SOURCE
    assert "No local fallback was opened" in APP_SOURCE


def test_database_url_uses_postgres_driver():
    assert 'import psycopg' in APP_SOURCE
    assert 'psycopg.connect(DATABASE_URL' in APP_SOURCE


def test_existing_schema_is_preserved_with_create_if_not_exists():
    assert "CREATE TABLE IF NOT EXISTS users" in APP_SOURCE
    assert "CREATE TABLE IF NOT EXISTS tasks" in APP_SOURCE
    assert "CREATE TABLE IF NOT EXISTS treasury_ledger" in APP_SOURCE


def test_password_hashing_remains_high_iteration_pbkdf2():
    assert "PBKDF2_ITERATIONS = 310_000" in APP_SOURCE
    assert "hashlib.pbkdf2_hmac" in APP_SOURCE
