# CEDARS EMPIRE — Global Commercial Grid Readiness

## Operating principle
Every grid can be marketed only for services it can actually deliver. A catalogue entry is not a live business, connected robot, customer contract, or revenue stream. Readiness must be evidenced independently per grid and per operating country.

## Required gates for every grid
1. **Legal and local permissions:** contracting entity, licenses, taxes, permits, insurance, worker/provider obligations, and sector-specific approvals for each country.
2. **Verified provider or runtime:** authenticated supplier/operator or registered robot runtime; current health/heartbeat and capability records where applicable.
3. **Customer order and contract:** named customer, scope, price, service level, delivery window, cancellation/refund terms, acceptance criteria, and responsible party.
4. **Delivery evidence and acceptance:** traceable task/order IDs, timestamped evidence, quality checks, authorized customer acceptance, dispute process.
5. **Durable records and audit:** database migrations, backups, access controls, retention policy, idempotent task processing, audit log, tested restore.
6. **Payment and reconciliation:** payment provider/network verified independently, duplicate transaction rejection, idempotency, fees/refunds/chargebacks, settlement-to-ledger matching, authorized payout controls.
7. **Security, privacy and safety:** least privilege, secrets management, threat review, privacy and consent, incident response, hardware safety controls, human approval for irreversible/high-risk actions.
8. **Unit economics and support:** measured cost per accepted task, contribution margin, capacity/uptime, support owner, failure recovery and customer complaint handling.

A grid is **not ready** when any gate is missing. Full gate completion qualifies it only for a controlled commercial pilot, not automatically for unrestricted global launch.

## Fleet scale: 250,000,000 target
- Treat 250 million as a long-term fleet target, not deployed capacity.
- Count a software worker only after unique identity, authorization, live heartbeat, health checks and a tested task.
- Count a physical robot only after asset registration, ownership/provider verification, site acceptance, safety review, connectivity and fail-safe test.
- Do not count catalogue rows, queued jobs, simulated agents, or planned capacity as active workers.
- Scale in measured cohorts; every cohort must pass reliability, security, cost and service-quality gates before the next expansion.
- Set per-worker/task budgets, rate limits, circuit breakers, kill switches, monitoring, incident response and rollback before adding autonomy.
- Never let worker count itself trigger a payment, investment return, package payout or revenue claim.

## Commercial revenue recognition
Recognize revenue only for a real customer obligation fulfilled under the applicable accounting policy, supported by delivery acceptance and an auditable invoice/settlement record. Customer deposits, package purchases, referrals, forecasts, token transfers not matched to an obligation, and internal wallet credits are not automatically earned revenue. Reconcile gross receipts, taxes, provider/worker payouts, refunds, chargebacks and operating costs.

## Global launch model
- **Stage 0 — Foundation:** catalogue, owner, service definition, risk classification and country scope.
- **Stage 1 — Provider/customer validation:** verified suppliers, a real customer, signed scope and price.
- **Stage 2 — Controlled pilot:** human-supervised work, evidence review, durable records and measured unit economics.
- **Stage 3 — Paid operations:** independently verified payments, reconciliation, support and dispute handling.
- **Stage 4 — Country rollout:** local legal/tax/privacy/safety review and country-specific operations owner.
- **Stage 5 — Multi-country scale:** monitoring, resilience, supplier diversity, incident drills and independent audit.
- **Stage 6 — Fleet expansion:** scale only after preceding stages pass with documented evidence.

## Current evidence boundary
The repository's grid catalogue defines proposed services, units, proof and equipment. The robot module explicitly describes a simulation-only registry and task state machine and does not connect hardware, upload evidence or move funds. Therefore code presence alone cannot certify any grid as globally commercially ready. Authentication and PostgreSQL persistence have also been reported as unresolved and must be proven in the hosted test environment before paid operations.

## Release checklist
- [ ] Named accountable owner for each grid and country.
- [ ] Eight readiness gates evidenced and reviewed.
- [ ] Real customer order/contract and service-level agreement.
- [ ] Task evidence, acceptance, disputes and refunds tested.
- [ ] Durable storage survives refresh, restart and restore drill.
- [ ] Role-based access, secrets, privacy and incident response tested.
- [ ] Payment verification and ledger reconciliation independently tested.
- [ ] Cost per accepted task and contribution margin measured.
- [ ] Controlled pilot completed with documented customer acceptance.
- [ ] Country-by-country legal/operational sign-off.
