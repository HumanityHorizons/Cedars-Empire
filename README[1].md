# Humanity Horizons — integrated starter

**Tagline:** People, Planet and Peace

This is a deployable Streamlit starter that brings the first core workflows into one application: sign-up/sign-in, personal dashboard, tasks, PDF text extraction, proposal outline workspace, budget lines, opportunity noticeboard, SDG learning brief, CV draft, M&E report draft, potential revenue service catalogue, and a role-protected administrator overview.

## Important status notice

This is a **development starter**, not a fully production-ready platform. It does not yet include a connected generative AI provider, live payment processing, bank reconciliation, automated monthly background scheduler, OCR, email verification, password recovery, production database, cloud object storage, or country-specific payroll/accounting configuration. It does not fabricate revenue or balances. Financial widgets display record counts only until real integrations are implemented and verified.

## Run locally

1. Install Python 3.11 or newer from https://www.python.org/downloads/.
2. Open a terminal in this folder.
3. Run `py -m pip install -r requirements.txt`
4. Run `py -m streamlit run app.py`
5. Open the local URL shown in the terminal.

## Admin setup

Before the **first** launch, set environment variables `HH_ADMIN_EMAIL` and `HH_ADMIN_PASSWORD`. The app creates that admin account if it does not already exist. Use a unique password of at least 16 characters. Do not commit credentials to GitHub. On Windows PowerShell for a local test:

```powershell
$env:HH_ADMIN_EMAIL="admin@example.com"
$env:HH_ADMIN_PASSWORD="replace-with-a-long-unique-password"
py -m streamlit run app.py
```

Set secrets in the hosting platform's Secrets interface for hosted deployments. If the database has already been initialized without an admin, use a reviewed administrative provisioning process rather than changing roles through the UI.

## Streamlit Community Cloud deployment

1. Upload `app.py`, `requirements.txt`, and `README.md` to the GitHub repository root.
2. Open https://share.streamlit.io/ and create an app from the repository.
3. Set the main file path to `app.py`.
4. Add the admin environment variables through the app's Secrets settings, never in the source code.
5. Test sign-up, PDF extraction, budget calculations, user isolation and admin access.

## Data storage warning

The default SQLite database is local to the app environment. Ephemeral hosting can reset local files during redeployment/restart. Do not rely on it for valuable production records. Before real public use, move to a managed database and private object storage, add migrations, backups, monitoring and restore tests.

## Core security notes

- Passwords are hashed using PBKDF2-HMAC-SHA256 with per-user salts.
- Admin page is checked server-side against the authenticated role.
- This starter does not provide a full security review or protection against all production threats.
- Do not upload highly sensitive records until hosting, retention and access controls are reviewed.
- AI output requires human review and should not invent donor requirements, organizational credentials, financial figures or impact data.
