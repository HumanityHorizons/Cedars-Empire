"""Static integrity checks for the additive 53-page catalog."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "pages" / "53_Cedars_Pages.py"


class CedarsPageCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = PAGE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        assignment = next(
            node for node in cls.tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "GROUPS" for target in node.targets)
        )
        cls.groups = ast.literal_eval(assignment.value)

    def test_all_53_pages_are_present(self):
        self.assertEqual([len(items) for items in self.groups.values()], [20, 20, 13])
        self.assertEqual(sum(map(len, self.groups.values())), 53)

    def test_brand_is_cedars_empire(self):
        self.assertIn("CEDARS EMPIRE", self.source)
        self.assertNotIn("Humanity Horizons", self.source)

    def test_existing_authentication_is_required(self):
        self.assertIn('st.session_state.get("user_email", "")', self.source)
        self.assertIn("st.stop()", self.source)

    def test_admin_section_fails_closed_without_role_flag(self):
        self.assertIn('st.session_state.get("is_admin", False)', self.source)
        self.assertIn('group == "03 · Administrator" and not is_admin', self.source)

    def test_page_catalog_does_not_claim_real_money_actions(self):
        self.assertIn("No funds, earnings, payment status, or KYC status are generated", self.source)
        self.assertIn("persistence tests are required before production release", self.source)


if __name__ == "__main__":
    unittest.main()
