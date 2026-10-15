# Humanity Horizons 360
## People, Planet and Peace

Humanity Horizons 360 v1.0 is a Humanity Horizons-owned workspace for opportunity analysis, proposal briefs, CV/resume development, Sustainable Development Goals planning, task management, results frameworks, monitoring and evaluation, feedback, noticeboard moderation, and administrative records.

The proprietary **Humanity Horizons Institutional Readiness & Impact Framework (HH-IRIF)** and **Humanity Horizons Future Workforce Readiness Matrix** organize the platform's internal readiness and skills-development approach. They are planning and self-assessment tools, not external certifications or guarantees. For each live application or project, check the actual opportunity instructions, agreement, applicable law and evidence requirements.

## Run locally (Windows)
1. Install Python 3.11+ from https://www.python.org/downloads/ (check “Add Python to PATH”).
2. Open Command Prompt in the extracted folder.
3. Run:
   ```
   py -m venv .venv
   .venv\Scripts\activate
   py -m pip install --upgrade pip
   pip install -r requirements.txt
   streamlit run app.py
   ```
4. Open the local address Streamlit prints (usually http://localhost:8501).

Optional: set configuration through environment variables or local Streamlit secrets; never commit secrets. DATABASE_URL connects to managed PostgreSQL. ADMIN_EMAILS controls administrator access. TRON_TREASURY_ADDRESS is an admin-visible public address reference only. Optional AI settings are described in the deployment guide.

The default SQLite database is stored in the operating system temporary folder and is for prototype testing only. Do not upload it to GitHub. Hosted use requires managed PostgreSQL, backups, privacy/security review, and professional operation. The app does not initiate cryptocurrency transactions or guarantee real revenue.
