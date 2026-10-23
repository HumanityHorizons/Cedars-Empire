import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from daily_crediting import initialize, process_daily_credits, business_date, previous_business_window


class DailyCreditingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "test.sqlite3")

        def connector():
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            return conn, "sqlite"

        self.connector = connector
        initialize(self.connector)
        self.now = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)
        conn, _ = self.connector()
        conn.execute(
            "INSERT INTO earning_rules (id,rule_name,activity_type,rate,reward_type,enabled,requires_verified_funding,created_at) VALUES (?,?,?,?,?,?,?,?)",
            ("r1", "Referral sales", "referral_sale", "0.10", "REFERRAL_COMMISSION", 1, 1, "2026-10-24T12:00:00+00:00"),
        )
        conn.execute(
            "INSERT INTO earning_activities (id,user_email,activity_type,qualifying_volume,currency,evidence_ref,status,funding_verified,risk_score,activity_at,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("a1", "user@example.com", "referral_sale", "100.00", "USDT", "verified-sale-001", "APPROVED", 1, 0, "2026-10-23T12:00:00+00:00", "2026-10-23T12:00:00+00:00"),
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_timezone_business_date(self):
        self.assertEqual(business_date("Pacific/Auckland", self.now), "2026-10-25")
        start, end = previous_business_window("Pacific/Auckland", self.now)
        self.assertLess(start, end)
        self.assertEqual((end - start).total_seconds(), 86400)

    def test_credits_once_and_ledger_matches_wallet(self):
        first = process_daily_credits(self.connector, "Pacific/Auckland", self.now)
        second = process_daily_credits(self.connector, "Pacific/Auckland", self.now)
        self.assertEqual(first["status"], "COMPLETED")
        self.assertEqual(first["count"], 1)
        self.assertEqual(first["amount"], "10.00")
        self.assertEqual(second["status"], "ALREADY_PROCESSED")
        conn, _ = self.connector()
        tx_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        ledger_count = conn.execute("SELECT COUNT(*) FROM ledger_entries").fetchone()[0]
        balance = conn.execute("SELECT available_balance FROM wallets WHERE user_email=?", ("user@example.com",)).fetchone()[0]
        self.assertEqual(tx_count, 1)
        self.assertEqual(ledger_count, 1)
        self.assertEqual(balance, "10.00")
        conn.close()

    def test_unverified_funding_is_not_credited(self):
        conn, _ = self.connector()
        conn.execute("UPDATE earning_activities SET funding_verified=0 WHERE id='a1'")
        conn.commit()
        conn.close()
        result = process_daily_credits(self.connector, "Pacific/Auckland", self.now)
        self.assertEqual(result["count"], 0)
        conn, _ = self.connector()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 0)
        conn.close()

    def test_high_risk_activity_is_flagged_not_credited(self):
        conn, _ = self.connector()
        conn.execute("UPDATE earning_activities SET risk_score=90 WHERE id='a1'")
        conn.commit()
        conn.close()
        result = process_daily_credits(self.connector, "Pacific/Auckland", self.now)
        self.assertEqual(result["count"], 0)
        conn, _ = self.connector()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM fraud_flags").fetchone()[0], 1)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 0)
        conn.close()


if __name__ == "__main__":
    unittest.main()
