# CEDARS EMPIRE — Website Assembly & Acceptance Plan

## Purpose
Unify the existing Streamlit application into one CEDARS EMPIRE business platform. This document is an acceptance plan, not a claim that every integration is already complete.

## Shared shell
- One shared CEDARS EMPIRE header/logo area, with no legacy Humanity Horizons identity or tagline.
- One grouped top navigation; no duplicate dashboard title/header and no visible sidebar.
- Keep the shared header consistent across authenticated pages.
- Responsive layout for desktop and mobile; forms and tables must remain usable on narrow screens.

## Member-facing pages
1. Dashboard — account overview, package entitlement, personal tasks and clearly labeled balances.
2. Customer & Client Management — contacts, customer requests and follow-up.
3. Calendar & Events — scheduled business activities.
4. Live Studio — display availability accurately; do not claim conferencing/recording is live until its runtime is connected and tested.
5. Work & Contracts — scope, terms, assigned work, delivery and acceptance evidence.
6. Client Services & Contracts — service catalogue, quotes, agreements and customer obligations.
7. Business Opportunity Pipeline — leads and prospects, never booked as revenue.
8. Earnings & Wallet — ledger-backed personal balances and transaction history.
9. Deposit & Packages — network-specific deposit instructions, transaction reference, confirmation state and package entitlements.
10. Withdrawals & Full KYC — eligibility, review, audit trail and safe withdrawal state; never claim payment sent without settlement evidence.
11. Staking & Compounding — show only contractually approved terms and actual calculations; no guaranteed return claims.
12. Referral Program — attributed referrals and verified qualifying events; no payment for merely recruiting.
13. World Grid Marketplace — catalogued business services, scope, price and proof requirements.
14. Cleaning Grid; Shelter & Accommodation Grid; Energy & Utilities Grid; AI Training & Data Operations — grid-specific service tasks and evidence.
15. Robot Operations Dashboard — worker target, grid readiness, task evidence, operating cost and safe-runtime state.
16. AI Business Scenario Lab — forecasts explicitly separated from actuals.
17. Business Reports — report source, period, generation time and data-quality caveats.
18. My Work & Wallet; My Tasks — user's own work, statuses and records.
19. Account — registration, login/logout, profile and security controls.

## Administrator-only Command Center
- Command & Finance: reconciled receipts, verified revenue, refunds, fees, costs, treasury movements and balanced ledger.
- Automation & Admin: integrations, scheduled jobs, worker registry, task queue health, audit events, permissions and system readiness.
- KYC/review queues, payment reconciliation and platform-wide operational reports must be restricted to authorized administrators.
- Keep private treasury and other members' personal data out of public/member dashboards.

## AI workforce roadmap
- Target: 250,000,000 AI workers long-term. This is a planning target, not a deployed count.
- A worker is counted as connected only after authenticated runtime registration and a recent heartbeat.
- A task is completed only when its output/evidence is durably stored and validated.
- A task becomes eligible for revenue only when there is a real customer order/contract, delivery acceptance, invoice/payment evidence, independent settlement verification, and reconciliation of fees, costs, refunds and obligations.
- Use least-privilege worker identities, per-task cost limits, idempotency keys, audit trails and human approval for irreversible or high-risk actions.
- Do not launch the fleet at target scale before a small, monitored end-to-end pilot proves reliability and unit economics.

## Release gates — must all pass before production promotion
- [ ] Navigation audit: every listed page opens for the correct role; no dead routes.
- [ ] Header audit: exactly one shared brand/header; no legacy name or tagline.
- [ ] Authentication: registration/login/logout and session restoration verified without clearing or deleting existing accounts.
- [ ] Persistence: create a test record, refresh, restart/redeploy, and verify the same record survives in PostgreSQL.
- [ ] Authorization: member cannot access admin pages, other users' data, treasury controls or KYC documents.
- [ ] Payments: network-specific transaction verification, duplicate hash rejection, idempotent callbacks and reconciliation tested.
- [ ] Robot runtime: simulation clearly labeled; no active-worker claims without real heartbeat evidence.
- [ ] Revenue integrity: forecasts/leads/packages/unconfirmed deposits excluded from verified revenue.
- [ ] Automated tests and syntax checks green.
- [ ] Test app visually checked in browser and user explicitly approves production promotion.

## Known open risks
- Login/session restoration and durable PostgreSQL persistence have previously been reported as failing and must be re-tested.
- A green syntax/test workflow does not by itself prove the deployed Streamlit app, database, authentication or real payment settlement works.
- Do not delete accounts, reset credentials, modify production secrets, or merge to `main` as part of this assembly without separate verification and approval.
