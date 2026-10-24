# CEDARS EMPIRE — Application Sitemap and Release Gates

> Scope: business operations, AI-enabled services, grid marketplace, account workspace, and verified treasury workflows. This sitemap describes the intended navigation contract; it is not a claim that every external integration is live.

## Entry and account access

| Destination | Access | Expected behavior |
|---|---|---|
| Sign in | Public | Authenticate an existing account; on success open Overview → Dashboard |
| Create account | Public | Validate inputs, create the account in the configured database, then open Dashboard |
| Public noticeboard | Public | Read approved public listings only |
| Forgot password / Set new password | Public, token-gated for reset | Issue and validate time-limited reset tokens; email delivery requires SMTP configuration |

## Member workspace

| Navigation area | Page / destination | Access and routing notes |
|---|---|---|
| Overview | Dashboard | Default destination after sign-in; account-scoped overview |
| Work | My Tasks / Work & Contracts | User-owned tasks, work opportunities, and submissions |
| Grid Marketplace | World Grid Marketplace | Browse registered business grids and evidence requirements |
| Grid Marketplace | Cleaning Grid | Cleaning and service-work workflows |
| Grid Marketplace | Shelter & Accommodation Grid | Accommodation-service workflows |
| Grid Marketplace | Energy & Utilities Grid | Energy, solar, and utilities workflows |
| Grid Marketplace | AI Training & Data Operations | Data and AI service workflows |
| Robotics | Robot Operations Dashboard | Readiness and simulation only until hardware, safety, and evidence integrations are verified |
| Customers | Customer & Client Management | User-scoped customer records |
| Schedule | Calendar & Events | User-scoped calendar records |
| Collaboration | Live Studio | Show only implemented/configured capabilities; do not imply a live media backend without a tested implementation |
| Finance | Earnings & Wallet | Separate customer wallet liabilities from company revenue; only reconciled amounts count as confirmed |
| Finance | Deposit & Packages | Consent, network/address display, transaction verification, duplicate prevention, and durable ledger recording |
| Finance | Withdrawals & Full KYC | KYC review and withdrawal requests; a request is not a completed payout |
| Finance | Staking & Compounding | Unavailable or informational unless the underlying compliant service is implemented and verified |
| Growth | Referral Program | No reward is credited without a defined, auditable qualifying event |
| Administrator workspace | AI Business Scenario Lab | Admin-only scenario planning; estimates are not revenue |
| Business | Business Reports | Reports derived from stored records, with source and verification status |

## Administrator workspace

| Destination | Access | Expected behavior |
|---|---|---|
| Command / Admin Console | Authorized administrators only | Audit events, operational controls, and administrative records |
| Payments Operations | Authorized administrators only | Reconcile on-chain evidence and ledger records; no private-key custody |
| Treasury / Revenue Allocation | Authorized administrators only | Segregation of duties, evidence references, balanced journal, durable records |
| KYC and Withdrawals Review | Authorized administrators only | Review requests and record decisions; no payout claim until externally verified |
| Reporting and System Health | Authorized administrators only | Database connectivity, migrations, reconciliation exceptions, and workflow status |

## Shared application shell

- Brand: CEDARS EMPIRE only; no tagline and no retired NGO-facing navigation.
- Header: one shared horizontal navigation shell; hide the default Streamlit sidebar.
- Responsive behavior: wide layouts on desktop, stacked cards and readable forms on narrow screens, no required horizontal page scrolling.
- Routing: navigation selection maps to a known destination; invalid or unauthorized destinations fail closed.
- Authentication: establish session identity through server-side account checks; scope records to the authenticated user; check admin privileges server-side.
- Persistence: use managed PostgreSQL through DATABASE_URL for production. Local SQLite on an ephemeral hosted filesystem is not durable.
- Errors: safe user-facing messages; never expose credentials, database connection strings, password hashes, or provider secrets.
- Financial truth: planning estimates, pending deposits, wallet liabilities, internal ledger entries, and verified company revenue remain separate states.
- Robotics truth: animation and registered grid definitions are not proof of connected hardware, autonomous work, or earnings.

## Production acceptance checklist

Do not call the release production-ready until each applicable item is evidenced in the target hosted app:

- [ ] Correct Streamlit app points to the intended repository and release branch.
- [ ] Every navigation item opens its intended page; no dead ends, duplicate labels, or stale legacy routes.
- [ ] Sign-up, sign-in, logout, invalid credentials, and password reset are tested end-to-end.
- [ ] Refresh/restart preserves account and task data in the configured PostgreSQL database.
- [ ] Database migrations and startup checks pass against the production-like schema.
- [ ] Authorization tests prove one member cannot read or mutate another member's records.
- [ ] Administrator routes reject non-admin accounts.
- [ ] Deposit tests cover wrong chain/token/recipient, insufficient confirmations, failed transactions, and duplicate hashes.
- [ ] Withdrawal request, approval, and completed payout are represented as distinct states.
- [ ] Mobile and desktop layouts are checked in the hosted app.
- [ ] CI passes syntax and route/navigation tests.
- [ ] Backups, recovery, privacy notice, incident response, and operational monitoring are configured.
- [ ] Final production release is explicitly approved and deployed, then smoke-tested.

## Current limitations

This repository contains a Streamlit application and modules for business workflows, payment verification, and robot-grid readiness. A green CI run verifies only the checks included in that workflow. It does not verify hosted login, database credentials, SMTP delivery, external APIs, real robot hardware, completed payouts, or the live UI. These must be tested in the deployed environment before launch.
