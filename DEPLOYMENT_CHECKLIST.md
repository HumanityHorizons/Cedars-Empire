# Deployment and acceptance checklist

## Protect baseline
- [ ] Download the current repository ZIP from GitHub before replacement.
- [ ] Confirm the active Streamlit app uses `HumanityHorizons/project`, branch `main`, file `app.py`.
- [ ] Confirm logo file path/name; the app can run without a logo, but the official logo should be added in the repository root or `assets/` using the path configured in `app.py`.

## Deployment checks
- [ ] `requirements.txt` is a file, not a directory.
- [ ] `app.py` is the main file and imports `pymupdf` from the `PyMuPDF` package.
- [ ] Streamlit build succeeds without import or schema errors.
- [ ] Set `ADMIN_EMAILS` in Streamlit secrets and test administrator access with an authorized address.
- [ ] Configure managed PostgreSQL and verify `DATABASE_URL` connectivity before real user data is entered.

## Feature acceptance tests
- [ ] Create account, sign out and sign back in.
- [ ] Create/update task; verify it remains after refresh and a fresh session.
- [ ] Upload a permitted PDF and inspect extracted text against original pages.
- [ ] Generate a proposal brief and CV/resume draft; confirm missing evidence is not fabricated.
- [ ] Confirm all 17 SDGs are available.
- [ ] Submit a noticeboard listing; verify only an admin can publish it.
- [ ] Submit feedback and verify only authorized admins can review all feedback.
- [ ] Create HR/volunteer record and revenue-planning entry.
- [ ] Create indicator records and download the M&E working report.
- [ ] Create a report schedule and verify UI clearly states that delivery requires external scheduling/mail configuration.
- [ ] Test export/download controls and verify audit events are recorded.
- [ ] Confirm a non-admin cannot see the Admin Console or Report Automation page.

## Go-live gates
- [ ] Privacy notice, terms, retention and deletion/export processes reviewed by qualified local counsel/data-protection professional.
- [ ] Email verification, password reset, rate limiting and MFA/identity-provider plan implemented.
- [ ] Database backups and restore drill completed.
- [ ] Security review and accessibility review completed.
- [ ] Payment provider, merchant terms, refunds, reconciliation and tax/accounting process separately tested before collecting money.
- [ ] Any automated report scheduler and delivery provider separately configured and tested end-to-end.


## Scheduled report delivery
- [ ] Configure the same managed PostgreSQL `DATABASE_URL` in Streamlit secrets and GitHub repository Actions secrets.
- [ ] Configure SMTP host, port, username, app password, and sender in GitHub Actions secrets. Use an email-provider app password where required.
- [ ] Run GitHub Actions → Humanity Horizons scheduled reports → Run workflow manually.
- [ ] Confirm test email delivery, check spam/quarantine, and confirm `last_run_at` updates for the matching schedule.
- [ ] Confirm the recipient is authorized to receive the selected report; treasury summary is limited to recipients listed in `ADMIN_EMAILS`.
- [ ] Review the report contents before any external donor submission.
