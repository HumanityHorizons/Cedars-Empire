# CEDARS EMPIRE Platform Unification — Test Branch

Scope: `cedars-empire-test` only. This is an assembly and acceptance checklist, not a claim that production readiness has been achieved.

## Phase 1 — Page assembly

- [x] Preserve one shared locked CEDARS EMPIRE header.
- [x] Keep the business workspace navigation grouped as Overview, Business, Earnings, Grids, AI & Reports, and Account; administrator-only groups remain separately gated.
- [x] Keep the main Dashboard as the single landing page.
- [x] Keep AI scenario notices inside AI Business Scenario Lab rather than the landing page.
- [ ] Browser-check every visible navigation destination after deployment.

## Phase 2 — Module integration

Current application modules imported by `app.py` include:

- `hh_workspace_widgets.py` — action grid, calendar and document exports.
- `hh_grid_marketplace.py` — canonical grid registry and evidence-first grid marketplace.
- `hh_robot_dashboard.py` and `hh_robotics.py` — robot operations and safety-state foundation.
- `hh_real_payments.py` — deposit, cash-out, payment operations and user treasury views.
- `hh_table_ui.py` — consistent table rendering.
- `daily_crediting.py` — daily crediting workflow.

- [x] Real Money Engines selector draws from the canonical grid registry so every listed grid can have an operating evidence register.
- [x] Grid records distinguish demand, delivery, costs, receipts/settlement and risk/incident records.
- [ ] Verify each module's end-to-end persistence and account/role boundaries against the configured database.
- [ ] Verify API and provider integrations with real credentials and provider-side evidence.

## Phase 3 — Platform consolidation

- [x] Visible navigation is driven from one grouped menu definition.
- [x] Existing route aliases include Work & Contracts → Client Services & Contracts, Deposit → Deposit & Packages, Earn → Real Money Engines, and Reports & Referrals → Business Reports.
- [ ] Browser-test every menu item for a successful route and correct access control.
- [ ] Resolve or explicitly retire any legacy route that is not part of the current business-only product.
- [ ] Complete login/session persistence and PostgreSQL migration/restart checks before production promotion.

## Phase 4 — Ecosystem integration

- [x] Grid registry describes tasks, unit of work, required evidence and operational requirements.
- [x] Grid marketplace clearly states that a listing does not certify a provider, contract, task completion or revenue.
- [ ] Verify provider identity, written customer agreements, delivery acceptance, invoices and payment reconciliation for each real commercial workflow.
- [ ] Verify external services and APIs individually; a module being imported is not proof that an external integration is live.

## Phase 5 — CEDARS EMPIRE OS deployment

- [x] Work is isolated to the test branch; no production branch promotion is included in this change.
- [x] Deposits are not required for non-payment grid operations to be assembled and tested.
- [x] Deposit/withdrawal functions remain subject to their own configuration, network/token verification, authorization and reconciliation gates.
- [ ] Require green syntax and regression workflows.
- [ ] Confirm successful test-app sign-in, refresh persistence, route navigation, database persistence, and admin/member separation.
- [ ] Test one real receipt end-to-end with source evidence and reconciliation before calling revenue controls production-ready.
- [ ] Review secrets, dependency installation, migrations, logging, backups, rollback and incident procedures.
- [ ] Obtain explicit approval before promoting any changes to `main` / live.

## Financial integrity rules

1. A grid's existence or status is not proof of demand, delivery, profitability or revenue.
2. Leads, quotes, forecasts, planned contracts, and submitted but unreconciled evidence are not earned revenue.
3. Deposits/customer funds are not operating revenue.
4. Count a receipt as verified only after source evidence and reconciliation are reviewed.
5. Do not imply earnings are guaranteed; do not issue payouts from unsupported or unreconciled balances.

## Current blockers / honest status

- Authentication and persistence have previously shown intermittent failures and must be re-tested on the current deployed build.
- Recent regression runs exposed stale single-header test assertions. Those assertions have been updated; the new workflow result must be checked before declaring the test suite green.
- Real provider contracts, payment reconciliation, and robot/device integrations have not been independently verified merely by this code assembly.

Status: **test-branch assembly in progress; not production-ready until the unchecked acceptance gates pass.**
