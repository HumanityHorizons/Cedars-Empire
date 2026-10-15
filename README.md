# Humanity Horizons 360 — upgrade package

**Tagline:** People, Planet and Peace

This package preserves the previously supplied Humanity Horizons Streamlit MVP and adds persistent HR/volunteer records, a 50-stream sustainability planner, a stored indicator register with downloadable M&E working reports, and report schedule configuration. It is an upgrade candidate, not a claim that every external service is production-ready.

## Included modules

- Account sign-up/sign-in and user-scoped task tracking
- Opportunity / TOR / fellowship document extraction and optional AI review
- Proposal and CV/resume drafting tools
- SDG Navigator for all 17 goals
- Moderated opportunity noticeboard
- Standards, risk and M&E workspace
- Donor / stakeholder feedback and B2B collaboration
- HR and volunteer record tracking
- 50 potential revenue-stream planning catalogue (not guaranteed income)
- Indicator register and downloadable M&E working report
- Report schedule configuration and a GitHub Actions scheduled-report job (requires managed PostgreSQL plus SMTP secrets)
- Administrator console and verified treasury ledger entry tracking (does not execute blockchain transactions)

## Deploy carefully

1. Download a ZIP backup of the current GitHub repository before making changes.
2. Upload the contents of this package into `https://github.com/HumanityHorizons/project/upload/main`. Commit the update. If GitHub warns about replacing files, replace `app.py` and `requirements.txt` only after confirming the backup exists; add the new `.streamlit` directory and `.gitignore`.
3. In Streamlit Community Cloud, confirm the main file is `app.py`, then reboot the app.
4. Test sign-in, creating a task, opportunity upload, noticeboard, HR/volunteer records, revenue planner, indicator register and report downloads.
5. Configure a managed PostgreSQL database using the `DATABASE_URL` secret for durable persistence. SQLite in the temporary hosted filesystem is not a durable production database.

## Streamlit secrets (template only)

Set `ADMIN_EMAILS`, `DATABASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, and `TRON_TREASURY_ADDRESS` under Streamlit app **Settings → Secrets**. For the scheduled report workflow, also set the matching repository Actions secrets `DATABASE_URL`, `ADMIN_EMAILS`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, and `SMTP_FROM`. Never commit real credentials to GitHub.

```toml
ADMIN_EMAILS = "your-authorized-admin@example.com"
DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require"
OPENAI_API_KEY = ""
OPENAI_MODEL = "gpt-5-mini"
TRON_TREASURY_ADDRESS = ""
```

Only set an AI key if you have authorized billing and intend to use the optional provider. Users must explicitly opt in before supported document text is sent to that provider. Do not put seed phrases, private keys or withdrawal credentials into Streamlit secrets or the app UI.

## Important limitations

- This package does not charge customers or execute payments, transfers or blockchain transactions. The treasury area is a reference ledger only.
- Saved report schedules are configuration records. The included GitHub Actions job can execute scheduled reports on the 25th monthly once repository secrets for PostgreSQL and SMTP are configured. Quarterly/semi-annual/annual schedules are filtered by the report job. The job sends internal working summaries, not a certified donor report.
- M&E working reports summarize indicators entered by users. They require human validation and source evidence before donor submission.
- Email verification, password-reset workflow, MFA inside the app, rate limiting, formal privacy/legal review, backup automation and incident response must be completed before a public production launch.
- No funder partnership, approval, compliance certification, employment result or grant award is implied.
