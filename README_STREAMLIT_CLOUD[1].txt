HUMANITY HORIZONS 360 — CLOUD DEPLOYMENT GUIDE
People, Planet and Peace

PRODUCT OWNERSHIP AND NAMING
Humanity Horizons independently owns and maintains the Humanity Horizons 360 product identity and the Humanity Horizons Institutional Readiness & Impact Framework (HH-IRIF), including its Future Workforce Readiness Matrix. Do not add outside institution logos, imply endorsements, or describe the framework as externally certified. This does not alter an opportunity publisher's identity: imported opportunities must retain the issuer, original source URL, deadlines and any attribution needed to avoid misleading users.

FEATURES IN THIS PROTOTYPE
- Account creation and sign-in with salted PBKDF2 password hashes
- Task tracking (not started, in progress, executed/completed, blocked)
- PDF/DOCX/TXT/Markdown text extraction and opportunity/TOR analysis
- Proposal and fellowship drafting briefs; optional user-consented generative AI
- Humanity Horizons Future Workforce Readiness Matrix and CV/resume studio
- All 17 Sustainable Development Goals with five representative problem areas each
- Noticeboard listings, original-source links, moderation and CSV import workflow
- Results framework, monitoring-data import, risk register and M&E report draft
- Humanity Horizons Institutional Readiness & Impact Framework (HH-IRIF)
- Donor/stakeholder feedback form
- Anonymous visit counts and optional identifiable attendance for opted-in follow-up
- Admin moderation and finance ledger; treasury address configured as a secret

IMPORTANT LIMITATIONS
This is an MVP/prototype, not a fully automated production system. Its readiness framework is owned by Humanity Horizons and is a self-assessment aid, not an external certification, legal opinion or guarantee of funding, employment, compliance or revenue. Requirements vary by opportunity, agreement, country, sector and risk. Map each application and project to its actual source documents and arrange authorized human review where necessary.

PRIVACY AND AI
Anonymous sessions are counted without IP-address collection or device fingerprinting. Identifiable attendance is stored only for signed-in users who opt in to follow-up. Sign-in and operational actions are logged for security and audit. Users provide a B2B/workspace purpose and confirm rights before upload/download actions; declared purposes are recorded in the action audit. Do not upload unnecessary sensitive or beneficiary data. Generative AI is optional; text is sent to the configured AI service only when the user explicitly opts in on the relevant screen. Review service terms, privacy, data residency and costs before enabling any provider integration.

DEPLOY TO GITHUB + STREAMLIT
1. Download this ZIP and extract it on Windows (right-click ZIP > Extract All).
2. Items are directly at the extracted root (no enclosing project folder):
   app.py
   requirements.txt (must be a normal text file, NOT a folder)
   README_STREAMLIT_CLOUD.txt
   README_LOCAL.md
   PRIVACY_AND_COMPLIANCE_NOTES.md
   HUMANITY_HORIZONS_FRAMEWORK.md
   assets\humanity_horizons_logo.jpg
3. In https://github.com/HumanityHorizons/project, open branch main.
4. Upload app.py from this ZIP to the repository root (or replace the existing app.py). Do not paste requirements lines into app.py.
5. Ensure requirements.txt is a regular file at the repository root. If GitHub shows a directory named requirements.txt, inspect it, remove the incorrect directory, then create a new root file exactly named requirements.txt and paste the package list included in this ZIP. Commit the changes.
6. Ensure assets/humanity_horizons_logo.jpg exists. Do not upload the local SQLite database.
7. In Streamlit Community Cloud, deploy this repository (not GitHub Pages), choose branch = main and Main file path = app.py. GitHub Pages can serve the static landing page, but it cannot run this Python/Streamlit application.
8. Wait for dependencies to install and the app to restart. Review the latest logs if there is an error; old logs may refer to earlier code.

DURABLE STORAGE
Hosted local filesystems are not reliable durable storage. Configure managed PostgreSQL before onboarding real users:
- In Streamlit Cloud > Manage app > Settings > Secrets, add:

DATABASE_URL = "postgresql://USER:PASSWORD@HOST:PORT/DATABASE?sslmode=require"
ADMIN_EMAILS = "your-authorized-admin-email@example.com"
TRON_TREASURY_ADDRESS = "YOUR_PUBLIC_TRON_TREASURY_ADDRESS"

Optional generative AI settings used by this build:
OPENAI_API_KEY = "YOUR_API_KEY"
OPENAI_MODEL = "gpt-5-mini"

Never commit secrets to GitHub. Never put treasury private keys or seed phrases into source code, repository files, application secrets or the database. Configure database backups, access control and recovery tests before inviting real users. If DATABASE_URL is absent, the prototype uses temporary SQLite storage which may be lost after restarts/rebuilds and is suitable for testing only.

ADMIN ACCESS
The admin console appears only for email addresses in ADMIN_EMAILS. If that setting is empty, nobody receives app-level admin controls. Secure GitHub, Streamlit and database accounts with MFA. Before production, add and test email verification, password reset, rate limiting, session management, account deletion/export, a retention schedule, incident response, backups and professional security/privacy review.

TREASURY
The treasury page is an administrator-only reference and ledger. It does not connect to the network, custody signing keys, or initiate withdrawals. Live payment integration requires a separately reviewed and tested design, payment-provider/custody arrangements, limits, multi-person approval, monitoring, reconciliation and applicable legal/accounting review.
