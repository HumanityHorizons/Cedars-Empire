from __future__ import annotations

import os
import re
import io
import csv
import json
import uuid
import hmac
import hashlib
import secrets
import sqlite3
import tempfile
from pathlib import Path
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st
import pymupdf
from docx import Document

# -----------------------------------------------------------------------------
# Humanity Horizons 360 — functional MVP / deployment-safe prototype
# -----------------------------------------------------------------------------
APP_DIR = Path(__file__).parent
LOGO = APP_DIR / "assets" / "humanity_horizons_logo.jpg"
LOCAL_DB = Path(os.getenv("HH_DATA_DIR", tempfile.gettempdir())) / "humanity_horizons.db"
PBKDF2_ITERATIONS = 310_000

st.set_page_config(page_title="Humanity Horizons 360", page_icon="🌍", layout="wide")
st.markdown("""
<style>
.stApp { background: linear-gradient(180deg,#f4fbff 0%,#ffffff 70%); }
h1,h2,h3 { color:#0b2d62; }
[data-testid="stSidebar"] { background:#eaf8ff; }
div.stButton>button[kind="primary"] { background:#078ee8; color:white; border:0; border-radius:10px; }
.hh-small { font-size: .88rem; color: #4f6072; }
</style>
""", unsafe_allow_html=True)


def setting(name: str, default: str = "") -> str:
    """Read from Streamlit secrets first, then environment; never print secret values."""
    try:
        value = st.secrets.get(name, default)
        if value not in (None, ""):
            return str(value)
    except Exception:
        pass
    return str(os.getenv(name, default))


DATABASE_URL = setting("DATABASE_URL", "").strip()
ADMIN_EMAILS = {e.strip().lower() for e in setting("ADMIN_EMAILS", "").split(",") if e.strip()}
TREASURY_ADDRESS = setting("TRON_TREASURY_ADDRESS", "").strip()
OPENAI_API_KEY = setting("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = setting("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_optional_ai(prompt: str) -> str | None:
    """Use an optional configured model only when the user explicitly opts in."""
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.responses.create(model=OPENAI_MODEL, input=prompt)
        return (getattr(response, "output_text", "") or "").strip() or None
    except Exception as exc:
        # Avoid leaking stack traces or credentials to the UI.
        st.warning(f"The connected AI service did not return a draft. You can continue with the local template. Details: {type(exc).__name__}")
        return None


def db_connect():
    if DATABASE_URL:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("DATABASE_URL is configured, but psycopg is missing. Rebuild after installing requirements.txt.") from exc
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)
        return conn, "postgres"
    LOCAL_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(LOCAL_DB), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn, "sqlite"


def db_exec(sql: str, params: tuple = ()) -> int:
    conn, kind = db_connect()
    try:
        q = sql.replace("?", "%s") if kind == "postgres" else sql
        cur = conn.cursor() if kind == "postgres" else conn
        cur.execute(q, params)
        rowcount = getattr(cur, "rowcount", 0)
        conn.commit()
        return rowcount
    finally:
        conn.close()


def db_all(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    conn, kind = db_connect()
    try:
        q = sql.replace("?", "%s") if kind == "postgres" else sql
        cur = conn.cursor() if kind == "postgres" else conn
        cur.execute(q, params)
        rows = cur.fetchall()
        return [dict(r) if not isinstance(r, dict) else r for r in rows]
    finally:
        conn.close()


def init_db() -> None:
    # Explicit TEXT/INTEGER types work in both SQLite and PostgreSQL.
    schemas = [
        """CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, full_name TEXT NOT NULL,
            password_salt TEXT NOT NULL, password_hash TEXT NOT NULL,
            account_type TEXT NOT NULL, organization TEXT, sector TEXT,
            b2b_purpose TEXT NOT NULL, followup_optin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL, last_login TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY, user_email TEXT NOT NULL, title TEXT NOT NULL,
            description TEXT, status TEXT NOT NULL, priority TEXT NOT NULL,
            due_date TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            completed_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS attendance (
            id TEXT PRIMARY KEY, session_id TEXT NOT NULL, event_name TEXT NOT NULL,
            user_email TEXT, followup_optin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL, details TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS audit_events (
            id TEXT PRIMARY KEY, user_email TEXT NOT NULL, event_name TEXT NOT NULL,
            declared_purpose TEXT, created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS feedback (
            id TEXT PRIMARY KEY, user_email TEXT, organization TEXT, category TEXT NOT NULL,
            rating INTEGER, message TEXT NOT NULL, anonymous INTEGER NOT NULL DEFAULT 0,
            followup_optin INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS noticeboard (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, organization TEXT,
            opportunity_type TEXT NOT NULL, country TEXT, deadline TEXT,
            link TEXT, description TEXT NOT NULL, source_url TEXT,
            status TEXT NOT NULL, created_by TEXT, created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS treasury_ledger (
            id TEXT PRIMARY KEY, entry_type TEXT NOT NULL, amount TEXT NOT NULL,
            currency TEXT NOT NULL, source TEXT NOT NULL, reference TEXT,
            notes TEXT, entered_by TEXT NOT NULL, created_at TEXT NOT NULL
        )""",
    ]
    conn, kind = db_connect()
    try:
        cur = conn.cursor() if kind == "postgres" else conn
        for schema in schemas:
            cur.execute(schema)
        conn.commit()
    finally:
        conn.close()


try:
    init_db()
except Exception as e:
    st.error("The workspace database could not initialize. If you configured DATABASE_URL, verify the database URL and network access in Streamlit secrets. For a durable production deployment, use a managed PostgreSQL database.")
    st.code(str(e))
    st.stop()


def record_event(user_email: str | None, event_name: str, purpose: str | None = None) -> None:
    # Activity events are only stored after sign-in; no IP address or fingerprint is collected.
    if user_email:
        db_exec("INSERT INTO audit_events (id,user_email,event_name,declared_purpose,created_at) VALUES (?,?,?,?,?)",
                (str(uuid.uuid4()), user_email, event_name, purpose, now_iso()))


def pw_hash(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return salt.hex(), hashed.hex()


def verify_password(password: str, salt_hex: str, expected_hash: str) -> bool:
    _, actual = pw_hash(password, salt_hex)
    return hmac.compare_digest(actual, expected_hash)


def extract_text(upload) -> str:
    raw = upload.getvalue()
    name = upload.name.lower()
    if name.endswith(".pdf"):
        with pymupdf.open(stream=raw, filetype="pdf") as doc:
            return "\n".join(f"[PAGE {i+1}]\n{page.get_text()}" for i, page in enumerate(doc))
    if name.endswith(".docx"):
        doc = Document(io.BytesIO(raw))
        lines = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                lines.append(" | ".join(cell.text.replace("\n", " ") for cell in row.cells))
        return "\n".join(lines)
    return raw.decode("utf-8", errors="replace")


def snippets(text: str, patterns: list[str], limit: int = 8) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        for m in re.finditer(pattern, text, re.I):
            hits.append(text[max(0, m.start()-130):min(len(text), m.end()+260)].replace("\n", " ").strip())
    result, seen = [], set()
    for hit in hits:
        key = hit[:110]
        if key not in seen:
            seen.add(key)
            result.append(hit)
    return result[:limit]


def safe_url(url: str) -> bool:
    return not url or url.strip().lower().startswith(("https://", "http://"))


def download_gate(label: str, data: bytes | str, filename: str, mime: str = "text/plain", key: str = "download") -> None:
    purpose = st.text_input(f"B2B / project purpose for: {label}", key=f"purpose_{key}", placeholder="e.g. prepare a proposal for a rural livelihoods project")
    rights = st.checkbox("I confirm I have the right to download/use this material and understand the platform records this action for operational audit.", key=f"rights_{key}")
    payload = data.encode("utf-8") if isinstance(data, str) else data
    clicked = st.download_button(label, payload, file_name=filename, mime=mime, disabled=not (purpose.strip() and rights), key=f"button_{key}")
    if clicked:
        record_event(st.session_state.get("user_email"), f"download:{filename}", purpose.strip())


def upload_rights_gate(key: str, label: str = "upload") -> bool:
    purpose = st.text_input(f"B2B / project purpose for this {label}", key=f"upload_purpose_{key}", placeholder="e.g. assess eligibility for a funding call")
    right = st.checkbox("I have permission to upload this file and have removed unnecessary sensitive personal/beneficiary data.", key=f"upload_rights_{key}")
    st.session_state[f"upload_purpose_value_{key}"] = purpose.strip()
    return bool(purpose.strip() and right)


def log_attendance(event_name: str, user_email: str | None = None, opted_in: bool = False, details: str = "") -> None:
    # No IP, device fingerprint or visitor name is collected for anonymous attendance.
    db_exec("INSERT INTO attendance (id,session_id,event_name,user_email,followup_optin,created_at,details) VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), st.session_state.get("visitor_session", str(uuid.uuid4())), event_name,
             user_email if opted_in else None, 1 if opted_in else 0, now_iso(), details[:200]))


# Anonymous visit is counted once per browser session; no IP/device fingerprint is collected.
if "visitor_session" not in st.session_state:
    st.session_state.visitor_session = str(uuid.uuid4())
    try:
        log_attendance("anonymous_page_session")
    except Exception:
        pass

# -----------------------------------------------------------------------------
# SDG navigator: five representative problem areas each Goal can help address.
# These are navigation examples, not a claim that each goal exclusively solves them.
# -----------------------------------------------------------------------------
SDGS = [
    (1, "No Poverty", "End poverty in all its forms everywhere", ["Extreme income poverty and insecure livelihoods", "Limited access to social protection", "Insecure housing and basic services", "Financial exclusion and vulnerability to shocks", "Unequal access to assets and economic opportunity"]),
    (2, "Zero Hunger", "End hunger, achieve food security and improved nutrition and promote sustainable agriculture", ["Food insecurity and seasonal hunger", "Child and maternal malnutrition", "Low smallholder productivity and incomes", "Food loss, waste and unstable supply chains", "Climate and conflict shocks to food systems"]),
    (3, "Good Health and Well-being", "Ensure healthy lives and promote well-being for all at all ages", ["Preventable disease and avoidable deaths", "Limited access to essential health services", "Maternal, newborn and child health gaps", "Mental-health needs and psychosocial distress", "Outbreak risk and inadequate health preparedness"]),
    (4, "Quality Education", "Ensure inclusive and equitable quality education and promote lifelong learning opportunities for all", ["Children out of school or at risk of dropping out", "Low literacy and numeracy outcomes", "Education costs and unequal access", "Digital and assistive-technology learning gaps", "Limited job-relevant and lifelong learning"]),
    (5, "Gender Equality", "Achieve gender equality and empower all women and girls", ["Gender-based violence and harmful practices", "Unequal unpaid care burdens", "Barriers to leadership and decision-making", "Unequal access to land, finance and assets", "Gender gaps in education, work and digital access"]),
    (6, "Clean Water and Sanitation", "Ensure availability and sustainable management of water and sanitation for all", ["Unsafe drinking water and waterborne disease", "Inadequate sanitation and hygiene facilities", "Water scarcity and unreliable supply", "Untreated wastewater and water pollution", "Weak water-resource management and resilience"]),
    (7, "Affordable and Clean Energy", "Ensure access to affordable, reliable, sustainable and modern energy for all", ["Households without reliable electricity", "Dependence on polluting cooking fuels", "High energy costs for households and enterprises", "Energy insecurity for schools and health centres", "Limited investment in clean and efficient energy"]),
    (8, "Decent Work and Economic Growth", "Promote sustained, inclusive and sustainable economic growth, full and productive employment and decent work for all", ["Youth unemployment and underemployment", "Unsafe, informal or low-paid work", "Skills mismatch and limited career pathways", "Barriers to entrepreneurship and MSME growth", "Forced labour, trafficking and labour-rights abuses"]),
    (9, "Industry, Innovation and Infrastructure", "Build resilient infrastructure, promote inclusive and sustainable industrialization and foster innovation", ["Unreliable transport, power and digital infrastructure", "Limited access to technology and research capacity", "Low value addition and industrial diversification", "Fragile infrastructure exposed to disasters", "Finance gaps for innovation and small enterprises"]),
    (10, "Reduced Inequalities", "Reduce inequality within and among countries", ["Discrimination and exclusion from services", "Unequal income and wealth opportunities", "Barriers facing persons with disabilities", "Unequal treatment of migrants and displaced people", "Digital, geographic and social mobility gaps"]),
    (11, "Sustainable Cities and Communities", "Make cities and human settlements inclusive, safe, resilient and sustainable", ["Unsafe or unaffordable housing and informal settlements", "Traffic congestion and unsafe mobility", "Insufficient accessible green and public spaces", "Urban waste, pollution and disaster exposure", "Weak local planning and heritage protection"]),
    (12, "Responsible Consumption and Production", "Ensure sustainable consumption and production patterns", ["Food and material waste across supply chains", "Pollution from unsustainable production", "Low recycling and circular-economy capacity", "Poor chemical and hazardous-waste management", "Unsustainable procurement and resource use"]),
    (13, "Climate Action", "Take urgent action to combat climate change and its impacts", ["Floods, droughts and heat impacts", "High greenhouse-gas emissions", "Climate risks to food, water and livelihoods", "Limited local adaptation and early-warning capacity", "Climate-finance and resilience planning gaps"]),
    (14, "Life Below Water", "Conserve and sustainably use the oceans, seas and marine resources for sustainable development", ["Marine plastic and land-based pollution", "Overfishing and declining fish stocks", "Damage to coastal and marine habitats", "Ocean acidification and warming impacts", "Weak coastal management and community resilience"]),
    (15, "Life on Land", "Protect, restore and promote sustainable use of terrestrial ecosystems, sustainably manage forests, combat desertification, and halt and reverse land degradation and halt biodiversity loss", ["Deforestation and habitat fragmentation", "Biodiversity loss and species decline", "Soil erosion, desertification and land degradation", "Illegal wildlife trade and poaching", "Invasive species and unsustainable land use"]),
    (16, "Peace, Justice and Strong Institutions", "Promote peaceful and inclusive societies for sustainable development, provide access to justice for all and build effective, accountable and inclusive institutions at all levels", ["Violence, insecurity and conflict-related harm", "Limited access to justice and legal identity", "Corruption, fraud and weak accountability", "Exclusion from public decision-making", "Abuse, exploitation and unsafe complaint pathways"]),
    (17, "Partnerships for the Goals", "Strengthen the means of implementation and revitalize the Global Partnership for Sustainable Development", ["Insufficient financing for development priorities", "Gaps in technology and knowledge exchange", "Weak multi-stakeholder coordination", "Limited, fragmented or disaggregated data", "Capacity gaps in trade, statistics and implementation"]),
]

FUTURE_SKILLS = [
    "AI and data literacy", "Networks and cybersecurity", "Technological literacy", "Creative thinking",
    "Resilience, flexibility and agility", "Curiosity and lifelong learning", "Leadership and social influence",
    "Talent management", "Analytical thinking", "Environmental stewardship", "Systems thinking",
    "Communication and stakeholder engagement", "Project and operations management", "Monitoring, evaluation and learning",
    "Financial literacy and budgeting", "Data visualization", "Safeguarding and ethical practice"
]

HH_STANDARDS_CHECKS = [
    ("Eligibility and due diligence", "Legal status, governance, registration, beneficial ownership where required, sanctions screening where required, capacity and partner declarations"),
    ("Results-based management", "Clear problem analysis, theory of change, outputs/outcomes, indicators, baselines, targets, assumptions and evidence"),
    ("Monitoring, evaluation and learning", "Data quality, disaggregation, learning loops, evaluation independence where relevant, feedback-informed adaptation"),
    ("Financial management", "Approved budget, segregation of duties, authorization limits, reconciliations, audit trail, eligible-cost rules and asset control"),
    ("Procurement and conflicts of interest", "Competition or approved procurement method, documented evaluation, conflict declarations, contract and supplier records"),
    ("Safeguarding and PSEA", "Code of conduct, prevention measures, safe reporting, survivor-centred handling and confidential referral routes"),
    ("Fraud, corruption and whistleblowing", "Fraud risk assessment, reporting channel, investigation protocol, anti-bribery and retaliation protections"),
    ("Data protection and confidentiality", "Purpose limitation, lawful basis/consent where required, minimization, access controls, retention and breach response"),
    ("Gender, disability and inclusion", "Barrier analysis, accessible participation, gender equality, non-discrimination and safe feedback channels"),
    ("Environmental and social safeguards", "Do-no-harm analysis, climate/environmental risks, community safety and mitigation measures"),
    ("Accountability to affected people", "Accessible complaints/feedback mechanism, response times, participation, closure and learning"),
    ("Partner/subgrant management", "Partner assessment, roles, capacity support, agreements, monitoring and documented risk-based assurance"),
    ("Records and communications", "Version control, document retention, consent for photos/case stories and source verification"),
    ("Exit and sustainability", "Ownership, maintenance, handover, financial/operational sustainability and responsible transition"),
]

# -----------------------------------------------------------------------------
# Page chrome and auth
# -----------------------------------------------------------------------------
if LOGO.exists():
    st.image(str(LOGO), width=310)
else:
    st.title("HUMANITY HORIZONS")
st.caption("People, Planet and Peace")
st.title("Humanity Horizons 360")
st.write("An integrated Humanity Horizons workspace for opportunity intelligence, proposals, career readiness, SDG programming, project delivery, accountability and partnerships.")
st.info("Privacy-first prototype: anonymous visits are counted without collecting IP addresses or device fingerprints. Personal follow-up data is stored only when you create an account and opt in. No data is sold by this prototype; all sponsored content or fees must be clearly labelled.")


def set_login(user: dict[str, Any], login_purpose: str = "") -> None:
    st.session_state.user_email = user["email"]
    st.session_state.full_name = user["full_name"]
    st.session_state.account_type = user.get("account_type", "Individual")
    st.session_state.followup_optin = int(user.get("followup_optin", 0)) == 1
    st.session_state.last_login = now_iso()
    db_exec("UPDATE users SET last_login=? WHERE email=?", (now_iso(), user["email"]))
    log_attendance("member_sign_in", user["email"], bool(user.get("followup_optin", 0)), "follow-up attendance opt-in controls identifiable attendance")
    record_event(user["email"], "sign_in", login_purpose.strip() or None)


def signup_page() -> None:
    signin, signup, public = st.tabs(["Sign in", "Create account", "Public noticeboard"])
    with signin:
        st.subheader("Welcome back")
        st.caption("Each sign-in records your stated B2B/workspace purpose for the session. This is not a payment request.")
        with st.form("signin_form"):
            email = st.text_input("Email address", key="signin_email").strip().lower()
            password = st.text_input("Password", type="password", key="signin_password")
            signin_purpose = st.text_input("B2B / business purpose for this session", placeholder="e.g. review a climate grant and plan proposal activities")
            confirm_profile = st.checkbox("I confirm my B2B purpose is accurate and I have read the privacy notice.")
            submit = st.form_submit_button("Sign in", type="primary")
        if submit:
            if len(signin_purpose.strip()) < 8:
                st.error("Enter your B2B / business purpose for this session (at least 8 characters).")
            elif not confirm_profile:
                st.error("Please confirm your B2B profile and privacy notice to continue.")
            elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                st.error("Enter a valid email address.")
            else:
                users = db_all("SELECT * FROM users WHERE email=?", (email,))
                if not users or not verify_password(password, users[0]["password_salt"], users[0]["password_hash"]):
                    st.error("Email or password is incorrect.")
                else:
                    set_login(users[0], signin_purpose.strip())
                    st.success("Signed in. Loading your workspace…")
                    st.rerun()
    with signup:
        st.subheader("Create your Humanity Horizons account")
        st.write("A short B2B / purpose profile helps tailor tools and understand legitimate organizational use. It is not an advertising consent and does not authorize data resale.")
        with st.form("signup_form"):
            full_name = st.text_input("Full name")
            email = st.text_input("Email address").strip().lower()
            password = st.text_input("Create password (at least 10 characters)", type="password")
            password2 = st.text_input("Confirm password", type="password")
            account_type = st.selectbox("Account type", ["Individual / job seeker", "NGO / civil society organization", "Business / private sector", "Public institution", "Donor / funder", "Research / academic", "Other"])
            organization = st.text_input("Organization (optional for individuals)")
            sector = st.selectbox("Main sector", ["Select…", "Education", "Health", "Climate / environment", "Livelihoods / economic inclusion", "Gender / protection", "Governance / peacebuilding", "Humanitarian response", "Agriculture / food security", "Digital / technology", "Research / evaluation", "Multiple sectors", "Other"])
            purpose = st.text_area("B2B / workspace purpose — how will you use Humanity Horizons?", placeholder="Example: identify grants, draft proposals and monitor a youth employment project.")
            followup = st.checkbox("I opt in to follow-up emails and identifiable attendance records. Optional; I can opt out later.")
            agree = st.checkbox("I agree to the Humanity Horizons platform terms and privacy notice. I understand that outputs are decision-support drafts and do not guarantee funding, employment or compliance outcomes.")
            create = st.form_submit_button("Create account", type="primary")
        if create:
            errors = []
            if not full_name.strip(): errors.append("Enter your name.")
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email): errors.append("Enter a valid email address.")
            if len(password) < 10: errors.append("Password must contain at least 10 characters.")
            if password != password2: errors.append("Passwords do not match.")
            if sector == "Select…": errors.append("Select a sector.")
            if len(purpose.strip()) < 12: errors.append("Describe your workspace purpose in at least 12 characters.")
            if not agree: errors.append("Accept the platform terms and privacy notice to create an account.")
            if errors:
                for err in errors: st.error(err)
            elif db_all("SELECT id FROM users WHERE email=?", (email,)):
                st.error("An account already exists for this email. Please sign in.")
            else:
                salt, hashed = pw_hash(password)
                db_exec("INSERT INTO users (id,email,full_name,password_salt,password_hash,account_type,organization,sector,b2b_purpose,followup_optin,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (str(uuid.uuid4()), email, full_name.strip(), salt, hashed, account_type, organization.strip(), sector, purpose.strip(), int(followup), now_iso()))
                user = db_all("SELECT * FROM users WHERE email=?", (email,))[0]
                set_login(user, purpose.strip())
                record_event(email, "account_created", purpose.strip())
                st.success("Account created. Your workspace is ready.")
                st.rerun()
    with public:
        st.subheader("Public opportunity noticeboard")
        st.caption("Only moderated, published listings are displayed. Verify any opportunity on its original source before sharing documents or paying fees.")
        board = db_all("SELECT * FROM noticeboard WHERE status=? ORDER BY created_at DESC", ("Published",))
        if not board:
            st.info("No approved opportunities have been posted yet. Sign in to submit a listing for moderation.")
        else:
            for item in board:
                with st.container(border=True):
                    st.markdown(f"**{item['title']}** · {item['opportunity_type']}")
                    st.caption(f"{item.get('organization') or 'Publisher not stated'} | {item.get('country') or 'Location not specified'} | Deadline: {item.get('deadline') or 'See source'}")
                    st.write(item["description"])
                    if item.get("link") and safe_url(item["link"]): st.markdown(f"[Open original opportunity]({item['link']})")
                    if item.get("source_url"): st.caption(f"Source: {item['source_url']}")


is_logged_in = bool(st.session_state.get("user_email"))
if not is_logged_in:
    with st.sidebar:
        st.subheader("Workspace access")
        st.write("Sign in or create an account to save your work, manage tasks and use the personal tools.")
        st.caption("Administrator tools are enabled only for addresses explicitly configured in Streamlit secrets.")
    signup_page()
    st.stop()

USER_EMAIL = st.session_state.user_email
USER_NAME = st.session_state.full_name
IS_ADMIN = USER_EMAIL.lower() in ADMIN_EMAILS

with st.sidebar:
    st.markdown(f"**Signed in as:** {USER_NAME}")
    st.caption(USER_EMAIL)
    if IS_ADMIN: st.success("Administrator workspace")
    pages = [
        "Dashboard", "My Tasks", "Opportunity Analysis", "Proposal Studio", "CV / Resume Studio",
        "SDG Navigator", "Noticeboard", "HH Standards & Impact", "Donor Feedback",
        "B2B Collaboration", "Privacy and Data", "Admin Console"
    ]
    if not IS_ADMIN: pages.remove("Admin Console")
    page = st.radio("Navigate", pages, label_visibility="collapsed")
    if st.button("Sign out"):
        record_event(USER_EMAIL, "sign_out")
        for key in ["user_email", "full_name", "account_type", "followup_optin", "last_login"]:
            st.session_state.pop(key, None)
        st.rerun()
    st.divider()
    st.caption("Platform release: 1.0 prototype")
    st.caption("AI: connected" if OPENAI_API_KEY else "AI: local structured mode (API key not configured)")
    st.caption("No funding, AI accuracy, compliance certification or payment settlement is guaranteed.")

# -----------------------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------------------
if page == "Dashboard":
    st.header(f"Welcome, {USER_NAME.split()[0]}")
    tasks = db_all("SELECT * FROM tasks WHERE user_email=? ORDER BY updated_at DESC", (USER_EMAIL,))
    total = len(tasks); in_progress = sum(1 for t in tasks if t["status"] == "In progress")
    completed = sum(1 for t in tasks if t["status"] == "Executed / completed")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("My tasks", total); col2.metric("In progress", in_progress); col3.metric("Executed", completed); col4.metric("Published opportunities", len(db_all("SELECT id FROM noticeboard WHERE status=?", ("Published",))))
    st.subheader("Continue your work")
    st.write("Your workspace is designed to keep proposal development, tasks, CV improvement, SDG alignment, feedback and delivery evidence in one place.")
    st.markdown("**Suggested workflow:** Review an opportunity → check eligibility → create a task → draft a proposal → build results indicators → track delivery → report evidence and feedback.")
    if tasks:
        st.dataframe(pd.DataFrame([{ "Task": t["title"], "Status": t["status"], "Priority": t["priority"], "Due": t["due_date"] or "—", "Last updated": t["updated_at"] } for t in tasks[:8]]), use_container_width=True, hide_index=True)
    st.subheader("Transparency and readiness")
    st.info("Humanity Horizons independently owns and maintains this workspace and its proprietary readiness framework. Use the exact eligibility rules, evaluation criteria and reporting instructions in each opportunity or agreement when preparing an application.")

# -----------------------------------------------------------------------------
# Task management: persisted through configured database
# -----------------------------------------------------------------------------
elif page == "My Tasks":
    st.header("My tasks: in progress and executed")
    st.caption("Tasks are saved to the configured database. Configure managed PostgreSQL for durable persistence on a hosted deployment.")
    with st.form("new_task_form"):
        title = st.text_input("Task title")
        description = st.text_area("Description / desired output")
        status = st.selectbox("Status", ["Not started", "In progress", "Executed / completed", "Blocked"])
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        due_text = st.text_input("Due date (YYYY-MM-DD, optional)", placeholder="2026-12-31")
        add = st.form_submit_button("Save task", type="primary")
    if add:
        if not title.strip(): st.error("Task title is required.")
        else:
            if due_text.strip() and not re.match(r"^\d{4}-\d{2}-\d{2}$", due_text.strip()):
                st.error("Due date must use YYYY-MM-DD.")
            else:
                db_exec("INSERT INTO tasks (id,user_email,title,description,status,priority,due_date,created_at,updated_at,completed_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (str(uuid.uuid4()), USER_EMAIL, title.strip(), description.strip(), status, priority, due_text.strip() or None, now_iso(), now_iso(), now_iso() if status == "Executed / completed" else None))
                record_event(USER_EMAIL, "task_created")
                st.success("Task saved."); st.rerun()
    all_tasks = db_all("SELECT * FROM tasks WHERE user_email=? ORDER BY updated_at DESC", (USER_EMAIL,))
    st.subheader("Update a task")
    if all_tasks:
        options = {f"{t['title']} · {t['status']} · {t['id'][:8]}": t for t in all_tasks}
        chosen_label = st.selectbox("Select task", list(options.keys()))
        selected = options[chosen_label]
        with st.form("update_task_form"):
            new_status = st.selectbox("Status", ["Not started", "In progress", "Executed / completed", "Blocked"], index=["Not started", "In progress", "Executed / completed", "Blocked"].index(selected["status"]))
            new_priority = st.selectbox("Priority", ["High", "Medium", "Low"], index=["High", "Medium", "Low"].index(selected["priority"]))
            new_due = st.text_input("Due date (YYYY-MM-DD; blank if none)", value=selected["due_date"] or "")
            save_change = st.form_submit_button("Update selected task")
        if save_change:
            if new_due and not re.match(r"^\d{4}-\d{2}-\d{2}$", new_due):
                st.error("Due date must use YYYY-MM-DD.")
            else:
                completed_at = now_iso() if new_status == "Executed / completed" else None
                db_exec("UPDATE tasks SET status=?,priority=?,due_date=?,updated_at=?,completed_at=? WHERE id=? AND user_email=?",
                        (new_status, new_priority, new_due or None, now_iso(), completed_at, selected["id"], USER_EMAIL))
                record_event(USER_EMAIL, "task_updated")
                st.success("Task updated."); st.rerun()
        st.subheader("All tasks")
        tdf = pd.DataFrame([{ "Task": t["title"], "Description": t["description"], "Status": t["status"], "Priority": t["priority"], "Due date": t["due_date"], "Created": t["created_at"], "Updated": t["updated_at"], "Completed": t["completed_at"] } for t in all_tasks])
        st.dataframe(tdf, use_container_width=True, hide_index=True)
        download_gate("task export", tdf.to_csv(index=False), "humanity_horizons_tasks.csv", "text/csv", "task_export")
    else:
        st.info("No tasks yet. Create one above to start tracking work.")

# -----------------------------------------------------------------------------
# Opportunity analysis
# -----------------------------------------------------------------------------
elif page == "Opportunity Analysis":
    st.header("Opportunity, TOR, grant and fellowship analysis")
    st.write("Upload a call or TOR. Automatic phrase extraction identifies evidence candidates; always check the complete official source.")
    gate = upload_rights_gate("opportunity", "opportunity document")
    up = st.file_uploader("Upload PDF, DOCX, TXT or Markdown", type=["pdf", "docx", "txt", "md"], key="opportunity_document")
    if up:
        if not gate:
            st.warning("Confirm the B2B purpose and upload rights before the system processes this file.")
        else:
            try:
                txt = extract_text(up)
                st.session_state["source_text"] = txt
                st.session_state["source_name"] = up.name
                record_event(USER_EMAIL, f"upload:{up.name}", st.session_state.get("upload_purpose_value_opportunity", ""))
                st.success(f"Extracted {len(txt):,} characters from {up.name}")
                st.text_area("Review extracted source text", txt[:25000], height=240)
                ai_opportunity_optin = st.checkbox("If an AI API key is configured, I consent to sending this extracted document text to that provider for additional analysis.", key="ai_opportunity_consent")
                if st.button("Run AI opportunity review", key="ai_opportunity_button", disabled=not (ai_opportunity_optin and bool(OPENAI_API_KEY))):
                    ai_prompt = f"""Analyze this funding/TOR/fellowship document carefully. Extract only evidence present in the source. Organize: (1) opportunity type/purpose, (2) eligibility requirements, (3) deadline and timezone if stated, (4) geography and applicant types, (5) grant range and eligible/ineligible costs if stated, (6) required attachments, (7) evaluation criteria, (8) submission method, (9) implementation and reporting requirements, (10) safeguarding/data protection/inclusion obligations, (11) risks and ambiguities, (12) missing facts to verify. Quote short source snippets or page markers where possible. Never assume eligibility from absent text; use 'not found in provided extract' when needed. End with a checklist. SOURCE TEXT:\n{txt[:18000]}"""
                    result = run_optional_ai(ai_prompt)
                    if result:
                        st.session_state["ai_opportunity_result"] = result
                        record_event(USER_EMAIL, "ai_opportunity_review", st.session_state.get("upload_purpose_value_opportunity", ""))
                if st.session_state.get("ai_opportunity_result"):
                    st.text_area("AI opportunity review (verify against the original)", st.session_state["ai_opportunity_result"], height=360)
                    download_gate("AI opportunity review", st.session_state["ai_opportunity_result"], "humanity_horizons_ai_opportunity_review.txt", key="ai_opportunity_review")
                categories = {
                    "Eligibility": [r"eligib(?:le|ility)", r"who can apply", r"applicant must", r"applicants must", r"registered organization"],
                    "Deadline": [r"deadline", r"closing date", r"due date", r"submit.{0,30}by"],
                    "Funding / budget": [r"funding available", r"grant size", r"maximum award", r"budget limit", r"amount of funding"],
                    "Required attachments": [r"required documents", r"supporting documents", r"attachments?", r"letter of support", r"CVs?"],
                    "Evaluation criteria": [r"evaluation criteria", r"selection criteria", r"scoring", r"assessment criteria"],
                    "Submission": [r"submission portal", r"submit.{0,25}application", r"email.{0,30}application"],
                    "Objectives / results": [r"objectives?", r"expected outcomes?", r"outputs?", r"terms of reference", r"scope of work"],
                    "Geography / duration": [r"eligible countr(?:y|ies)", r"geographic(?:al)? focus", r"project duration", r"implementation period"]}
                for label, patterns in categories.items():
                    with st.expander(label, expanded=label in ("Eligibility", "Deadline")):
                        found = snippets(txt, patterns)
                        if found:
                            for i, item in enumerate(found, 1): st.markdown(f"**Evidence candidate {i}:** {item}")
                        else: st.write("No matching phrase found automatically. Check the whole source; this is not proof the criterion is absent.")
                download_gate("extracted opportunity text", txt, "humanity_horizons_source_extract.txt", key="source_extract")
            except Exception as e:
                st.error(f"Could not read this document: {e}")
    st.warning("Scanned PDFs may need OCR. Tables, footnotes and annexes must be checked against the original call. Do not upload case files or unnecessary beneficiary details.")

# -----------------------------------------------------------------------------
# Proposal drafting
# -----------------------------------------------------------------------------
elif page == "Proposal Studio":
    st.header("Proposal Studio")
    st.caption("Creates structured, editable briefs; it does not connect to a hosted generative-AI model in this release.")
    dtype = st.selectbox("Document type", ["Concept note", "Full grant proposal", "Consultancy technical proposal", "Fellowship statement", "Cover letter", "Research proposal", "Theory of change", "Budget narrative"])
    title = st.text_input("Project / application title")
    applicant = st.text_input("Applicant / organization / candidate")
    donor = st.text_input("Donor / institution / fellowship")
    problem = st.text_area("Problem, need or motivation")
    objective = st.text_area("Objectives and expected results")
    approach = st.text_area("Activities, methodology and implementation approach")
    evidence = st.text_area("Verified experience, evidence and past results")
    budget = st.text_input("Requested amount and currency")
    instructions = st.text_area("Exact donor headings, evaluation criteria, word limits and instructions")
    ai_proposal_optin = st.checkbox("If an AI API key is configured, I consent to sending these proposal inputs to that provider for drafting. Do not include sensitive beneficiary data.")
    if st.button("Generate structured drafting brief", type="primary"):
        source = st.session_state.get("source_text", "[No opportunity document uploaded in this session]")
        brief = f"""HUMANITY HORIZONS — {dtype.upper()} DRAFTING BRIEF\n\nTitle: {title or '[INPUT REQUIRED]'}\nApplicant: {applicant or '[INPUT REQUIRED]'}\nFunder/programme: {donor or '[INPUT REQUIRED]'}\nBudget: {budget or '[Confirm if applicable]'}\n\nPROBLEM / MOTIVATION\n{problem or '[NEEDS APPLICANT INPUT]'}\n\nOBJECTIVES / EXPECTED RESULTS\n{objective or '[NEEDS APPLICANT INPUT]'}\n\nAPPROACH / ACTIVITIES\n{approach or '[NEEDS APPLICANT INPUT]'}\n\nVERIFIED EVIDENCE\n{evidence or '[NEEDS VERIFIED EVIDENCE]'}\n\nDONOR INSTRUCTIONS\n{instructions or '[Paste exact official instructions]'}\n\nSOURCE EXTRACT FOR HUMAN REVIEW\n{source[:12000]}\n\nDRAFTING CONTROLS\n- Do not invent statistics, experience, partners, credentials, citations or commitments.\n- Mark missing facts [NEEDS APPLICANT INPUT].\n- Mirror mandatory donor headings and evaluation criteria from the original call.\n- Align problem -> objectives -> activities -> outputs -> outcomes -> indicators -> budget.\n- Consider safeguarding, inclusion, gender, disability, climate/environmental risks and data protection where relevant.\n- Obtain technical, finance and authorized management review before submission.\n"""
        if ai_proposal_optin and OPENAI_API_KEY:
            ai_prompt = f"""Prepare a grant/fellowship proposal working draft, not a final submission. Use only provided facts; do not invent statistics, track record, partners, beneficiaries, citations, budgets or commitments. Clearly mark missing elements [NEEDS APPLICANT INPUT]. Preserve the donor instructions and explain assumptions/risks. Document type: {dtype}. Title: {title}. Applicant: {applicant}. Donor: {donor}. Budget: {budget}. Problem: {problem}. Objectives: {objective}. Approach: {approach}. Verified evidence: {evidence}. Official instructions: {instructions}. Extract from uploaded source: {source[:10000]}. Structure around context/problem, rationale, target groups, theory of change, outcomes/outputs/activities, indicators, implementation, safeguarding/inclusion, risks, budget narrative, sustainability and M&E as appropriate. Output an editable draft with evidence gaps explicitly flagged."""
            ai_brief = run_optional_ai(ai_prompt)
            if ai_brief:
                brief = ai_brief
                st.session_state["proposal_ai_used"] = True
            else:
                st.session_state["proposal_ai_used"] = False
        else:
            st.session_state["proposal_ai_used"] = False
        st.session_state["proposal_draft"] = brief
    if st.session_state.get("proposal_draft"):
        st.caption("Connected AI draft" if st.session_state.get("proposal_ai_used") else "Structured local draft — connect an API key and opt in for generative drafting")
        st.text_area("Editable proposal brief", st.session_state["proposal_draft"], height=420)
        download_gate("proposal brief", st.session_state["proposal_draft"], "humanity_horizons_proposal_brief.txt", key="proposal_brief")

# -----------------------------------------------------------------------------
# CV / Resume Studio
# -----------------------------------------------------------------------------
elif page == "CV / Resume Studio":
    st.header("CV / Resume Studio — future-skills aware")
    st.write("Build an ATS-readable CV/resume and skills development plan from your own verified experience. This is a structured drafting tool, not a connected AI model or a guarantee of employment.")
    st.caption("The Humanity Horizons Future Workforce Readiness Matrix helps users assess and build practical skills in AI/data literacy, cybersecurity, technology, creative thinking, adaptability, lifelong learning, leadership, analytical thinking and environmental stewardship. These are development prompts, not a guarantee of employment.")
    with st.form("cv_form"):
        cv_name = st.text_input("Full name", value=USER_NAME)
        target_role = st.text_input("Target role / vacancy title")
        cv_email = st.text_input("Professional email")
        cv_location = st.text_input("City / country")
        cv_link = st.text_input("LinkedIn / portfolio URL (optional)")
        profile = st.text_area("Professional profile / career objective", height=90)
        experience = st.text_area("Experience: role, employer, dates, achievements and metrics", height=150)
        education = st.text_area("Education and training", height=100)
        skills_text = st.text_area("Current skills (comma-separated)", placeholder="Project management, Excel, MEAL, facilitation")
        certifications = st.text_area("Certifications, awards and licences")
        projects = st.text_area("Selected projects, portfolio, volunteer work and verifiable outcomes")
        languages = st.text_input("Languages and proficiency")
        ai_cv_optin = st.checkbox("If an AI API key is configured, I consent to sending these CV inputs to that provider for drafting. I have removed unnecessary sensitive data.")
        cv_submit = st.form_submit_button("Build CV and skills plan", type="primary")
    if cv_submit:
        current = {x.strip().lower() for x in re.split(r"[,;\n]", skills_text) if x.strip()}
        skill_lines = "\n".join(f"- {x}" for x in FUTURE_SKILLS)
        missing = [x for x in FUTURE_SKILLS if x.lower() not in current and not any(w in x.lower() for w in current)]
        cv_text = f"""{cv_name or '[FULL NAME]'}\n{cv_location} | {cv_email} | {cv_link}\n\nPROFESSIONAL PROFILE\n{profile or '[Write a concise, evidence-based 3–4 line summary targeted to the vacancy.]'}\n\nTARGET ROLE\n{target_role or '[Target position]'}\n\nCORE SKILLS\n{skills_text or '[List only skills you can demonstrate.]'}\n\nPROFESSIONAL EXPERIENCE\n{experience or '[Add role, employer, dates, responsibilities and quantified, verified achievements.]'}\n\nEDUCATION AND TRAINING\n{education or '[Qualification, institution, location, completion year]'}\n\nSELECTED PROJECTS AND ACHIEVEMENTS\n{projects or '[Describe your role, contribution, deliverable and evidence of results.]'}\n\nCERTIFICATIONS AND LICENCES\n{certifications or '[List current, verifiable credentials.]'}\n\nLANGUAGES\n{languages or '[Language and proficiency]'}\n\nSKILLS TO CONSIDER DEVELOPING (NOT A CLAIM OF CURRENT PROFICIENCY)\n{skill_lines}\n\nQUALITY CHECK\n- Tailor keywords and evidence to the exact vacancy; do not invent credentials or metrics.\n- Prefer clear headings, reverse chronology and concise accomplishment bullets.\n- Quantify results only when you can verify the source.\n- Remove date of birth, national ID, marital status and other sensitive details unless a legitimate, lawful application requirement specifically calls for them.\n- Check grammar, accessibility, references and local hiring norms before sending.\n"""
        if ai_cv_optin and OPENAI_API_KEY:
            ai_prompt = f"""You are a careful CV editor. Draft an ATS-readable CV and a concise, role-specific skills development plan using only the candidate-provided facts. Never invent employers, dates, degrees, certificates, metrics or skills. Mark gaps as [CANDIDATE TO VERIFY]. Do not infer protected characteristics. Target role: {target_role}. Name/contact/location: {cv_name}; {cv_email}; {cv_location}; {cv_link}. Profile: {profile}. Experience: {experience}. Education: {education}. Skills: {skills_text}. Certifications: {certifications}. Projects: {projects}. Languages: {languages}. Relevant skill areas to consider (do not claim these are held unless stated): {', '.join(FUTURE_SKILLS)}.
Return a polished CV with standard headings, then a separate 'Skills development plan' with priorities and practical evidence-building exercises. Keep all claims grounded in the input."""
            ai_result = run_optional_ai(ai_prompt)
            if ai_result:
                cv_text = ai_result
                st.session_state["cv_ai_used"] = True
            else:
                st.session_state["cv_ai_used"] = False
        else:
            st.session_state["cv_ai_used"] = False
        st.session_state["cv_text"] = cv_text
        st.session_state["cv_gaps"] = missing
    if st.session_state.get("cv_text"):
        st.subheader("Draft CV / Resume")
        st.caption("Connected AI draft" if st.session_state.get("cv_ai_used") else "Structured local draft — connect an API key and opt in for generative drafting")
        st.text_area("Editable CV content", st.session_state["cv_text"], height=500)
        download_gate("CV / resume", st.session_state["cv_text"], "humanity_horizons_cv_resume.txt", key="cv_resume")
        st.subheader("Future-skills development checklist")
        st.write("Consider these skill areas in light of the role you want. The list is a development prompt, not an employer-specific prediction.")
        for skill in FUTURE_SKILLS:
            st.checkbox(skill, key=f"cvskill_{re.sub('[^a-z0-9]+','_',skill.lower())}")
        gaps = st.session_state.get("cv_gaps", [])
        if gaps:
            st.markdown("**Skills to evidence or consider developing**")
            st.write(", ".join(gaps))
        st.info("Skill gap matching is based on the text you typed and is approximate. A missing keyword does not necessarily mean you lack the skill. Use the Humanity Horizons Future Workforce Readiness Matrix as a development guide, then validate the role-specific requirements in the actual vacancy.")

# -----------------------------------------------------------------------------
# SDG Navigator
# -----------------------------------------------------------------------------
elif page == "SDG Navigator":
    st.header("Sustainable Development Goals navigator")
    st.write("Explore all 17 Sustainable Development Goals and five representative problem areas each goal helps address. Humanity Horizons uses this goal map as a planning taxonomy. The problem areas are issue prompts, not exhaustive target lists or a claim that one goal alone solves them.")
    choice = st.selectbox("Choose an SDG", SDGS, format_func=lambda x: f"SDG {x[0]} — {x[1]}")
    num, name, official, problems = choice
    st.subheader(f"SDG {num}: {name}")
    st.write(official)
    for i, item in enumerate(problems, 1):
        st.markdown(f"**Problem area {i}.** {item}")
    st.markdown("**Project design prompts**")
    with st.form("sdg_project_form"):
        sdg_project = st.text_input("Project / intervention name")
        sdg_population = st.text_input("Who is affected? (disaggregate appropriately)")
        sdg_baseline = st.text_area("What evidence describes the problem and baseline?")
        sdg_change = st.text_area("What change should this intervention contribute to?")
        sdg_indicator = st.text_input("Proposed indicator and target")
        sdg_submit = st.form_submit_button("Create SDG alignment brief")
    if sdg_submit:
        alignment = f"SDG {num} — {name}\nGoal statement: {official}\nProject: {sdg_project}\nPopulation: {sdg_population}\nProblem evidence/baseline: {sdg_baseline}\nIntended contribution: {sdg_change}\nProposed indicator/target: {sdg_indicator}\n\nValidate the goal/target alignment against the official SDG targets and relevant national indicators. Do not claim attribution without an appropriate evaluation design."
        st.text_area("SDG alignment brief", alignment, height=240)
        download_gate("SDG alignment brief", alignment, f"sdg_{num}_alignment.txt", key=f"sdg_{num}_brief")
    with st.expander("View all 17 goals and problem areas"):
        for n, nm, statement, items in SDGS:
            st.markdown(f"**SDG {n} — {nm}.** {statement}")
            st.write(" · ".join(items))
    download_data = pd.DataFrame([{"SDG": n, "Name": nm, "Official statement": s, "Problem area 1": p[0], "Problem area 2": p[1], "Problem area 3": p[2], "Problem area 4": p[3], "Problem area 5": p[4]} for n, nm, s, p in SDGS])
    download_gate("SDG navigator library", download_data.to_csv(index=False), "humanity_horizons_sdg_problem_library.csv", "text/csv", "sdg_library")
    st.caption("Humanity Horizons SDG Navigator — maintained as part of the Humanity Horizons planning framework.")

# -----------------------------------------------------------------------------
# Noticeboard: member-submitted/imported listing queue; admin moderation required
# -----------------------------------------------------------------------------
elif page == "Noticeboard":
    st.header("Humanity Horizons noticeboard")
    st.caption("Publish opportunities, events and clearly labelled sponsored adverts. Imported listings must retain the original source URL and be checked for expiration, licensing and accuracy.")
    published = db_all("SELECT * FROM noticeboard WHERE status=? ORDER BY created_at DESC", ("Published",))
    st.subheader("Published opportunities and adverts")
    filters = st.multiselect("Filter listing types", sorted({r["opportunity_type"] for r in published}), default=sorted({r["opportunity_type"] for r in published}))
    items = [r for r in published if r["opportunity_type"] in filters]
    if not items:
        st.info("No approved listings match the filter yet.")
    for item in items:
        with st.container(border=True):
            st.markdown(f"**{item['title']}** · {item['opportunity_type']}")
            st.caption(f"{item.get('organization') or 'Publisher not stated'} | {item.get('country') or 'Location not stated'} | Deadline: {item.get('deadline') or 'See source'}")
            st.write(item["description"])
            if item.get("link") and safe_url(item["link"]): st.markdown(f"[Open opportunity / advert]({item['link']})")
            if item.get("source_url"): st.caption(f"Original source: {item['source_url']}")
    st.divider()
    st.subheader("Submit a listing for moderation")
    with st.form("listing_form"):
        board_title = st.text_input("Opportunity / advert title")
        board_org = st.text_input("Publisher / organization")
        board_type = st.selectbox("Type", ["Grant", "Job", "Fellowship", "Consultancy", "Tender", "Event", "Partnership", "Learning resource", "Sponsored advert"])
        board_country = st.text_input("Country / region")
        board_deadline = st.text_input("Deadline (as shown by original source)")
        board_link = st.text_input("Application / destination URL (https:// or http://)")
        board_source = st.text_input("Original source URL (for imported adverts and opportunities)")
        board_description = st.text_area("Description, requirements, costs and important caveats")
        rights_list = st.checkbox("I am authorized to submit this listing, have kept the source attribution and have labelled sponsored content honestly.")
        submit_listing = st.form_submit_button("Submit for review")
    if submit_listing:
        errors = []
        if not board_title.strip(): errors.append("Title is required.")
        if not board_description.strip(): errors.append("Description is required.")
        if not safe_url(board_link) or not safe_url(board_source): errors.append("URLs must start with http:// or https://.")
        if not rights_list: errors.append("Confirm listing rights and transparent attribution.")
        if errors:
            for err in errors: st.error(err)
        else:
            db_exec("INSERT INTO noticeboard (id,title,organization,opportunity_type,country,deadline,link,description,source_url,status,created_by,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), board_title.strip(), board_org.strip(), board_type, board_country.strip(), board_deadline.strip(), board_link.strip(), board_description.strip(), board_source.strip(), "Pending review", USER_EMAIL, now_iso()))
            record_event(USER_EMAIL, "noticeboard_listing_submitted")
            st.success("Listing submitted for moderation. It will not appear publicly until approved by an administrator.")
    st.subheader("Import listings from a CSV for review")
    st.write("Use columns: title, organization, opportunity_type, country, deadline, link, description, source_url. Importing creates pending listings; it does not scrape external sites automatically.")
    import_gate = upload_rights_gate("ad_import", "noticeboard CSV")
    import_file = st.file_uploader("Upload listing CSV", type=["csv"], key="notice_import_csv")
    if import_file:
        if not import_gate:
            st.warning("Complete the B2B purpose and rights confirmation before importing.")
        else:
            try:
                im_df = pd.read_csv(import_file).fillna("")
                st.dataframe(im_df.head(50), use_container_width=True)
                if st.button("Import these listings into moderation queue"):
                    required = {"title", "description"}
                    if not required.issubset(set(im_df.columns)):
                        st.error("CSV must include at least title and description columns.")
                    else:
                        for _, rr in im_df.iterrows():
                            title_val = str(rr.get("title", "")).strip()
                            desc_val = str(rr.get("description", "")).strip()
                            link_val = str(rr.get("link", "")).strip()
                            source_val = str(rr.get("source_url", "")).strip()
                            if title_val and desc_val and safe_url(link_val) and safe_url(source_val):
                                db_exec("INSERT INTO noticeboard (id,title,organization,opportunity_type,country,deadline,link,description,source_url,status,created_by,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                        (str(uuid.uuid4()), title_val, str(rr.get("organization", "")), str(rr.get("opportunity_type", "Grant")) or "Grant", str(rr.get("country", "")), str(rr.get("deadline", "")), link_val, desc_val, source_val, "Pending review", USER_EMAIL, now_iso()))
                        record_event(USER_EMAIL, "noticeboard_csv_import", st.session_state.get("upload_purpose_value_ad_import", ""))
                        st.success("Eligible rows added to the moderation queue. Check every listing before publishing."); st.rerun()
            except Exception as e:
                st.error(f"Unable to read CSV: {e}")

# -----------------------------------------------------------------------------
# MEAL & donor-readiness self-assessment
# -----------------------------------------------------------------------------
elif page == "HH Standards & Impact":
    st.header("Humanity Horizons Standards & Impact Workspace")
    tabs = st.tabs(["Results framework", "Indicator data", "Risk register", "Funding readiness", "M&E report"])
    with tabs[0]:
        st.caption("Create an aligned result chain. Add indicators with definition, baseline, target, source, disaggregation and frequency.")
        nrows = st.number_input("Number of result rows", min_value=1, max_value=20, value=5, key="lf_rows")
        lrows = []
        for i in range(int(nrows)):
            with st.expander(f"Result row {i+1}", expanded=(i == 0)):
                level = st.selectbox("Level", ["Impact", "Outcome", "Output", "Activity"], key=f"lf_level_{i}")
                res = st.text_input("Result statement", key=f"lf_result_{i}")
                ind = st.text_input("Indicator", key=f"lf_ind_{i}")
                definition = st.text_input("Indicator definition / unit", key=f"lf_def_{i}")
                baseline = st.text_input("Baseline", key=f"lf_base_{i}")
                target = st.text_input("Target", key=f"lf_target_{i}")
                source = st.text_input("Means / source of verification", key=f"lf_source_{i}")
                freq = st.selectbox("Frequency", ["Monthly", "Quarterly", "Semi-annual", "Annual", "Endline"], key=f"lf_freq_{i}")
                owner = st.text_input("Responsible role", key=f"lf_owner_{i}")
                lrows.append({"Level": level, "Result": res, "Indicator": ind, "Definition / unit": definition, "Baseline": baseline, "Target": target, "Source": source, "Frequency": freq, "Responsible": owner})
        ldf = pd.DataFrame(lrows)
        st.dataframe(ldf, use_container_width=True, hide_index=True)
        download_gate("results framework CSV", ldf.to_csv(index=False), "humanity_horizons_results_framework.csv", "text/csv", "logframe")
    with tabs[1]:
        datafile = st.file_uploader("Upload monitoring dataset CSV/XLSX", type=["csv", "xlsx"], key="meal_dataset")
        gate = upload_rights_gate("meal_data", "monitoring dataset")
        if datafile:
            if gate:
                try:
                    ddf = pd.read_csv(datafile) if datafile.name.lower().endswith(".csv") else pd.read_excel(datafile)
                    st.session_state["monitoring_df"] = ddf
                    st.dataframe(ddf, use_container_width=True)
                    record_event(USER_EMAIL, f"upload:{datafile.name}", st.session_state.get("upload_purpose_value_meal_data", ""))
                except Exception as e: st.error(f"Cannot read monitoring data: {e}")
            else: st.warning("Confirm purpose and upload rights before processing.")
        st.markdown("**Quick indicator record**")
        ci1, ci2, ci3 = st.columns(3)
        with ci1: qi = st.text_input("Indicator name", key="quick_ind")
        with ci2: qt = st.number_input("Target", min_value=0.0, value=100.0, key="quick_targ")
        with ci3: qa = st.number_input("Achieved", min_value=0.0, value=0.0, key="quick_ach")
        qp = st.text_input("Reporting period", value=str(date.today().year), key="quick_period")
        qd = st.text_input("Disaggregation / population group", key="quick_disagg")
        qnote = st.text_area("Interpretation and limitations", key="quick_note")
        if st.button("Save quick indicator record"):
            recs = st.session_state.get("quick_records", [])
            recs.append({"Indicator": qi, "Period": qp, "Target": qt, "Achieved": qa, "Progress %": round(qa/qt*100, 1) if qt else None, "Disaggregation": qd, "Notes": qnote})
            st.session_state["quick_records"] = recs
            st.success("Added to this session. Export to save a copy.")
        qdf = pd.DataFrame(st.session_state.get("quick_records", []))
        if not qdf.empty:
            st.dataframe(qdf, use_container_width=True)
            download_gate("indicator records CSV", qdf.to_csv(index=False), "humanity_horizons_indicator_records.csv", "text/csv", "indicator_records")
    with tabs[2]:
        risk_count = st.number_input("Number of risks", min_value=1, max_value=15, value=4, key="risk_count")
        rrows = []
        for i in range(int(risk_count)):
            with st.expander(f"Risk {i+1}", expanded=(i == 0)):
                risk = st.text_input("Risk / issue", key=f"risk_name_{i}")
                likelihood = st.selectbox("Likelihood", ["Low", "Medium", "High"], key=f"risk_l_{i}")
                impact = st.selectbox("Impact", ["Low", "Medium", "High"], key=f"risk_i_{i}")
                mitigation = st.text_area("Mitigation / response", key=f"risk_m_{i}")
                owner = st.text_input("Risk owner", key=f"risk_o_{i}")
                status = st.selectbox("Status", ["Open", "Monitoring", "Mitigated", "Escalated", "Closed"], key=f"risk_s_{i}")
                rrows.append({"Risk": risk, "Likelihood": likelihood, "Impact": impact, "Mitigation": mitigation, "Owner": owner, "Status": status})
        risk_df = pd.DataFrame(rrows)
        st.dataframe(risk_df, use_container_width=True, hide_index=True)
        download_gate("risk register CSV", risk_df.to_csv(index=False), "humanity_horizons_risk_register.csv", "text/csv", "risk_export")
    with tabs[3]:
        st.markdown("**Humanity Horizons Institutional Readiness & Impact Framework (HH-IRIF)**\n\nThis proprietary self-assessment organizes practical controls for governance, eligibility, results management, evaluation and learning, financial stewardship, procurement, safeguarding, fraud prevention, data protection, inclusion, environmental/social risk, feedback, partner management, records and sustainability. It is a planning and evidence-checking tool—not a legal opinion, external certification or guarantee. Use the requirements in the specific opportunity, contract and applicable law as the final checklist.")
        checked = []
        for i, (heading, desc) in enumerate(HH_STANDARDS_CHECKS):
            with st.expander(heading):
                st.write(desc)
                checked.append(st.checkbox("Evidence is documented and current", key=f"donor_check_{i}"))
        total = len(HH_STANDARDS_CHECKS); count = sum(checked)
        st.progress(count / total)
        st.metric("Control themes with evidence attested", f"{count}/{total}", f"{count/total:.0%}")
        if count != total: st.warning("Open items remain. A completed checklist is a self-attestation, not independent verification.")
        else: st.success("All control themes marked complete. An independent review is still recommended.")
        st.markdown("**Framework owner:** Humanity Horizons.\n\n**Review areas:** results chain and indicators; learning and data quality; financial controls; procurement and conflicts of interest; safeguarding and safe complaints handling; prevention of exploitation and abuse; privacy and confidentiality; inclusion and accessibility; environmental and social risk; partner oversight; records, accountability and sustainability. Administrators should review and version this framework periodically against current institutional good practice and the exact requirements contained in each opportunity or agreement.")
    with tabs[4]:
        org = st.text_input("Organization", key="report_org")
        project = st.text_input("Project", key="report_project")
        donor = st.text_input("Donor / reporting recipient", key="report_donor")
        reporting_period = st.text_input("Reporting period", value="Quarterly", key="report_period")
        summary = st.text_area("Executive summary", key="report_summary")
        achievements = st.text_area("Evidence-supported achievements", key="report_achieve")
        challenges = st.text_area("Challenges / deviations", key="report_challenges")
        actions = st.text_area("Corrective actions and lessons", key="report_actions")
        nextsteps = st.text_area("Next period priorities", key="report_next")
        quick = pd.DataFrame(st.session_state.get("quick_records", []))
        dataset = st.session_state.get("monitoring_df", pd.DataFrame())
        if st.button("Generate M&E report draft", type="primary"):
            if not quick.empty:
                metrics = quick.to_dict(orient="records")
            elif not dataset.empty:
                metrics = dataset.head(100).to_dict(orient="records")
            else: metrics = []
            metric_lines = []
            for row in metrics:
                if "Indicator" in row and "Target" in row and "Achieved" in row:
                    try: pct = f"{float(row.get('Achieved'))/float(row.get('Target'))*100:.1f}%" if float(row.get("Target")) else "Target zero/not set"
                    except Exception: pct = "Progress not calculable"
                    metric_lines.append(f"- {row.get('Indicator','Unnamed indicator')}: target {row.get('Target')}; achieved {row.get('Achieved')}; progress {pct}; notes {row.get('Notes','')}")
                else: metric_lines.append("- Data row: " + ", ".join(f"{k}={v}" for k,v in row.items()))
            report = f"""HUMANITY HORIZONS — M&E REPORT (DRAFT)\nOrganization: {org}\nProject: {project}\nDonor: {donor}\nPeriod: {reporting_period}\nGenerated: {date.today().isoformat()}\n\n1. SUMMARY\n{summary or '[Add evidence-based summary]'}\n\n2. INDICATOR PERFORMANCE\n{chr(10).join(metric_lines) or '[No indicator data supplied — insert verified results]'}\n\n3. ACHIEVEMENTS\n{achievements or '[Add verified achievements and source references]'}\n\n4. CHALLENGES AND DEVIATIONS\n{challenges or '[Explain shortfalls, causes and adaptive action]'}\n\n5. CORRECTIVE ACTIONS AND LESSONS\n{actions or '[Action, owner and due date]'}\n\n6. NEXT PERIOD PRIORITIES\n{nextsteps or '[Planned activities and milestones]'}\n\n7. DATA QUALITY, SAFEGUARDING AND LIMITATIONS\nVerify source records, calculations, denominators and disaggregation. Document gaps and revisions. Do not place identifiable safeguarding reports in a general donor narrative; use authorized confidential channels.\n\nDRAFT ONLY: Human review required. The software does not independently verify supplied inputs.\n"""
            st.session_state["report_text"] = report
        if st.session_state.get("report_text"):
            st.text_area("M&E report draft", st.session_state["report_text"], height=420)
            download_gate("M&E report", st.session_state["report_text"], "humanity_horizons_me_report.txt", key="me_report")

# -----------------------------------------------------------------------------
# Donor feedback / accountability
# -----------------------------------------------------------------------------
elif page == "Donor Feedback":
    st.header("Donor and stakeholder feedback")
    st.write("Record service feedback, donor comments and improvement requests. Do not submit identifiable sensitive safeguarding allegations through this general form; use the relevant confidential reporting channel.")
    with st.form("feedback_form"):
        category = st.selectbox("Feedback type", ["Service quality", "Donor / partner feedback", "Project implementation", "Accessibility / inclusion", "Complaint", "Suggestion", "Other"])
        org = st.text_input("Organization (optional)")
        rating = st.slider("Overall experience", 1, 5, 4, help="1 = very poor, 5 = excellent")
        anonymous = st.checkbox("Submit this feedback anonymously (your account email will not be attached to this feedback item)")
        message = st.text_area("Feedback / complaint / suggestion")
        reply = st.checkbox("I consent to follow-up about this feedback. Optional.")
        feedback_submit = st.form_submit_button("Submit feedback", type="primary")
    if feedback_submit:
        if len(message.strip()) < 10:
            st.error("Please provide at least 10 characters so the issue can be understood.")
        else:
            db_exec("INSERT INTO feedback (id,user_email,organization,category,rating,message,anonymous,followup_optin,status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), None if anonymous else USER_EMAIL, org.strip(), category, int(rating), message.strip(), int(anonymous), int(reply and not anonymous), "Received", now_iso()))
            record_event(USER_EMAIL, "donor_feedback_submitted")
            st.success("Feedback received. Administrators can review it and record follow-up actions.")
    st.info("For urgent risk or safeguarding matters, use the organisation's designated confidential reporting procedure. This general feedback form is not a substitute for a formal independent mechanism.")

# -----------------------------------------------------------------------------
# B2B collaboration and sustainability
# -----------------------------------------------------------------------------
elif page == "B2B Collaboration":
    st.header("B2B collaboration and platform sustainability")
    st.write("Connect NGOs, funders, researchers, service providers and businesses around measurable development outcomes.")
    st.markdown("**Transparent approach:** This release does not charge hidden access fees, sell visitor data or pay users for downloads. Sponsored content must be labelled and reviewed. A real revenue programme requires written sponsor/advertiser agreements, tax/accounting review and a tested payment provider.")
    with st.form("b2b_form"):
        kind = st.selectbox("Collaboration type", ["Institutional partnership", "Corporate sponsorship", "Sponsored noticeboard placement", "Research / data collaboration", "Service provider offer", "NGO-to-NGO collaboration", "Training / CV support", "Other"])
        org = st.text_input("Organization / business")
        sector = st.text_input("Sector / capability")
        offer = st.text_area("What can you offer or what do you need?")
        outcome = st.text_area("Intended development outcome / social value")
        contact_ok = st.checkbox("I consent to being contacted about this collaboration request.")
        b2b_submit = st.form_submit_button("Submit collaboration request")
    if b2b_submit:
        if len(offer.strip()) < 10:
            st.error("Please describe the offer or need in at least 10 characters.")
        elif not contact_ok:
            st.error("Confirm consent to contact you about this specific request.")
        else:
            db_exec("INSERT INTO feedback (id,user_email,organization,category,rating,message,anonymous,followup_optin,status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), USER_EMAIL, org.strip(), "B2B collaboration: " + kind, None, f"Capability/need: {offer}\nIntended outcome: {outcome}\nSector: {sector}", 0, 1, "Collaboration request", now_iso()))
            record_event(USER_EMAIL, "b2b_collaboration_request")
            st.success("Request saved for review. This prototype does not automatically sell placements or settle revenue.")
    st.subheader("B2B engagement ideas")
    st.markdown("- Clearly labelled sponsored opportunity placements.\n- Paid training or institutional workshops with written terms.\n- Ethical business services for NGOs (translation, design, evaluation, data tools).\n- Approved downloadable templates with transparent licensing.\n- Research partnerships with data minimization and consent.")

# -----------------------------------------------------------------------------
# Privacy and user data
# -----------------------------------------------------------------------------
elif page == "Privacy and Data":
    st.header("Privacy, consent and data controls")
    me = db_all("SELECT * FROM users WHERE email=?", (USER_EMAIL,))[0]
    st.subheader("Your profile")
    st.write(f"**Name:** {me['full_name']}  \n**Account type:** {me['account_type']}  \n**Organization:** {me.get('organization') or 'Not provided'}  \n**Sector:** {me.get('sector') or 'Not provided'}  \n**B2B purpose:** {me.get('b2b_purpose')}")
    desired = st.checkbox("I opt in to follow-up emails and identifiable attendance records", value=bool(me.get("followup_optin", 0)), key="privacy_followup")
    if st.button("Save follow-up preference"):
        db_exec("UPDATE users SET followup_optin=? WHERE email=?", (int(desired), USER_EMAIL))
        st.session_state.followup_optin = desired
        record_event(USER_EMAIL, "followup_consent_changed", "opt_in" if desired else "opt_out")
        st.success("Preference updated.")
    st.subheader("What this prototype stores")
    st.markdown("- Account email, display name, password hash and B2B profile. The original password is not stored.\n- Your tasks and their status changes.\n- Opportunity uploads are processed by the running app; extracted content may remain in your current session, not a private long-term document vault.\n- Action audit events needed to record authenticated uploads/downloads and their declared purposes.\n- Anonymous session counts without IP addresses or device fingerprinting. Identifiable attendance is added only when you opt in.\n- Feedback and B2B requests you submit.\n- Noticeboard listings and their source links.")
    st.warning("For production, configure a managed database, TLS, secrets management, backups, role-based access, deletion/export workflows, a retention schedule, breach response, email verification, password reset, rate limiting and an approved privacy notice. Have counsel/local data-protection professionals review applicable Ugandan law and any other jurisdictions served.")
    st.markdown("Review applicable local data-protection, cybersecurity, employment, safeguarding, financial and records-retention laws with qualified advisers in each jurisdiction where Humanity Horizons operates.")
    my_tasks = db_all("SELECT * FROM tasks WHERE user_email=? ORDER BY created_at", (USER_EMAIL,))
    mydf = pd.DataFrame([{ "Title": t["title"], "Description": t["description"], "Status": t["status"], "Priority": t["priority"], "Due": t["due_date"], "Created": t["created_at"] } for t in my_tasks])
    download_gate("my data export", mydf.to_csv(index=False), "my_humanity_horizons_tasks.csv", "text/csv", "my_data_export")

# -----------------------------------------------------------------------------
# Administrator console: moderated postings, feedback, attendance, treasury ledger
# -----------------------------------------------------------------------------
elif page == "Admin Console" and IS_ADMIN:
    st.header("Administrator console")
    st.warning("Restricted administration. Keep ADMIN_EMAILS and any database credentials in Streamlit secrets, never in GitHub code. Restrict admin access to authorized personnel and enable MFA on provider accounts.")
    admin_tabs = st.tabs(["Noticeboard moderation", "Feedback review", "Attendance / task operations", "Treasury ledger"])
    with admin_tabs[0]:
        pending = db_all("SELECT * FROM noticeboard WHERE status=? ORDER BY created_at", ("Pending review",))
        st.subheader(f"Pending listings: {len(pending)}")
        if not pending: st.info("No listings awaiting review.")
        for item in pending:
            with st.container(border=True):
                st.markdown(f"**{item['title']}** · {item['opportunity_type']}")
                st.write(item["description"])
                st.caption(f"Submitted by {item.get('created_by')} | source {item.get('source_url') or 'not supplied'}")
                c1, c2 = st.columns(2)
                if c1.button("Publish", key=f"publish_{item['id']}"):
                    db_exec("UPDATE noticeboard SET status=? WHERE id=?", ("Published", item["id"]))
                    record_event(USER_EMAIL, "noticeboard_listing_published")
                    st.rerun()
                if c2.button("Reject", key=f"reject_{item['id']}"):
                    db_exec("UPDATE noticeboard SET status=? WHERE id=?", ("Rejected", item["id"]))
                    st.rerun()
        st.subheader("Published or rejected listings")
        st.dataframe(pd.DataFrame(db_all("SELECT title,opportunity_type,organization,status,deadline,source_url,created_at FROM noticeboard ORDER BY created_at DESC")), use_container_width=True, hide_index=True)
    with admin_tabs[1]:
        fb = db_all("SELECT * FROM feedback ORDER BY created_at DESC")
        st.write(f"Feedback and collaboration records: {len(fb)}")
        if fb:
            fdf = pd.DataFrame([{k: v for k, v in f.items() if k != "id"} for f in fb])
            st.dataframe(fdf, use_container_width=True, hide_index=True)
            download_gate("feedback export", fdf.to_csv(index=False), "humanity_horizons_feedback_admin.csv", "text/csv", "admin_feedback")
    with admin_tabs[2]:
        attendance = db_all("SELECT event_name,user_email,followup_optin,created_at,details FROM attendance ORDER BY created_at DESC LIMIT 1000")
        st.subheader("Attendance events (latest 1,000)")
        st.dataframe(pd.DataFrame(attendance), use_container_width=True, hide_index=True)
        st.caption("Anonymous session attendance has no visitor identity. Identifiable attendee emails are stored only for users who opted in to follow-up.")
        tasks_admin = db_all("SELECT user_email,title,status,priority,due_date,created_at,updated_at,completed_at FROM tasks ORDER BY updated_at DESC LIMIT 500")
        st.subheader("Task progress across users (latest 500)")
        st.dataframe(pd.DataFrame(tasks_admin), use_container_width=True, hide_index=True)
    with admin_tabs[3]:
        st.subheader("Treasury reference and verified ledger")
        st.write("This is an administrative finance area. It does not perform blockchain transactions or automate withdrawals. Treasury details are shown only to configured administrators in the app UI.")
        st.write(f"**Configured TRON treasury address:** `{TREASURY_ADDRESS or 'Not configured — set TRON_TREASURY_ADDRESS in Streamlit secrets'}`")
        st.write("**Network/asset intended:** TRON mainnet · USDT (TRC-20) / TRX. Do not enter private keys or seed phrases here.")
        st.info("Automatic withdrawals require a reviewed custody/signing model, key management, transaction simulation, address/network checks, limits, approvals, reconciliation, monitoring, tax/accounting controls and applicable legal review. No funds are moved by this prototype.")
        with st.form("ledger_form"):
            entry_type = st.selectbox("Entry type", ["Verified income received", "Verified expense", "Refund", "Adjustment"])
            amount = st.text_input("Amount (decimal as received; do not include a currency symbol)")
            currency = st.selectbox("Currency", ["UGX", "USD", "EUR", "USDT", "TRX", "Other"])
            source = st.text_input("Source / purpose / payer")
            tx_ref = st.text_input("Bank / blockchain transaction reference (optional)")
            notes = st.text_area("Reconciliation note / evidence reference")
            ledger_add = st.form_submit_button("Record verified ledger entry")
        if ledger_add:
            try:
                from decimal import Decimal, InvalidOperation
                amt = Decimal(amount.strip())
                if amt < 0: raise ValueError("Amount must be non-negative; use entry type for the direction.")
                if not source.strip(): raise ValueError("Source / purpose is required.")
                db_exec("INSERT INTO treasury_ledger (id,entry_type,amount,currency,source,reference,notes,entered_by,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                        (str(uuid.uuid4()), entry_type, str(amt), currency, source.strip(), tx_ref.strip(), notes.strip(), USER_EMAIL, now_iso()))
                record_event(USER_EMAIL, "treasury_ledger_entry_created")
                st.success("Ledger entry recorded (not a blockchain transaction).")
                st.rerun()
            except Exception as e:
                st.error(f"Ledger entry not saved: {e}")
        ledger = db_all("SELECT entry_type,amount,currency,source,reference,notes,entered_by,created_at FROM treasury_ledger ORDER BY created_at DESC")
        if ledger:
            led_df = pd.DataFrame(ledger)
            st.dataframe(led_df, use_container_width=True, hide_index=True)
            download_gate("treasury ledger export", led_df.to_csv(index=False), "humanity_horizons_treasury_ledger.csv", "text/csv", "treasury_ledger_export")
        else:
            st.info("No verified ledger entries recorded yet.")

# Unknown page guard
else:
    st.error("This administrator page is not available for the current account.")

st.divider()
st.caption("Humanity Horizons · People, Planet and Peace · Build 1.0. Humanity Horizons owns and maintains its proprietary standards and workforce-readiness framework. Verify source documents, application instructions, CV claims, indicators and legal requirements before relying on an output.")
