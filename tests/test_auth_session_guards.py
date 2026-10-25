"""Regression guards for persistent authentication behavior.

These source-level checks complement hosted browser and database tests.
They do not access credentials or production account records.
"""
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")


def test_session_expiry_normalizes_database_timestamp_values():
    assert 'expires_value = session["expires_at"]' in SOURCE
    assert "isinstance(expires_value, datetime)" in SOURCE
    assert 'datetime.fromisoformat(str(expires_value).replace("Z", "+00:00"))' in SOURCE
    assert "expires_at.astimezone(timezone.utc)" in SOURCE


def test_session_restore_exception_has_safe_diagnostic():
    assert 'logging.exception("CEDARS_SESSION_RESTORE_FAILED error_type=%s", type(exc).__name__)' in SOURCE


def test_login_error_stays_generic_and_logs_failure_categories():
    assert 'st.error("Email or password is incorrect.")' in SOURCE
    assert "reason=account_lookup_miss" in SOURCE
    assert "reason=password_hash_mismatch" in SOURCE
