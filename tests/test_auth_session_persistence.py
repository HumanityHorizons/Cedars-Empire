"""Regression checks for login and refresh persistence in CEDARS EMPIRE."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AuthSessionPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (ROOT / "app.py").read_text(encoding="utf-8")
        cls.requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

    def test_cookie_manager_dependency_is_declared(self):
        self.assertIn("extra-streamlit-components", self.requirements)
        self.assertIn("import extra_streamlit_components as stx", self.app)

    def test_database_backed_sessions_are_created(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS login_sessions", self.app)
        self.assertIn("INSERT INTO login_sessions (token_hash,user_email,expires_at,revoked_at,created_at,last_seen_at)", self.app)
        self.assertIn("AUTH_SESSION_DAYS = 14", self.app)

    def test_refresh_restores_only_valid_unrevoked_session(self):
        self.assertIn("def _restore_persistent_session()", self.app)
        self.assertIn("WHERE token_hash=? AND revoked_at IS NULL", self.app)
        self.assertIn("_restore_persistent_session()", self.app)
        self.assertIn("UPDATE login_sessions SET last_seen_at=?", self.app)

    def test_logout_revokes_session_and_deletes_cookie(self):
        self.assertIn("UPDATE login_sessions SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL", self.app)
        self.assertIn("AUTH_COOKIE_MANAGER.delete(AUTH_COOKIE_NAME", self.app)

    def test_login_and_signup_do_not_force_rerun_before_cookie_component_commit(self):
        signin = self.app.split('set_login(users[0], signin_purpose.strip())', 1)[1].split('with signup:', 1)[0]
        self.assertNotIn("st.rerun()", signin)
        signup = self.app.split('set_login(user, purpose.strip())', 1)[1].split('with public:', 1)[0]
        self.assertNotIn("st.rerun()", signup)

    def test_signin_does_not_require_reentering_profile_consent(self):
        signin = self.app.split('with st.form("signin_form")', 1)[1].split('with signup:', 1)[0]
        self.assertNotIn("confirm_profile", signin)
        self.assertNotIn("len(signin_purpose.strip()) < 8", signin)
        self.assertIn('st.form_submit_button("Sign in"', signin)


if __name__ == "__main__":
    unittest.main(verbosity=2)
