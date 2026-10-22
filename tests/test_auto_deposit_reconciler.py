import unittest

from auto_deposit_reconciler import find_intent_candidates, _intent_wallet_is_verified


class AutoDepositMatchingTests(unittest.TestCase):
    def setUp(self):
        self.event = {
            "network": "TRON-TRC20",
            "txid": "a" * 64,
            "sender_address": "TSourceAddress111",
            "receiving_address": "TTreasuryAddress222",
            "amount": "1.000000",
        }
        self.intent = {
            "id": "intent-1",
            "user_email": "user@example.invalid",
            "network": "TRON-TRC20",
            "sender_address": "TSourceAddress111",
            "receiving_address": "TTreasuryAddress222",
            "amount": "1.00",
            "status": "Awaiting payment",
            "consent_accepted": 1,
        }

    def test_exact_unique_match_is_automatic_candidate(self):
        self.assertEqual([self.intent], find_intent_candidates(self.event, [self.intent]))

    def test_different_sender_does_not_match(self):
        other = dict(self.intent, sender_address="TOtherSource333")
        self.assertEqual([], find_intent_candidates(self.event, [other]))

    def test_wrong_amount_does_not_match(self):
        other = dict(self.intent, amount="5.00")
        self.assertEqual([], find_intent_candidates(self.event, [other]))

    def test_multiple_matching_requests_are_ambiguous_not_credited(self):
        second = dict(self.intent, id="intent-2", user_email="other@example.invalid")
        self.assertEqual(2, len(find_intent_candidates(self.event, [self.intent, second])))

    def test_consent_required_for_automatic_credit(self):
        other = dict(self.intent, consent_accepted=0)
        self.assertEqual([], find_intent_candidates(self.event, [other]))

    def test_verified_intents_are_not_reused(self):
        other = dict(self.intent, status="Verified")
        self.assertEqual([], find_intent_candidates(self.event, [other]))

    def test_automatic_credit_requires_verified_wallet_owned_by_same_account(self):
        good = [{
            "user_email": "USER@example.invalid",
            "network": "TRON-TRC20",
            "address": "TSourceAddress111",
            "status": "Verified",
        }]
        self.assertTrue(_intent_wallet_is_verified(self.intent, good))
        self.assertFalse(_intent_wallet_is_verified(
            self.intent, [dict(good[0], user_email="someone-else@example.invalid")]))
        self.assertFalse(_intent_wallet_is_verified(
            self.intent, [dict(good[0], status="Pending verification")]))
        self.assertFalse(_intent_wallet_is_verified(
            self.intent, [dict(good[0], address="TsourceAddress111")]))

    def test_bsc_sender_wallet_verification_is_case_insensitive(self):
        intent = dict(self.intent, network="BSC-BEP20",
                      sender_address="0xAbCd000000000000000000000000000000001234")
        wallets = [{
            "user_email": "user@example.invalid",
            "network": "BSC-BEP20",
            "address": "0xabcd000000000000000000000000000000001234",
            "status": "Verified",
        }]
        self.assertTrue(_intent_wallet_is_verified(intent, wallets))

    def test_bsc_address_matching_is_case_insensitive(self):
        event = dict(self.event, network="BSC-BEP20",
                     sender_address="0xAbCd000000000000000000000000000000001234",
                     receiving_address="0x0D4C2B95E8FB7BE3DB9953BACEF3A4BE643BA77B")
        intent = dict(self.intent, network="BSC-BEP20",
                      sender_address="0xabcd000000000000000000000000000000001234",
                      receiving_address="0x0d4c2b95e8fb7be3db9953bacef3a4be643ba77b")
        self.assertEqual([intent], find_intent_candidates(event, [intent]))


if __name__ == "__main__":
    unittest.main()
