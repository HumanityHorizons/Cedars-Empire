"""Unit tests for the isolated CEDARS EMPIRE business persistence foundation."""
import tempfile
import unittest
from pathlib import Path

from cedars_backend import Database


class DatabaseFoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.db")
        self.db = Database(database_url="", sqlite_path=self.db_path)
        self.db.migrate()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_migrations_are_idempotent(self):
        self.db.migrate()
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT version FROM cedars_schema_migrations WHERE version = ?",
                (1,),
            ).fetchone()
        self.assertIsNotNone(row)

    def test_clients_are_scoped_to_owner(self):
        self.db.create_client("Owner@Example.com", "Acme Ltd", organization="Acme")
        self.db.create_client("other@example.com", "Other Ltd")
        self.assertEqual([c["client_name"] for c in self.db.list_clients("owner@example.com")], ["Acme Ltd"])
        self.assertEqual([c["client_name"] for c in self.db.list_clients("other@example.com")], ["Other Ltd"])

    def test_tasks_persist_and_validate_priority(self):
        task_id = self.db.create_task("owner@example.com", "Prepare deliverable", priority="high")
        self.assertEqual(self.db.list_tasks("owner@example.com")[0]["id"], task_id)
        with self.assertRaises(ValueError):
            self.db.create_task("owner@example.com", "Bad priority", priority="SUPER")

    def test_contracts_and_evidence_are_owner_scoped(self):
        client_id = self.db.create_client("owner@example.com", "Owned Client")
        with self.assertRaises(ValueError):
            self.db.create_contract("other@example.com", "Foreign contract", client_id=client_id)
        contract_id = self.db.create_contract("owner@example.com", "Service contract", client_id=client_id)
        task_id = self.db.create_task("owner@example.com", "Deliver work", contract_id=contract_id)
        evidence_id = self.db.create_evidence(task_id, "owner@example.com", "URL", "https://example.invalid/evidence")
        self.assertTrue(evidence_id)
        with self.assertRaises(ValueError):
            self.db.create_evidence(task_id, "other@example.com", "URL", "https://example.invalid/foreign")

    def test_missing_owner_or_name_is_rejected(self):
        with self.assertRaises(ValueError):
            self.db.create_client("", "Acme")
        with self.assertRaises(ValueError):
            self.db.create_task("owner@example.com", "   ")


if __name__ == "__main__":
    unittest.main()
