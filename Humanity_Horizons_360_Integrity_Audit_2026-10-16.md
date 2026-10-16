# Humanity Horizons 360 — integrity audit report

Audit date: 2026-10-16

Scope: locally available prepared source files only. The live GitHub source could not be fetched during this audit, and Streamlit is not installed in this checking environment. Therefore this is not a certification or proof of 100% production correctness.

## Baseline file: `Humanity_Horizons_app.py`

- SHA-256: `a8289c93d327eba44fdc611e2b50fa37be8dfba8c5da508d7575ee754b00ef4f`
- Size: 104,838 bytes; 1,271 lines
- Python AST parse + compile: PASS
- Duplicate top-level function names: none

## Candidate file: `Humanity_Horizons_app_with_command_center_studio.py`

- SHA-256: `2e63edcd98098a40663cb7369164d249b5b0a38f5c80cc94858d24e179f27117`
- Size: 110,331 bytes; 1,333 lines
- Python AST parse + compile: PASS
- Duplicate top-level function names: none

- Sidebar pages: 17
- Navigation labels without matching page branch: []
- Page branches without sidebar label: []

- SDG entries: 17; each has five listed problem areas: True

- Potential revenue stream catalogue entries: 50

- Admin email fallback is hard-coded in source: YES — HIGH RISK if public sign-up is enabled without ADMIN_EMAILS secret

- Password handling: PBKDF2-HMAC-SHA256 with 310,000 iterations and constant-time digest comparison found.

- Missing production safeguards explicitly acknowledged in app: managed DB/backups, email verification, password reset, rate limiting, role controls, retention/deletion workflows.

- Live Studio limitation documented: external meeting provider required; no built-in video engine.

## Runtime-isolated tests
- SQLite schema initialization: PASS (11 tables)
- Noticeboard SELECT/INSERT flow using parameterized query: PASS
- Task SELECT/INSERT flow using parameterized query: PASS
- Password hash / correct-password and wrong-password checks: PASS

## Findings and release decision

1. **Do not replace the currently working deployment yet.** This audit has not verified the exact source or behavior of the live Streamlit app.

2. **High risk:** the code defaults `ADMIN_EMAILS` to a public email address. If the deployed app lacks a locked-down `ADMIN_EMAILS` secret and allows public registration, an unverified account could claim that address and be treated as administrator. Set `ADMIN_EMAILS` explicitly in Streamlit Secrets and implement email verification before treating this as production-ready.

3. **Durability risk:** SQLite falls back to the system temporary directory. Hosted deployments may lose data across rebuilds/restarts. Configure managed PostgreSQL and test backup/restore before relying on saved records.

4. **Security/compliance gaps:** no email verification, password-reset flow, login rate limiting, MFA, or tested data export/deletion lifecycle was verified. These are required before public production use.

5. **Feature boundaries:** report schedules are stored but require an external scheduler/email provider; Live Studio is a session hub, not a built-in conferencing engine; the treasury ledger records manual entries and does not move crypto funds.

6. **Not tested:** browser/UI workflows, real Streamlit execution, PostgreSQL behavior/migrations, concurrency, deployment secrets, live network integrations, accessibility, and recovery from real backups.


**Conclusion:** The candidate passes syntax checks and isolated SQLite/password smoke tests. It does **not** pass a 100% / 360-degree production integrity certification. Keep the current working deployment unchanged until the exact live source is captured and the high-risk items are resolved and tested.
