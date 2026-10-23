# CEDARS EMPIRE

Business workspace for real AI-enabled services, client work, business grids, verified revenue records and controlled treasury operations.

## Platform scope

- Member Portal with account registration, sign-in, tasks, calendar and business workspace tools
- Business client and customer management
- Work activities, contracts and service delivery
- Grid Marketplace and AI business operations
- Earnings, deposit intents, withdrawal requests and referral records
- KYC workflow and administrator-reviewed payment operations
- Executive Command Center, treasury ledger and audit records for authorized administrators
- Business reports, document tools and scheduled reporting configuration
- Shared workspace tables, exports and calendar controls

## Branding and navigation

- Product name: **CEDARS EMPIRE**
- Business-only platform; no NGO division or NGO Operations navigation
- No legacy Humanity Horizons branding, “360” branding or former tagline
- Member and administrator workspaces remain role-separated; sensitive treasury and reconciliation functions are administrator-only

## Data and deployment

The app launches from `streamlit_app.py`, which imports `app.py`. Configure secrets and a managed persistent database before relying on hosted data durability. A temporary local SQLite database is not a durable production store on ephemeral hosting.

Before deployment, back up the repository and test registration, sign-in, refresh persistence, role restrictions, business navigation, task storage, exports and the deployed app's page rendering.

## Payment and revenue limitations

The application records payment intents, requests and treasury ledger entries; those records alone do not prove that money arrived or that a payment was sent. Do not label revenue as verified without independent transaction evidence and a successful network-specific verification. This repository does not by itself guarantee that customer charging, on-chain deposits, or withdrawals are fully integrated and operational.

Never commit passwords, API keys, seed phrases, private keys or withdrawal credentials. Keep all secrets in the hosting provider's secret manager. Do not present projected revenue, pending deposits or unverified ledger entries as received funds.
