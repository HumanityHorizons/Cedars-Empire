"""Regression guards for persistent authentication behavior.

These source-level checks complement, but do not replace, hosted browser tests.
They deliberately do not access credentials or production account records.
"""
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")


def test_session_expiry_handles_string_and_datetime_database_values():
    assert 'expires_value = session["expires_at"]' in SOURCE
    assert "isinstance(expires_value, datetime)" in SOURCE
    assert 'datetime.fromisoformat(str(expires_value).replace("Z", "+00:00"))' in SOURCE
    assert "expires_at.astimezone(timezone.utc)" in SOURCE


def test_session_restore_failure_has_safe_diagnostic_without_clearing_data():
    assert "CEDARS_SESSION_RESTORE_FAILED error_type=%s" in SOURCE
    assert 'st.session_state.pop("user_email", None)' in SOURCE
    # Session restore failures should be diagnosable without exposing secrets.
    restore = SOURCE.split("def restore_persistent_session() -> None:", 1)[1].split(
        "\ndef set_login(", 1
    )[0]
    assert "logging.exception" in restore
    assert "password" not in restore.lower().split("except Exception as exc:", 1)[1]


def test_invalid_login_remains_generic_but_logs_non_sensitive_failure_category():
    assert 'st.error("Email or password is incorrect.")' in SOURCE
    assert "reason=account_lookup_miss" in SOURCE
    assert "reason=password_hash_mismatch" in SOURCE
    assert "branch=test" not in SOURCE
