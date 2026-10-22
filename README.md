# CEDARS EMPIRE

**Tagline:** People · Prosperity · Impact

CEDARS EMPIRE is a Streamlit platform with member accounts, task tracking, opportunity and proposal tools, HR/volunteer records, sustainability planning, monitoring and evaluation (M&E) working reports, report scheduling, and an administrator console.

## Included modules

- Account sign-up/sign-in and user-scoped task tracking
- Opportunity / TOR / fellowship document extraction and optional AI review
- Proposal and CV/resume drafting tools
- SDG Navigator for all 17 goals
- Moderated opportunity noticeboard
- Standards, risk and M&E workspace
- Donor / stakeholder feedback and B2B collaboration
- HR and volunteer record tracking
- Potential revenue-stream planning catalogue (not guaranteed income)
- Indicator register and downloadable M&E working report
- Report schedule configuration and a GitHub Actions scheduled-report job (requires managed PostgreSQL plus SMTP secrets)
- Administrator console and treasury ledger entry tracking (does not execute blockchain transactions)

## Deployment and verification

1. Back up the repository before changing production files.
2. Confirm the Streamlit Community Cloud app points to this repository's `main` branch and uses `app.py` as its main file.
3. Test sign-in, creating a task, opportunity upload, noticeboard, HR/volunteer records, revenue planner, indicator register and report downloads.
4. Configure a managed PostgreSQL database using the `DATABASE_URL` secret for durable persistence. SQLite in the temporary hosted filesystem is not a durable production database.
5. After each change, verify the live app and review its deployment logs before considering the change released.

## Streamlit secrets (template only)

Set `ADMIN_EMAILS`, `DATABASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, and any required treasury address under Streamlit app **Settings → Secrets**. For the scheduled report workflow, also set the matching repository Actions secrets `DATABASE_URL`, `ADMIN_EMAILS`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, and `SMTP_FROM`. Never commit real credentials to GitHub.

```toml
ADMIN_EMAILS = "your-authorized-admin@example.com"
DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require"
OPENAI_API_KEY = ""
OPENAI_MODEL = "gpt-5-mini"
TRON_TREASURY_ADDRESS = ""
```

Only set an AI key if you have authorized billing and intend to use the optional provider. Users must explicitly opt in before supported document text is sent to that provider. Do not put seed phrases, private keys or withdrawal credentials into GitHub, Streamlit secrets or the app UI.

## Important limitations

- This application does not charge customers or execute payments, transfers or blockchain transactions. The treasury area is a reference ledger only.
- Saved report schedules are configuration records. The included GitHub Actions job can execute scheduled reports on the 25th monthly once repository secrets for PostgreSQL and SMTP are configured. Quarterly/semi-annual/annual schedules are filtered by the report job. The job sends internal working summaries, not a certified donor report.
- M&E working reports summarize indicators entered by users. They require human validation and source evidence before donor submission.
- Email verification, password-reset workflow, MFA inside the app, rate limiting, formal privacy/legal review, backup automation and incident response must be completed before a public production launch.
- No funder partnership, approval, compliance certification, employment result or grant award is implied.

## Brand standard

Use **CEDARS EMPIRE** as the current company and platform name in application interfaces, repository documentation, release notes and new project materials. Do not reintroduce the former brand name or “360” in current-facing branding. Historical Git history and immutable audit records may retain their original text.
