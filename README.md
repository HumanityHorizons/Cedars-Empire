# CEDARS EMPIRE

Business-focused Streamlit workspace for AI-enabled services, grid operations, customer work, account-scoped records, and evidence-led treasury workflows.

## Test deployment

- Repository: https://github.com/HumanityHorizons/Cedars-Empire
- Test branch: `cedars-empire-test`
- Sitemap and release gates: [SITEMAP.md](SITEMAP.md)
- Test app URL (confirm the Streamlit app is configured to this repository and branch): https://cedars-empire-9lqijkawgdj3sfqkqg25ty.streamlit.app/
- Workflow runs: https://github.com/HumanityHorizons/Cedars-Empire/actions

The application uses a shared CEDARS EMPIRE header, horizontal navigation, a dashboard landing route, member business pages, and administrator-only operational routes. Navigation shortcuts should update the same top-menu and submenu state used by the shared shell.

## Local run

Python 3.12 is recommended.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Use a dedicated test database and test credentials. Do not connect a local experiment to the production database.

## Configuration

Set deployment credentials using Streamlit Community Cloud **App settings → Secrets** or environment variables. Never commit actual credentials.

Required for durable hosted persistence:

```toml
DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require"
ADMIN_EMAILS = "authorized-admin@example.com"
```

Optional integrations must remain clearly unavailable until configured and tested. Depending on the feature, these may include an AI provider key, SMTP settings for password-reset email, and explorer/provider API credentials. Never store seed phrases or private keys in this application.

If `DATABASE_URL` is absent, the application may use local SQLite. A temporary filesystem on a hosted service is not durable storage and is not suitable for production accounts or financial records.

## Core workflows

- Account registration, sign-in, sign-out and token-based password reset (email delivery requires SMTP configuration).
- Dashboard, account-scoped tasks, grid marketplace, robot simulation/readiness view and business operations records.
- Deposits, KYC and withdrawal request flows with explicit verification/reconciliation states.
- Administrator review of business evidence, treasury settings and operational records.
- Database-backed records when a persistent database is correctly configured.

## Financial and operational safety

- A user-submitted transaction hash, explorer lookup, internal review status or wallet display alone does not establish a reconciled payment.
- Customer wallet balances are liabilities, not company revenue.
- A withdrawal request is not a completed payout.
- Scenario estimates and business pipeline entries are not realized income.
- Robot animation and grid registries are not proof of connected hardware, autonomous work or earnings.
- Do not enable deposits or cash-out until recipient addresses, token contracts, network, compliance requirements and the reconciliation controls have been independently checked.

## Verification and release

The CI workflow runs syntax checks and selected robot/grid/navigation tests. A green workflow is necessary but not sufficient for release. Follow the [production acceptance checklist](SITEMAP.md#production-acceptance-checklist) and test in the hosted test app:

1. Confirm Streamlit points to the `cedars-empire-test` branch and `app.py` entrypoint.
2. Register a dedicated test user, sign out, sign in and confirm the Dashboard opens.
3. Create a task, refresh, restart the app and confirm the record remains in the configured database.
4. Confirm one user cannot access another user's records and non-admin accounts cannot open admin routes.
5. Test invalid credentials and password reset with the configured email provider.
6. Test invalid, pending, failed, wrong-network, wrong-token, wrong-recipient and duplicate deposit transactions on a safe test plan.
7. Verify layouts on desktop and a narrow/mobile viewport.
8. Review CI and hosted logs for errors. Do not deploy to production until all applicable checks pass and the release is approved.

## Privacy and operations

Use least-privilege database access, managed secrets, backups and tested restore procedures. Before public production use, complete formal security and privacy review, rate limiting, incident response, monitoring and applicable legal/compliance review.
