# CEDARS EMPIRE

Business workspace for AI-enabled services, client work, business grids, account-scoped records, and evidence-led treasury operations.

## Platform scope

- Member portal with account registration, sign-in, tasks, calendar, and business workspace tools
- Customer and client management, work activities, contracts, and service delivery
- Grid Marketplace, AI business operations, and robot readiness/simulation views
- Earnings and wallet records, deposit intents, withdrawal requests, KYC workflows, and referrals
- Administrator-only Command Center, treasury ledger, payment reconciliation, audit records, and operational reports
- Business reports, document tools, scheduled reporting configuration, shared tables, exports, and calendar controls

The platform is business-focused. It does not include legacy nonprofit navigation or former company branding/taglines. Member and administrator workspaces must remain role-separated, with sensitive treasury and reconciliation functions restricted to authorized administrators.

## Test deployment

- Repository: https://github.com/HumanityHorizons/Cedars-Empire
- Test branch: `cedars-empire-test`
- Sitemap and release gates: [SITEMAP.md](SITEMAP.md)
- Test app URL (verify that Streamlit Community Cloud is configured to this repository, branch, and entry point): https://cedars-empire-9lqijkawgdj3sfqkqg25ty.streamlit.app/
- Workflow runs: https://github.com/HumanityHorizons/Cedars-Empire/actions

The shared application shell is intended to use one CEDARS EMPIRE header and horizontal navigation, a Dashboard landing route, member business pages, and administrator-only operational routes. Navigation shortcuts should update the same top-menu and submenu state used by the shared shell.

## Local run

Python 3.12 is recommended.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

The Streamlit entry point, `streamlit_app.py`, imports `app.py`, which owns page configuration, branding, navigation, and rendering. Use dedicated test credentials and a test database for local experiments; do not connect local tests to the production database.

## Configuration

Set deployment credentials in Streamlit Community Cloud **App settings → Secrets** or through environment variables. Never commit actual credentials.

Example configuration (replace placeholders with values held securely by the deployment):

```toml
DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require"
ADMIN_EMAILS = "authorized-admin@example.com"
```

A managed persistent database is required for durable hosted accounts and records. If `DATABASE_URL` is absent, the application may use local SQLite; a temporary filesystem on hosted infrastructure is not durable production storage.

Optional integrations must remain clearly unavailable until configured and tested. These may include an AI provider key, SMTP settings for password-reset email, and explorer/provider API credentials. Never store seed phrases, private keys, passwords, API keys, or withdrawal credentials in the repository or application source.

## Core workflows

- Account registration, sign-in, sign-out, and token-based password reset (email delivery requires SMTP configuration).
- Dashboard, account-scoped tasks, grid marketplace, robot simulation/readiness view, and business operations records.
- Deposits, KYC, and withdrawal request flows with explicit verification and reconciliation states.
- Administrator review of business evidence, treasury settings, and operational records.
- Database-backed records when a persistent database is correctly configured and verified.

## Financial and operational safety

- A submitted transaction hash, explorer lookup, internal review status, or wallet display alone does not establish a reconciled payment.
- Customer wallet balances are liabilities, not company revenue.
- A withdrawal request is not a completed payout.
- Scenario estimates and business pipeline entries are not realized income.
- Package purchases, internal credits, and projected earnings must not be presented as earned revenue by default.
- Robot animation and grid registries are not proof of connected hardware, autonomous work, or earnings.
- Do not enable deposits or cash-out until recipient addresses, token contracts, network, applicable compliance requirements, and reconciliation controls have been independently checked.
- This repository alone does not guarantee that customer charging, on-chain deposits, or withdrawals are fully integrated and operational.

## Verification and release

CI syntax and selected robot/grid/navigation tests are necessary checks, but a green workflow is not sufficient for release. Follow the [production acceptance checklist](SITEMAP.md#production-acceptance-checklist) and test in the hosted test app:

1. Confirm Streamlit points to this repository, the `cedars-empire-test` branch, and the `streamlit_app.py` entry point.
2. Register a dedicated test user, sign out, sign in, and confirm the Dashboard opens.
3. Create a task, refresh the page, restart the app, and confirm the record remains in the configured persistent database.
4. Confirm one user cannot access another user's records and non-admin accounts cannot open administrator routes.
5. Test invalid credentials and password reset with the configured email provider.
6. On a safe test plan, test invalid, pending, failed, wrong-network, wrong-token, wrong-recipient, insufficient-confirmation, and duplicate deposit transactions.
7. Verify desktop and narrow/mobile layouts, navigation shortcuts, exports, and page rendering.
8. Review CI and hosted logs for errors, including database connection, schema/migration, and session-restoration failures.

Do not deploy to production until applicable checks pass, the hosted environment is verified, and the release is explicitly approved. A CI pass does not prove hosted authentication, database persistence, external API integrations, real robot hardware, or completed payouts.

## Privacy and operations

Use least-privilege database access, managed secrets, backups, and tested restore procedures. Before public production use, complete security and privacy review, rate limiting, incident response, monitoring, and applicable legal/compliance review.
