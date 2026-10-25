import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import hh_real_payments as p


class PaymentModuleTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        db_path = str(Path(self._temp.name) / "payments.sqlite3")

        def connect():
            conn = sqlite3.connect(db_path, timeout=5)
            conn.row_factory = sqlite3.Row
            return conn, "sqlite"

        def execute(sql, params=()):
            conn, _kind = connect()
            try:
                cur = conn.execute(sql, params)
                conn.commit()
                return cur.rowcount
            finally:
                conn.close()

        def all_rows(sql, params=()):
            conn, _kind = connect()
            try:
                cur = conn.execute(sql, params)
                return [dict(row) for row in cur.fetchall()]
            finally:
                conn.close()

        self.db_connect = connect
        self.db_exec = execute
        self.db_all = all_rows
        p.ensure_payment_tables(self.db_exec, self.db_all)

    def tearDown(self):
        self._temp.cleanup()

    def _approve_sender(self, email, network, address):
        now = "2026-10-21T00:00:00+00:00"
        self.db_exec(
            "INSERT INTO hh_verified_sender_wallets(id,user_email,network,address,status,verification_method,evidence_reference,verified_by,verification_note,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            ("wallet-row-1", email, network, address, "Verified", "Signed wallet challenge",
             "unit-test-evidence", "admin@test.invalid", "Approved by test fixture", now, now),
        )

    def _create_test_intent(self, amount=Decimal("1.00")):
        email = "participant@test.invalid"
        network = "BSC-BEP20"
        treasury = "0x0d4c2B95e8FB7Be3DB9953bAcEf3A4Be643bA77B"
        sender = "0x1111111111111111111111111111111111111111"
        self._approve_sender(email, network, sender)
        now = lambda: "2026-10-21T00:00:00+00:00"
        intent = p._create_intent(email, amount, network, treasury, sender,
                                  "Test deposit", self.db_exec, self.db_all, True, now,
                                  True, p.DEPOSIT_CONSENT_VERSION, p.DEPOSIT_CONSENT_TEXT)
        return email, network, treasury, sender, intent, now
    def test_bsc_address_valid(self):
        self.assertTrue(p.validate_destination("BSC-BEP20", "0x0d4c2B95e8FB7Be3DB9953bAcEf3A4Be643bA77B"))

    def test_bsc_invalid(self):
        self.assertFalse(p.validate_destination("BSC-BEP20", "0xabc"))

    def test_tron_treasury_checksum(self):
        self.assertTrue(p.validate_destination("TRON-TRC20", "TE26B7zQjMbahYAWcxEsSPC6aZEr2Hcz1u"))

    def test_invalid_tron_rejected(self):
        self.assertFalse(p.validate_destination("TRON-TRC20", "T-not-a-wallet"))

    def test_unsupported_network_rejected(self):
        self.assertFalse(p.validate_destination("ETH-ERC20", "0x" + "1" * 40))

    def test_deposit_packages_are_plain_amounts(self):
        self.assertEqual(p.PACKAGE_AMOUNTS["Deposit $1 — verification"], Decimal("1.00"))
        self.assertEqual(p.PACKAGE_AMOUNTS["Deposit $25"], Decimal("25.00"))

    def test_nonfinite_amount_rejected(self):
        with self.assertRaises(p.PaymentError):
            p._decimal("NaN")

    def test_zero_transfer_rejected_before_network_access(self):
        with self.assertRaises(p.PaymentError):
            p.verify_transfer("TRON-TRC20", "0" * 64, Decimal("0"),
                              "TE26B7zQjMbahYAWcxEsSPC6aZEr2Hcz1u", "in")

    def test_incoming_deposit_requires_sender_wallet(self):
        with self.assertRaises(p.PaymentError):
            p.verify_transfer("TRON-TRC20", "a" * 64, Decimal("1"),
                              "TE26B7zQjMbahYAWcxEsSPC6aZEr2Hcz1u", "in")

    def test_treasury_self_transfer_is_not_a_deposit(self):
        treasury = "TE26B7zQjMbahYAWcxEsSPC6aZEr2Hcz1u"
        with self.assertRaises(p.PaymentError):
            p.verify_transfer("TRON-TRC20", "a" * 64, Decimal("1"), treasury, "in", expected_sender=treasury)

    def _bsc_incoming_rpc(self, txid, sender):
        treasury = "0x0d4c2B95e8FB7Be3DB9953bAcEf3A4Be643bA77B"
        receiver_topic = "0x" + "0" * 24 + treasury[2:].lower()
        sender_topic = "0x" + "0" * 24 + sender[2:].lower()
        receipt = {
            "status": "0x1",
            "blockNumber": "0x64",
            "logs": [{
                "address": p.DEFAULT_BSC_PEG_USDT_CONTRACT,
                "topics": [p.TRANSFER_TOPIC, sender_topic, receiver_topic],
                "data": hex(10**18),
            }],
        }
        def fake_rpc(url, method, params):
            if method == "eth_chainId":
                return "0x38"
            if method == "eth_getTransactionByHash":
                return {"hash": txid}
            if method == "eth_getTransactionReceipt":
                return receipt
            if method == "eth_blockNumber":
                return "0x100"
            raise AssertionError("Unexpected RPC method: " + method)
        return fake_rpc

    def test_bsc_deposit_requires_expected_sender_match(self):
        txid = "0x" + "a" * 64
        sender = "0x1111111111111111111111111111111111111111"
        with patch.object(p, "_rpc", side_effect=self._bsc_incoming_rpc(txid, sender)):
            result = p.verify_transfer(
                "BSC-BEP20", txid, Decimal("1"),
                "0x0d4c2B95e8FB7Be3DB9953bAcEf3A4Be643bA77B", "in",
                bsc_token_contract=p.DEFAULT_BSC_PEG_USDT_CONTRACT,
                bsc_rpc_url="https://unit.test.invalid", expected_sender=sender,
            )
        self.assertEqual(result["status"], "Verified")

    def test_bsc_transfer_from_another_sender_is_not_credited(self):
        txid = "0x" + "b" * 64
        actual_sender = "0x1111111111111111111111111111111111111111"
        claimed_sender = "0x2222222222222222222222222222222222222222"
        with patch.object(p, "_rpc", side_effect=self._bsc_incoming_rpc(txid, actual_sender)):
            result = p.verify_transfer(
                "BSC-BEP20", txid, Decimal("1"),
                "0x0d4c2B95e8FB7Be3DB9953bAcEf3A4Be643bA77B", "in",
                bsc_token_contract=p.DEFAULT_BSC_PEG_USDT_CONTRACT,
                bsc_rpc_url="https://unit.test.invalid", expected_sender=claimed_sender,
            )
        self.assertEqual(result["status"], "Needs review")

    def test_create_intent_does_not_require_manual_admin_wallet_review(self):
        email = "participant@test.invalid"
        network = "BSC-BEP20"
        treasury = "0x0d4c2B95e8FB7Be3DB9953bAcEf3A4Be643bA77B"
        sender = "0x1111111111111111111111111111111111111111"
        now = lambda: "2026-10-21T00:00:00+00:00"
        intent = p._create_intent(email, Decimal("1"), network, treasury, sender,
                                  "Deposit $1", self.db_exec, self.db_all, True, now,
                                  True, p.DEPOSIT_CONSENT_VERSION, p.DEPOSIT_CONSENT_TEXT)
        saved = self.db_all("SELECT status,sender_address,consent_accepted FROM hh_payment_intents WHERE id=?", (intent["id"],))[0]
        self.assertEqual(saved["status"], "Awaiting payment")
        self.assertEqual(saved["sender_address"], sender)
        self.assertEqual(saved["consent_accepted"], 1)

    def test_confirmed_deposit_credit_is_idempotent(self):
        email, network, treasury, sender, intent, now = self._create_test_intent(Decimal("1.00"))
        result = {"status": "Verified", "actual_amount": "1.000000000000000000", "message": "mock-verified"}
        txid = "0x" + "a" * 64
        p._credit_deposit(self.db_connect, True, intent["id"], txid, result, now)
        p._credit_deposit(self.db_connect, True, intent["id"], txid, result, now)
        account = self.db_all("SELECT * FROM hh_wallet_accounts WHERE user_email=? AND network=?", (email, network))[0]
        self.assertEqual(Decimal(account["available_balance"]), Decimal("1"))
        self.assertEqual(Decimal(account["reserved_balance"]), Decimal("0"))
        entries = self.db_all("SELECT * FROM hh_wallet_ledger WHERE entry_type=?", ("confirmed_deposit_credit",))
        self.assertEqual(len(entries), 1)
        intent_row = self.db_all("SELECT consent_accepted,consent_version,consent_text,consented_at FROM hh_payment_intents WHERE id=?", (intent["id"],))[0]
        self.assertEqual(intent_row["consent_accepted"], 1)
        self.assertEqual(intent_row["consent_version"], p.DEPOSIT_CONSENT_VERSION)
        self.assertIn("rather than company revenue", intent_row["consent_text"])
        self.assertTrue(intent_row["consented_at"])
        queue = self.db_all("SELECT * FROM hh_grid_deployment_queue WHERE payment_intent_id=?", (intent["id"],))
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["status"], "Blocked - user wallet liability")
        self.assertEqual(queue[0]["requested_scope"], "ALL GRIDS")

    def test_consent_is_mandatory_before_creating_intent(self):
        email = "participant@test.invalid"
        network = "BSC-BEP20"
        treasury = "0x0d4c2B95e8FB7Be3DB9953bAcEf3A4Be643bA77B"
        sender = "0x1111111111111111111111111111111111111111"
        self._approve_sender(email, network, sender)
        now = lambda: "2026-10-21T00:00:00+00:00"
        with self.assertRaises(p.PaymentError):
            p._create_intent(email, Decimal("1"), network, treasury, sender,
                             "Deposit $1", self.db_exec, self.db_all, True, now,
                             False, p.DEPOSIT_CONSENT_VERSION, p.DEPOSIT_CONSENT_TEXT)
        rows = self.db_all("SELECT id FROM hh_payment_intents WHERE user_email=?", (email,))
        self.assertEqual(rows, [])

    def test_unmatched_txid_is_audited_without_reserving_txid(self):
        email, network, treasury, sender, intent, now = self._create_test_intent()
        txid = "0x" + "f" * 64
        with patch.object(p, "verify_transfer", return_value={
            "status": "Needs review", "message": "No unique expected token transfer matched."
        }):
            result = p._verify_deposit(
                intent, txid, self.db_all, self.db_exec, self.db_connect, True,
                "TE26B7zQjMbahYAWcxEsSPC6aZEr2Hcz1u", treasury,
                p.DEFAULT_BSC_PEG_USDT_CONTRACT, "https://unit.test.invalid", "", now
            )
        row = self.db_all("SELECT txid,last_attempted_txid,status FROM hh_payment_intents WHERE id=?", (intent["id"],))[0]
        self.assertEqual(result["status"], "Needs review")
        self.assertIsNone(row["txid"])
        self.assertEqual(row["last_attempted_txid"], txid)
        self.assertEqual(row["status"], "Needs review")

    def test_unreviewed_sender_wallet_cannot_be_credited(self):
        email = "unreviewed@test.invalid"
        network = "BSC-BEP20"
        treasury = "0x0d4c2B95e8FB7Be3DB9953bAcEf3A4Be643bA77B"
        sender = "0x3333333333333333333333333333333333333333"
        now = lambda: "2026-10-22T00:00:00+00:00"
        intent = p._create_intent(
            email, Decimal("1"), network, treasury, sender, "Test deposit",
            self.db_exec, self.db_all, True, now, True,
            p.DEPOSIT_CONSENT_VERSION, p.DEPOSIT_CONSENT_TEXT,
        )
        with patch.object(p, "verify_transfer") as chain_check:
            with self.assertRaisesRegex(p.PaymentError, "ownership must be independently verified"):
                p._verify_deposit(
                    intent, "0x" + "a" * 64, self.db_all, self.db_exec,
                    self.db_connect, True,
                    "TE26B7zQjMbahYAWcxEsSPC6aZEr2Hcz1u", treasury,
                    p.DEFAULT_BSC_PEG_USDT_CONTRACT, "https://unit.test.invalid", "", now,
                )
            chain_check.assert_not_called()
        balance_rows = self.db_all(
            "SELECT available_balance FROM hh_wallet_accounts WHERE user_email=? AND network=?",
            (email, network),
        )
        self.assertEqual(balance_rows, [])

    def test_deposit_credit_helper_rejects_unverified_result(self):
        with self.assertRaises(p.PaymentError):
            p._credit_deposit(lambda: self.fail("database should not be opened"),
                              True, "intent", "0x" + "a" * 64,
                              {"status": "Pending"}, lambda: "2026-10-21T00:00:00+00:00")

    def test_cashout_rejection_releases_reserved_balance(self):
        email, network, treasury, sender, intent, now = self._create_test_intent(Decimal("5.00"))
        txid = "0x" + "c" * 64
        p._credit_deposit(self.db_connect, True, intent["id"], txid,
                          {"status": "Verified", "actual_amount": "5.000000000000000000", "message": "mock-verified"}, now)
        destination = "0x2222222222222222222222222222222222222222"
        request_id = p._new_cashout(self.db_connect, True, email, network, Decimal("3"),
                                    destination, treasury, now)
        reserved = self.db_all("SELECT * FROM hh_wallet_accounts WHERE user_email=? AND network=?", (email, network))[0]
        self.assertEqual(Decimal(reserved["available_balance"]), Decimal("2"))
        self.assertEqual(Decimal(reserved["reserved_balance"]), Decimal("3"))
        p._cashout_decision(self.db_connect, True, request_id, "Rejected", "Unit-test rejection", now)
        released = self.db_all("SELECT * FROM hh_wallet_accounts WHERE user_email=? AND network=?", (email, network))[0]
        self.assertEqual(Decimal(released["available_balance"]), Decimal("5"))
        self.assertEqual(Decimal(released["reserved_balance"]), Decimal("0"))

    def test_cashout_cannot_target_treasury(self):
        treasury = "0x0d4c2B95e8FB7Be3DB9953bAcEf3A4Be643bA77B"
        with self.assertRaises(p.PaymentError):
            p._new_cashout(self.db_connect, True, "participant@test.invalid", "BSC-BEP20",
                           Decimal("1"), treasury, treasury,
                           lambda: "2026-10-21T00:00:00+00:00")

    def test_cashout_paid_rejects_amount_mismatch(self):
        email, network, treasury, sender, intent, now = self._create_test_intent(Decimal("5.00"))
        deposit_txid = "0x" + "d" * 64
        p._credit_deposit(self.db_connect, True, intent["id"], deposit_txid,
                          {"status": "Verified", "actual_amount": "5.000000000000000000", "message": "mock-verified"}, now)
        destination = "0x2222222222222222222222222222222222222222"
        request_id = p._new_cashout(self.db_connect, True, email, network, Decimal("3"),
                                    destination, treasury, now)
        p._cashout_decision(self.db_connect, True, request_id, "Approved for manual processing", "approved", now)
        with self.assertRaises(p.PaymentError):
            p._cashout_paid(self.db_connect, True, request_id, "0x" + "e" * 64,
                            {"status": "Verified", "actual_amount": "2.000000000000000000"},
                            now)
        request = self.db_all("SELECT status FROM hh_cashout_requests WHERE id=?", (request_id,))[0]
        account = self.db_all("SELECT * FROM hh_wallet_accounts WHERE user_email=? AND network=?", (email, network))[0]
        self.assertEqual(request["status"], "Approved for manual processing")
        self.assertEqual(Decimal(account["reserved_balance"]), Decimal("3"))

    def test_cashout_txid_uniqueness_index_exists(self):
        found = self.db_all("SELECT name FROM sqlite_master WHERE type='index' AND name=?",
                            ("uq_hh_cashout_network_txid",))
        self.assertEqual(len(found), 1)

    def test_cashout_paid_helper_rejects_unverified_result(self):
        with self.assertRaises(p.PaymentError):
            p._cashout_paid(lambda: self.fail("database should not be opened"),
                            True, "request", "0x" + "a" * 64,
                            {"status": "Needs review"}, lambda: "2026-10-21T00:00:00+00:00")

    def test_verified_intent_without_ledger_is_repaired_idempotently(self):
        email, network, treasury, sender, intent, now = self._create_test_intent(Decimal("1.00"))
        txid = "0x" + "c" * 64
        self.db_exec("UPDATE hh_payment_intents SET status=?,txid=? WHERE id=?", ("Verified", txid, intent["id"]))
        result = {"status": "Verified", "actual_amount": "1.000000000000000000", "message": "reverified on-chain"}
        p._credit_deposit(self.db_connect, True, intent["id"], txid, result, now)
        p._credit_deposit(self.db_connect, True, intent["id"], txid, result, now)
        account = self.db_all("SELECT available_balance FROM hh_wallet_accounts WHERE user_email=? AND network=?", (email, network))[0]
        self.assertEqual(Decimal(account["available_balance"]), Decimal("1"))
        self.assertEqual(len(self.db_all("SELECT id FROM hh_wallet_ledger WHERE reference_id=? AND entry_type=?", (intent["id"], "confirmed_deposit_credit"))), 1)
        self.assertEqual(len(self.db_all("SELECT id FROM hh_grid_deployment_queue WHERE payment_intent_id=?", (intent["id"],))), 1)

    def test_grid_gate_backfills_verified_receipts_with_ledger_credit(self):
        email, network, treasury, sender, intent, now = self._create_test_intent(Decimal("1.00"))
        txid = "0x" + "d" * 64
        result = {"status": "Verified", "actual_amount": "1.000000000000000000", "message": "verified"}
        p._credit_deposit(self.db_connect, True, intent["id"], txid, result, now)
        self.db_exec("DELETE FROM hh_grid_deployment_queue WHERE payment_intent_id=?", (intent["id"],))
        repaired = p.sync_grid_deployment_queue(self.db_all, self.db_exec, now)
        self.assertEqual(repaired["gate_events_backfilled"], 1)
        self.assertEqual(len(self.db_all("SELECT id FROM hh_grid_deployment_queue WHERE payment_intent_id=?", (intent["id"],))), 1)

    def test_bsc_token_warning_is_explicit(self):
        label = p._network_label("BSC-BEP20", p.DEFAULT_BSC_PEG_USDT_CONTRACT)
        self.assertIn("Binance-Peg", label)
        self.assertIn("not native Tether-issued USDT", label)

    def test_streamlit_routes_are_integrated_and_legacy_paid_path_is_disabled(self):
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertIn('TREASURY_ADDRESS = "TE26B7zQjMbahYAWcxEsSPC6aZEr2Hcz1u"', source)
        self.assertIn('BNB_TREASURY_ADDRESS = "0x0d4c2B95e8FB7Be3DB9953bAcEf3A4Be643bA77B"', source)
        for route in (
            'elif page == "Deposit & Packages":',
            'elif page == "Withdraw / Cash Out":',
            'elif page == "Payment Operations" and IS_ADMIN:',
        ):
            self.assertIn(route, source)
        self.assertNotIn('elif page == "Packages":', source)
        # Navigation is now grouped into compact business menus; test the new contract
        # instead of depending on the retired flat user_pages list.
        self.assertIn('"Earnings": ["Earnings & Wallet", "Deposit & Packages", "Withdrawals & Full KYC", "Staking & Compounding", "Referral Program"]', source)
        self.assertIn('"Customer & Client Management"', source)
        self.assertIn('"Studio": "Live Studio"', source)
        self.assertIn('"Deposit": "Deposit & Packages"', source)
        self.assertNotIn('"Packages":', source)
        self.assertIn('menu_groups = admin_menu if IS_ADMIN else business_menu', source)
        self.assertIn('selected_page = st.selectbox("Pages"', source)
        self.assertIn("Deposit & Packages QR integration (build 2026-10-21)", source)
        payment_source = Path("hh_real_payments.py").read_text(encoding="utf-8")
        deposit_start = payment_source.index("def _deposit_ui(")
        deposit_end = payment_source.index("def render_cashout_page(", deposit_start)
        deposit_ui = payment_source[deposit_start:deposit_end]
        self.assertIn('st.title("Deposit & Packages")', deposit_ui)
        self.assertLess(deposit_ui.index("_show_address(st,network,address,bsc_token)"), deposit_ui.index("if not durable:"))
        self.assertIn("I have read and agree to the deposit consent above.", deposit_ui)
        self.assertIn("def _render_deposit_history", payment_source)
        self.assertIn("hh_grid_deployment_queue", payment_source)
        self.assertNotIn('"Rejected", "Paid (reference required)"', source)
        self.assertIn("Do not mark this request paid here", source)
        # The live app may use optional references in its general ledger; payment settlement still requires on-chain verification.
        payment_source = Path("hh_real_payments.py").read_text(encoding="utf-8")
        self.assertIn("hh_verified_sender_wallets", payment_source)
        self.assertIn("expected transaction source", payment_source)
        self.assertNotIn("This sender wallet is not admin-verified for your account yet", payment_source)
        self.assertIn("a self-transfer is not a deposit", payment_source)


if __name__ == "__main__":
    unittest.main()
