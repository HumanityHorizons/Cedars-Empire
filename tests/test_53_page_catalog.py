"""Static integrity checks for the integrated 53-page navigation hub."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "cedars_pages_hub.py"
APP = ROOT / "app.py"


class CedarsPageCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = HUB.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        assignment = next(
            node for node in cls.tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "CATALOG" for target in node.targets)
        )
        cls.groups = ast.literal_eval(assignment.value)
        cls.app_source = APP.read_text(encoding="utf-8")

    def test_all_53_pages_are_present_in_ordered_sections(self):
        self.assertEqual([len(items) for items in self.groups.values()], [20, 20, 13])
        self.assertEqual(sum(map(len, self.groups.values())), 53)
        titles = [item[0] for items in self.groups.values() for item in items]
        self.assertEqual(len(titles), len(set(titles)))

    def test_brand_is_cedars_empire(self):
        self.assertIn("CEDARS EMPIRE", self.source)
        self.assertNotIn("Humanity Horizons", self.source)

    def test_hub_is_in_existing_navigation_and_allowlist(self):
        self.assertIn('"53-page Website Hub"', self.app_source)
        self.assertIn('render_cedars_pages_hub(menu_groups, IS_ADMIN)', self.app_source)
        self.assertIn("from cedars_pages_hub import render_cedars_pages_hub", self.app_source)

    def test_existing_member_routes_are_allowed_by_the_page_guard(self):
        start = self.app_source.index("BUSINESS_PAGES =")
        end = self.app_source.index("# Fail closed", start)
        allowlist = self.app_source[start:end]
        for route in ["Earnings & Wallet", "My Work & Wallet", "My Tasks", "Staking & Compounding", "53-page Website Hub"]:
            self.assertIn('"' + route + '"', allowlist)

    def test_hub_uses_existing_session_and_database_context(self):
        self.assertIn("menu_groups: dict[str, list[str]]", self.source)
        self.assertIn('st.session_state["ce_pending_top_menu"]', self.source)
        self.assertIn('st.session_state["ce_pending_sub_menu"]', self.source)
        self.assertIn("Existing app authentication, database, and role checks remain the source of truth.", self.source)

    def test_catalog_discloses_unimplemented_workflows(self):
        self.assertIn("A catalog entry is not proof", self.source)
        self.assertIn("No new account store is created", self.source)


if __name__ == "__main__":
    unittest.main()
