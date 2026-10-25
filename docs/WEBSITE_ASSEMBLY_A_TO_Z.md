# CEDARS EMPIRE — End-to-End Website Assembly Map (A–Z)

## Scope and safety
This is the assembly blueprint for the existing Streamlit application. Keep changes on the `website-assembly/cedars-empire-a-to-z` branch until the user authorizes review/merge. Do not deploy, delete/reset accounts, alter production secrets, migrate/delete records, or claim verification during assembly. Preserve working components and data. Brand only as **CEDARS EMPIRE**; no legacy Humanity Horizons/NGO copy or tagline in visible navigation or page content.

## Information architecture

### 1. Public entry and account access
1. Welcome / business overview
2. Create account
3. Sign in / sign out
4. Password reset request and single-use reset completion
5. Terms, privacy, risk disclosures, and support/contact
6. Account profile and security

### 2. Member workspace
1. Dashboard — package/plan, account status, work progress, and only reconciled financial summaries
2. Business profile and customer/client records
3. Work & Contracts — available work, assigned tasks, contracts, deliverables, evidence
4. AI Business Tools — business scenario planning and approved AI utilities
5. Grid Marketplace — browse business grids and services
6. Grid workspaces — Energy & Utilities, Shelter & Accommodation, Cleaning, AI Training & Data Operations, and other configured grids
7. Live Studio — meetings, training, chat, recording status, and attendance only where supported/configured
8. Calendar & Events
9. Earnings & Wallet — clearly separate verified balances from pending/unverified items
10. Deposit — supported network, receiving address/QR, transaction hash submission, and status
11. Withdrawals & KYC — identity submission/status, eligibility, and withdrawal request status
12. Staking & Compounding — disclose terms/risks; never imply guaranteed returns
13. Referral Program — referral link, attribution, and qualification status
14. Business Reports — member-owned reports and exports
15. My Tasks / My Work
16. Help & Support
17. Account settings, privacy, and sign out

### 3. Administrator Command Center (restricted)
1. Executive Command Center — platform overview, operational alerts, risk and reconciliation queues
2. Real Money Engines — evidence-backed operational records; ideas and forecasts are not revenue
3. Grid Marketplace administration and grid status
4. Work & Contracts administration
5. Customer & Client Management
6. Payments & Treasury — reconciled inflows/outflows, fees, refunds, settlement status
7. Blockchain & Treasury — TRON and BNB Smart Chain kept separate; transaction hashes checked against public chain data
8. Deposit review — duplicate hash prevention and confirmation thresholds
9. Withdrawals & KYC review — least-privilege access to sensitive data
10. Earnings, referrals, and daily crediting — credits only after configured approval rules
11. AI Operations and robot/task oversight — tasks, evidence, exception handling, persistence status
12. Business Reports and scheduled reporting
13. Branding Settings — CEDARS EMPIRE logo and approved page assets
14. Admin Console — users/roles, app settings, audit events, operational controls
15. Security, privacy, retention, and audit trail

## Global navigation rules
- Use one consistent header with CEDARS EMPIRE branding and grouped top navigation; hide Streamlit's sidebar.
- Show only member-safe pages to members. Enforce authorization in server-side page logic, not just by hiding menu options.
- Every visible navigation item must route to an implemented page. No dead links, unknown-page fallbacks masquerading as success, or duplicate menu labels for the same destination.
- Include a page finder/search that navigates to a matching page rather than only printing matches.
- Keep user portal and administrator Command Center separate. Never show private treasury or platform-wide user records to ordinary members.
- Mobile layouts must remain usable; forms need clear labels, validation, confirmation and error states.
- Use consistent page titles, breadcrumbs/section labels, empty states, and save/cancel feedback.

## Data and transaction display rules
- Treat database records as the source of truth; do not rely on session state or temporary local files for durable user/account/financial records.
- Never display a submitted transaction as confirmed until network, asset, destination, amount, transaction hash, confirmations and duplicate checks pass the configured verification process.
- Distinguish: estimate/idea, submitted, pending review, verified/reconciled, rejected, and paid/settled.
- Do not claim funds are sent, earnings are guaranteed, or balances are withdrawable unless supported by actual system state and policy.
- Keep credentials and secrets out of code, logs, pages, exports, and commits.

## Assembly sequence (do this before the later verification phase)
1. Inventory all page handlers and reusable modules in the existing app.
2. Remove legacy NGO-facing links/text from the visible experience without deleting useful shared capabilities or historical records.
3. Normalize page IDs and create a single route registry for public, member, and admin pages.
4. Reconcile the top navigation with actual page handlers; ensure every link works and restricted routes fail closed.
5. Assemble public account screens and the complete member portal.
6. Assemble administrator Command Center sections and separate them from member navigation.
7. Standardize branding, responsive header, forms, empty/loading/error/success states.
8. Audit all buttons, forms, save operations, downloads and page transitions for complete flows.
9. Run static checks and unit/navigation tests on the branch.
10. Only after assembly is reviewed, begin the separate verification phase for authentication, PostgreSQL durability across refresh/restart, payment and on-chain checks, and deployment. Do not merge or deploy without explicit approval.

## Definition of assembly complete
- Every intended page is represented in the route registry and reachable by the correct role.
- No visible navigation item leads to a missing handler.
- Legacy NGO branding/navigation is absent from the visible product.
- Public, member, and admin surfaces are clearly separated.
- Existing accounts and records are preserved.
- A test checklist documents any feature that remains a placeholder or requires external credentials/services.
- No claim of production readiness or transaction verification is made until the later verification phase passes.
