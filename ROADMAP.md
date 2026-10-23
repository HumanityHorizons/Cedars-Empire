# CEDARS EMPIRE — Consolidated Feature Roadmap

Implement and verify **one item at a time**. Work only on `fix/durable-storage-and-login` or a dedicated repair branch. Do not merge to `main` or change the live app without explicit approval. Preserve existing data. Business-only product: do not restore the NGO workspace. Brand: CEDARS EMPIRE; no “Humanity Horizons” or “360” in user-facing branding.

## 1. Launch-critical foundation — first
- [ ] Durable database persistence across refreshes and redeploys; verify persistent PostgreSQL configuration and fail safely if absent.
- [ ] Secure login/session persistence without bearer tokens in query strings or JavaScript-readable storage; test refresh, expiry, logout and re-login.
- [ ] Verify common header/footer, no duplicate header, brand/tagline and logo sizing.
- [ ] Run syntax, dependency, security, persistence and runtime smoke tests; report evidence and blockers.
- [ ] Keep production unchanged until explicit approval.

## 2. Six core business components
- [ ] **Studio:** client meetings/collaboration, attendance, documents/chat and moderation; clearly identify integration-dependent features.
- [ ] **Customer & Client Management:** persistent customer/service-provider records, follow-ups and status.
- [ ] **Business Calendar:** deadlines, time zones, regional public holidays and greetings; claim external notifications only when delivery is configured.
- [ ] **Work & Contracts:** persistent tasks, deliverables, contract records and a 1,095-day countdown.
- [ ] **Business Reports:** operational reports and PDF/Excel exports; distinguish verified actuals, estimates and pending evidence.
- [ ] **Real Business Engines:** 13-grid operations, verified revenue, treasury, payments and reconciliation.
- [ ] Relevant banking-style tables: search, sorting, filters, PDF/Excel export; concise forms, accessible high-contrast UI.

## 3. 13-grid business economics
Model NeuroWave, EchoMap, BioLoop, DreamGrid, EchoPulse, MindScape, SoundWave, SleepCycle, MoodLift, FocusFlow, SolarGrid, AeroWave and HydroGrid individually.
- [ ] For each Grid record activation capital (the $10 minimum is only an input, not proof of viability), deployed capital, real customer/buyer, product/service, price/frequency, evidence, monthly revenue, costs, net profit, Treasury contribution, growth and break-even.
- [ ] Separate customer deposits/capital from operating revenue. Prevent double counting. Stress tests assume zero new deposits.
- [ ] Keep both allocation choices configurable: 40% reserve/60% deployment; or 40% reserve/30% core grids/20% expansion/10% liquidity buffer. Never silently combine.
- [ ] Treasury ledger: opening/closing cash, verified Grid revenue and other verified income, fees, expenses, reserves, retained earnings, expansion, pending withdrawals/obligations and evidence-backed on-chain reconciliation.
- [ ] Distribution engine only uses eligible available distributable cash after expenses, obligations and reserve controls; no guaranteed daily payout.
- [ ] 5% monthly treasury compound, 6% monthly staking, 15% annual staking, 1% daily target and fee assumptions are unverified scenario inputs only—not live promises/defaults.

## 4. Risk, solvency and 50-year stress test
- [ ] 600 monthly periods (50 years): base, 25%, 50%, 75%, 100% Grid-revenue-loss scenarios; no new deposits.
- [ ] Current policy target: **maximum tolerated Grid-revenue-loss stress is 15%**. At/below target, test profitability and solvency; above 15%, flag emergency controls, reduce discretionary costs, protect reserves and reassess distributions.
- [ ] 25/50/75/100% are stress tests, not acceptable targets. At 100% Grid-revenue loss, suspend unsupported payouts and protect remaining capital.
- [ ] Report profit, cash flow, solvency and liquidity separately: monthly Treasury balance, coverage ratios, reserve months, first deficit, first unmet obligation and failure month/year.
- [ ] Validate formulas using a calculation engine and independently review key outputs before claiming the model passes the 15% target.
- [ ] Dashboard: revenue, contract, withdrawal and reserve coverage; survival months; configurable traffic-light thresholds.

## 5. Proposed customer packages — gated, not an active offer
- [ ] Configurable Cedars Growth Ladder concept: Seed $300, Root $1,000, Branch $2,500, Grove $5,000, Forest $10,000, Empire $25,000.
- [ ] Package weights, benefits and distribution formulas remain simulations until terms are legally reviewed and funding verified.
- [ ] Do not market/activate promised staking, guaranteed returns, ownership or distributions before legal/regulatory, custody, disclosure and liquidity review.
- [ ] Member distributions are limited to the validated share of an eligible pool and cannot exceed available distributable cash.

## 6. Real-money controls — gated
- [ ] Read-only chain-specific verification first; label transactions pending/confirmed/failed and identify network/token.
- [ ] Separate deposit intent from on-chain confirmed receipt; never mark a client claim as confirmed revenue.
- [ ] Withdrawals require authorization, liquidity checks, screening, network-specific verification and a real payout integration; claim success only with transaction evidence.
- [ ] Admin-only reconciliation; hide private treasury balances and controls from ordinary users.
- [ ] No private keys in app code, no demo balances presented as real, no unsupported signing/custody claims.
- [ ] Require written agreements and counterparty evidence before Grid/vendor transfers. Discovery is not a contract.

## 7. Launch gate
- [ ] Test role separation, signup/login/logout/refresh, durable records, calendar, tasks/contracts, reports/exports, Grid pages, audit events and error paths.
- [ ] Verify all claims against runtime, database and transaction evidence.
- [ ] Provide a concise report with exact pass/fail results, blockers, commit and links. Deploy only after explicit approval.

## Working rule
Complete one item, test it, report what passed and failed, then continue. Code existing is not proof of completion.