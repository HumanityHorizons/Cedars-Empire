"""CEDARS EMPIRE business-domain persistence foundation.

This module is intentionally separate from the Streamlit UI. It provides a small,
explicit schema and parameterized operations for business records. It does not
verify payments, create earnings, or execute blockchain transfers.
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _database_url() -> str:
    return os.getenv("DATABASE_URL", "").strip()


class Database:
    """Connection provider supporting PostgreSQL and SQLite.

    PostgreSQL is selected when DATABASE_URL is configured. SQLite is for local
    development only and uses CEDARS_DATA_DIR rather than the system temp folder.
    """

    def __init__(self, database_url: str | None = None, sqlite_path: str | None = None):
        self.database_url = (database_url if database_url is not None else _database_url()).strip()
        default_dir = Path(os.getenv("CEDARS_DATA_DIR", str(Path.home() / ".cedars-empire")))
        self.sqlite_path = Path(sqlite_path) if sqlite_path else default_dir / "cedars_empire.db"

    @property
    def dialect(self) -> str:
        return "postgres" if self.database_url else "sqlite"

    def connect(self):
        if self.database_url:
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError as exc:
                raise RuntimeError("PostgreSQL is configured but psycopg is not installed.") from exc
            return psycopg.connect(self.database_url, row_factory=dict_row)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.sqlite_path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _sql(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.dialect == "postgres" else sql

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def migrate(self) -> None:
        """Create the initial business-domain tables idempotently."""
        statements = [
            """CREATE TABLE IF NOT EXISTS cedars_schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS business_clients (
                id TEXT PRIMARY KEY,
                owner_email TEXT NOT NULL,
                client_name TEXT NOT NULL,
                organization TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            """CREATE INDEX IF NOT EXISTS idx_business_clients_owner
                ON business_clients(owner_email, updated_at)""",
            """CREATE TABLE IF NOT EXISTS business_contracts (
                id TEXT PRIMARY KEY,
                owner_email TEXT NOT NULL,
                client_id TEXT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'DRAFT',
                start_date TEXT,
                end_date TEXT,
                currency TEXT NOT NULL DEFAULT 'USD',
                amount TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(client_id) REFERENCES business_clients(id)
            )""",
            """CREATE INDEX IF NOT EXISTS idx_business_contracts_owner
                ON business_contracts(owner_email, updated_at)""",
            """CREATE TABLE IF NOT EXISTS business_tasks (
                id TEXT PRIMARY KEY,
                owner_email TEXT NOT NULL,
                contract_id TEXT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'OPEN',
                priority TEXT NOT NULL DEFAULT 'NORMAL',
                due_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(contract_id) REFERENCES business_contracts(id)
            )""",
            """CREATE INDEX IF NOT EXISTS idx_business_tasks_owner
                ON business_tasks(owner_email, status, updated_at)""",
            """CREATE TABLE IF NOT EXISTS task_evidence (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                submitted_by TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                evidence_ref TEXT NOT NULL,
                review_status TEXT NOT NULL DEFAULT 'PENDING',
                reviewed_by TEXT,
                reviewed_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(task_id) REFERENCES business_tasks(id)
            )""",
            """CREATE INDEX IF NOT EXISTS idx_task_evidence_task
                ON task_evidence(task_id, created_at)""",
            """CREATE TABLE IF NOT EXISTS business_audit_events (
                id TEXT PRIMARY KEY,
                actor_email TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL DEFAULT '',
                entity_id TEXT NOT NULL DEFAULT '',
                details_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )""",
            """CREATE INDEX IF NOT EXISTS idx_business_audit_created
                ON business_audit_events(created_at)""",
        ]
        with self.transaction() as conn:
            cur = conn.cursor()
            for statement in statements:
                cur.execute(statement if self.dialect == "postgres" else statement)
            cur.execute(self._sql(
                "INSERT INTO cedars_schema_migrations(version, applied_at) VALUES (?, ?) "
                "ON CONFLICT(version) DO NOTHING"
            ), (SCHEMA_VERSION, utc_now()))

    def record_audit(self, actor_email: str, action: str, entity_type: str = "",
                     entity_id: str = "", details_json: str = "{}") -> str:
        event_id = str(uuid.uuid4())
        with self.transaction() as conn:
            conn.cursor().execute(self._sql(
                "INSERT INTO business_audit_events "
                "(id, actor_email, action, entity_type, entity_id, details_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)"
            ), (event_id, actor_email.lower().strip(), action, entity_type, entity_id,
                details_json, utc_now()))
        return event_id

    def create_client(self, owner_email: str, client_name: str, **fields: str) -> str:
        owner = owner_email.lower().strip()
        name = client_name.strip()
        if not owner or not name:
            raise ValueError("A signed-in owner email and client name are required.")
        client_id, now = str(uuid.uuid4()), utc_now()
        with self.transaction() as conn:
            conn.cursor().execute(self._sql(
                "INSERT INTO business_clients "
                "(id, owner_email, client_name, organization, email, phone, status, notes, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            ), (client_id, owner, name, fields.get("organization", "").strip(),
                fields.get("email", "").strip().lower(), fields.get("phone", "").strip(),
                fields.get("status", "ACTIVE").strip().upper(), fields.get("notes", "").strip(), now, now))
        return client_id

    def list_clients(self, owner_email: str) -> list[dict[str, Any]]:
        with self.transaction() as conn:
            cur = conn.cursor()
            cur.execute(self._sql(
                "SELECT id, client_name, organization, email, phone, status, notes, created_at, updated_at "
                "FROM business_clients WHERE owner_email = ? ORDER BY updated_at DESC"
            ), (owner_email.lower().strip(),))
            return [dict(row) for row in cur.fetchall()]

    def create_task(self, owner_email: str, title: str, description: str = "",
                    contract_id: str | None = None, priority: str = "NORMAL",
                    due_at: str | None = None) -> str:
        owner, clean_title = owner_email.lower().strip(), title.strip()
        if not owner or not clean_title:
            raise ValueError("A signed-in owner email and task title are required.")
        task_id, now = str(uuid.uuid4()), utc_now()
        allowed_priorities = {"LOW", "NORMAL", "HIGH", "URGENT"}
        normalized_priority = priority.strip().upper()
        if normalized_priority not in allowed_priorities:
            raise ValueError("Priority must be LOW, NORMAL, HIGH, or URGENT.")
        with self.transaction() as conn:
            conn.cursor().execute(self._sql(
                "INSERT INTO business_tasks "
                "(id, owner_email, contract_id, title, description, status, priority, due_at, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?)"
            ), (task_id, owner, contract_id, clean_title, description.strip(),
                normalized_priority, due_at, now, now))
        return task_id

    def list_tasks(self, owner_email: str) -> list[dict[str, Any]]:
        with self.transaction() as conn:
            cur = conn.cursor()
            cur.execute(self._sql(
                "SELECT id, contract_id, title, description, status, priority, due_at, created_at, updated_at "
                "FROM business_tasks WHERE owner_email = ? ORDER BY updated_at DESC"
            ), (owner_email.lower().strip(),))
            return [dict(row) for row in cur.fetchall()]
