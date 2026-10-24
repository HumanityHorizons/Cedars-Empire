"""Regression guard for Streamlit cookie-manager element-key collisions."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CookieManagerKeyCollisionTests(unittest.TestCase):
    def test_sign_in_does_not_render_cookie_manager_twice_in_one_run(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        issue = source.split("def issue_persistent_session(", 1)[1].split(
            "\ndef restore_persistent_session(", 1
        )[0]
        restore = source.split("def restore_persistent_session(", 1)[1].split(
            "\ndef set_login(", 1
        )[0]
        self.assertNotIn("auth_cookie_manager.get_all()", issue)
        self.assertIn("auth_cookie_manager.get_all()", restore)
        self.assertIn("auth_cookie_manager.set(AUTH_COOKIE_NAME, token", issue)


if __name__ == "__main__":
    unittest.main(verbosity=2)
