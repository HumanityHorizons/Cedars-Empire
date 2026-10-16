import os, sqlite3, hashlib, secrets, hmac, io, csv
from datetime import date, datetime
from pathlib import Path
import streamlit as st

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

APP_DIR = Path(__file__).parent
DATA_DIR = Path(os.getenv('HH_DATA_DIR', APP_DIR / 'data'))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv('HH_DB_PATH', DATA_DIR / 'humanity_horizons.db'))
APP_NAME = 'Humanity Horizons'
TAGLINE = 'People, Planet and Peace'

st.set_page_config(page_title=APP_NAME, page_icon='🌅', layout='wide')

SDGS = [
    '1. No Poverty','2. Zero Hunger','3. Good Health and Well-Being','4. Quality Education','5. Gender Equality',
    '6. Clean Water and Sanitation','7. Affordable and Clean Energy','8. Decent Work and Economic Growth',
    '9. Industry, Innovation and Infrastructure','10. Reduced Inequalities','11. Sustainable Cities and Communities',
    '12. Responsible Consumption and Production','13. Climate Action','14. Life Below Water','15. Life on Land',
    '16. Peace, Justice and Strong Institutions','17. Partnerships for the Goals'
]
INCOME_ACTIVITIES = [
'Premium AI proposal drafting','CFP and TOR analysis','Funding opportunity intelligence subscriptions','Advanced proposal quality review',
'Budget preparation and validation','Logframe development','Theory-of-change facilitation','M&E report drafting','Project workplan generation',
'CV and resume development','Cover letter preparation','Fellowship application support','Scholarship application preparation',
'Professional online courses','Skills assessments','NGO readiness assessments','Institutional platform subscriptions','Additional organizational user seats',
'Expert-reviewed deliverables','Policy and compliance document packages','Premium project-management templates','Document storage and collaboration upgrades',
'Deadline monitoring and alerts','API access','White-label platform licensing','Custom integrations and development','Priority support and onboarding',
'Training workshops and webinars','Grantmaker workflow services','Recruitment and talent matching','Professional services marketplace','Premium calendar automation',
'Live Studio meeting plans','Meeting transcription and summaries','Voice and audio production','E-signature workflow integrations',
'Translation and localization','Annual and impact report production','Impact measurement services','Research and survey tools',
'Beneficiary and project management','Procurement workflow tools','Volunteer management tools','Appointment and consultation booking',
'White-label training academies','Custom AI assistants','Knowledge-base and document search','Data migration and digitization',
'Corporate social-impact reporting','Sponsored listings and voluntary donations'
]

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, full_name TEXT NOT NULL,
 password_hash TEXT NOT NULL, salt TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, title TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'In progress', due_date TEXT, created_at TEXT NOT NULL,
 FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS opportunities (
 id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, category TEXT NOT NULL,
 source_url TEXT, deadline TEXT, eligibility TEXT, status TEXT NOT NULL DEFAULT 'Published', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS budgets (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, project TEXT NOT NULL, item TEXT NOT NULL,
 quantity REAL NOT NULL, unit_cost REAL NOT NULL, currency TEXT NOT NULL, created_at TEXT NOT NULL,
 FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS documents (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, filename TEXT NOT NULL,
 extracted_text TEXT, created_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS report_runs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, period TEXT NOT NULL, report_type TEXT NOT NULL,
 status TEXT NOT NULL, notes TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, event TEXT NOT NULL, created_at TEXT NOT NULL
);
'''

def db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

def init_db():
    with db() as conn:
        conn.executescript(SCHEMA)
        # First-time local bootstrap admin. Set HH_ADMIN_EMAIL and HH_ADMIN_PASSWORD before first launch.
        try:
            admin_email = str(st.secrets.get('HH_ADMIN_EMAIL', os.getenv('HH_ADMIN_EMAIL', ''))).strip().lower()
            admin_password = str(st.secrets.get('HH_ADMIN_PASSWORD', os.getenv('HH_ADMIN_PASSWORD', '')))
        except Exception:
            admin_email = os.getenv('HH_ADMIN_EMAIL', '').strip().lower()
            admin_password = os.getenv('HH_ADMIN_PASSWORD', '')
        if admin_email and admin_password and not conn.execute('SELECT 1 FROM users WHERE email=?', (admin_email,)).fetchone():
            salt = secrets.token_hex(16)
            pw_hash = hashlib.pbkdf2_hmac('sha256', admin_password.encode(), salt.encode(), 310000).hex()
            conn.execute('INSERT INTO users(email,full_name,password_hash,salt,role,created_at) VALUES(?,?,?,?,?,?)',
                         (admin_email, 'Platform Administrator', pw_hash, salt, 'admin', datetime.utcnow().isoformat()))

def audit(user_id, event):
    with db() as conn:
        conn.execute('INSERT INTO audit_events(user_id,event,created_at) VALUES(?,?,?)',
                     (user_id, event[:300], datetime.utcnow().isoformat()))

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 310000).hex()
    return digest, salt

def verify_password(password, salt, expected):
    got, _ = hash_password(password, salt)
    return hmac.compare_digest(got, expected)

def get_user(email):
    with db() as conn:
        return conn.execute('SELECT * FROM users WHERE email=?', (email.strip().lower(),)).fetchone()

def register_user(name, email, password):
    ph, salt = hash_password(password)
    with db() as conn:
        conn.execute('INSERT INTO users(email,full_name,password_hash,salt,role,created_at) VALUES(?,?,?,?,?,?)',
                     (email.strip().lower(), name.strip(), ph, salt, 'user', datetime.utcnow().isoformat()))

def set_page(title):
    st.title(title)
    st.caption(TAGLINE)

def add_task(user_id, title, due):
    with db() as conn:
        conn.execute('INSERT INTO tasks(user_id,title,due_date,created_at) VALUES(?,?,?,?)',
                     (user_id, title.strip(), str(due) if due else None, datetime.utcnow().isoformat()))

def extract_pdf(upload):
    if fitz is None:
        return '', 'PDF engine is unavailable. Confirm PyMuPDF is installed from requirements.txt.'
    try:
        doc = fitz.open(stream=upload.getvalue(), filetype='pdf')
        text = '\n\n'.join(page.get_text('text') for page in doc)
        doc.close()
        if not text.strip():
            return '', 'No selectable text was found. This may be a scanned PDF and needs OCR.'
        return text, ''
    except Exception as exc:
        return '', f'Could not read this PDF: {exc}'

def show_auth():
    st.sidebar.title(APP_NAME)
    st.sidebar.caption(TAGLINE)
    action = st.sidebar.radio('Account', ['Sign in', 'Create account'])
    if action == 'Create account':
        st.subheader('Create your Humanity Horizons account')
        with st.form('register_form'):
            name = st.text_input('Full name')
            email = st.text_input('Email')
            password = st.text_input('Password', type='password')
            confirm = st.text_input('Confirm password', type='password')
            submitted = st.form_submit_button('Create account', type='primary')
        if submitted:
            if not name.strip() or '@' not in email or len(password) < 12:
                st.error('Enter your name, a valid email and a password of at least 12 characters.')
            elif password != confirm:
                st.error('Passwords do not match.')
            else:
                try:
                    register_user(name, email, password)
                    st.success('Account created. Please sign in.')
                    audit(None, f'Account registered: {email.strip().lower()}')
                except sqlite3.IntegrityError:
                    st.error('An account with this email already exists.')
        st.info('For a public production launch, add email verification, rate limiting, secure recovery and a managed database before opening registration widely.')
    else:
        st.subheader('Sign in')
        with st.form('login_form'):
            email = st.text_input('Email')
            password = st.text_input('Password', type='password')
            submitted = st.form_submit_button('Sign in', type='primary')
        if submitted:
            user = get_user(email)
            if user and verify_password(password, user['salt'], user['password_hash']):
                st.session_state.user = {'id': user['id'], 'name': user['full_name'], 'email': user['email'], 'role': user['role']}
                audit(user['id'], 'Successful sign in')
                st.rerun()
            else:
                st.error('Sign-in failed. Check the email and password.')
        st.caption('Administrator access must be provisioned through the server environment before the first launch. Do not make yourself an administrator by changing a browser field.')

def dashboard(user):
    set_page('Command Center 360°')
    with db() as conn:
        tasks = conn.execute('SELECT * FROM tasks WHERE user_id=? ORDER BY id DESC', (user['id'],)).fetchall()
        docs = conn.execute('SELECT COUNT(*) n FROM documents WHERE user_id=?', (user['id'],)).fetchone()['n']
        budgets = conn.execute('SELECT COUNT(*) n FROM budgets WHERE user_id=?', (user['id'],)).fetchone()['n']
    a,b,c,d = st.columns(4)
    a.metric('My tasks', len(tasks)); b.metric('Documents analysed', docs); c.metric('Budget lines', budgets); d.metric('Role', user['role'].title())
    st.subheader('My tasks')
    if tasks:
        st.dataframe([dict(x) for x in tasks], use_container_width=True, hide_index=True)
    else:
        st.info('No tasks yet. Add your first task in My Tasks.')
    st.subheader('Suggested next steps')
    st.markdown('- Analyse a funding call or TOR.\n- Create a budget linked to a project.\n- Track deadlines and deliverables.\n- Review the evidence before exporting any AI-assisted document.')

def task_page(user):
    set_page('My Tasks')
    with st.form('task_add'):
        title = st.text_input('Task title')
        due = st.date_input('Due date', value=date.today())
        ok = st.form_submit_button('Add task', type='primary')
    if ok:
        if title.strip():
            add_task(user['id'], title, due); audit(user['id'], 'Task created'); st.success('Task added.'); st.rerun()
        else: st.error('Enter a task title.')
    with db() as conn:
        rows = conn.execute('SELECT id,title,status,due_date,created_at FROM tasks WHERE user_id=? ORDER BY id DESC', (user['id'],)).fetchall()
    if rows: st.dataframe([dict(r) for r in rows], use_container_width=True, hide_index=True)

def proposal_page(user):
    set_page('AI Proposal Studio')
    st.write('Upload a call for proposals, TOR or funding guideline to extract text and build a review checklist.')
    upload = st.file_uploader('Upload a PDF', type=['pdf'])
    if upload:
        text, err = extract_pdf(upload)
        if err: st.warning(err)
        else:
            st.success('PDF text extracted. Review the text before using it in an application.')
            st.text_area('Extracted source text', text, height=320)
            if st.button('Save extracted document'):
                with db() as conn:
                    conn.execute('INSERT INTO documents(user_id,filename,extracted_text,created_at) VALUES(?,?,?,?)',
                                 (user['id'], upload.name, text, datetime.utcnow().isoformat()))
                audit(user['id'], 'PDF text extracted and saved')
                st.success('Document saved to this local application database.')
    st.divider()
    st.subheader('Proposal drafting workspace')
    call = st.text_area('Paste key call requirements or extracted text', height=140, key='call_requirements')
    context = st.text_area('Your organization, location, problem and evidence', height=100)
    objective = st.text_input('Proposed project objective')
    if st.button('Create structured proposal outline', type='primary'):
        if not call.strip(): st.error('Paste the call requirements first.')
        else:
            st.markdown('### Draft outline — requires human review')
            sections = ['Executive summary','Problem statement and evidence','Target population and geographic scope','Goal and specific objectives','Theory of change and results framework','Activities and implementation plan','Monitoring, evaluation and learning','Gender, disability inclusion and safeguards','Risk analysis and mitigation','Sustainability','Organizational capacity','Budget narrative','Required annexes and compliance checklist']
            for i, section in enumerate(sections, 1): st.markdown(f'{i}. **{section}** — add source-backed content and verify against the call.')
            st.warning('This starter builds an outline, not a fully validated donor-ready proposal. Connect a configured AI provider and test citations before relying on automated drafting.')
            audit(user['id'], 'Proposal outline generated')

def budget_page(user):
    set_page('Budget Builder')
    with st.form('budget_form'):
        project = st.text_input('Project name')
        item = st.text_input('Budget line description')
        currency = st.selectbox('Currency', ['UGX','USD','EUR','GBP','KES','TZS','RWF'])
        qcol, ucol = st.columns(2)
        qty = qcol.number_input('Quantity', min_value=0.0, value=1.0, step=1.0)
        unit = ucol.number_input('Unit cost', min_value=0.0, value=0.0, step=1000.0)
        ok = st.form_submit_button('Save budget line', type='primary')
    if ok:
        if project.strip() and item.strip():
            with db() as conn:
                conn.execute('INSERT INTO budgets(user_id,project,item,quantity,unit_cost,currency,created_at) VALUES(?,?,?,?,?,?,?)',
                             (user['id'], project.strip(), item.strip(), qty, unit, currency, datetime.utcnow().isoformat()))
            audit(user['id'], 'Budget line created'); st.success(f'Line total: {qty*unit:,.2f} {currency}'); st.rerun()
        else: st.error('Enter the project and line description.')
    with db() as conn:
        rows = conn.execute('SELECT project,item,quantity,unit_cost,currency,quantity*unit_cost AS line_total FROM budgets WHERE user_id=? ORDER BY id DESC', (user['id'],)).fetchall()
    if rows:
        st.dataframe([dict(r) for r in rows], use_container_width=True, hide_index=True)
        st.caption('Totals are grouped by currency; do not add unlike currencies together without a documented exchange rate.')
        csvdata = io.StringIO(); writer = csv.DictWriter(csvdata, fieldnames=list(dict(rows[0]).keys())); writer.writeheader(); writer.writerows([dict(r) for r in rows])
        st.download_button('Export budget CSV', csvdata.getvalue(), file_name='humanity_horizons_budget.csv', mime='text/csv')

def opportunities_page():
    set_page('Opportunity Noticeboard')
    st.caption('Listings are entered by authorized administrators in this starter. Verify each opportunity on the original publisher website before applying.')
    with db() as conn:
        rows = conn.execute("SELECT * FROM opportunities WHERE status='Published' ORDER BY deadline ASC").fetchall()
    if not rows: st.info('No opportunities published yet.')
    for r in rows:
        with st.expander(f"{r['title']} · {r['category']}"):
            st.write('Deadline:', r['deadline'] or 'Not provided')
            st.write('Eligibility:', r['eligibility'] or 'Check original notice')
            if r['source_url']: st.link_button('Open original source', r['source_url'])

def sdg_page():
    set_page('SDG Learning Center')
    sdg = st.selectbox('Choose a Sustainable Development Goal', SDGS)
    st.subheader(sdg)
    st.write('Learning workspace: define the local problem, gather reliable evidence, identify affected groups, design a solution and choose measurable indicators.')
    with st.form('sdg_form'):
        location = st.text_input('Country, district or community')
        problem = st.text_area('Problem to investigate')
        idea = st.text_area('Potential solution or community action')
        indicator = st.text_input('How will progress be measured?')
        ok = st.form_submit_button('Create learning brief')
    if ok:
        st.markdown('### Learning brief')
        st.write('**Goal:**', sdg); st.write('**Location:**', location or 'Not specified'); st.write('**Problem:**', problem or 'Not specified'); st.write('**Solution idea:**', idea or 'Not specified'); st.write('**Indicator:**', indicator or 'To be defined')
        st.caption('Add verified local statistics, source links, dates and consultation with affected communities before publishing claims.')

def cv_page():
    set_page('CV and Career Studio')
    with st.form('cv_form'):
        name = st.text_input('Full name')
        role = st.text_input('Target role')
        skills = st.text_area('Skills and tools')
        experience = st.text_area('Employment, volunteering or project experience (dates and achievements)')
        education = st.text_area('Education and verified qualifications')
        ok = st.form_submit_button('Create CV draft', type='primary')
    if ok:
        cv = f'# {name}\n\n## Target role\n{role}\n\n## Professional profile\nDraft a short profile based only on the verified information below.\n\n## Skills\n{skills}\n\n## Experience\n{experience}\n\n## Education and qualifications\n{education}\n'
        st.text_area('Editable CV draft', cv, height=350)
        st.download_button('Download CV draft (Markdown)', cv, file_name='humanity_horizons_cv.md', mime='text/markdown')
        st.warning('Check all dates, achievements and qualifications before sending this CV to an employer.')

def report_page(user):
    set_page('M&E and Report Studio')
    st.write('Prepare a structured report draft. This starter does not invent project results or automatically send reports.')
    with st.form('report_form'):
        title = st.text_input('Report title')
        period = st.text_input('Reporting period')
        activities = st.text_area('Activities completed and evidence')
        outputs = st.text_area('Verified outputs and indicator values')
        challenges = st.text_area('Challenges, risks and corrective actions')
        next_steps = st.text_area('Next steps')
        ok = st.form_submit_button('Build report draft', type='primary')
    if ok:
        report = f'# {title}\n\n**Reporting period:** {period}\n\n## Activities and evidence\n{activities}\n\n## Verified outputs and indicators\n{outputs}\n\n## Challenges and corrective actions\n{challenges}\n\n## Next steps\n{next_steps}\n\n## Review note\nVerify figures against source records before approval.'
        st.text_area('Report draft', report, height=350)
        st.download_button('Download report draft', report, file_name='humanity_horizons_report.md', mime='text/markdown')
        with db() as conn:
            conn.execute('INSERT INTO report_runs(period,report_type,status,notes,created_at) VALUES(?,?,?,?,?)',
                         (period, 'M&E draft', 'Draft', title, datetime.utcnow().isoformat()))

def revenue_page():
    set_page('Income-Generating Activities')
    st.info('These are proposed services, not evidence of current income. This page does not record payments.')
    st.dataframe([{'No.': i+1, 'Potential service': name, 'Status': 'Proposed — not launched'} for i, name in enumerate(INCOME_ACTIVITIES)], use_container_width=True, hide_index=True)

def admin_page(user):
    if user['role'] != 'admin':
        st.error('Access denied. This area is restricted to authorized administrators.'); return
    set_page('Private Administrator Command Center')
    st.warning('Starter status: no live payment provider is connected. The figures below are database record counts, not revenue or bank balances.')
    with db() as conn:
        user_count = conn.execute('SELECT COUNT(*) n FROM users').fetchone()['n']
        task_count = conn.execute('SELECT COUNT(*) n FROM tasks').fetchone()['n']
        doc_count = conn.execute('SELECT COUNT(*) n FROM documents').fetchone()['n']
        budget_count = conn.execute('SELECT COUNT(*) n FROM budgets').fetchone()['n']
        audit_rows = conn.execute('SELECT created_at,event,user_id FROM audit_events ORDER BY id DESC LIMIT 100').fetchall()
    a,b,c,d = st.columns(4); a.metric('Accounts', user_count); b.metric('Tasks', task_count); c.metric('Saved documents', doc_count); d.metric('Budget lines', budget_count)
    st.subheader('Publish an opportunity')
    with st.form('opportunity_form'):
        title = st.text_input('Opportunity title')
        category = st.selectbox('Category', ['Grant','Scholarship','Fellowship','Job','Internship','Tender','Training','Event','Volunteer'])
        url = st.text_input('Official source URL')
        deadline = st.text_input('Deadline (YYYY-MM-DD or as published)')
        eligibility = st.text_area('Eligibility notes')
        ok = st.form_submit_button('Publish opportunity')
    if ok:
        if not title.strip(): st.error('Title is required.')
        else:
            with db() as conn:
                conn.execute('INSERT INTO opportunities(title,category,source_url,deadline,eligibility,status,created_at) VALUES(?,?,?,?,?,?,?)',
                             (title.strip(), category, url.strip(), deadline.strip(), eligibility.strip(), 'Published', datetime.utcnow().isoformat()))
            audit(user['id'], 'Opportunity published'); st.success('Opportunity published.'); st.rerun()
    st.subheader('Recent audit events')
    if audit_rows: st.dataframe([dict(r) for r in audit_rows], use_container_width=True, hide_index=True)
    st.subheader('Financial integrations')
    st.write('Payment processing, settlement reconciliation, ledger postings and actual balance calculations are not connected in this starter. Do not report financial totals until the provider and accounting integrations are implemented and tested.')

def main():
    init_db()
    if 'user' not in st.session_state:
        st.session_state.user = None
    if not st.session_state.user:
        st.markdown(f'# 🌅 {APP_NAME}')
        st.subheader(TAGLINE)
        st.write('An integrated workspace for funding opportunities, proposals, project delivery, career development and impact learning.')
        show_auth(); return
    user = st.session_state.user
    st.sidebar.success(f"Signed in: {user['name']}")
    pages = ['Command Center 360°','My Tasks','AI Proposal Studio','Budget Builder','Opportunity Noticeboard','SDG Learning Center','CV and Career Studio','M&E and Report Studio','Income-Generating Activities']
    if user['role'] == 'admin': pages.append('Private Administrator Command Center')
    choice = st.sidebar.radio('Navigate', pages)
    if st.sidebar.button('Sign out'):
        audit(user['id'], 'Signed out'); del st.session_state.user; st.rerun()
    if choice == 'Command Center 360°': dashboard(user)
    elif choice == 'My Tasks': task_page(user)
    elif choice == 'AI Proposal Studio': proposal_page(user)
    elif choice == 'Budget Builder': budget_page(user)
    elif choice == 'Opportunity Noticeboard': opportunities_page()
    elif choice == 'SDG Learning Center': sdg_page()
    elif choice == 'CV and Career Studio': cv_page()
    elif choice == 'M&E and Report Studio': report_page(user)
    elif choice == 'Income-Generating Activities': revenue_page()
    elif choice == 'Private Administrator Command Center': admin_page(user)

if __name__ == '__main__':
    main()
