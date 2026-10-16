# Humanity Horizons — Email Security Setup Guide

## Included in the candidate application

- Welcome email after account creation, if SMTP delivery is configured.
- Optional sign-in security alert, respecting the account's security-email preference.
- Change password while signed in (requires the current password).
- Forgot-password flow using a one-time six-digit code, stored as a hash, with a 20-minute expiry and up to five code attempts.
- Security email after password change/reset.
- Email notification preferences for security, task updates, earnings/withdrawals, opportunities, and product news.
- Email on task creation/update and an optional opportunity email to users who opt in when an administrator publishes a noticeboard listing.

The candidate does not yet send earnings/withdrawal emails because real reward and crypto-withdrawal workflows are not yet implemented. The preference is ready for those later event hooks. The candidate has not been run in a full Streamlit environment in this audit, and no live app has been changed.

## Required Streamlit Secrets

Open the app's Streamlit Cloud settings, then **Secrets**. Add settings in TOML format. Replace every placeholder with values from your chosen SMTP provider. Do not commit real credentials to GitHub.

```toml
# SMTP email delivery
SMTP_HOST = "smtp.your-email-provider.example"
SMTP_PORT = "587"
SMTP_USERNAME = "your-sending-account"
SMTP_PASSWORD = "YOUR_PROVIDER_SMTP_PASSWORD_OR_APP_PASSWORD"
SMTP_FROM_EMAIL = "notifications@your-verified-domain.example"
SMTP_USE_TLS = "true"

# Required for administrator access in this candidate; use the authorised address(es).
ADMIN_EMAILS = "your-authorised-admin@example.com"

# Configure a managed PostgreSQL URL for durable hosted data before production.
# DATABASE_URL = "YOUR_PRIVATE_POSTGRES_CONNECTION_STRING"
```

The example values above are placeholders, not working credentials. If the provider uses port 465, set `SMTP_PORT = "465"`; the code uses SMTP-over-SSL for that port. For other ports, TLS is enabled when `SMTP_USE_TLS = "true"`.

## Safe setup checklist

1. Choose a reputable email provider and verify the sending domain/address.
2. Generate provider-specific SMTP credentials. If using Gmail, use an App Password where supported; never paste your normal account password into the app.
3. Add the settings to Streamlit Secrets only, not to `app.py`, `requirements.txt`, or GitHub commits.
4. Ensure `ADMIN_EMAILS` is explicitly set. The candidate intentionally no longer grants administrator status through a hard-coded default email.
5. Deploy to a staging copy first and test: signup email, sign-in alert, change password, expired code, incorrect code, one-time code use, task email, and opted-in opportunity email.
6. Confirm spam-folder/delivery behavior and rate limits with your provider.
7. Configure a managed PostgreSQL database and backups before production use; the temporary SQLite fallback is not durable on many hosted deployments.
8. Do not enable real crypto rewards or withdrawals until those workflows, ledger reconciliation, and legal/security reviews are complete.

## Candidate status

Static Python compile and AST checks passed. The SQL schemas, including the new email-preference and password-reset tables, executed successfully in a temporary SQLite test. This is not a full browser/UI test or a live SMTP test. The environment used for this audit did not have Streamlit installed, so full application runtime testing remains outstanding.
