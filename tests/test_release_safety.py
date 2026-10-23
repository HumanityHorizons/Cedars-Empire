"""Fast, dependency-free release safety checks for CEDARS EMPIRE."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseSafetyTests(unittest.TestCase):
    def read(self, name):
        return (ROOT / name).read_text(encoding="utf-8")

    def test_branding_is_cedars_empire(self):
        app = self.read("app.py")
        self.assertIn('st.set_page_config(page_title="CEDARS EMPIRE"', app)
        self.assertIn("CEDARS EMPIRE", app)

    def test_business_only_route_guard_is_present(self):
        app = self.read("app.py")
        self.assertIn("if page not in BUSINESS_PAGES:", app)
        self.assertIn('page = "Business Dashboard"', app)

    def test_production_database_fails_closed(self):
        app = self.read("app.py")
        self.assertIn("Durable storage is not configured", app)
        self.assertIn("Local SQLite fallback is disabled in production", app)
        self.assertIn("No local fallback was opened", app)

    def test_payment_module_documents_no_private_key_custody(self):
        payments = self.read("hh_real_payments.py")
        self.assertIn("No private-key custody or auto-signing", payments)

    def test_payment_verification_fails_closed(self):
        payments = self.read("hh_real_payments.py")
        self.assertIn("No balance credited", payments)
        self.assertIn("No credit.", payments)

    def test_ci_workflow_is_present(self):
        workflow = ROOT / ".github" / "workflows" / "cedars-release-guard.yml"
        self.assertTrue(workflow.is_file(), "Release guard workflow must exist")
        content = workflow.read_text(encoding="utf-8")
        self.assertIn("compileall", content)
        self.assertIn("unittest", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
