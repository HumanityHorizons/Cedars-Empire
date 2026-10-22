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
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from datetime import date, datetime, timezone, timedelta
from typing import Any

import pandas as pd
import streamlit as st
import pymupdf
from docx import Document
from hh_workspace_widgets import render_action_grid, render_calendar, render_document_exports
from hh_real_payments import (
    ensure_payment_tables, render_deposit_page, render_cashout_page,
    render_payment_ops_page, render_user_treasury_overview_page,
)
from hh_table_ui import render_bank_table, reset_table_counter, set_table_scope

# -----------------------------------------------------------------------------
# CEDARS EMPIRE — functional MVP / deployment-safe prototype
# Build marker retained for integration checks: Deposit & Packages QR integration (build 2026-10-21)
# -----------------------------------------------------------------------------
APP_DIR = Path(__file__).parent
LOGO = APP_DIR / "assets" / "humanity_horizons_logo.jpg"
if not LOGO.exists():
    LOGO = APP_DIR / "humanity_horizons_logo.jpg"
LOCAL_DB = Path(os.getenv("HH_DATA_DIR", tempfile.gettempdir())) / "humanity_horizons.db"
PBKDF2_ITERATIONS = 310_000

st.set_page_config(page_title="CEDARS EMPIRE", page_icon="🌍", layout="wide")
st.markdown("""
<style>
:root { color-scheme: light; }
.stApp, [data-testid="stAppViewContainer"] {
  background: linear-gradient(180deg,#f4fbff 0%,#ffffff 70%) !important;
  color: #172b4d !important;
}
/* Explicit high-contrast text so a dark Streamlit theme cannot turn text white on white. */
[data-testid="stMain"] h1, [data-testid="stMain"] h2,
[data-testid="stMain"] h3, [data-testid="stMain"] h4,
[data-testid="stMain"] p, [data-testid="stMain"] li,
[data-testid="stMain"] label,
[data-testid="stMain"] [data-testid="stMarkdownContainer"],
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p,
[data-testid="stMain"] [data-testid="stCaptionContainer"],
[data-testid="stMain"] [data-testid="stCaptionContainer"] p,
[data-testid="stMain"] [data-testid="stWidgetLabel"],
[data-testid="stMain"] [data-testid="stWidgetLabel"] p,
[data-testid="stMain"] [data-testid="stWidgetLabel"] label,
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] label, [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
  color: #172b4d !important;
}
[data-testid="stSidebar"] { background: #eaf8ff !important; }
input, textarea { color: #172b4d !important; background-color: #ffffff !important; }
[data-baseweb="select"] input { color: #172b4d !important; }
div.stButton > button { color: #172b4d !important; border-radius: 10px; }
div.stButton > button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"] {
  background: #078ee8 !important; color: #ffffff !important; border: 0 !important;
}
.hh-small { font-size: .88rem; color: #445569 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
:root { --ce-navy:#0A2540; --ce-blue:#0066CC; --ce-green:#00A86B; --ce-amber:#F59E0B; --ce-bg:#F8FAFC; --ce-card:#FFFFFF; --ce-border:#D8E1EB; --ce-text:#0A2540; --ce-muted:#526579; }
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background:var(--ce-bg) !important; color:var(--ce-text) !important; }
[data-testid="stMain"] h1,[data-testid="stMain"] h2,[data-testid="stMain"] h3,[data-testid="stMain"] h4 { color:var(--ce-navy) !important; }
[data-testid="stMain"] p,[data-testid="stMain"] li,[data-testid="stMain"] label,[data-testid="stMain"] [data-testid="stMarkdownContainer"],[data-testid="stMain"] [data-testid="stCaptionContainer"] { color:var(--ce-text) !important; }
[data-testid="stSidebar"] { background:var(--ce-navy) !important; border-right:1px solid #183B5D !important; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,[data-testid="stSidebar"] p,[data-testid="stSidebar"] label,[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color:#FFFFFF !important; }
[data-testid="stMetric"] { background:var(--ce-card) !important; border:1px solid var(--ce-border) !important; border-radius:12px !important; padding:12px 14px !important; box-shadow:0 2px 7px rgba(10,37,64,.045) !important; }
[data-testid="stDataFrame"],[data-testid="stForm"] { border:1px solid var(--ce-border) !important; border-radius:10px !important; background:var(--ce-card) !important; }
[data-testid="stForm"] { padding:.75rem .9rem !important; }
div.stButton > button,[data-testid="stDownloadButton"] button,[data-testid="stFormSubmitButton"] button { min-height:2.4rem; border-radius:8px !important; font-weight:650 !important; }
div.stButton > button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"] { background:var(--ce-blue) !important; color:white !important; border-color:var(--ce-blue) !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color:var(--ce-blue) !important; border-bottom-color:var(--ce-blue) !important; }
@media (max-width:768px) { [data-testid="stMainBlockContainer"] { padding:.8rem !important; } [data-testid="stForm"] { padding:.65rem !important; } }
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
.ce-fixed-header {
 position:fixed; top:0; left:0; right:0; z-index:999999;
 display:flex; align-items:center; gap:18px; min-height:66px;
 padding:10px 26px; background:#0A2540; color:#fff;
 border-bottom:3px solid #D6A84F; box-shadow:0 4px 16px rgba(10,37,64,.18);
 font-family:Arial,Helvetica,sans-serif;
}
.ce-brand-mark { width:38px; height:38px; border-radius:10px; display:flex; align-items:center;
 justify-content:center; background:#D6A84F; color:#0A2540; font-weight:900; font-size:21px; }
.ce-brand-title { font-size:19px; font-weight:800; letter-spacing:.7px; color:#fff; line-height:1.2; }
.ce-header-right { margin-left:auto; color:#E8F1F8; font-size:12px; text-align:right; }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display:none !important; }\n[data-testid="stMainBlockContainer"] { padding-top:6.2rem !important; }
.ce-menu-label { font-size:12px; font-weight:800; color:#526579; letter-spacing:.8px; text-transform:uppercase; }
@media(max-width:700px) {
 .ce-fixed-header { min-height:58px; padding:8px 12px; }
 .ce-brand-title { font-size:15px; }
 .ce-header-right { display:none; }
}
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
ADMIN_EMAILS = {e.strip().lower() for e in setting("ADMIN_EMAILS", "ogwal.bemmanuel@gmail.com").split(",") if e.strip()}
# Public TRON receiving address requested for the Cedars Empire treasury display.
# This is a public wallet address, NOT a private key. The app does not execute transfers.
TREASURY_ADDRESS = "TE26B7zQjMbahYAWcxEsSPC6aZEr2Hcz1u"
BNB_TREASURY_ADDRESS = "0x0d4c2B95e8FB7Be3DB9953bAcEf3A4Be643bA77B"
OPENAI_API_KEY = setting("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = setting("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"
TRONSCAN_API_KEY = setting("TRONSCAN_API_KEY", "").strip()
ETHERSCAN_API_KEY = setting("ETHERSCAN_API_KEY", "").strip()
SMTP_HOST = setting("SMTP_HOST", "").strip()
SMTP_PORT = int(setting("SMTP_PORT", "587") or "587")
SMTP_USERNAME = setting("SMTP_USERNAME", setting("SMTP_USER", "")).strip()
SMTP_PASSWORD = setting("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = setting("SMTP_FROM_EMAIL", setting("SMTP_FROM", SMTP_USERNAME)).strip()
SMTP_USE_TLS = setting("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def email_delivery_configured() -> bool:
    return bool(SMTP_HOST and SMTP_FROM_EMAIL and SMTP_PORT > 0)


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send email only with configured SMTP; never expose credentials or provider errors."""
    if not email_delivery_configured():
        return False
    message = EmailMessage()
    message["From"] = SMTP_FROM_EMAIL
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    try:
        context = ssl.create_default_context()
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15, context=context) as server:
                if SMTP_USERNAME:
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(message)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.ehlo()
                if SMTP_USE_TLS:
                    server.starttls(context=context)
                    server.ehlo()
                if SMTP_USERNAME:
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(message)
        return True
    except Exception:
        return False


def post_4060_allocation(db_connect_fn, *, source_ref: str, currency: str, gross_amount: str,
                         deductible_costs: str, evidence_ref: str, approved_by: str,
                         entered_by: str, notes: str = "") -> dict[str, str]:
    """Post a balanced, persistent 40/60 accounting allocation. Never sends funds."""
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
    if not source_ref.strip() or not evidence_ref.strip() or not approved_by.strip():
        raise ValueError("Receipt reference, evidence reference and approver email are required.")
    cur_code = currency.upper().strip()
    if cur_code not in {"USD", "UGX", "EUR", "GBP", "USDT", "USDC", "TRX", "BNB"}:
        raise ValueError("Unsupported currency code.")
    try:
        gross = Decimal(gross_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        costs = Decimal(deductible_costs).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Gross amount and deductible costs must be valid decimal numbers.")
    if not gross.is_finite() or not costs.is_finite() or gross <= 0 or costs < 0 or costs > gross:
        raise ValueError("Gross must be positive; costs must be zero or more and cannot exceed gross.")
    net = gross - costs
    if net <= 0:
        raise ValueError("Eligible net revenue must be greater than zero.")
    contributor = (net * Decimal("0.40")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sustainability = net - contributor
    if approved_by.strip().lower() not in ADMIN_EMAILS:
        raise ValueError("Approver must be an email listed in ADMIN_EMAILS.")
    if approved_by.strip().lower() == entered_by.strip().lower():
        raise ValueError("A second configured administrator must approve this allocation.")
    import uuid as _uuid
    allocation_id, timestamp = str(_uuid.uuid4()), now_iso()
    conn, kind = db_connect_fn()
    cur = conn.cursor()
    q = (lambda sql: sql.replace("?", "%s")) if kind == "postgres" else (lambda sql: sql)
    journal = [
        ("TREASURY_CLEARED", "DEBIT", gross),
        ("CUSTOMER_REVENUE", "CREDIT", gross),
    ]
    if costs:
        journal.extend([("DIRECT_COST_EXPENSE", "DEBIT", costs), ("TREASURY_CLEARED", "CREDIT", costs)])
    journal.extend([
        ("CONTRIBUTOR_POOL_LIABILITY", "CREDIT", contributor),
        ("SUSTAINABILITY_RESERVE", "CREDIT", sustainability),
        ("CUSTOMER_REVENUE", "DEBIT", net),
    ])
    debits = sum((amount for _,side,amount in journal if side=="DEBIT"), Decimal("0"))
    credits = sum((amount for _,side,amount in journal if side=="CREDIT"), Decimal("0"))
    if debits != credits:
        cur.close()
        conn.close()
        raise RuntimeError("Accounting journal is unbalanced; no allocation was posted.")
    try:
        cur.execute(q("INSERT INTO revenue_allocations (id,receipt_reference,gross_amount,deductible_costs,eligible_net,currency,user_pool_amount,sustainability_amount,status,evidence_ref,approved_by,entered_by,notes,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"),
            (allocation_id,source_ref.strip(),str(gross),str(costs),str(net),cur_code,str(contributor),str(sustainability),
             "Posted — source evidence declared; external reconciliation still required",evidence_ref.strip(),
             approved_by.strip().lower(),entered_by.strip().lower(),notes.strip(),timestamp))
        for account, side, amount in journal:
            cur.execute(q("INSERT INTO revenue_allocation_journal (id,allocation_id,account_code,side,amount,currency,created_at) VALUES (?,?,?,?,?,?,?)"),
                (str(_uuid.uuid4()),allocation_id,account,side,str(amount),cur_code,timestamp))
        conn.commit()
        return {"allocation_id":allocation_id,"receipt_reference":source_ref.strip(),"currency":cur_code,
                "gross_amount":str(gross),"deductible_costs":str(costs),"eligible_net":str(net),
                "contributor_pool_40_percent":str(contributor),"sustainability_60_percent":str(sustainability),
                "status":"Posted to internal accounting register only"}
    except Exception as exc:
        conn.rollback()
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            raise ValueError("That receipt reference has already been allocated; duplicate allocation was blocked.")
        raise
    finally:
        cur.close()
        conn.close()


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
    """Fetch rows using a real cursor for both SQLite and PostgreSQL.

    sqlite3.Connection has execute(), but it does not have fetchall(); using
    the connection itself as `cur` caused the signup page to crash.
    """
    conn, kind = db_connect()
    cur = None
    try:
        q = sql.replace("?", "%s") if kind == "postgres" else sql
        cur = conn.cursor()
        cur.execute(q, params)
        rows = cur.fetchall()
        return [dict(r) if not isinstance(r, dict) else r for r in rows]
    finally:
        if cur is not None:
            cur.close()
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
        """CREATE TABLE IF NOT EXISTS volunteer_records (
            id TEXT PRIMARY KEY, owner_email TEXT NOT NULL, person_name TEXT NOT NULL,
            record_type TEXT NOT NULL, role_title TEXT NOT NULL, skills TEXT,
            availability TEXT, start_date TEXT, status TEXT NOT NULL,
            notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS revenue_opportunities (
            id TEXT PRIMARY KEY, owner_email TEXT NOT NULL, stream_name TEXT NOT NULL,
            category TEXT NOT NULL, status TEXT NOT NULL, estimated_amount TEXT,
            currency TEXT, assumptions TEXT, next_step TEXT, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS app_settings (
            setting_key TEXT PRIMARY KEY, setting_value TEXT NOT NULL,
            updated_by TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS engine_records (
            id TEXT PRIMARY KEY, engine_name TEXT NOT NULL, record_type TEXT NOT NULL,
            title TEXT NOT NULL, counterparty TEXT, amount TEXT, currency TEXT,
            verification_status TEXT NOT NULL, evidence_ref TEXT, notes TEXT,
            owner_email TEXT NOT NULL, created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS kyc_requests (
            id TEXT PRIMARY KEY, user_email TEXT NOT NULL, legal_name TEXT NOT NULL,
            country TEXT NOT NULL, verification_provider TEXT, provider_reference TEXT,
            status TEXT NOT NULL, reviewer_email TEXT, review_note TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS withdrawal_requests (
            id TEXT PRIMARY KEY, user_email TEXT NOT NULL, amount TEXT NOT NULL,
            asset TEXT NOT NULL, network TEXT NOT NULL, destination_address TEXT NOT NULL,
            status TEXT NOT NULL, tx_hash TEXT, admin_note TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS deposit_intents (
            id TEXT PRIMARY KEY, user_email TEXT NOT NULL, asset TEXT NOT NULL,
            network TEXT NOT NULL, amount TEXT, tx_hash TEXT, status TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS referral_records (
            id TEXT PRIMARY KEY, referrer_email TEXT NOT NULL, referred_email TEXT,
            referral_code TEXT NOT NULL, status TEXT NOT NULL, reward_amount TEXT,
            reward_asset TEXT, evidence_ref TEXT, created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS report_schedules (
            id TEXT PRIMARY KEY, owner_email TEXT NOT NULL, report_name TEXT NOT NULL,
            frequency TEXT NOT NULL, run_day INTEGER NOT NULL, recipient_email TEXT,
            enabled INTEGER NOT NULL DEFAULT 1, timezone_name TEXT NOT NULL,
            last_run_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS project_indicators (
            id TEXT PRIMARY KEY, owner_email TEXT NOT NULL, project_name TEXT NOT NULL,
            indicator_name TEXT NOT NULL, indicator_type TEXT NOT NULL,
            baseline TEXT, target TEXT, current_value TEXT, unit TEXT,
            disaggregation TEXT, data_source TEXT, reporting_frequency TEXT,
            reporting_period TEXT, notes TEXT, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS workspace_grids (
            id TEXT PRIMARY KEY, owner_email TEXT NOT NULL, page_name TEXT NOT NULL,
            grid_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS calendar_events (
            id TEXT PRIMARY KEY, owner_email TEXT NOT NULL, title TEXT NOT NULL,
            event_date TEXT NOT NULL, event_time TEXT NOT NULL, timezone_name TEXT NOT NULL,
            reminder_minutes INTEGER NOT NULL DEFAULT 15, status TEXT NOT NULL DEFAULT 'Scheduled',
            details TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id TEXT PRIMARY KEY, user_email TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL, used_at TEXT, created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS notification_preferences (
            user_email TEXT PRIMARY KEY, email_security INTEGER NOT NULL DEFAULT 1,
            email_task_updates INTEGER NOT NULL DEFAULT 1, email_earnings INTEGER NOT NULL DEFAULT 1,
            email_opportunities INTEGER NOT NULL DEFAULT 0, email_product_updates INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS work_activities (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL,
            eligibility TEXT, instructions TEXT, rate_amount TEXT, currency TEXT NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 1, status TEXT NOT NULL, created_by TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS work_submissions (
            id TEXT PRIMARY KEY, activity_id TEXT NOT NULL, user_email TEXT NOT NULL,
            submission_text TEXT NOT NULL, status TEXT NOT NULL, reviewer_note TEXT,
            approved_amount TEXT, currency TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS revenue_allocations (
            id TEXT PRIMARY KEY, receipt_reference TEXT NOT NULL UNIQUE, gross_amount TEXT NOT NULL,
            deductible_costs TEXT NOT NULL, eligible_net TEXT NOT NULL, currency TEXT NOT NULL,
            user_pool_amount TEXT NOT NULL, sustainability_amount TEXT NOT NULL, status TEXT NOT NULL,
            evidence_ref TEXT NOT NULL, approved_by TEXT NOT NULL, entered_by TEXT NOT NULL,
            notes TEXT, created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS revenue_allocation_journal (
            id TEXT PRIMARY KEY, allocation_id TEXT NOT NULL, account_code TEXT NOT NULL,
            side TEXT NOT NULL CHECK(side IN ('DEBIT','CREDIT')), amount TEXT NOT NULL,
            currency TEXT NOT NULL, created_at TEXT NOT NULL
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



def verify_chain_transaction(chain: str, tx_hash: str) -> dict[str, Any]:
    """Read-only transaction lookup. A returned payload still requires destination/token reconciliation."""
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen
    if not re.fullmatch(r"(0x)?[a-fA-F0-9]{64}", tx_hash.strip()):
        raise ValueError("Transaction hash format is not recognized.")
    if chain == "TRON mainnet":
        if not TRONSCAN_API_KEY:
            raise RuntimeError("Set TRONSCAN_API_KEY in Streamlit secrets to enable TRON read-only lookup.")
        url = "https://apilist.tronscanapi.com/api/transaction-info?" + urlencode({"hash": tx_hash.strip()})
        req = Request(url, headers={"TRON-PRO-API-KEY": TRONSCAN_API_KEY, "Accept": "application/json", "User-Agent": "CedarsEmpire-readonly-check/1.0"})
        with urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not data or data.get("hash", "").lower() != tx_hash.strip().lower():
            return {"lookup": "No matching transaction returned", "chain": chain, "confirmed": False}
        transfers = data.get("trc20TransferInfo") or data.get("transfersAllList") or []
        return {"lookup": "TRONSCAN API response", "chain": chain, "hash": data.get("hash"), "confirmed": data.get("confirmed"), "revert": data.get("revert"), "contract_result": data.get("contractRet"), "block": data.get("block"), "timestamp_ms": data.get("timestamp"), "from": data.get("ownerAddress"), "to": data.get("toAddress"), "token_transfers": transfers[:20]}
    if chain == "BNB Smart Chain mainnet":
        if not ETHERSCAN_API_KEY:
            raise RuntimeError("Set ETHERSCAN_API_KEY in Streamlit secrets to enable BNB Smart Chain read-only lookup.")
        base = "https://api.etherscan.io/v2/api?"
        params = {"chainid": "56", "module": "proxy", "action": "eth_getTransactionReceipt", "txhash": tx_hash.strip() if tx_hash.startswith("0x") else "0x" + tx_hash.strip(), "apikey": ETHERSCAN_API_KEY}
        with urlopen(Request(base + urlencode(params), headers={"Accept": "application/json", "User-Agent": "CedarsEmpire-readonly-check/1.0"}), timeout=12) as response:
            receipt = json.loads(response.read().decode("utf-8"))
        result = receipt.get("result")
        if not result:
            return {"lookup": "No receipt returned (possibly pending, unknown, or API unavailable)", "chain": chain, "hash": tx_hash.strip()}
        transfer_params = {"chainid": "56", "module": "account", "action": "tokentx", "txhash": tx_hash.strip() if tx_hash.startswith("0x") else "0x" + tx_hash.strip(), "apikey": ETHERSCAN_API_KEY}
        transfers = []
        try:
            with urlopen(Request(base + urlencode(transfer_params), headers={"Accept": "application/json", "User-Agent": "CedarsEmpire-readonly-check/1.0"}), timeout=12) as response:
                transfer_response = json.loads(response.read().decode("utf-8"))
            if isinstance(transfer_response.get("result"), list):
                transfers = transfer_response["result"][:20]
        except Exception:
            transfers = []
        return {"lookup": "Etherscan API V2 response", "chain": chain, "hash": result.get("transactionHash"), "receipt_status": result.get("status"), "block_number": result.get("blockNumber"), "to_contract_or_address": result.get("to"), "gas_used": result.get("gasUsed"), "token_transfers": transfers}
    raise ValueError("Unsupported chain.")

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
def render_engine_dashboard(engine_name: str) -> None:
    """Record evidence-backed operating activity for one business engine."""
    st.write("Track counterparties, demand, delivery, costs and receipts. A status entered here is not independently verified by the platform.")
    safe_key = re.sub(r"[^a-z0-9]+", "_", engine_name.lower()).strip("_")
    with st.form("engine_dashboard_" + safe_key):
        record_type = st.selectbox("Record type", ["Provider verification", "Customer demand", "Service delivery", "Operating cost", "Receipt / settlement", "Risk / incident"], key="engine_type_" + safe_key)
        title = st.text_input("Record title / service reference", key="engine_title_" + safe_key)
        counterparty = st.text_input("Provider / customer / counterparty", key="engine_party_" + safe_key)
        amount = st.text_input("Amount (optional; supported by evidence)", key="engine_amount_" + safe_key)
        currency = st.selectbox("Currency / asset", ["UGX", "USD", "EUR", "USDT", "TRX", "BNB", "Other"], key="engine_currency_" + safe_key)
        status = st.selectbox("Self-declared evidence status", ["Unverified", "Evidence submitted", "Pending administrator review", "Rejected"], key="engine_status_" + safe_key)
        evidence = st.text_input("Evidence reference (contract, invoice, receipt or transaction hash)", key="engine_evidence_" + safe_key)
        notes = st.text_area("Demand evidence, delivery proof, costs, risks and reconciliation notes", key="engine_notes_" + safe_key)
        save = st.form_submit_button("Save engine record")
    if save:
        if not title.strip():
            st.error("A record title is required.")
        else:
            db_exec("INSERT INTO engine_records (id,engine_name,record_type,title,counterparty,amount,currency,verification_status,evidence_ref,notes,owner_email,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), engine_name, record_type, title.strip(), counterparty.strip(), amount.strip() or None, currency, status, evidence.strip() or None, notes.strip(), USER_EMAIL, now_iso()))
            record_event(USER_EMAIL, "real_money_engine_record_created", engine_name + ": " + record_type)
            st.success("Record saved. User-entered evidence status does not itself prove verification or payment.")
            st.rerun()
    rows = db_all("SELECT record_type,title,counterparty,amount,currency,verification_status,evidence_ref,notes,owner_email,created_at FROM engine_records WHERE engine_name=? ORDER BY created_at DESC", (engine_name,))
    st.subheader("Operating evidence register")
    if rows: render_bank_table(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else: st.info("No operating records yet.")
    st.caption("Only receipts reconciled against source evidence count as actual revenue. Estimates, leads and pending invoices are not receipts.")


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
st.title("CEDARS EMPIRE")


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
    signin, signup, public, reset_request, reset_finish = st.tabs(
        ["Sign in", "Create account", "Public noticeboard", "Forgot password", "Set new password"])
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
        st.subheader("Create your Cedars Empire account")
        st.write("A short B2B / purpose profile helps tailor tools and understand legitimate organizational use. It is not an advertising consent and does not authorize data resale.")
        with st.form("signup_form"):
            full_name = st.text_input("Full name")
            email = st.text_input("Email address").strip().lower()
            password = st.text_input("Create password (at least 10 characters)", type="password")
            password2 = st.text_input("Confirm password", type="password")
            account_type = st.selectbox("Account type", ["Individual / job seeker", "NGO / civil society organization", "Business / private sector", "Public institution", "Donor / funder", "Research / academic", "Other"])
            organization = st.text_input("Organization (optional for individuals)")
            sector = st.selectbox("Main sector", ["Select…", "Education", "Health", "Climate / environment", "Livelihoods / economic inclusion", "Gender / protection", "Governance / peacebuilding", "Humanitarian response", "Agriculture / food security", "Digital / technology", "Research / evaluation", "Multiple sectors", "Other"])
            purpose = st.text_area("B2B / workspace purpose — how will you use Cedars Empire?", placeholder="Example: identify grants, draft proposals and monitor a youth employment project.")
            followup = st.checkbox("I opt in to follow-up emails and identifiable attendance records. Optional; I can opt out later.")
            agree = st.checkbox("I agree to the Cedars Empire platform terms and privacy notice. I understand that outputs are decision-support drafts and do not guarantee funding, employment or compliance outcomes.")
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
                db_exec("INSERT INTO notification_preferences (user_email,updated_at) VALUES (?,?) ON CONFLICT (user_email) DO NOTHING", (email, now_iso()))
                user = db_all("SELECT * FROM users WHERE email=?", (email,))[0]
                # Attribute a referral only when the code matches an existing account.
                try:
                    referral_code = str(st.query_params.get("ref", "")).strip().upper()
                    if referral_code and re.fullmatch(r"[A-F0-9]{12}", referral_code):
                        candidates = db_all("SELECT email FROM users WHERE email<>?", (email,))
                        referrer = next((row["email"] for row in candidates if hashlib.sha256(row["email"].lower().encode("utf-8")).hexdigest()[:12].upper() == referral_code), None)
                        if referrer:
                            db_exec("INSERT INTO referral_records (id,referrer_email,referred_email,referral_code,status,evidence_ref,created_at) VALUES (?,?,?,?,?,?,?)", (str(uuid.uuid4()), referrer, email, referral_code, "Signup claimed", "Account creation event", now_iso()))
                except Exception:
                    pass
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


    with reset_request:
        st.subheader("Reset account password")
        st.caption("A single-use reset link expires after 30 minutes. Email delivery must be configured by an administrator.")
        with st.form("password_reset_request_form"):
            reset_email = st.text_input("Account email address", key="reset_request_email").strip().lower()
            send_reset = st.form_submit_button("Send password reset link", type="primary")
        if send_reset:
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", reset_email):
                st.error("Enter a valid email address.")
            elif not email_delivery_configured():
                st.error("Password reset email is unavailable because secure email delivery is not configured. Contact the administrator.")
            else:
                users = db_all("SELECT email,full_name FROM users WHERE email=?", (reset_email,))
                if users:
                    token = secrets.token_urlsafe(32)
                    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
                    created = datetime.now(timezone.utc)
                    expires = (created + timedelta(minutes=30)).replace(microsecond=0).isoformat()
                    db_exec("INSERT INTO password_reset_tokens (id,user_email,token_hash,expires_at,used_at,created_at) VALUES (?,?,?,?,?,?)",
                            (str(uuid.uuid4()), reset_email, token_hash, expires, None, created.replace(microsecond=0).isoformat()))
                    base_url = setting("PUBLIC_APP_URL", "https://project-x4vqe4f3kfpeugzai2oqed.streamlit.app/").rstrip("/")
                    reset_url = base_url + "/?reset_token=" + __import__("urllib.parse", fromlist=["quote"]).quote(token)
                    sent = send_email(reset_email, "Cedars Empire password reset",
                        "A password reset was requested for your account.\n\n"
                        + "Use this single-use link within 30 minutes:\n" + reset_url
                        + "\n\nIf you did not request this reset, ignore this email. No password has been changed.")
                    if not sent:
                        db_exec("UPDATE password_reset_tokens SET used_at=? WHERE token_hash=?",
                                (now_iso(), token_hash))
                st.success("If the account exists and mail delivery is working, a password reset link has been sent.")
    with reset_finish:
        st.subheader("Set a new password")
        query_token = str(st.query_params.get("reset_token", "")).strip()
        token_value = st.text_input("Single-use reset token", value=query_token, key="password_reset_token_value")
        with st.form("password_reset_finish_form"):
            new_password = st.text_input("New password (at least 10 characters)", type="password")
            confirm_password = st.text_input("Confirm new password", type="password")
            finish_reset = st.form_submit_button("Change password", type="primary")
        if finish_reset:
            token_hash = hashlib.sha256(token_value.encode("utf-8")).hexdigest() if token_value else ""
            tokens = db_all("SELECT * FROM password_reset_tokens WHERE token_hash=? AND used_at IS NULL",
                            (token_hash,)) if token_hash else []
            valid_token = False
            if tokens:
                try:
                    valid_token = datetime.fromisoformat(tokens[0]["expires_at"]) > datetime.now(timezone.utc)
                except Exception:
                    valid_token = False
            if not valid_token:
                st.error("This reset link is invalid, expired or already used. Request a new link.")
            elif len(new_password) < 10:
                st.error("New password must contain at least 10 characters.")
            elif new_password != confirm_password:
                st.error("The passwords do not match.")
            else:
                new_salt, new_hash = pw_hash(new_password)
                db_exec("UPDATE users SET password_salt=?,password_hash=? WHERE email=?",
                        (new_salt, new_hash, tokens[0]["user_email"]))
                db_exec("UPDATE password_reset_tokens SET used_at=? WHERE id=?",
                        (now_iso(), tokens[0]["id"]))
                send_email(tokens[0]["user_email"], "Your Cedars Empire password was changed",
                           "Your account password was changed. If this was not you, contact the administrator immediately.")
                record_event(tokens[0]["user_email"], "password_reset_completed")
                st.success("Password changed. The reset link cannot be reused.")
                try:
                    st.query_params.clear()
                except Exception:
                    pass

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

# Page lists are kept in the application layer; navigation is rendered in the main page area.
business_user_pages = ["Dashboard", "Deposit", "Earn", "Withdraw", "Refer", "Account"]
business_admin_pages = [
    "Dashboard", "Executive Command Center", "Treasury Management", "Real Money Engines",
    "Grid Marketplace", "Work & Contracts", "Payments & Treasury",
    "Blockchain & Treasury", "Payment Operations", "Reports & Referrals", "AI Operations",
]
ngo_user_pages = [
    "Climate and Career Hub", "My Tasks", "Opportunity Analysis", "Proposal Studio",
    "Live Studio", "CV / Resume Studio", "SDG Navigator", "Noticeboard",
    "HH Standards & Impact", "Donor Feedback", "B2B Collaboration", "HR & Volunteers",
    "Income Activities", "My Work & Wallet", "Revenue & Sustainability",
    "Privacy and Data", "Calendar & Events",
]
ngo_admin_pages = [
    "Command Center", "HR Department", "Finance Department", "40/60 Allocation Foundation",
    "Income & Revenue", "Admin Studio", "Admin Noticeboard", "Wallet & Withdrawals",
    "Branding Settings", "Report Automation", "Admin Console",
]
# Locked CEDARS EMPIRE identity header, rendered in the page body (never in the sidebar).
st.markdown("""
<div class="ce-fixed-header">
  <div class="ce-brand-mark">C</div>
  <div><div class="ce-brand-title">CEDARS EMPIRE</div></div>
  <div class="ce-header-right">SECURE WORKSPACE · VERIFIED ACTIVITY</div>
</div>
""", unsafe_allow_html=True)

workspace_mode = st.radio(
    "Workspace", ["Real Money Business", "NGO Operations"],
    index=0, key="cedars_workspace_mode", horizontal=True,
)
if workspace_mode == "NGO Operations":
    pages = ngo_user_pages + (ngo_admin_pages if IS_ADMIN else [])
else:
    pages = business_admin_pages if IS_ADMIN else business_user_pages

st.markdown('<div class="ce-menu-label">MAIN MENU</div>', unsafe_allow_html=True)
selected_page = st.radio(
    "Navigate CEDARS EMPIRE", pages,
    index=min(pages.index(st.session_state.get("ce_header_menu", pages[0])), len(pages)-1)
      if st.session_state.get("ce_header_menu", pages[0]) in pages else 0,
    horizontal=True, label_visibility="collapsed", key="ce_header_menu",
)
if "ce_header_search" not in st.session_state:
    st.session_state.ce_header_search = ""
quick_search = st.text_input(
    "Quick search", placeholder="Find a page…",
    label_visibility="collapsed", key="ce_header_search",
)
if quick_search.strip():
    matches = [p for p in pages if quick_search.strip().lower() in p.lower()]
    st.caption("Matching pages: " + (" · ".join(matches) if matches else "No matching page names."))

page_routes = {
    "Dashboard": "Business Dashboard",
    "Deposit": "Deposit & Packages",
    "Earn": "Real Money Engines",
    "Withdraw": "Withdrawals & Full KYC",
    "Refer": "Referral Program",
    "Account": "Payments & Treasury",
    "Grid Marketplace": "World Grid Marketplace",
    "Work & Contracts": "Client Services & Contracts",
    "Payments & Treasury": "Blockchain & Treasury",
    "Payment Operations": "Payment Operations",
    "Reports & Referrals": "Business Reports",
    "AI Operations": "AI Business Scenario Lab",
    "Climate and Career Hub": "Dashboard",
    "Command Center": "Executive Command Center",
    "Admin Noticeboard": "Admin Noticeboard",
    "Wallet & Withdrawals": "Payment Operations",
    "My Work & Wallet": "My Work & Wallet",
    "Branding Settings": "Branding Settings",
}
if selected_page == "Withdraw" and not IS_ADMIN:
    try:
        kyc_route_rows = db_all(
            "SELECT status,verification_provider,provider_reference FROM kyc_requests WHERE user_email=? ORDER BY created_at DESC",
            (USER_EMAIL,),
        )
        if kyc_route_rows and kyc_route_rows[0].get("status") == "Verified" and kyc_route_rows[0].get("verification_provider") and kyc_route_rows[0].get("provider_reference"):
            page_routes["Withdraw"] = "Withdraw / Cash Out"
        else:
            page_routes["Withdraw"] = "Withdrawals & Full KYC"
    except Exception:
        page_routes["Withdraw"] = "Withdrawals & Full KYC"
page = page_routes.get(selected_page, selected_page)
set_table_scope(page)
reset_table_counter()
account_col, signout_col = st.columns([5, 1])
with account_col:
    st.caption(f"Signed in as {USER_NAME} · {USER_EMAIL}" + (" · Administrator" if IS_ADMIN else ""))
with signout_col:
    if st.button("Sign out", key="ce_sign_out"):
        record_event(USER_EMAIL, "sign_out")
        for key in ["user_email", "full_name", "account_type", "followup_optin", "last_login"]:
            st.session_state.pop(key, None)
        st.rerun()
st.divider()
st.caption("CEDARS EMPIRE · Release 2.1")
st.caption("AI: connected" if OPENAI_API_KEY else "AI: local structured mode (API key not configured)")

# Cedars Empire: real-business scenario workspace.
# NGO operations pages remain in the codebase but are intentionally inaccessible from this business-only navigation.
BUSINESS_PAGES = {
    "Investor Landing", "Business Dashboard", "Real Money Engines", "NeuroWave + Health", "EchoMap + Mobility", "BioLoop + Finance", "DreamGrid + Education", "EmoFlux + Shelter", "IdeaForge + Data", "QuantumLeap + Energy", "AI Business Scenario Lab",
    "Cleaning Grid", "Shelter & Accommodation Grid", "Energy & Utilities Grid",
    "AI Training & Data Operations", "World Grid Marketplace", "Client Services & Contracts",
    "Business Opportunity Pipeline", "Blockchain & Treasury", "Deposit QR & TIGERS",
    "Withdrawals & Full KYC", "Staking & Compounding", "Referral Program",
    "Business Reports", "Executive Command Center", "Treasury Management", "Grid Marketplace", "Work & Contracts",
    "Payments & Treasury", "Deposits & Withdrawals", "Payment Operations", "Deposit & Packages", "Withdraw / Cash Out", "Reports & Referrals", "AI Operations"
}
if page in BUSINESS_PAGES:
    # Internal 360-degree command oversight; keep public-facing branding clean and never print "360" in UI.
    media_rows = db_all("SELECT setting_key,setting_value FROM app_settings WHERE setting_key IN (?,?)",
                        ("site_logo", "page_image:" + page))
    media = {row["setting_key"]: row["setting_value"] for row in media_rows}
    if media.get("site_logo"):
        try: st.image(io.BytesIO(__import__("base64").b64decode(media["site_logo"])), width=180)
        except Exception: pass
    if media.get("page_image:" + page):
        try: st.image(io.BytesIO(__import__("base64").b64decode(media["page_image:" + page])), use_container_width=True)
        except Exception: pass
    st.title("CEDARS EMPIRE")
    st.caption("AI Real Business Scenarios")
    st.info("Integrity rule: scenarios, leads, estimates and planned contracts are not revenue. Record income only after a verifiable payment is received and reconciled. No earnings or contract is guaranteed.")
    MERGED_GRID_CATALOG = {
        "NeuroWave + Health": {"service":"Workplace wellbeing education and opt-in, non-clinical wellbeing workshops", "buyer":"Employers, universities, care-service operators and wellbeing providers", "revenue":"Fixed-fee workshops, organization subscriptions, and vetted non-clinical care/wellbeing service referrals", "proof":"Written client scope, qualified facilitator/provider, participant consent, safeguarding plan and delivery sign-off", "guardrail":"Do not diagnose, claim clinical outcomes, collect mental-health histories for resale or sell identifiable/sensitive health data.", "integrated_streams":["Care services (non-clinical, safeguarding-led)","Corporate wellbeing workshops","Education and training partnerships"]},
        "EchoMap + Mobility": {"service":"Licensed soundscape design and accessible audio experiences for journeys, delivery routes and venues", "buyer":"Transport operators, delivery businesses, hotels, tourism operators and mobility apps", "revenue":"Licensed content packages, integration fees, business subscriptions, and verified mobility/delivery service referrals", "proof":"Rights-cleared audio assets, accessibility testing, signed license, qualified provider agreements and delivery/usage records", "guardrail":"Do not sell individual location histories. Collect only necessary, consented, aggregated usage metrics.", "integrated_streams":["Mobility and delivery services","Travel soundscapes and audio guides","World Grid Marketplace provider listings"]},
        "BioLoop + Finance": {"service":"SME bookkeeping hygiene, cash-flow dashboards, procurement cost analysis and financial data-quality support", "buyer":"Small businesses, accountants, suppliers and business-support organizations", "revenue":"Monthly service retainers, fixed-fee financial operations projects, procurement support fees, and disclosed supplier referrals", "proof":"Client authorization, written scope, reconciled source records, supplier quotes and approved deliverables", "guardrail":"No sale of personal financial data, no unlicensed investment advice, no guaranteed savings or returns.", "integrated_streams":["Procurement and supply-chain sourcing","Supplier quote comparison","Business finance operations and reporting"]},
        "DreamGrid + Education": {"service":"Sleep-science literacy, learning journals, digital courses and education workshops", "buyer":"Schools, universities, adult-learning providers, employers and publishers", "revenue":"Institutional workshop fees, course licenses, subscriptions and commissioned learning content", "proof":"Evidence-based curriculum, instructor approval, participant consent, licensing rights and completion records", "guardrail":"No medical claims or claims that lucid dreaming treats illness; protect learner and sleep-related data.", "integrated_streams":["Climate and career learning content","Digital training and AI skills tasks","Institutional course and content licensing"]},
        "EmoFlux + Shelter": {"service":"Resident experience surveys, accommodation matching and comfort-improvement recommendations for property operators", "buyer":"Hotels, hostels, property managers, emergency accommodation operators and supported-living providers", "revenue":"Property assessment fees, accommodation/service referrals under written terms, and recurring property contracts", "proof":"Property/provider permission, lawful listing, voluntary survey process, documented recommendations, availability confirmation and client acceptance", "guardrail":"Do not infer or sell residents emotional states, identify vulnerable occupants or make clinical claims. Never list shelter capacity as available without provider confirmation.", "integrated_streams":["Shelter and accommodation matching","Cleaning and property turnover services","Food and water access/service referrals","Care services with safeguarding controls"]},
        "IdeaForge + Data": {"service":"Human-reviewed research synthesis, data cleaning, AI data-labeling and innovation sprint facilitation", "buyer":"SMEs, research teams, AI developers, universities and product teams", "revenue":"Fixed-price research packages, data-quality projects, contracted labeling tasks, workshops or monthly retainers", "proof":"Written deliverables, source register, lawful data rights, task acceptance, quality review and client acceptance", "guardrail":"Use lawfully obtained data; do not resell client-confidential information or claim AI output is verified without review.", "integrated_streams":["AI training and data operations","Paid research/survey tasks with verified buyers","World Grid Marketplace demand and provider discovery"]},
        "QuantumLeap + Energy": {"service":"Solar+ energy opportunity assessments, energy-bill analysis, efficiency reports, qualified solar/utility referrals and authorized monitoring", "buyer":"SMEs, property operators, schools, facility managers, solar installers and energy-service providers", "revenue":"Assessment fees, contracted monitoring, installation/service referrals under written agreements, and disclosed referral fees", "proof":"Authorized bills or meter data, documented methodology, qualified/verified partners, written scope, installation/service completion and measured before/after results", "guardrail":"No probability-based earnings claims, fake kWh trading, unverified energy credits or guaranteed savings. Do not claim solar capacity, energy availability or savings without evidence.", "integrated_streams":["Solar+ installation and maintenance referrals","Energy-efficiency audits and monitoring","Battery/backup power and utility-service referrals"]}
    }
    if page in MERGED_GRID_CATALOG:
        grid = MERGED_GRID_CATALOG[page]
        st.header(page)
        st.subheader(grid["service"])
        st.write("**Target paying customers:** " + grid["buyer"])
        st.write("**Commercial model:** " + grid["revenue"])
        st.write("**Integrated existing real-money streams:** " + " · ".join(grid["integrated_streams"]))
        st.write("These are connected service lines within the existing grid portfolio—not separate promised-income products. Use World Grid Marketplace for provider discovery and Real Money Engines to record each opportunity, contract, delivery, cost and reconciled receipt.")
        st.write("**Evidence required before calling revenue real:** " + grid["proof"])
        st.warning("Integrity boundary: " + grid["guardrail"])
        st.caption("No customer, contract, provider, revenue, payout or performance result is presumed to exist. Record actual activity below and submit evidence for review.")
        render_engine_dashboard(page)
    elif page == "Investor Landing":
        st.header("CEDARS EMPIRE")
        st.subheader("Investment-grade operating discipline for real AI and real-world services")
        st.write("Explore business engines, verified counterparties, service delivery, costs and reconciled receipts. This workspace is an operating platform—not a public investment offer and not a promise of returns.")
        tiles = st.columns(3)
        tiles[0].metric("Verified receipts", "Evidence required")
        tiles[1].metric("Verified on-chain activity", "Not connected")
        tiles[2].metric("Staking", "Not enabled")
        st.subheader("Seven merged business grids with existing real-money streams")
        st.markdown("- **NeuroWave + Health:** organization-funded, non-clinical wellbeing education.\n- **EchoMap + Mobility:** licensed audio and accessible soundscape services.\n- **BioLoop + Finance:** SME financial operations and data-quality support.\n- **DreamGrid + Education:** sleep-science literacy and education products.\n- **EmoFlux + Shelter:** property comfort assessments using voluntary feedback.\n- **IdeaForge + Data:** research synthesis, data cleaning and innovation services.\n- **QuantumLeap + Energy:** evidence-based energy-bill analysis and efficiency services.")
        st.subheader("Operating system")
        st.markdown("- **Real Money Engines:** provider and buyer verification, demand evidence, delivery, costs and receipts.\n- **Treasury:** chain-specific verification separated from internal ledger entries.\n- **Deposits and withdrawals:** disabled until destination, network, compliance and approval controls are verified.\n- **KYC and referrals:** clear status tracking; no automatic payouts or unearned referral rewards.")
        st.info("No investment product, deposit destination, staking provider, payout rail, customer contract or revenue figure is represented as verified unless supporting evidence is recorded and checked.")
    elif page == "Real Money Engines":
        st.header("Real Money Engines")
        st.write("Each engine should have a verified provider, evidence of customer demand, agreed service terms, delivery proof, itemized costs and reconciled receipts.")
        engines = ["Cleaning services", "Shelter & accommodation", "Energy & utilities", "AI training & data operations", "World Grid marketplace", "Client services & contracts"]
        chosen_engine = st.selectbox("Choose an engine", engines)
        with st.form("engine_record_form"):
            record_type = st.selectbox("Record type", ["Provider verification", "Customer demand", "Service delivery", "Operating cost", "Receipt / settlement", "Risk / incident"])
            title = st.text_input("Record title / service reference")
            counterparty = st.text_input("Provider / customer / counterparty")
            amount = st.text_input("Amount (optional; exact amount supported by evidence)")
            currency = st.selectbox("Currency / asset", ["UGX", "USD", "EUR", "USDT", "TRX", "BNB", "Other"])
            verification_status = st.selectbox("Self-declared evidence status", ["Unverified", "Evidence submitted", "Pending administrator review", "Rejected"])
            evidence_ref = st.text_input("Evidence reference (contract, invoice, receipt or transaction hash)")
            notes = st.text_area("Scope, delivery proof, costs, risks and reconciliation notes")
            save_engine = st.form_submit_button("Save engine record")
        if save_engine:
            if not title.strip():
                st.error("A record title is required.")
            else:
                db_exec("INSERT INTO engine_records (id,engine_name,record_type,title,counterparty,amount,currency,verification_status,evidence_ref,notes,owner_email,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), chosen_engine, record_type, title.strip(), counterparty.strip(), amount.strip() or None, currency, verification_status, (evidence_ref.strip() if evidence_ref.strip() else None), notes.strip(), USER_EMAIL, now_iso()))
                record_event(USER_EMAIL, "real_money_engine_record_created", chosen_engine + ": " + record_type)
                st.success("Record saved. Its status is user-entered and does not itself prove independent verification or payment.")
                st.rerun()
        rows = db_all("SELECT engine_name,record_type,title,counterparty,amount,currency,verification_status,evidence_ref,notes,owner_email,created_at FROM engine_records WHERE engine_name=? ORDER BY created_at DESC", (chosen_engine,))
        st.subheader("Engine evidence register")
        if rows: render_bank_table(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else: st.info("No engine evidence records yet.")
        st.caption("Only reconciled receipts backed by source evidence should be counted as actual revenue. Planning estimates and pending invoices are not receipts.")
    elif page == "Deposit QR & TIGERS":
        st.header("Deposit QR & TIGERS")
        st.warning("Deposits are disabled by default. Never send assets until an administrator independently verifies the destination, network and token contract and formally enables deposits.")
        cfg = {row["setting_key"]: row["setting_value"] for row in db_all("SELECT setting_key,setting_value FROM app_settings")}
        enabled = cfg.get("deposit_enabled") == "true" and cfg.get("deposit_destinations_verified") == "true"
        asset_networks = {}
        if cfg.get("tron_deposit_address"):
            asset_networks.update({"TRX": "TRON mainnet", "USDT (TRC-20)": "TRON mainnet"})
        if cfg.get("bnb_deposit_address"):
            asset_networks.update({"BNB": "BNB Smart Chain mainnet", "USDT (BEP-20)": "BNB Smart Chain mainnet"})
        tigers_network = cfg.get("tigers_network", "")
        if cfg.get("tigers_token_contract") and tigers_network in ("TRON mainnet", "BNB Smart Chain mainnet") and ((tigers_network == "TRON mainnet" and cfg.get("tron_deposit_address")) or (tigers_network == "BNB Smart Chain mainnet" and cfg.get("bnb_deposit_address"))):
            asset_networks["TIGERS"] = tigers_network
        st.write("**TIGERS token contract:** " + (cfg.get("tigers_token_contract") or "Not configured — contract not verified"))
        st.write("**TRON destination:** " + (cfg.get("tron_deposit_address") or "Not configured"))
        st.write("**BNB Smart Chain destination:** " + (cfg.get("bnb_deposit_address") or "Not configured"))
        if not enabled:
            st.error("DEPOSITS DISABLED — verification and formal enablement are incomplete. No deposit QR code is issued.")
        else:
            st.success("Destinations are marked enabled by an administrator. Independently verify the exact network and address in your wallet before sending.")
            for label, address in [("TRON",cfg.get("tron_deposit_address","")),("BNB Smart Chain",cfg.get("bnb_deposit_address",""))]:
                if address:
                    st.markdown("**" + label + " address**")
                    st.code(address)
                    try:
                        import qrcode
                        st.image(qrcode.make(address).get_image(), caption=label + " address QR — confirm network and asset before use", width=220)
                    except Exception:
                        st.caption("QR generation is unavailable in this deployment; use the address above only after independent verification.")
        st.subheader("Record a deposit claim for reconciliation")
        with st.form("deposit_intent_form"):
            asset_choices = list(asset_networks) or ["No supported asset configured"]
            asset = st.selectbox("Asset", asset_choices)
            network = asset_networks.get(asset, "Not configured")
            st.caption("Network is fixed to the configured asset/network pairing to reduce cross-chain deposit errors: " + network)
            amount = st.text_input("Amount claimed (optional)")
            tx_hash = st.text_input("Transaction hash")
            submit_deposit = st.form_submit_button("Submit deposit for review", disabled=not enabled)
        if submit_deposit:
            if not tx_hash.strip(): st.error("A transaction hash is required for verification on the correct network.")
            else:
                db_exec("INSERT INTO deposit_intents (id,user_email,asset,network,amount,tx_hash,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), USER_EMAIL, asset, network, amount.strip() or None, tx_hash.strip(), "Pending verification", now_iso(), now_iso()))
                record_event(USER_EMAIL, "deposit_claim_submitted", network + " / " + asset)
                st.success("Deposit claim queued for verification. This is not confirmation that funds arrived.")
                st.rerun()
        mine = db_all("SELECT asset,network,amount,tx_hash,status,created_at,updated_at FROM deposit_intents WHERE user_email=? ORDER BY created_at DESC", (USER_EMAIL,))
        if mine: render_bank_table(pd.DataFrame(mine), use_container_width=True, hide_index=True)
    elif page == "Withdrawals & Full KYC":
        st.header("Withdrawals & Full KYC")
        st.warning("Withdrawal requests are not automatic payouts. Do not enter government ID numbers or upload identity documents here until an approved secure verification provider and privacy process are configured.")
        kyc_rows = db_all("SELECT id,legal_name,country,verification_provider,provider_reference,status,review_note,created_at,updated_at FROM kyc_requests WHERE user_email=? ORDER BY created_at DESC", (USER_EMAIL,))
        latest_kyc = kyc_rows[0] if kyc_rows else None
        st.metric("KYC status", latest_kyc["status"] if latest_kyc else "Not submitted")
        with st.form("kyc_request_form"):
            legal_name = st.text_input("Legal name (as required by the approved verifier)")
            country = st.selectbox("Country of residence", ["Uganda","Kenya","Tanzania","Rwanda","Nigeria","Ghana","United States","United Kingdom","Other"])
            provider = st.text_input("Approved KYC provider (leave blank if not appointed)")
            provider_ref = st.text_input("Provider verification reference (never enter ID number)")
            submit_kyc = st.form_submit_button("Submit KYC review request")
        if submit_kyc:
            if not legal_name.strip(): st.error("Legal name is required to open a review request.")
            else:
                db_exec("INSERT INTO kyc_requests (id,user_email,legal_name,country,verification_provider,provider_reference,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), USER_EMAIL, legal_name.strip(), country, provider.strip() or None, (provider_ref.strip() if provider_ref.strip() else None), "Pending review", now_iso(), now_iso()))
                record_event(USER_EMAIL, "kyc_review_requested")
                st.success("KYC review request saved. This is not identity verification or approval.")
                st.rerun()
        st.subheader("Request a withdrawal")
        withdrawal_cfg = {row["setting_key"]: row["setting_value"] for row in db_all("SELECT setting_key,setting_value FROM app_settings")}
        withdrawal_asset_networks = {"USDT (TRC-20)": "TRON mainnet", "TRX": "TRON mainnet", "USDT (BEP-20)": "BNB Smart Chain mainnet", "BNB": "BNB Smart Chain mainnet"}
        if withdrawal_cfg.get("tigers_token_contract") and withdrawal_cfg.get("tigers_network") in ("TRON mainnet", "BNB Smart Chain mainnet"):
            withdrawal_asset_networks["TIGERS"] = withdrawal_cfg["tigers_network"]
        kyc_approved = bool(latest_kyc and latest_kyc["status"] == "Verified" and latest_kyc.get("verification_provider") and latest_kyc.get("provider_reference"))
        if not kyc_approved: st.info("Withdrawal submission is locked until KYC status is verified and eligibility checks are completed.")
        with st.form("withdrawal_request_form"):
            amount = st.text_input("Withdrawal amount")
            asset = st.selectbox("Asset", list(withdrawal_asset_networks))
            network = withdrawal_asset_networks[asset]
            st.caption("Network is fixed to the asset pairing: " + network)
            destination = st.text_input("Destination wallet address")
            acknowledge = st.checkbox("I checked the destination address and network; I understand requests can be rejected and no payout is guaranteed.")
            submit_withdrawal = st.form_submit_button("Submit withdrawal request", disabled=not kyc_approved)
        if submit_withdrawal:
            try:
                from decimal import Decimal
                amt = Decimal(amount.strip())
                if amt <= 0: raise ValueError("Amount must be greater than zero.")
                if not destination.strip() or not acknowledge: raise ValueError("Destination address and network confirmation are required.")
                db_exec("INSERT INTO withdrawal_requests (id,user_email,amount,asset,network,destination_address,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), USER_EMAIL, str(amt), asset, network, destination.strip(), "Pending eligibility and approval", now_iso(), now_iso()))
                record_event(USER_EMAIL, "withdrawal_request_created", network + " / " + asset)
                st.success("Withdrawal request saved. No transaction has been broadcast and no funds have been sent.")
                st.rerun()
            except Exception as exc: st.error("Withdrawal request not saved: " + str(exc))
        withdrawals = db_all("SELECT amount,asset,network,destination_address,status,tx_hash,admin_note,created_at,updated_at FROM withdrawal_requests WHERE user_email=? ORDER BY created_at DESC", (USER_EMAIL,))
        if withdrawals: render_bank_table(pd.DataFrame(withdrawals), use_container_width=True, hide_index=True)
    elif page == "Staking & Compounding":
        st.header("Staking & Compounding")
        st.warning("No staking transaction is available in this version. Do not transfer assets to an unverified provider or interpret examples as projected or guaranteed returns.")
        st.write("Before any provider is listed as approved, verify its legal identity, supported chain, contract address, audited code, terms, lock-up and unbonding rules, fees, custody model, slashing risk and independent security reviews.")
        with st.form("staking_provider_review_form"):
            provider = st.text_input("Provider name")
            network = st.selectbox("Network", ["TRON", "BNB Smart Chain", "Other"])
            contract = st.text_input("Contract address (reference only)")
            terms_url = st.text_input("Official terms URL")
            lockup = st.text_input("Lock-up / unbonding terms")
            fees = st.text_input("Fees")
            risks = st.text_area("Risk and independent audit evidence")
            submit_provider = st.form_submit_button("Submit provider for due diligence")
        if submit_provider:
            if not provider.strip() or not terms_url.strip().startswith("https://") or not risks.strip():
                st.error("Provider, HTTPS terms URL and risk/evidence notes are required.")
            else:
                db_exec("INSERT INTO engine_records (id,engine_name,record_type,title,counterparty,amount,currency,verification_status,evidence_ref,notes,owner_email,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), "Staking & Compounding", "Provider due diligence", provider.strip(), provider.strip(), None, None, "Evidence submitted", terms_url.strip(), "Network: " + network + "; contract: " + contract.strip() + "; lock-up: " + lockup.strip() + "; fees: " + fees.strip() + "; risks: " + risks.strip(), USER_EMAIL, now_iso()))
                record_event(USER_EMAIL, "staking_provider_due_diligence_submitted")
                st.success("Provider submitted for due diligence; it is not approved or enabled.")
                st.rerun()
        stake_rows = db_all("SELECT title,counterparty,verification_status,evidence_ref,notes,created_at FROM engine_records WHERE engine_name=? ORDER BY created_at DESC", ("Staking & Compounding",))
        if stake_rows: render_bank_table(pd.DataFrame(stake_rows), use_container_width=True, hide_index=True)
        st.caption("No simulated APR, projected profit or compounding estimate is presented as earnings. Provider approval and transaction integration are separate release gates.")
    elif page == "Referral Program":
        st.header("Referral Program")
        st.write("Share a referral link. Attribution is not a reward entitlement; any reward requires published terms, anti-fraud checks, a verified qualifying event and an approved payout process.")
        referral_code = hashlib.sha256(USER_EMAIL.lower().encode("utf-8")).hexdigest()[:12].upper()
        base_url = setting("PUBLIC_APP_URL", "https://project-x4vqe4f3kfpeugzai2oqed.streamlit.app/").rstrip("/")
        referral_url = base_url + "/?ref=" + referral_code
        st.text_input("Your referral link", value=referral_url, disabled=True)
        st.caption("Configure PUBLIC_APP_URL if the production URL changes. Referral rewards are not enabled unless written terms and verification are approved.")
        with st.form("referral_record_form"):
            referred_email = st.text_input("Referred person email (only with their consent; optional)")
            status = st.selectbox("Referral status", ["Link shared", "Signup claimed", "Qualifying action pending verification", "Verified qualifying action", "Rejected"])
            evidence_ref = st.text_input("Evidence reference (optional)")
            save_referral = st.form_submit_button("Record referral activity")
        if save_referral:
            db_exec("INSERT INTO referral_records (id,referrer_email,referred_email,referral_code,status,evidence_ref,created_at) VALUES (?,?,?,?,?,?,?)", (str(uuid.uuid4()), USER_EMAIL, referred_email.strip().lower() or None, referral_code, status, (evidence_ref.strip() if evidence_ref.strip() else None), now_iso()))
            record_event(USER_EMAIL, "referral_activity_recorded", status)
            st.success("Referral activity recorded. No reward has been accrued or paid.")
            st.rerun()
        own_refs = db_all("SELECT referral_code,referred_email,status,reward_amount,reward_asset,evidence_ref,created_at FROM referral_records WHERE referrer_email=? ORDER BY created_at DESC", (USER_EMAIL,))
        if own_refs: render_bank_table(pd.DataFrame(own_refs), use_container_width=True, hide_index=True)
    elif page == "Business Dashboard":
        st.header("Business Dashboard")
        st.write("Operate service businesses, validate demand, track real contracts and reconcile verified receipts.")
        cols = st.columns(3)
        cols[0].metric("Verified revenue", "Not connected")
        cols[1].metric("Active contracts", "Not connected")
        cols[2].metric("Treasury balance", "Not connected")
        st.caption("Live financial figures are intentionally withheld until connected to verified transaction records.")
        st.subheader("Business grids")
        st.write("Cleaning services · Accommodation matching · Energy and utilities · AI training/data operations · Marketplace · Client services")
    elif page == "AI Business Scenario Lab":
        st.header("AI Business Scenario Lab")
        st.write("Build a testable operating plan. Estimates are planning inputs only; they are not evidence of market demand or income.")
        with st.form("business_scenario_form"):
            scenario_name = st.text_input("Scenario / service name")
            customer = st.text_input("Target customer and location")
            problem = st.text_area("Customer problem and proposed service")
            price = st.text_input("Proposed price and currency (optional)")
            cost = st.text_input("Expected delivery costs (optional)")
            proof = st.text_area("Evidence of demand, provider agreement, permits and key risks")
            submitted = st.form_submit_button("Review scenario")
        if submitted:
            st.subheader("Scenario review")
            st.write("**Service:** " + (scenario_name.strip() or "Not provided"))
            st.write("**Customer:** " + (customer.strip() or "Not provided"))
            st.write("**Problem / solution:** " + (problem.strip() or "Not provided"))
            st.write("**Price / costs:** " + (price.strip() or "Not provided") + " / " + (cost.strip() or "Not provided"))
            st.write("**Evidence and risks:** " + (proof.strip() or "No evidence supplied"))
            st.warning("Validation status: NOT VERIFIED. Confirm real customers, supplier capacity, unit economics, legal requirements and written agreements before spending or promising service.")
    elif page == "Cleaning Grid":
        st.header("Cleaning Grid")
        render_engine_dashboard("Cleaning services")
    elif page == "Shelter & Accommodation Grid":
        st.header("Shelter & Accommodation Grid")
        render_engine_dashboard("Shelter & accommodation")
    elif page == "Energy & Utilities Grid":
        st.header("Energy & Utilities Grid")
        render_engine_dashboard("Energy & utilities")
    elif page == "AI Training & Data Operations":
        st.header("AI Training & Data Operations")
        st.write("Validate buyer identity, written scope, data rights, privacy/security requirements, participant consent, age eligibility and payment terms before work begins.")
        render_engine_dashboard("AI training & data operations")
    elif page == "World Grid Marketplace":
        st.header("World Grid Marketplace")
        st.write("A marketplace operations dashboard for provider checks, customer demand, delivery, costs and receipt reconciliation.")
        st.caption("Listings remain unverified until supporting evidence is reviewed. No marketplace transaction or income is implied by a saved record.")
        render_engine_dashboard("World Grid marketplace")
    elif page == "Client Services & Contracts":
        st.header("Client Services & Contracts")
        st.write("Potential paid services: document and workflow automation, data analysis, digital operations, reporting, training and custom business support.")
        with st.form("client_contract_checklist"):
            client = st.text_input("Client / organisation")
            service = st.text_input("Service and deliverables")
            amount = st.text_input("Agreed amount and currency")
            terms = st.text_area("Written agreement, milestones, acceptance criteria and payment evidence")
            contract_submitted = st.form_submit_button("Check contract readiness")
        if contract_submitted:
            missing = [label for label,value in [("Client",client),("Service",service),("Amount",amount),("Written terms",terms)] if not value.strip()]
            if missing:
                st.warning("Not ready: provide " + ", ".join(missing) + ".")
            else:
                st.success("Checklist fields supplied. This is not legal review, client verification, or proof of payment.")
        st.subheader("Client services operating records")
        render_engine_dashboard("Client services & contracts")
    elif page == "Business Opportunity Pipeline":
        st.header("Business Opportunity Pipeline")
        st.write("Use the Scenario Lab to document a business idea, target buyer, delivery costs and demand evidence. A pipeline entry is not a customer, signed contract or revenue.")
        st.write("Recommended stages: Idea → Demand evidence → Buyer verified → Written terms → Pilot delivered → Invoice issued → Payment reconciled.")
    elif page == "Blockchain & Treasury":
        st.header("Blockchain & Treasury")
        st.write("Keep independently checked on-chain evidence separate from the internal accounting ledger and user-submitted claims.")
        st.warning("Read-only explorer API lookup is available when the relevant API key is configured. Results are evidence for review, not proof of a Cedars Empire deposit until the correct destination, token contract, amount and confirmations are reconciled.")
        chain = st.selectbox("Network for transaction lookup", ["TRON mainnet", "BNB Smart Chain mainnet"])
        tx_hash = st.text_input("Transaction hash / transaction ID")
        if tx_hash.strip():
            tx = tx_hash.strip()
            valid_hash = bool(re.fullmatch(r"(0x)?[a-fA-F0-9]{64}", tx))
            if not valid_hash:
                st.error("Transaction hash format is not recognized. Check the correct network and copy the transaction hash, not a wallet address.")
            elif chain == "TRON mainnet":
                st.markdown("[Open transaction on TRONSCAN](https://tronscan.org/#/transaction/" + tx + ")")
            else:
                st.markdown("[Open transaction on BscScan](https://bscscan.com/tx/" + (tx if tx.startswith("0x") else "0x" + tx) + ")")
            if st.button("Run read-only API lookup", key="run_chain_api_lookup"):
                try:
                    chain_result = verify_chain_transaction(chain, tx)
                    st.subheader("Read-only chain API result")
                    st.json(chain_result)
                    st.caption("Check destination, token contract, decimals, amount, success status and confirmations before recording or reconciling a receipt.")
                except Exception as exc:
                    st.error("Chain lookup unavailable: " + str(exc))
        st.subheader("What a reviewer must verify")
        st.markdown("- Correct chain and transaction success status\n- Exact destination wallet\n- Correct token contract and token standard (for token transfers)\n- Amount and decimals\n- Block confirmations and timestamp\n- No duplicate transaction hash in the internal ledger")
        st.subheader("Internal ledger versus on-chain evidence")
        st.write("Internal ledger entries are accounting records. They are not proof of an on-chain transfer. Explorer-checked entries should include the explorer URL, transaction hash, chain, destination, token contract, amount, confirmations and reviewer.")
        if IS_ADMIN:
            st.subheader("Administrator chain-review record")
            with st.form("chain_review_record_form"):
                review_chain = st.selectbox("Reviewed network", ["TRON mainnet", "BNB Smart Chain mainnet"])
                review_hash = st.text_input("Reviewed transaction hash")
                review_asset = st.text_input("Asset and token contract (if token transfer)")
                review_destination = st.text_input("Destination address")
                review_amount = st.text_input("Observed amount and unit")
                review_confirmations = st.text_input("Observed confirmations / block height")
                review_status = st.selectbox("Review status", ["Unreviewed", "Explorer inspected — pending confirmations", "Explorer inspected — successful", "Rejected / failed", "Needs further verification"])
                review_url = st.text_input("Explorer URL (evidence)")
                review_notes = st.text_area("Reviewer notes / reconciliation reference")
                save_review = st.form_submit_button("Save internal chain-review record")
            if save_review:
                expected_prefix = "https://tronscan.org/" if review_chain == "TRON mainnet" else "https://bscscan.com/"
                if not re.fullmatch(r"(0x)?[a-fA-F0-9]{64}", review_hash.strip()):
                    st.error("Enter a transaction hash in the expected format.")
                elif not review_url.strip().startswith(expected_prefix):
                    st.error("Use the matching official explorer URL for the selected network.")
                elif not review_destination.strip() or not review_amount.strip():
                    st.error("Destination and observed amount are required.")
                else:
                    db_exec("INSERT INTO engine_records (id,engine_name,record_type,title,counterparty,amount,currency,verification_status,evidence_ref,notes,owner_email,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), "Blockchain & Treasury", "Chain review", review_hash.strip(), review_destination.strip(), review_amount.strip(), review_asset.strip() or "Not specified", review_status, review_url.strip(), "Network: " + review_chain + "; confirmations/block: " + review_confirmations.strip() + "; " + review_notes.strip(), USER_EMAIL, now_iso()))
                    record_event(USER_EMAIL, "blockchain_review_record_created", review_chain + " / " + review_status)
                    st.success("Internal review record saved. It is not a direct API verification or blockchain transaction.")
                    st.rerun()
        else:
            st.info("Only administrators can create internal chain-review records.")
        chain_reviews = db_all("SELECT title AS transaction_hash,counterparty AS destination,amount,currency AS asset,verification_status AS review_status,evidence_ref AS explorer_url,notes,created_at FROM engine_records WHERE engine_name=? ORDER BY created_at DESC", ("Blockchain & Treasury",))
        if chain_reviews:
            st.subheader("Recorded chain reviews — internal records")
            render_bank_table(pd.DataFrame(chain_reviews), use_container_width=True, hide_index=True)
    elif page == "Business Reports":
        st.header("Business Reports")
        st.write("Operational reports distinguish evidence-reviewed records from pending items, estimates and user-entered claims.")
        records = db_all("SELECT engine_name,record_type,title,counterparty,amount,currency,verification_status,evidence_ref,owner_email,created_at FROM engine_records WHERE engine_name<>? ORDER BY created_at DESC", ("Staking & Compounding",))
        frame = pd.DataFrame(records)
        verified_count = sum(1 for row in records if row["verification_status"] == "Admin reviewed — verified")
        pending_receipts = sum(1 for row in records if row["record_type"] == "Receipt / settlement" and row["verification_status"] != "Admin reviewed — verified")
        cols = st.columns(3)
        cols[0].metric("Operating records", len(records))
        cols[1].metric("Admin-reviewed records", verified_count)
        cols[2].metric("Receipt records pending review", pending_receipts)
        st.info("These counts are internal workflow indicators, not a verified revenue total or a live treasury balance. Amounts are not aggregated across currencies, and only reconciled source receipts should be reported as actual income.")
        if records:
            st.subheader("Business evidence register")
            render_bank_table(frame, use_container_width=True, hide_index=True)
            download_gate("business evidence report", frame.to_csv(index=False), "cedars_empire_business_evidence.csv", "text/csv", "business_evidence_report")
        else:
            st.info("No business evidence records have been entered yet.")
        deposits = db_all("SELECT asset,network,amount,status,created_at,updated_at FROM deposit_intents WHERE user_email=? ORDER BY created_at DESC", (USER_EMAIL,))
        withdrawals = db_all("SELECT asset,network,amount,status,created_at,updated_at FROM withdrawal_requests WHERE user_email=? ORDER BY created_at DESC", (USER_EMAIL,))
        st.subheader("My treasury request status")
        st.write("Deposit claims")
        if deposits: render_bank_table(pd.DataFrame(deposits), use_container_width=True, hide_index=True)
        else: st.caption("No deposit claims submitted.")
        st.write("Withdrawal requests")
        if withdrawals: render_bank_table(pd.DataFrame(withdrawals), use_container_width=True, hide_index=True)
        else: st.caption("No withdrawal requests submitted.")
        st.warning("Automated report delivery requires a persistent scheduler and approved delivery credentials; it is not active in this deployment.")
    elif page == "Executive Command Center":
        if not IS_ADMIN:
            st.error("Administrator access required.")
        else:
            st.header("Executive Command Center")
            st.write("Admin-only oversight for business operations. Financial records must be evidence-backed; no simulated balance or revenue is shown.")

            # Grid terminal board: operational health is deliberately separate from revenue.
            # No live health probes are configured yet, so never imply a grid is working or failed.
            st.subheader("Grid Operations Terminal")
            st.caption("Blinking yellow = Ready / health probe not connected. Green Working and blue Error will be used only after a real, defined operational check reports that state. These indicators are not payment or revenue evidence.")
            grid_terminals = [
                ("NeuroWave + Health", "Wellbeing education and workshops"),
                ("EchoMap + Mobility", "Licensed audio and mobility services"),
                ("BioLoop + Finance", "SME financial operations and data quality"),
                ("DreamGrid + Education", "Courses and institutional learning"),
                ("EmoFlux + Shelter", "Accommodation and property services"),
                ("IdeaForge + Data", "Research, data cleaning and AI labeling"),
                ("QuantumLeap + Energy", "Solar+ assessments and energy efficiency"),
                ("Cleaning Grid", "Cleaning and property turnover"),
                ("Shelter & Accommodation Grid", "Accommodation and shelter referrals"),
                ("Energy & Utilities Grid", "Energy and utility services"),
                ("AI Training & Data Operations", "Contracted data tasks and quality review"),
                ("World Grid Marketplace", "Provider discovery and service listings"),
                ("Client Services & Contracts", "Client scopes, delivery and agreements"),
                ("Business Opportunity Pipeline", "Leads, eligibility and proposal tracking"),
            ]
            st.markdown("""
            <style>
            @keyframes cedars-ready-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .28; } }
            .cedars-terminal-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; margin:8px 0 18px 0; }
            .cedars-terminal { border:1px solid rgba(150,150,150,.38); border-radius:10px; padding:13px; background:rgba(120,120,120,.06); min-height:105px; }
            .cedars-terminal-title { font-weight:650; margin-bottom:5px; }
            .cedars-terminal-detail { font-size:13px; opacity:.82; min-height:34px; }
            .cedars-terminal-status { font-size:12px; margin-top:9px; font-weight:650; }
            .cedars-terminal-light { display:inline-block; width:10px; height:10px; border-radius:50%; background:#eab308; margin-right:7px; animation:cedars-ready-pulse 1.2s infinite; box-shadow:0 0 7px rgba(234,179,8,.45); }
            </style>
            """, unsafe_allow_html=True)
            terminal_html = ['<div class="cedars-terminal-grid">']
            for grid_name, grid_detail in grid_terminals:
                safe_name = (grid_name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
                safe_detail = (grid_detail.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
                terminal_html.append(
                    '<div class="cedars-terminal"><div class="cedars-terminal-title">' + safe_name +
                    '</div><div class="cedars-terminal-detail">' + safe_detail +
                    '</div><div class="cedars-terminal-status"><span class="cedars-terminal-light"></span>READY · probe not connected</div></div>'
                )
            terminal_html.append('</div>')
            st.markdown("".join(terminal_html), unsafe_allow_html=True)

            # Money-flow lights are based only on admin-entered reconciled ledger records.
            # They are not live chain attestations; references and supporting evidence must be checked.
            money_rows = db_all(
                "SELECT entry_type,amount,currency,source,reference,notes,created_at FROM treasury_ledger ORDER BY created_at DESC"
            )
            incoming_rows = [r for r in money_rows if r["entry_type"] == "Verified income received" and (r.get("reference") or "").strip() and (r.get("notes") or "").strip()]
            outgoing_rows = [r for r in money_rows if r["entry_type"] == "Verified payment sent" and (r.get("reference") or "").strip() and (r.get("notes") or "").strip()]
            st.subheader("Real-money flow indicators")
            money_cols = st.columns(2)
            with money_cols[0]:
                st.markdown("### 🟢 Real Money In" if incoming_rows else "### 🟡 Real Money In")
                st.metric("Evidence-complete incoming entries", len(incoming_rows))
                if incoming_rows:
                    by_currency = {}
                    for row in incoming_rows:
                        by_currency[row["currency"]] = by_currency.get(row["currency"], 0) + float(row["amount"])
                    st.write("Amounts by currency: " + " · ".join(f"{currency} {amount:,.8g}" for currency, amount in sorted(by_currency.items())))
                else:
                    st.caption("Ready — no evidence-complete incoming receipt is recorded.")
            with money_cols[1]:
                st.markdown("### 🟢 Real Money Out" if outgoing_rows else "### 🟡 Real Money Out")
                st.metric("Evidence-complete outgoing entries", len(outgoing_rows))
                if outgoing_rows:
                    by_currency = {}
                    for row in outgoing_rows:
                        by_currency[row["currency"]] = by_currency.get(row["currency"], 0) + float(row["amount"])
                    st.write("Amounts by currency: " + " · ".join(f"{currency} {amount:,.8g}" for currency, amount in sorted(by_currency.items())))
                else:
                    st.caption("Ready — no evidence-complete outgoing payment is recorded.")
            st.caption("These lights reflect internal ledger entries with a transaction/reference and reconciliation note. They do not independently verify blockchain settlement; use Blockchain & Treasury to inspect and reconcile the source transaction.")
            st.subheader("Treasury destination controls")
            st.warning("Only enable deposit instructions after independently verifying each address, token contract and network and recording the approval evidence.")
            settings_now = {row["setting_key"]: row["setting_value"] for row in db_all("SELECT setting_key,setting_value FROM app_settings")}
            with st.form("treasury_destination_settings"):
                tron_addr = st.text_input("TRON deposit address", value=settings_now.get("tron_deposit_address", ""))
                bnb_addr = st.text_input("BNB Smart Chain deposit address", value=settings_now.get("bnb_deposit_address", ""))
                tigers_contract = st.text_input("TIGERS token contract address", value=settings_now.get("tigers_token_contract", ""))
                tigers_network = st.selectbox("TIGERS token network", ["Not configured", "TRON mainnet", "BNB Smart Chain mainnet"], index=["Not configured", "TRON mainnet", "BNB Smart Chain mainnet"].index(settings_now.get("tigers_network", "Not configured")) if settings_now.get("tigers_network", "Not configured") in ["Not configured", "TRON mainnet", "BNB Smart Chain mainnet"] else 0)
                destinations_verified = st.checkbox("I independently verified the destinations and exact network/token contracts", value=settings_now.get("deposit_destinations_verified") == "true")
                deposit_enabled = st.checkbox("Formally enable deposit instructions", value=settings_now.get("deposit_enabled") == "true")
                save_destinations = st.form_submit_button("Save treasury destination controls")
            if save_destinations:
                valid_tron = not tron_addr.strip() or (tron_addr.strip().startswith("T") and len(tron_addr.strip()) == 34)
                valid_bnb = not bnb_addr.strip() or (re.fullmatch(r"0x[a-fA-F0-9]{40}", bnb_addr.strip()) is not None)
                if not valid_tron or not valid_bnb:
                    st.error("Address format check failed. Format checks do not prove ownership or legitimacy.")
                elif deposit_enabled and (not destinations_verified or not (tron_addr.strip() or bnb_addr.strip())):
                    st.error("Cannot enable deposits without verified destinations and at least one configured address.")
                else:
                    for sk, sv in [("tron_deposit_address",tron_addr.strip()),("bnb_deposit_address",bnb_addr.strip()),("tigers_token_contract",tigers_contract.strip()),("tigers_network","" if tigers_network == "Not configured" else tigers_network),("deposit_destinations_verified","true" if destinations_verified else "false"),("deposit_enabled","true" if deposit_enabled else "false")]:
                        db_exec("INSERT INTO app_settings (setting_key,setting_value,updated_by,updated_at) VALUES (?,?,?,?) ON CONFLICT (setting_key) DO UPDATE SET setting_value=excluded.setting_value,updated_by=excluded.updated_by,updated_at=excluded.updated_at", (sk, sv, USER_EMAIL, now_iso()))
                    record_event(USER_EMAIL, "treasury_destination_settings_updated", "Deposits enabled=" + str(deposit_enabled))
                    st.success("Treasury settings saved. This control does not replace independent verification, legal review or custody controls.")
                    st.rerun()
            st.subheader("Business engine evidence review")
            engine_queue = db_all("SELECT id,engine_name,record_type,title,counterparty,amount,currency,verification_status,evidence_ref,notes,owner_email,created_at FROM engine_records WHERE engine_name<>? ORDER BY created_at DESC LIMIT 500", ("Staking & Compounding",))
            if engine_queue:
                render_bank_table(pd.DataFrame(engine_queue), use_container_width=True, hide_index=True)
                for item in engine_queue:
                    with st.container(border=True):
                        st.write(f"{item['engine_name']} · {item['record_type']} · {item['title']} · {item['verification_status']}")
                        st.caption("Owner: " + item["owner_email"] + " | Evidence: " + (item["evidence_ref"] or "not supplied"))
                        review_status = st.selectbox("Administrator evidence decision", ["Unverified","Evidence submitted","Pending administrator review","Admin reviewed — verified","Rejected"], key="engine_review_" + item["id"])
                        if st.button("Save evidence decision", key="save_engine_review_" + item["id"]):
                            db_exec("UPDATE engine_records SET verification_status=? WHERE id=?", (review_status, item["id"]))
                            record_event(USER_EMAIL, "business_evidence_reviewed", item["id"] + " -> " + review_status)
                            st.rerun()
            else:
                st.info("No business engine records awaiting review.")
            st.caption("Use the verified status only after checking the source evidence. This review status remains an internal record and is not an on-chain API attestation.")
            st.subheader("Deposit reconciliation queue")
            deposit_queue = db_all("SELECT id,user_email,asset,network,amount,tx_hash,status,created_at FROM deposit_intents ORDER BY created_at DESC")
            if deposit_queue:
                render_bank_table(pd.DataFrame(deposit_queue), use_container_width=True, hide_index=True)
                for item in deposit_queue:
                    with st.container(border=True):
                        st.write(f"{item['user_email']} · {item['amount'] or 'Amount pending'} {item['asset']} · {item['network']} · {item['status']}")
                        dep_status = st.selectbox("Deposit review status", ["Pending verification","Explorer checked — pending confirmations","Confirmed on-chain","Rejected","Needs more information"], key="dep_status_" + item["id"])
                        if st.button("Save deposit review", key="save_dep_" + item["id"]):
                            db_exec("UPDATE deposit_intents SET status=?,updated_at=? WHERE id=?", (dep_status, now_iso(), item["id"]))
                            record_event(USER_EMAIL, "deposit_claim_status_updated", item["id"] + " -> " + dep_status)
                            st.rerun()
                st.caption("The status is an internal review record. Mark a transaction confirmed only after checking the correct chain explorer, token contract, destination, amount and confirmations.")
            else:
                st.info("No deposit claims awaiting review.")
            st.subheader("KYC and withdrawal review queues")
            kyc_queue = db_all("SELECT id,user_email,legal_name,country,verification_provider,provider_reference,status,created_at FROM kyc_requests ORDER BY created_at DESC")
            for item in kyc_queue:
                with st.container(border=True):
                    st.write(item["user_email"] + " · " + item["legal_name"] + " · " + item["country"] + " · " + item["status"])
                    kyc_options = ["Pending review","Verification required","Verified","Rejected"]
                    new_kyc_status = st.selectbox("KYC review status", kyc_options, index=kyc_options.index(item["status"]) if item["status"] in kyc_options else 0, key="admin_kyc_" + item["id"])
                    kyc_note = st.text_input("KYC evidence / reviewer note", key="admin_kyc_note_" + item["id"])
                    if st.button("Save KYC review", key="save_admin_kyc_" + item["id"]):
                        db_exec("UPDATE kyc_requests SET status=?,reviewer_email=?,review_note=?,updated_at=? WHERE id=?", (new_kyc_status, USER_EMAIL, kyc_note.strip(), now_iso(), item["id"]))
                        record_event(USER_EMAIL, "kyc_status_updated", item["id"] + " -> " + new_kyc_status)
                        st.rerun()
            withdrawal_queue = db_all("SELECT id,user_email,amount,asset,network,destination_address,status,tx_hash,admin_note,created_at FROM withdrawal_requests ORDER BY created_at DESC")
            for item in withdrawal_queue:
                with st.container(border=True):
                    st.write(f"{item['user_email']} · {item['amount']} {item['asset']} · {item['network']} · {item['status']}")
                    st.caption("Destination: " + item["destination_address"])
                    wopts = ["Pending eligibility and approval","Approved for manual processing","Rejected","Broadcast — hash required","Confirmed on-chain","Failed","Cancelled"]
                    wstatus = st.selectbox("Withdrawal status", wopts, key="admin_w_status_" + item["id"])
                    whash = st.text_input("Transaction hash", value=item["tx_hash"] or "", key="admin_w_hash_" + item["id"])
                    wnote = st.text_input("Withdrawal review note", value=item["admin_note"] or "", key="admin_w_note_" + item["id"])
                    if st.button("Save withdrawal review", key="save_admin_w_" + item["id"]):
                        if wstatus in ["Broadcast — hash required","Confirmed on-chain"] and not whash.strip():
                            st.error("A transaction hash is required before marking a withdrawal broadcast or confirmed.")
                        else:
                            db_exec("UPDATE withdrawal_requests SET status=?,tx_hash=?,admin_note=?,updated_at=? WHERE id=?", (wstatus, whash.strip() or None, wnote.strip(), now_iso(), item["id"]))
                            record_event(USER_EMAIL, "withdrawal_status_updated", item["id"] + " -> " + wstatus)
                            st.rerun()
            st.subheader("Branding and page media")
            st.caption("Upload an official logo and optional image for each business page. Uploads are stored in the configured application database. For persistence across redeployments, configure DATABASE_URL to a durable database.")
            current_settings = {row["setting_key"]: row["setting_value"] for row in db_all("SELECT setting_key,setting_value FROM app_settings")}
            with st.form("cedars_media_uploads"):
                logo_upload = st.file_uploader("Official Cedars Empire logo", type=["png","jpg","jpeg","webp"], key="ce_admin_logo_upload")
                page_choice = st.selectbox("Page to update with a photo/banner", [p for p in pages if p not in ("Executive Command Center",)])
                page_upload = st.file_uploader("Page photo / banner", type=["png","jpg","jpeg","webp"], key="ce_admin_page_upload")
                remove_page_image = st.checkbox("Remove the selected page image")
                media_submit = st.form_submit_button("Save media updates")
            if media_submit:
                saved = []
                errors = []
                if logo_upload is not None:
                    raw = logo_upload.getvalue()
                    if len(raw) > 4 * 1024 * 1024:
                        errors.append("Logo exceeds 4 MB.")
                    else:
                        try:
                            from PIL import Image
                            Image.open(io.BytesIO(raw)).verify()
                            import base64
                            db_exec("INSERT INTO app_settings (setting_key,setting_value,updated_by,updated_at) VALUES (?,?,?,?) ON CONFLICT (setting_key) DO UPDATE SET setting_value=excluded.setting_value,updated_by=excluded.updated_by,updated_at=excluded.updated_at",
                                    ("site_logo", base64.b64encode(raw).decode("ascii"), USER_EMAIL, now_iso()))
                            saved.append("logo")
                        except Exception:
                            errors.append("Logo is not a valid supported image.")
                key = "page_image:" + page_choice
                if page_upload is not None:
                    raw = page_upload.getvalue()
                    if len(raw) > 4 * 1024 * 1024:
                        errors.append("Page image exceeds 4 MB.")
                    else:
                        try:
                            from PIL import Image
                            Image.open(io.BytesIO(raw)).verify()
                            import base64
                            db_exec("INSERT INTO app_settings (setting_key,setting_value,updated_by,updated_at) VALUES (?,?,?,?) ON CONFLICT (setting_key) DO UPDATE SET setting_value=excluded.setting_value,updated_by=excluded.updated_by,updated_at=excluded.updated_at",
                                    (key, base64.b64encode(raw).decode("ascii"), USER_EMAIL, now_iso()))
                            saved.append("image for " + page_choice)
                        except Exception:
                            errors.append("Page image is not a valid supported image.")
                if remove_page_image:
                    db_exec("DELETE FROM app_settings WHERE setting_key=?", (key,))
                    saved.append("removed image for " + page_choice)
                if saved:
                    record_event(USER_EMAIL, "admin_media_updated", ", ".join(saved))
                    st.success("Saved: " + ", ".join(saved) + ". Navigate to the target page to preview.")
                for err in errors: st.error(err)
            st.subheader("Current media")
            current_settings = {row["setting_key"]: row["setting_value"] for row in db_all("SELECT setting_key,setting_value FROM app_settings")}
            if current_settings.get("site_logo"):
                st.image(io.BytesIO(__import__("base64").b64decode(current_settings["site_logo"])), caption="Current site logo", width=220)
            for setting_key, encoded in current_settings.items():
                if setting_key.startswith("page_image:"):
                    st.caption("Page image: " + setting_key.split(":",1)[1])
            st.subheader("Available integrity checks")
            st.write("- Verify contracts and supplier agreements")
            st.write("- Reconcile receipts against source transaction records")
            st.write("- Separate pipeline estimates from realized income")
            st.write("- Review failed or pending integrations")
    elif page == "Deposit & Packages":
        render_deposit_page(st, USER_EMAIL, db_all, db_exec, db_connect, bool(DATABASE_URL),
            TREASURY_ADDRESS, BNB_TREASURY_ADDRESS,
            setting("HH_ENABLE_BSC_PEGGED_USDT", "false").lower() in {"1", "true", "yes", "on"},
            setting("BSC_USDT_CONTRACT", "0x55d398326f99059ff775485246999027B3197955"),
            setting("BSC_RPC_URL", "https://bsc-dataseed.bnbchain.org"),
            setting("TRONGRID_API_KEY", setting("TRON_PRO_API_KEY", "")), now_iso, record_event)
    elif page == "Withdraw / Cash Out":
        kyc_gate_rows = db_all("SELECT status,verification_provider,provider_reference FROM kyc_requests WHERE user_email=? ORDER BY created_at DESC", (USER_EMAIL,))
        kyc_gate_ok = bool(kyc_gate_rows and kyc_gate_rows[0].get("status") == "Verified" and kyc_gate_rows[0].get("verification_provider") and kyc_gate_rows[0].get("provider_reference"))
        if not kyc_gate_ok:
            st.error("Cash-out is locked until an administrator verifies your KYC request and provider reference.")
        else:
            render_cashout_page(st, USER_EMAIL, db_all, db_exec, db_connect, bool(DATABASE_URL),
                TREASURY_ADDRESS, BNB_TREASURY_ADDRESS,
                setting("HH_ENABLE_BSC_PEGGED_USDT", "false").lower() in {"1", "true", "yes", "on"},
                setting("BSC_USDT_CONTRACT", "0x55d398326f99059ff775485246999027B3197955"),
                setting("BSC_RPC_URL", "https://bsc-dataseed.bnbchain.org"),
                setting("TRONGRID_API_KEY", setting("TRON_PRO_API_KEY", "")), now_iso, record_event)
    elif page == "Payment Operations" and IS_ADMIN:
        st.caption("Do not mark this request paid here; verify settlement on-chain.")
        render_payment_ops_page(st, USER_EMAIL, db_all, db_exec, db_connect, bool(DATABASE_URL), IS_ADMIN,
            TREASURY_ADDRESS, BNB_TREASURY_ADDRESS,
            setting("BSC_USDT_CONTRACT", "0x55d398326f99059ff775485246999027B3197955"),
            setting("BSC_RPC_URL", "https://bsc-dataseed.bnbchain.org"),
            setting("TRONGRID_API_KEY", setting("TRON_PRO_API_KEY", "")), now_iso, record_event)
    elif page == "Payments & Treasury":
        render_user_treasury_overview_page(st, USER_EMAIL, db_all, db_exec, bool(DATABASE_URL), now_iso)
    elif page == "Treasury Management":
        if not IS_ADMIN:
            st.error("Administrator access required.")
        else:
            from cedars_treasury_model import render_treasury_management
            render_treasury_management(db_all, db_exec, record_event, USER_EMAIL, bool(DATABASE_URL))
    st.stop()

# Legacy NGO operations handlers are intentionally unreachable from the business-only navigation.
# Shared working grids and calendar controls are available throughout the authenticated workspace.
render_action_grid(page, USER_EMAIL, db_all, db_exec, record_event)
if page != "Calendar & Events":
    render_calendar(USER_EMAIL, IS_ADMIN, db_all, db_exec, record_event, full_page=False)

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
        render_bank_table(pd.DataFrame([{ "Task": t["title"], "Status": t["status"], "Priority": t["priority"], "Due": t["due_date"] or "—", "Last updated": t["updated_at"] } for t in tasks[:8]]), use_container_width=True, hide_index=True)
    st.subheader("Transparency and readiness")
    st.info("Cedars Empire independently owns and maintains this workspace and its proprietary readiness framework. Use the exact eligibility rules, evaluation criteria and reporting instructions in each opportunity or agreement when preparing an application.")

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
        render_bank_table(tdf, use_container_width=True, hide_index=True)
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
                    render_document_exports("AI opportunity review", st.session_state["ai_opportunity_result"], "ai_opportunity_review", record_event, USER_EMAIL)
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
                render_document_exports("Opportunity source extract", txt, "source_extract", record_event, USER_EMAIL)
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
        brief = f"""CEDARS EMPIRE — {dtype.upper()} DRAFTING BRIEF\n\nTitle: {title or '[INPUT REQUIRED]'}\nApplicant: {applicant or '[INPUT REQUIRED]'}\nFunder/programme: {donor or '[INPUT REQUIRED]'}\nBudget: {budget or '[Confirm if applicable]'}\n\nPROBLEM / MOTIVATION\n{problem or '[NEEDS APPLICANT INPUT]'}\n\nOBJECTIVES / EXPECTED RESULTS\n{objective or '[NEEDS APPLICANT INPUT]'}\n\nAPPROACH / ACTIVITIES\n{approach or '[NEEDS APPLICANT INPUT]'}\n\nVERIFIED EVIDENCE\n{evidence or '[NEEDS VERIFIED EVIDENCE]'}\n\nDONOR INSTRUCTIONS\n{instructions or '[Paste exact official instructions]'}\n\nSOURCE EXTRACT FOR HUMAN REVIEW\n{source[:12000]}\n\nDRAFTING CONTROLS\n- Do not invent statistics, experience, partners, credentials, citations or commitments.\n- Mark missing facts [NEEDS APPLICANT INPUT].\n- Mirror mandatory donor headings and evaluation criteria from the original call.\n- Align problem -> objectives -> activities -> outputs -> outcomes -> indicators -> budget.\n- Consider safeguarding, inclusion, gender, disability, climate/environmental risks and data protection where relevant.\n- Obtain technical, finance and authorized management review before submission.\n"""
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
        render_document_exports("Proposal drafting brief", st.session_state["proposal_draft"], "proposal_brief", record_event, USER_EMAIL)

# -----------------------------------------------------------------------------
# CV / Resume Studio
# -----------------------------------------------------------------------------
elif page == "Live Studio":
    st.header("Live Studio")
    st.empty()
    lt1,lt2,lt3=st.tabs(["Schedule", "Join / attendance", "Session register"])
    with lt1:
        with st.form("live_studio_session_form"):
            a,b=st.columns(2)
            session_title=a.text_input("Session title",placeholder="Proposal clinic")
            session_date=b.date_input("Date",value=date.today())
            c,d=st.columns(2)
            session_time=c.time_input("Start time")
            duration=d.selectbox("Duration",[30,45,60,90,120],index=2,format_func=lambda x:f"{x} minutes")
            meeting_url=st.text_input("Video meeting link",placeholder="https://…")
            invitees=st.text_input("Invitees (comma-separated emails)",placeholder="name@example.org, team@example.org")
            agenda=st.text_input("Agenda (optional)")
            consent=st.checkbox("I will notify participants before recording or sharing transcripts.")
            save_session=st.form_submit_button("Save session",type="primary",use_container_width=True)
        if save_session:
            if not session_title.strip(): st.error("Enter a session title.")
            elif meeting_url.strip() and not safe_url(meeting_url.strip()): st.error("Meeting link must use http:// or https://.")
            else:
                detail=f"Scheduled: {session_date.isoformat()} {session_time.strftime('%H:%M')}; duration={duration}m; invitees={invitees.strip()}; agenda={agenda.strip()}; recording_notice={'confirmed' if consent else 'not confirmed'}; meeting_url={meeting_url.strip()}"
                sid=str(uuid.uuid5(uuid.NAMESPACE_URL,session_title.strip().lower()+"|"+session_date.isoformat()+"|"+session_time.strftime('%H:%M')+"|"+(meeting_url.strip() or "no-link")))
                db_exec("INSERT INTO attendance (id,session_id,event_name,user_email,followup_optin,created_at,details) VALUES (?,?,?,?,?,?,?)",(str(uuid.uuid4()),sid,session_title.strip(),USER_EMAIL,0,now_iso(),detail))
                record_event(USER_EMAIL,"live_studio_session_scheduled",session_title.strip())
                st.success("Session saved to the register.")
                if invitees.strip():
                    import urllib.parse
                    body = f"You are invited to {session_title.strip()} on {session_date.isoformat()} at {session_time.strftime('%H:%M')}.\nDuration: {duration} minutes\nMeeting: {meeting_url.strip()}\nAgenda: {agenda.strip()}"
                    mailto="mailto:"+urllib.parse.quote(invitees.strip(),safe="@,;.")+"?subject="+urllib.parse.quote("Invitation: "+session_title.strip())+"&body="+urllib.parse.quote(body)
                    st.link_button("Open email invitation draft",mailto,use_container_width=True)
                if meeting_url.strip(): st.link_button("Open meeting",meeting_url.strip(),use_container_width=True)
                st.rerun()
    with lt2:
        with st.form("live_studio_attendance_form"):
            attendance_title=st.text_input("Session title")
            attendance_optin=st.checkbox("I agree that my attendance is recorded.",value=True)
            join_submit=st.form_submit_button("Record my attendance",type="primary",use_container_width=True)
        if join_submit:
            if not attendance_title.strip(): st.error("Enter the session title.")
            elif not attendance_optin: st.warning("Attendance was not recorded.")
            else:
                db_exec("INSERT INTO attendance (id,session_id,event_name,user_email,followup_optin,created_at,details) VALUES (?,?,?,?,?,?,?)",(str(uuid.uuid4()),str(uuid.uuid5(uuid.NAMESPACE_URL,attendance_title.strip().lower())),attendance_title.strip(),USER_EMAIL,0,now_iso(),"Attendance recorded by signed-in user"))
                record_event(USER_EMAIL,"live_studio_attendance_saved",attendance_title.strip()); st.success("Attendance recorded."); st.rerun()
    with lt3:
        sessions=db_all("SELECT event_name,user_email,created_at,details FROM attendance WHERE user_email=? ORDER BY created_at DESC",(USER_EMAIL,))
        if sessions:
            sdf=pd.DataFrame(sessions).rename(columns={"event_name":"Session","user_email":"Owner","created_at":"Recorded","details":"Details"})
            render_bank_table(sdf,use_container_width=True,hide_index=True)
            download_gate("Download register",sdf.to_csv(index=False),"humanity_horizons_live_studio.csv","text/csv","hh_live_register")
        else: st.info("No records.")
    st.empty()

elif page == "CV / Resume Studio":
    st.header("CV / Resume Studio — future-skills aware")
    st.write("Build an ATS-readable CV/resume and skills development plan from your own verified experience. This is a structured drafting tool, not a connected AI model or a guarantee of employment.")
    st.caption("The Cedars Empire Future Workforce Readiness Matrix helps users assess and build practical skills in AI/data literacy, cybersecurity, technology, creative thinking, adaptability, lifelong learning, leadership, analytical thinking and environmental stewardship. These are development prompts, not a guarantee of employment.")
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
        st.info("Skill gap matching is based on the text you typed and is approximate. A missing keyword does not necessarily mean you lack the skill. Use the Cedars Empire Future Workforce Readiness Matrix as a development guide, then validate the role-specific requirements in the actual vacancy.")

# -----------------------------------------------------------------------------
# SDG Navigator
# -----------------------------------------------------------------------------
elif page == "SDG Navigator":
    st.header("Sustainable Development Goals navigator")
    st.write("Explore all 17 Sustainable Development Goals and five representative problem areas each goal helps address. Cedars Empire uses this goal map as a planning taxonomy. The problem areas are issue prompts, not exhaustive target lists or a claim that one goal alone solves them.")
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
    st.caption("Cedars Empire SDG Navigator — maintained as part of the Cedars Empire planning framework.")

# -----------------------------------------------------------------------------
# Noticeboard: member-submitted/imported listing queue; admin moderation required
# -----------------------------------------------------------------------------
elif page == "Noticeboard":
    st.header("Cedars Empire noticeboard")
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
                render_bank_table(im_df.head(50), use_container_width=True)
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
    st.header("Cedars Empire Standards & Impact Workspace")
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
        render_bank_table(ldf, use_container_width=True, hide_index=True)
        download_gate("results framework CSV", ldf.to_csv(index=False), "humanity_horizons_results_framework.csv", "text/csv", "logframe")
    with tabs[1]:
        datafile = st.file_uploader("Upload monitoring dataset CSV/XLSX", type=["csv", "xlsx"], key="meal_dataset")
        gate = upload_rights_gate("meal_data", "monitoring dataset")
        if datafile:
            if gate:
                try:
                    ddf = pd.read_csv(datafile) if datafile.name.lower().endswith(".csv") else pd.read_excel(datafile)
                    st.session_state["monitoring_df"] = ddf
                    render_bank_table(ddf, use_container_width=True)
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
            render_bank_table(qdf, use_container_width=True)
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
        render_bank_table(risk_df, use_container_width=True, hide_index=True)
        download_gate("risk register CSV", risk_df.to_csv(index=False), "humanity_horizons_risk_register.csv", "text/csv", "risk_export")
    with tabs[3]:
        st.markdown("**Cedars Empire Institutional Readiness & Impact Framework (HH-IRIF)**\n\nThis proprietary self-assessment organizes practical controls for governance, eligibility, results management, evaluation and learning, financial stewardship, procurement, safeguarding, fraud prevention, data protection, inclusion, environmental/social risk, feedback, partner management, records and sustainability. It is a planning and evidence-checking tool—not a legal opinion, external certification or guarantee. Use the requirements in the specific opportunity, contract and applicable law as the final checklist.")
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
        st.markdown("**Framework owner:** Cedars Empire.\n\n**Review areas:** results chain and indicators; learning and data quality; financial controls; procurement and conflicts of interest; safeguarding and safe complaints handling; prevention of exploitation and abuse; privacy and confidentiality; inclusion and accessibility; environmental and social risk; partner oversight; records, accountability and sustainability. Administrators should review and version this framework periodically against current institutional good practice and the exact requirements contained in each opportunity or agreement.")
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
            report = f"""CEDARS EMPIRE — M&E REPORT (DRAFT)\nOrganization: {org}\nProject: {project}\nDonor: {donor}\nPeriod: {reporting_period}\nGenerated: {date.today().isoformat()}\n\n1. SUMMARY\n{summary or '[Add evidence-based summary]'}\n\n2. INDICATOR PERFORMANCE\n{chr(10).join(metric_lines) or '[No indicator data supplied — insert verified results]'}\n\n3. ACHIEVEMENTS\n{achievements or '[Add verified achievements and source references]'}\n\n4. CHALLENGES AND DEVIATIONS\n{challenges or '[Explain shortfalls, causes and adaptive action]'}\n\n5. CORRECTIVE ACTIONS AND LESSONS\n{actions or '[Action, owner and due date]'}\n\n6. NEXT PERIOD PRIORITIES\n{nextsteps or '[Planned activities and milestones]'}\n\n7. DATA QUALITY, SAFEGUARDING AND LIMITATIONS\nVerify source records, calculations, denominators and disaggregation. Document gaps and revisions. Do not place identifiable safeguarding reports in a general donor narrative; use authorized confidential channels.\n\nDRAFT ONLY: Human review required. The software does not independently verify supplied inputs.\n"""
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
    st.subheader("Change password")
    with st.form("change_password_form"):
        current_password = st.text_input("Current password", type="password")
        new_password = st.text_input("New password (at least 10 characters)", type="password")
        confirm_new_password = st.text_input("Confirm new password", type="password")
        change_password_submit = st.form_submit_button("Change password", type="primary")
    if change_password_submit:
        if not verify_password(current_password, me["password_salt"], me["password_hash"]):
            st.error("Current password is incorrect.")
        elif len(new_password) < 10:
            st.error("New password must contain at least 10 characters.")
        elif new_password != confirm_new_password:
            st.error("New passwords do not match.")
        elif verify_password(new_password, me["password_salt"], me["password_hash"]):
            st.error("Choose a password different from your current password.")
        else:
            new_salt, new_hash = pw_hash(new_password)
            db_exec("UPDATE users SET password_salt=?,password_hash=? WHERE email=?", (new_salt, new_hash, USER_EMAIL))
            record_event(USER_EMAIL, "password_changed")
            send_email(USER_EMAIL, "Your Cedars Empire password was changed", f"Hello {USER_NAME},\n\nYour Cedars Empire password was changed at {now_iso()}. If you did not make this change, contact platform support immediately.\n\nCedars Empire")
            st.success("Password changed successfully. A security email will be sent if email delivery is configured.")
            st.rerun()
    st.subheader("Email notifications")
    st.empty()
    prefs_rows = db_all("SELECT * FROM notification_preferences WHERE user_email=?", (USER_EMAIL,))
    prefs = prefs_rows[0] if prefs_rows else {"email_security": 1, "email_task_updates": 1, "email_earnings": 1, "email_opportunities": 0, "email_product_updates": 0}
    with st.form("email_notification_preferences_form"):
        pref_security = st.checkbox("Account security alerts (recommended)", value=bool(prefs.get("email_security", 1)))
        pref_tasks = st.checkbox("Task assignments and review updates", value=bool(prefs.get("email_task_updates", 1)))
        pref_earnings = st.checkbox("Earnings, rewards, and withdrawal updates", value=bool(prefs.get("email_earnings", 1)))
        pref_opportunities = st.checkbox("New opportunities and relevant B2B work", value=bool(prefs.get("email_opportunities", 0)))
        pref_product = st.checkbox("Product news and feature announcements", value=bool(prefs.get("email_product_updates", 0)))
        save_email_preferences = st.form_submit_button("Save email preferences")
    if save_email_preferences:
        db_exec("INSERT INTO notification_preferences (user_email,email_security,email_task_updates,email_earnings,email_opportunities,email_product_updates,updated_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT(user_email) DO UPDATE SET email_security=excluded.email_security,email_task_updates=excluded.email_task_updates,email_earnings=excluded.email_earnings,email_opportunities=excluded.email_opportunities,email_product_updates=excluded.email_product_updates,updated_at=excluded.updated_at", (USER_EMAIL, int(pref_security), int(pref_tasks), int(pref_earnings), int(pref_opportunities), int(pref_product), now_iso()))
        record_event(USER_EMAIL, "email_notification_preferences_changed")
        st.success("Email preferences saved.")
        st.rerun()
    if not email_delivery_configured():
        st.info("Email delivery not configured.")
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
    st.warning("Production hardening is incomplete: configure persistent storage, backups, access controls and recovery procedures.")
    st.empty()
    my_tasks = db_all("SELECT * FROM tasks WHERE user_email=? ORDER BY created_at", (USER_EMAIL,))
    mydf = pd.DataFrame([{ "Title": t["title"], "Description": t["description"], "Status": t["status"], "Priority": t["priority"], "Due": t["due_date"], "Created": t["created_at"] } for t in my_tasks])
    download_gate("my data export", mydf.to_csv(index=False), "my_humanity_horizons_tasks.csv", "text/csv", "my_data_export")

# -----------------------------------------------------------------------------
# Admin-published noticeboard: direct publishing path for authorized admins
# -----------------------------------------------------------------------------

elif page == "HR Department" and IS_ADMIN:
    st.title("Human Resources Department")
    st.empty()
    records = db_all("SELECT owner_email,person_name,record_type,role_title,skills,availability,start_date,status,created_at,updated_at FROM volunteer_records ORDER BY updated_at DESC")
    users = db_all("SELECT email,full_name,account_type,organization,created_at,last_login FROM users ORDER BY created_at DESC")
    active = sum(1 for r in records if r.get("status") == "Active")
    a,b,c,d = st.columns(4)
    a.metric("Registered platform users", len(users)); b.metric("HR / volunteer records", len(records)); c.metric("Active assignments", active)
    d.metric("Open recruitment / prospective", sum(1 for r in records if r.get("status") == "Prospective"))
    tab1,tab2,tab3=st.tabs(["Workforce register","Add staff / volunteer","People & development"])
    with tab1:
        st.markdown("**Current HR records**")
        if records:
            df=pd.DataFrame([{ "Name":r.get("person_name"),"Type":r.get("record_type"),"Role":r.get("role_title"),"Owner account":r.get("owner_email"),"Availability":r.get("availability"),"Start date":r.get("start_date") or "—","Status":r.get("status"),"Updated":r.get("updated_at")} for r in records])
            render_bank_table(df,use_container_width=True,hide_index=True)
            download_gate("HR workforce register",df.to_csv(index=False),"hh_hr_workforce_register.csv","text/csv","hh_hr_register")
        else: st.info("No records.")
    with tab2:
        with st.form("admin_hr_record_form"):
            name=st.text_input("Full name")
            owner=st.text_input("Owning account email",value=USER_EMAIL)
            typ=st.selectbox("Record type",["Employee","Volunteer","Consultant","Intern","Mentor"])
            role=st.text_input("Position / assignment")
            skills=st.text_area("Skills and experience")
            availability=st.selectbox("Availability",["Available","Limited","Unavailable","To be confirmed"])
            start=st.text_input("Start date (YYYY-MM-DD, optional)")
            status=st.selectbox("Status",["Prospective","Active","On hold","Completed","Archived"])
            notes=st.text_area("Operational notes (no sensitive case details)")
            save=st.form_submit_button("Save HR record",type="primary")
        if save:
            if not name.strip() or not role.strip() or not owner.strip(): st.error("Name, owning account email and role are required.")
            elif start.strip() and not re.match(r"^\d{4}-\d{2}-\d{2}$",start.strip()): st.error("Use YYYY-MM-DD for the start date.")
            else:
                db_exec("INSERT INTO volunteer_records (id,owner_email,person_name,record_type,role_title,skills,availability,start_date,status,notes,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",(str(uuid.uuid4()),owner.strip().lower(),name.strip(),typ,role.strip(),skills.strip(),availability,start.strip() or None,status,notes.strip(),now_iso(),now_iso()))
                record_event(USER_EMAIL,"admin_hr_record_created"); st.success("HR record saved."); st.rerun()
    with tab3:
        st.markdown("**Platform user directory**")
        if users: render_bank_table(pd.DataFrame([{ "Name":u.get("full_name"),"Email":u.get("email"),"Account type":u.get("account_type"),"Organization":u.get("organization") or "—","Registered":u.get("created_at"),"Last login":u.get("last_login") or "Not recorded"} for u in users]),use_container_width=True,hide_index=True)
        st.empty()

elif page == "40/60 Allocation Foundation" and IS_ADMIN:
    st.title("Cedars Empire — 40/60 Allocation Foundation")
    st.warning("Model and internal accounting register only. Posting requires evidence, a distinct second configured administrator, and explicit confirmation. Nothing is transferred.")
    with st.form("hh_4060_post_receipt"):
        c1,c2,c3=st.columns(3)
        source_ref=c1.text_input("Unique cleared receipt reference")
        currency=c2.selectbox("Currency",["USD","UGX","EUR","GBP","USDT","USDC","TRX","BNB"])
        gross=c3.text_input("Cleared gross amount")
        c4,c5,c6=st.columns(3)
        costs=c4.text_input("Deductible costs",value="0.00")
        evidence=c5.text_input("Evidence reference (statement / invoice / transaction hash)")
        approver=c6.text_input("Second administrator approver email")
        notes=st.text_area("Accounting notes")
        confirmed=st.checkbox("I confirm this receipt and its deductible costs have been independently reconciled.")
        submit=st.form_submit_button("Post balanced 40/60 allocation",type="primary")
    if submit:
        if not confirmed:
            st.error("Confirm source reconciliation before posting.")
        else:
            try:
                result=post_4060_allocation(db_connect,source_ref=source_ref,currency=currency,gross_amount=gross,
                    deductible_costs=costs,evidence_ref=evidence,approved_by=approver,entered_by=USER_EMAIL,notes=notes)
                record_event(USER_EMAIL,"revenue_allocation_posted",source_ref.strip())
                st.success("Balanced allocation recorded in the persistent internal register; no payment was sent.")
                st.json(result)
                st.rerun()
            except Exception as exc:
                st.error("Allocation not posted: "+str(exc))
    records=db_all("SELECT * FROM revenue_allocations ORDER BY created_at DESC")
    st.subheader("Allocation register")
    if records:
        df=pd.DataFrame(records); render_bank_table(df,use_container_width=True,hide_index=True)
        download_gate("40/60 allocation register",df.to_csv(index=False),"cedars_40_60_allocations.csv","text/csv","cedars_4060")
    else:
        st.info("No allocations recorded.")
    journal=db_all("SELECT allocation_id,account_code,side,amount,currency,created_at FROM revenue_allocation_journal ORDER BY created_at DESC LIMIT 1000")
    st.subheader("Double-entry journal")
    if journal: render_bank_table(pd.DataFrame(journal),use_container_width=True,hide_index=True)
    else: st.info("No journal entries recorded.")
elif page == "Finance Department" and IS_ADMIN:
    st.title("Finance Department")
    ledger=db_all("SELECT entry_type,amount,currency,source,reference,notes,entered_by,created_at FROM treasury_ledger ORDER BY created_at DESC")
    withdrawals=db_all("SELECT * FROM withdrawal_requests ORDER BY created_at DESC")
    incomes=[x for x in ledger if str(x.get("entry_type","")).lower() in ("income","receipt","revenue","deposit","grant receipt","subscription receipt")]
    expenses=[x for x in ledger if str(x.get("entry_type","")).lower() in ("expense","payment","withdrawal","cost","supplier payment","payroll payment")]
    a,b,c,d=st.columns(4); a.metric("Ledger",len(ledger)); b.metric("Income records",len(incomes)); c.metric("Expense records",len(expenses)); d.metric("Withdrawal requests",len(withdrawals))
    st.subheader("Sustainability allocation policy — proposed, not yet automated")
    p1,p2=st.columns(2)
    p1.metric("Participant pool", "40%", help="Allocated from reconciled net eligible revenue only, not gross unverified receipts.")
    p2.metric("Sustainability & operations", "60%", help="Retained for hosting, security, support, safeguarding, compliance, maintenance and reserves.")
    st.empty()
    tab1,tab2,tab3,tab4=st.tabs(["Ledger", "＋ Record", "Allocations", "Controls"])
    with tab1:
        f1,f2,f3=st.columns(3)
        type_filter=f1.selectbox("Type",["All"]+sorted({str(x.get("entry_type","")) for x in ledger}),key="fin_type_filter")
        currency_filter=f2.selectbox("Currency",["All"]+sorted({str(x.get("currency","")) for x in ledger}),key="fin_currency_filter")
        search=f3.text_input("Search source / reference",key="fin_search")
        shown=[x for x in ledger if (type_filter=="All" or x.get("entry_type")==type_filter) and (currency_filter=="All" or x.get("currency")==currency_filter) and (search.lower() in (str(x.get("source",""))+" "+str(x.get("reference",""))).lower())]
        if shown:
            df=pd.DataFrame(shown).rename(columns={"entry_type":"Type","amount":"Amount","currency":"Currency","source":"Source / payee","reference":"Reference","notes":"Notes","entered_by":"Entered by","created_at":"Date"})
            render_bank_table(df,use_container_width=True,hide_index=True)
            download_gate("Download CSV",df.to_csv(index=False),"humanity_horizons_finance_ledger.csv","text/csv","hh_finance_ledger")
        else: st.info("No records.")
        if withdrawals:
            st.markdown("**Withdrawal requests**")
            wd=pd.DataFrame(withdrawals); render_bank_table(wd,use_container_width=True,hide_index=True)
            download_gate("Download withdrawal requests",wd.to_csv(index=False),"humanity_horizons_withdrawals.csv","text/csv","hh_finance_withdrawals")
    with tab2:
        with st.form("finance_ledger_form"):
            r1,r2,r3=st.columns(3)
            kind=r1.selectbox("Transaction type",["Income","Expense","Grant receipt","Subscription receipt","Supplier payment","Payroll payment","Refund","Adjustment"])
            amount=r2.text_input("Amount",placeholder="0.00")
            currency=r3.selectbox("Currency",["UGX","USD","EUR","GBP","Other"])
            source=st.text_input("Source / payee / project")
            r4,r5=st.columns(2)
            reference=r4.text_input("Receipt / invoice / transaction reference")
            notes=r5.text_input("Note (optional)")
            submit=st.form_submit_button("Save record",type="primary",use_container_width=True)
        if submit:
            try: valid_amount=float(amount.replace(",",""))
            except Exception: valid_amount=0
            if valid_amount<=0 or not source.strip(): st.error("Enter a positive amount and source/payee.")
            else:
                db_exec("INSERT INTO treasury_ledger (id,entry_type,amount,currency,source,reference,notes,entered_by,created_at) VALUES (?,?,?,?,?,?,?,?,?)",(str(uuid.uuid4()),kind,f"{valid_amount:.2f}",currency,source.strip(),reference.strip() or None,notes.strip(),USER_EMAIL,now_iso()))
                record_event(USER_EMAIL,"finance_ledger_record_created"); st.success("Saved. Reconcile against source evidence before marking verified."); st.rerun()
    with tab3:
        allocations = db_all("SELECT * FROM revenue_allocations ORDER BY created_at DESC")
        if allocations:
            adf = pd.DataFrame(allocations)
            render_bank_table(adf, use_container_width=True, hide_index=True)
            download_gate("Download allocation register", adf.to_csv(index=False), "hh_revenue_allocations.csv", "text/csv", "hh_revenue_allocations")
        else:
            st.info("No records.")
        st.warning("Allocation posting is disabled pending reconciled receipts and tested payout controls.")
    with tab4:
        checks=["Source evidence attached","Bank/provider statement reconciled","Preparer and approver separated","Budget versus actual reviewed","Grant restrictions checked","Sensitive records access-restricted"]
        cols=st.columns(2)
        for i,item in enumerate(checks): cols[i%2].checkbox(item,key="fin_check_"+str(i))
        st.empty()

elif page == "Income & Revenue" and IS_ADMIN:
    st.title("Income & Revenue Management")
    st.empty()
    ledger=db_all("SELECT entry_type,amount,currency,source,reference,entered_by,created_at FROM treasury_ledger ORDER BY created_at DESC")
    plans=db_all("SELECT stream_name,category,status,estimated_amount,currency,updated_at FROM revenue_opportunities ORDER BY updated_at DESC")
    receipts=[r for r in ledger if str(r.get("entry_type","")).lower() in ("income","receipt","revenue","deposit","grant receipt","subscription receipt")]
    a,b,c=st.columns(3); a.metric("Recorded receipt entries",len(receipts)); b.metric("Revenue streams in planning",len(plans)); c.metric("Potential streams marked active",sum(1 for p in plans if p.get("status")=="Active"))
    st.subheader("Recorded receipts (not independently bank-verified)")
    if receipts: render_bank_table(pd.DataFrame(receipts),use_container_width=True,hide_index=True)
    else: st.info("No records.")
    st.subheader("Revenue pipeline — estimates are not income")
    if plans: render_bank_table(pd.DataFrame(plans),use_container_width=True,hide_index=True)
    else: st.info("No records.")
    st.empty()

elif page == "Admin Studio" and IS_ADMIN:
    st.title("Cedars Empire Admin Studio")
    st.empty()
    st.empty()
    ai_ready=bool(OPENAI_API_KEY)
    checks=[("AI text generation",ai_ready,"API key configured" if ai_ready else "Local structured mode; API key not configured"),("PDF/document processing",True,"PyMuPDF package available"),("Word document support",True,"python-docx package available"),("Email delivery",email_delivery_configured() and bool(SMTP_USERNAME and SMTP_PASSWORD),"SMTP credentials configured" if email_delivery_configured() and SMTP_USERNAME and SMTP_PASSWORD else "SMTP delivery not fully configured"),("Managed database",bool(DATABASE_URL),"DATABASE_URL configured" if DATABASE_URL else "SQLite fallback; hosted persistence may be temporary")]
    for label,ready,detail in checks:
        (st.success if ready else st.warning)(f"{'●' if ready else '○'} **{label}** — {detail}")
    st.subheader("Studio modules")
    modules=[("Proposal Studio","Proposal drafting and opportunity requirements"),("Opportunity Analysis","Call/TOR review and eligibility"),("CV / Resume Studio","Career documents and skills"),("SDG Navigator","SDG alignment and impact planning"),("Live Studio","Session and attendance hub"),("Report Automation","Reporting schedules and indicator records"),("Noticeboard","Opportunity and announcement management"),("B2B Collaboration","Organization collaboration")]
    for i in range(0,len(modules),2):
        x,y=st.columns(2)
        for col,(name,desc) in zip((x,y),modules[i:i+2]):
            with col:
                with st.container(border=True): st.markdown(f"**{name}**"); st.empty()
    st.empty()

elif page == "Admin Noticeboard" and IS_ADMIN:
    st.header("Admin Noticeboard Publisher")
    st.empty()
    with st.form("admin_direct_publish_form"):
        title = st.text_input("Opportunity title *")
        org = st.text_input("Publisher / organization")
        kind = st.selectbox("Opportunity type", ["Grant", "Job", "Fellowship", "Consultancy", "Tender", "Event", "Partnership", "Learning resource", "Sponsored advert"])
        country = st.text_input("Country / region")
        deadline = st.text_input("Deadline (YYYY-MM-DD or text)")
        link = st.text_input("Application / event link")
        source_url = st.text_input("Original source URL")
        description = st.text_area("Description and eligibility *", height=160)
        publish_now = st.form_submit_button("Publish opportunity", type="primary")
    if publish_now:
        if not title.strip() or not description.strip():
            st.error("Title and description are required.")
        elif link.strip() and not safe_url(link.strip()):
            st.error("The application link must be a valid HTTP(S) URL.")
        elif source_url.strip() and not safe_url(source_url.strip()):
            st.error("The source URL must be a valid HTTP(S) URL.")
        else:
            db_exec("INSERT INTO noticeboard (id,title,organization,opportunity_type,country,deadline,link,description,source_url,status,created_by,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), title.strip(), org.strip(), kind, country.strip(), deadline.strip(), link.strip(), description.strip(), source_url.strip(), "Published", USER_EMAIL, now_iso()))
            record_event(USER_EMAIL, "admin_noticeboard_published")
            st.success("Opportunity published to the public noticeboard.")
            st.rerun()
    st.subheader("Manage published listings")
    listings = db_all("SELECT * FROM noticeboard ORDER BY created_at DESC LIMIT 500")
    for item in listings:
        with st.container(border=True):
            st.markdown(f"**{item['title']}** — {item['status']}")
            st.caption(f"{item.get('organization') or 'Publisher not stated'} · {item['opportunity_type']} · {item.get('deadline') or 'No deadline'}")
            c1, c2, c3 = st.columns(3)
            if item['status'] != 'Published' and c1.button("Publish", key=f"admin_pub_{item['id']}"):
                db_exec("UPDATE noticeboard SET status=? WHERE id=?", ("Published", item['id'])); record_event(USER_EMAIL, "admin_noticeboard_republished"); st.rerun()
            if item['status'] == 'Published' and c2.button("Unpublish", key=f"admin_unpub_{item['id']}"):
                db_exec("UPDATE noticeboard SET status=? WHERE id=?", ("Archived", item['id'])); record_event(USER_EMAIL, "admin_noticeboard_unpublished"); st.rerun()
            if item['status'] != 'Deleted' and c3.button("Archive", key=f"admin_arch_{item['id']}"):
                db_exec("UPDATE noticeboard SET status=? WHERE id=?", ("Archived", item['id'])); st.rerun()

elif page == "Income Activities":
    st.header("Income-Generating Activities")
    st.empty()
    if IS_ADMIN:
        with st.expander("Create a work activity", expanded=True):
            with st.form("create_work_activity"):
                wtitle = st.text_input("Activity title *")
                wcat = st.selectbox("Work category", ["AI text evaluation", "Data annotation", "Transcription", "Translation", "Climate / education data", "Research support", "Other"])
                wdesc = st.text_area("Description *")
                welig = st.text_area("Eligibility / skills")
                winstructions = st.text_area("Instructions and quality criteria")
                wrate = st.text_input("Proposed pay per approved unit (optional)")
                wcurrency = st.selectbox("Currency", ["UGX", "USD", "EUR"])
                wcapacity = st.number_input("Number of available slots", min_value=1, max_value=10000, value=1)
                wstatus = st.selectbox("Activity status", ["Draft", "Open", "Paused", "Closed"])
                wsave = st.form_submit_button("Save activity", type="primary")
            if wsave:
                if not wtitle.strip() or not wdesc.strip(): st.error("Title and description are required.")
                else:
                    from decimal import Decimal, InvalidOperation
                    try:
                        if wrate.strip() and Decimal(wrate.strip()) < 0: raise ValueError()
                        db_exec("INSERT INTO work_activities (id,title,category,description,eligibility,instructions,rate_amount,currency,capacity,status,created_by,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                (str(uuid.uuid4()), wtitle.strip(), wcat, wdesc.strip(), welig.strip(), winstructions.strip(), wrate.strip() or None, wcurrency, int(wcapacity), wstatus, USER_EMAIL, now_iso(), now_iso()))
                        record_event(USER_EMAIL, "work_activity_created"); st.success("Activity saved."); st.rerun()
                    except Exception: st.error("Enter a valid non-negative rate, or leave the rate blank.")
    activities = db_all("SELECT * FROM work_activities ORDER BY created_at DESC")
    st.subheader("Available activities")
    for act in activities:
        if act["status"] not in ("Open", "Paused") and not IS_ADMIN: continue
        with st.container(border=True):
            st.markdown(f"**{act['title']}** · {act['category']} · {act['status']}")
            st.write(act["description"])
            if act.get("eligibility"): st.caption("Eligibility: " + act["eligibility"])
            if act.get("instructions"): st.write("**Instructions / quality criteria:** " + act["instructions"])
            st.caption(f"Proposed rate: {act.get('rate_amount') or 'Not set'} {act.get('currency') or ''}. A rate is not a guarantee of available work or payment.")
            if act["status"] == "Open":
                with st.form(f"submit_work_{act['id']}"):
                    submission = st.text_area("Your work / submission notes", key=f"submission_{act['id']}")
                    submit_work = st.form_submit_button("Submit for review")
                if submit_work:
                    if not submission.strip(): st.error("Add your submission before sending.")
                    else:
                        db_exec("INSERT INTO work_submissions (id,activity_id,user_email,submission_text,status,reviewer_note,approved_amount,currency,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                (str(uuid.uuid4()), act["id"], USER_EMAIL, submission.strip(), "Submitted", None, None, act["currency"], now_iso(), now_iso()))
                        record_event(USER_EMAIL, "work_submission_created"); st.success("Submission recorded for review."); st.rerun()
    if IS_ADMIN:
        st.subheader("Review work submissions")
        submissions = db_all("SELECT s.*, a.title AS activity_title FROM work_submissions s LEFT JOIN work_activities a ON s.activity_id=a.id ORDER BY s.created_at DESC")
    else:
        st.subheader("My submissions")
        submissions = db_all("SELECT s.*, a.title AS activity_title FROM work_submissions s LEFT JOIN work_activities a ON s.activity_id=a.id WHERE s.user_email=? ORDER BY s.created_at DESC", (USER_EMAIL,))
    for sub in submissions:
        with st.container(border=True):
            st.markdown(f"**{sub.get('activity_title') or 'Activity'}** · {sub['status']}")
            st.write(sub["submission_text"])
            if sub.get("reviewer_note"): st.caption("Reviewer note: " + sub["reviewer_note"])
            if IS_ADMIN and sub["status"] == "Submitted":
                with st.form(f"review_{sub['id']}"):
                    decision = st.selectbox("Review decision", ["Approved", "Needs revision", "Rejected"], key=f"decision_{sub['id']}")
                    approved_amount = st.text_input("Approved amount (optional)", key=f"amount_{sub['id']}")
                    review_note = st.text_area("Review note", key=f"note_{sub['id']}")
                    review_submit = st.form_submit_button("Save review")
                if review_submit:
                    from decimal import Decimal
                    try:
                        if approved_amount.strip() and Decimal(approved_amount.strip()) < 0: raise ValueError()
                        db_exec("UPDATE work_submissions SET status=?, reviewer_note=?, approved_amount=?, currency=?, updated_at=? WHERE id=?",
                                (decision, review_note.strip(), approved_amount.strip() or None, sub.get("currency") or "UGX", now_iso(), sub["id"]))
                        record_event(USER_EMAIL, "work_submission_reviewed"); st.rerun()
                    except Exception: st.error("Approved amount must be a non-negative number.")

elif page == "My Work & Wallet":
    st.header("My Work & Wallet")
    work=db_all("SELECT title,description,status,priority,due_date,created_at,updated_at FROM tasks WHERE user_email=? ORDER BY updated_at DESC",(USER_EMAIL,))
    submissions=db_all("SELECT activity_id,submission_text,status,reviewer_note,approved_amount,currency,created_at,updated_at FROM work_submissions WHERE user_email=? ORDER BY created_at DESC",(USER_EMAIL,))
    a,b,c=st.columns(3)
    a.metric("My tasks",len(work))
    b.metric("Work submissions",len(submissions))
    c.metric("Approved records",sum(1 for row in submissions if row.get("status")=="Approved" and row.get("approved_amount")))
    st.info("An approved work submission is not proof of payment. Confirm actual settlement separately; no earnings or payout is guaranteed.")
    if work:
        render_bank_table(pd.DataFrame(work),use_container_width=True,hide_index=True)
    else: st.info("No tasks recorded.")
    if submissions:
        render_bank_table(pd.DataFrame(submissions),use_container_width=True,hide_index=True)
    else: st.info("No income activities submitted.")
    render_user_treasury_overview_page(st,USER_EMAIL,db_all,db_exec,bool(DATABASE_URL),now_iso)
elif page == "Branding Settings" and IS_ADMIN:
    st.header("Branding Settings")
    with st.form("brand_logo_form"):
        logo_file=st.file_uploader("Official Cedars Empire logo (PNG, JPG or WEBP)",type=["png","jpg","jpeg","webp"])
        save_logo=st.form_submit_button("Save logo",type="primary")
    if save_logo:
        if logo_file is None:
            st.error("Choose a logo file first.")
        elif len(logo_file.getvalue()) > 4*1024*1024:
            st.error("Logo must be no larger than 4 MB.")
        else:
            try:
                from PIL import Image
                Image.open(io.BytesIO(logo_file.getvalue())).verify()
                encoded=__import__("base64").b64encode(logo_file.getvalue()).decode("ascii")
                db_exec("INSERT INTO app_settings (setting_key,setting_value,updated_by,updated_at) VALUES (?,?,?,?) ON CONFLICT (setting_key) DO UPDATE SET setting_value=excluded.setting_value,updated_by=excluded.updated_by,updated_at=excluded.updated_at",
                        ("site_logo",encoded,USER_EMAIL,now_iso()))
                record_event(USER_EMAIL,"branding_logo_updated")
                st.success("Logo saved to the persistent app database.")
                st.rerun()
            except Exception:
                st.error("The selected logo is not a valid supported image.")
    current=db_all("SELECT setting_value,updated_at FROM app_settings WHERE setting_key=?",("site_logo",))
    if current:
        st.caption("A custom logo is stored in the database.")
        try: st.image(io.BytesIO(__import__("base64").b64decode(current[0]["setting_value"])),width=260)
        except Exception: st.warning("The saved logo could not be previewed.")
    else:
        st.info("No custom logo saved.")
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
        render_bank_table(pd.DataFrame(db_all("SELECT title,opportunity_type,organization,status,deadline,source_url,created_at FROM noticeboard ORDER BY created_at DESC")), use_container_width=True, hide_index=True)
    with admin_tabs[1]:
        fb = db_all("SELECT * FROM feedback ORDER BY created_at DESC")
        st.write(f"Feedback and collaboration records: {len(fb)}")
        if fb:
            fdf = pd.DataFrame([{k: v for k, v in f.items() if k != "id"} for f in fb])
            render_bank_table(fdf, use_container_width=True, hide_index=True)
            download_gate("feedback export", fdf.to_csv(index=False), "humanity_horizons_feedback_admin.csv", "text/csv", "admin_feedback")
    with admin_tabs[2]:
        attendance = db_all("SELECT event_name,user_email,followup_optin,created_at,details FROM attendance ORDER BY created_at DESC LIMIT 1000")
        st.subheader("Attendance events (latest 1,000)")
        render_bank_table(pd.DataFrame(attendance), use_container_width=True, hide_index=True)
        st.caption("Anonymous session attendance has no visitor identity. Identifiable attendee emails are stored only for users who opted in to follow-up.")
        tasks_admin = db_all("SELECT user_email,title,status,priority,due_date,created_at,updated_at,completed_at FROM tasks ORDER BY updated_at DESC LIMIT 500")
        st.subheader("Task progress across users (latest 500)")
        render_bank_table(pd.DataFrame(tasks_admin), use_container_width=True, hide_index=True)
    with admin_tabs[3]:
        st.subheader("Treasury reference and verified ledger")
        st.write("This is an administrative finance area. It does not perform blockchain transactions or automate withdrawals. Treasury details are shown only to configured administrators in the app UI.")
        st.write(f"**TRON treasury (TRON mainnet):** `{TREASURY_ADDRESS}`")
        st.write("**Network/asset intended:** TRON mainnet · USDT (TRC-20) / TRX.")
        st.write(f"**BNB Smart Chain treasury:** `{BNB_TREASURY_ADDRESS}`")
        st.write("**Network/asset intended:** BNB Smart Chain mainnet · verify the official USDT token contract and network before sending. Do not enter private keys or seed phrases here.")
        st.info("Automatic withdrawals require a reviewed custody/signing model, key management, transaction simulation, address/network checks, limits, approvals, reconciliation, monitoring, tax/accounting controls and applicable legal review. No funds are moved by this prototype.")
        with st.form("ledger_form"):
            entry_type = st.selectbox("Entry type", ["Verified income received", "Verified payment sent", "Verified expense", "Refund", "Adjustment"])
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
                if entry_type in ("Verified income received", "Verified payment sent") and (not tx_ref.strip() or not notes.strip()):
                    raise ValueError("For incoming receipts and outgoing payments, provide the transaction reference and reconciliation/evidence note.")
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
            render_bank_table(led_df, use_container_width=True, hide_index=True)
            download_gate("treasury ledger export", led_df.to_csv(index=False), "humanity_horizons_treasury_ledger.csv", "text/csv", "treasury_ledger_export")
        else:
            st.info("No verified ledger entries recorded yet.")

# -----------------------------------------------------------------------------
# HR & Volunteer Hub — user-scoped records, admin visibility
# -----------------------------------------------------------------------------
elif page == "HR & Volunteers":
    st.header("HR & Volunteer Hub")
    st.caption("Track staff, volunteers, skills and availability. Store only information you are authorized to manage; avoid sensitive personal data.")
    with st.form("volunteer_record_form"):
        person_name = st.text_input("Person name")
        record_type = st.selectbox("Record type", ["Volunteer", "Staff", "Consultant", "Intern", "Mentor"])
        role_title = st.text_input("Role / assignment")
        skills = st.text_area("Skills and experience summary")
        availability = st.selectbox("Availability", ["Available", "Limited", "Unavailable", "To be confirmed"])
        start_date = st.text_input("Start date (YYYY-MM-DD, optional)", placeholder="2026-11-01")
        status = st.selectbox("Record status", ["Prospective", "Active", "On hold", "Completed", "Archived"])
        notes = st.text_area("Operational notes (no sensitive case details)")
        save_person = st.form_submit_button("Save HR / volunteer record", type="primary")
    if save_person:
        if not person_name.strip() or not role_title.strip():
            st.error("Person name and role are required.")
        elif start_date.strip() and not re.match(r"^\d{4}-\d{2}-\d{2}$", start_date.strip()):
            st.error("Use YYYY-MM-DD for the start date.")
        else:
            db_exec("INSERT INTO volunteer_records (id,owner_email,person_name,record_type,role_title,skills,availability,start_date,status,notes,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), USER_EMAIL, person_name.strip(), record_type, role_title.strip(), skills.strip(), availability, start_date.strip() or None, status, notes.strip(), now_iso(), now_iso()))
            record_event(USER_EMAIL, "hr_volunteer_record_created")
            st.success("Record saved.")
            st.rerun()
    records = db_all("SELECT * FROM volunteer_records WHERE owner_email=? ORDER BY updated_at DESC", (USER_EMAIL,))
    st.subheader("My HR / volunteer records")
    if records:
        frame = pd.DataFrame([{ "Name": r["person_name"], "Type": r["record_type"], "Role": r["role_title"], "Skills": r["skills"], "Availability": r["availability"], "Start date": r["start_date"], "Status": r["status"], "Notes": r["notes"], "Updated": r["updated_at"] } for r in records])
        render_bank_table(frame, use_container_width=True, hide_index=True)
        download_gate("HR / volunteer records", frame.to_csv(index=False), "humanity_horizons_hr_volunteers.csv", "text/csv", "hr_volunteers")
    else:
        st.info("No HR or volunteer records yet.")
    if IS_ADMIN:
        st.subheader("All platform records — administrator only")
        all_records = db_all("SELECT owner_email,person_name,record_type,role_title,availability,status,created_at,updated_at FROM volunteer_records ORDER BY updated_at DESC LIMIT 1000")
        render_bank_table(pd.DataFrame(all_records), use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Revenue opportunity tracker — ideas are not recognized revenue
# -----------------------------------------------------------------------------
elif page == "Revenue & Sustainability":
    st.header("Revenue & Sustainability Planner")
    st.warning("These are potential income opportunities, not guaranteed earnings or recorded income. Record actual receipts only in the verified treasury ledger after reconciliation.")
    revenue_streams = [
        ("Proposal development support", "Professional services"), ("Call / TOR analysis service", "Professional services"),
        ("Grant readiness assessment", "Professional services"), ("Logframe and theory-of-change support", "Professional services"),
        ("M&E framework design", "Professional services"), ("Donor report preparation", "Professional services"),
        ("Budget and budget-narrative support", "Professional services"), ("CV and resume coaching", "Career services"),
        ("Cover-letter and application coaching", "Career services"), ("Interview preparation workshops", "Training"),
        ("Grant-writing training", "Training"), ("M&E training", "Training"),
        ("Digital-skills training", "Training"), ("NGO governance workshops", "Training"),
        ("Safeguarding and accountability training", "Training"), ("Institutional subscriptions", "Subscription"),
        ("NGO team subscriptions", "Subscription"), ("University / research institution licences", "Institutional licence"),
        ("White-label platform licence", "Licensing"), ("API access for approved clients", "Licensing"),
        ("Custom integrations", "Technology services"), ("Data migration and setup", "Technology services"),
        ("Custom dashboard development", "Technology services"), ("Impact measurement services", "Research and evaluation"),
        ("Independent evaluation coordination", "Research and evaluation"), ("Baseline / endline study support", "Research and evaluation"),
        ("Survey and data-collection tools", "Research and evaluation"), ("Research synthesis and briefs", "Research and evaluation"),
        ("Translation and localization", "Content services"), ("Accessible document formatting", "Content services"),
        ("Annual report design and production", "Content services"), ("Infographic and visual reporting", "Content services"),
        ("Approved template library", "Digital products"), ("Online courses", "Digital products"),
        ("Paid certification preparation", "Training"), ("Sponsored opportunity placements", "Sponsorship"),
        ("Clearly labelled sponsored newsletters", "Sponsorship"), ("Corporate impact reporting", "Professional services"),
        ("ESG / sustainability reporting support", "Professional services"), ("Talent and consultant matching", "Marketplace"),
        ("Service-provider directory listings", "Marketplace"), ("Event and conference partnerships", "Partnerships"),
        ("Institutional workshops", "Partnerships"), ("Research collaborations", "Partnerships"),
        ("Donations with transparent accounting", "Donations"), ("Grant-funded platform development", "Grants"),
        ("Corporate sponsorship agreements", "Sponsorship"), ("Membership programme", "Membership"),
        ("Job-readiness cohort programmes", "Career services"), ("Licensed sector-specific knowledge packs", "Digital products")
    ]
    st.metric("Potential streams in the planning catalogue", len(revenue_streams))
    with st.expander("Browse all 50 potential revenue streams"):
        render_bank_table(pd.DataFrame([{"Potential stream": n, "Category": c, "Status": "Idea only"} for n,c in revenue_streams]), use_container_width=True, hide_index=True)
    with st.form("revenue_opportunity_form"):
        stream_name = st.selectbox("Opportunity", [n for n,_ in revenue_streams])
        category = dict(revenue_streams)[stream_name]
        stage = st.selectbox("Planning status", ["Idea", "Validation needed", "Business case drafted", "Approved to test", "Pilot", "Active", "Paused", "Rejected"])
        estimate = st.text_input("Estimated amount (optional; planning estimate only)")
        currency = st.selectbox("Currency", ["UGX", "USD", "EUR", "GBP", "Other"])
        assumptions = st.text_area("Assumptions, costs, risks and evidence")
        next_step = st.text_input("Next action / owner")
        save_stream = st.form_submit_button("Save revenue opportunity")
    if save_stream:
        db_exec("INSERT INTO revenue_opportunities (id,owner_email,stream_name,category,status,estimated_amount,currency,assumptions,next_step,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), USER_EMAIL, stream_name, category, stage, estimate.strip() or None, currency, assumptions.strip(), next_step.strip(), now_iso(), now_iso()))
        record_event(USER_EMAIL, "revenue_opportunity_created")
        st.success("Planning opportunity saved; no income has been recorded.")
        st.rerun()
    own = db_all("SELECT stream_name,category,status,estimated_amount,currency,assumptions,next_step,updated_at FROM revenue_opportunities WHERE owner_email=? ORDER BY updated_at DESC", (USER_EMAIL,))
    st.subheader("My sustainability pipeline")
    if own:
        rdf = pd.DataFrame(own)
        render_bank_table(rdf, use_container_width=True, hide_index=True)
        download_gate("revenue opportunity plan", rdf.to_csv(index=False), "humanity_horizons_revenue_plan.csv", "text/csv", "revenue_plan")
    else:
        st.info("No revenue opportunities have been saved yet.")

# -----------------------------------------------------------------------------
# Report schedule and indicator register — delivery requires external scheduler
# -----------------------------------------------------------------------------
elif page == "Report Automation":
    st.header("Reporting Calendar & Automation")
    st.caption("Configure reporting requirements and maintain a persistent indicator register. This page records schedules; an external scheduled job and email credentials are required to execute and deliver reports automatically.")
    with st.form("indicator_form"):
        project_name = st.text_input("Project / programme")
        indicator_name = st.text_input("Indicator name")
        indicator_type = st.selectbox("Indicator type", ["Output", "Outcome", "Impact", "Process", "Safeguarding / accountability", "Financial"])
        baseline = st.text_input("Baseline")
        target = st.text_input("Target")
        current_value = st.text_input("Current value / latest result")
        unit = st.text_input("Unit (e.g. people, %, UGX)")
        disaggregation = st.text_input("Disaggregation (e.g. sex, age, disability, location; where safe and lawful)")
        data_source = st.text_input("Data source / verification evidence")
        reporting_frequency = st.selectbox("Indicator reporting frequency", ["Monthly", "Quarterly", "Semi-annual", "Annual", "Ad hoc"])
        reporting_period = st.text_input("Reporting period (e.g. 2026-Q4)")
        indicator_notes = st.text_area("Limitations, assumptions and data-quality notes")
        save_indicator = st.form_submit_button("Save indicator record", type="primary")
    if save_indicator:
        if not project_name.strip() or not indicator_name.strip():
            st.error("Project and indicator name are required.")
        else:
            db_exec("INSERT INTO project_indicators (id,owner_email,project_name,indicator_name,indicator_type,baseline,target,current_value,unit,disaggregation,data_source,reporting_frequency,reporting_period,notes,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), USER_EMAIL, project_name.strip(), indicator_name.strip(), indicator_type, baseline.strip(), target.strip(), current_value.strip(), unit.strip(), disaggregation.strip(), data_source.strip(), reporting_frequency, reporting_period.strip(), indicator_notes.strip(), now_iso(), now_iso()))
            record_event(USER_EMAIL, "project_indicator_created")
            st.success("Indicator record saved.")
            st.rerun()
    indicators = db_all("SELECT * FROM project_indicators WHERE owner_email=? ORDER BY updated_at DESC", (USER_EMAIL,))
    st.subheader("Indicator register")
    if indicators:
        idf = pd.DataFrame([{ "Project": x["project_name"], "Indicator": x["indicator_name"], "Type": x["indicator_type"], "Baseline": x["baseline"], "Target": x["target"], "Current value": x["current_value"], "Unit": x["unit"], "Disaggregation": x["disaggregation"], "Data source": x["data_source"], "Frequency": x["reporting_frequency"], "Period": x["reporting_period"], "Notes": x["notes"] } for x in indicators])
        render_bank_table(idf, use_container_width=True, hide_index=True)
        download_gate("indicator register", idf.to_csv(index=False), "humanity_horizons_indicator_register.csv", "text/csv", "indicator_register")
        report = ["CEDARS EMPIRE — INDICATOR / M&E WORKING REPORT", f"Generated: {now_iso()}", "", "IMPORTANT: Validate every value against source records before external submission.", ""]
        for row in indicators:
            report += [f"Project: {row['project_name']}", f"Indicator: {row['indicator_name']} ({row['indicator_type']})", f"Baseline: {row['baseline'] or 'Not recorded'} | Target: {row['target'] or 'Not recorded'} | Current: {row['current_value'] or 'Not recorded'} {row['unit'] or ''}", f"Period: {row['reporting_period'] or 'Not recorded'} | Frequency: {row['reporting_frequency']}", f"Data source: {row['data_source'] or 'Not recorded'}", f"Disaggregation: {row['disaggregation'] or 'Not recorded'}", f"Data-quality notes: {row['notes'] or 'None recorded'}", ""]
        report_text = "\n".join(report)
        st.text_area("Generated working M&E report", report_text, height=280)
        download_gate("indicator / M&E working report", report_text, "humanity_horizons_me_working_report.txt", key="indicator_me_report")
    else:
        st.info("Add indicator records to begin generating a report from stored project data.")
    st.divider()
    st.subheader("Report delivery schedules")
    with st.form("report_schedule_form"):
        report_name = st.selectbox("Report to schedule", ["Platform operations summary", "Project indicator / M&E report", "Donor feedback summary", "Treasury reconciliation summary"])
        frequency = st.selectbox("Frequency", ["Monthly", "Quarterly", "Semi-annual", "Annual"])
        run_day = st.number_input("Day of month (monthly schedules; default 25)", min_value=1, max_value=28, value=25)
        recipient_email = st.text_input("Delivery recipient email (optional until mail is configured)")
        timezone_name = st.selectbox("Reporting timezone", ["Africa/Kampala", "UTC", "Africa/Nairobi", "Europe/London"])
        enabled = st.checkbox("Enable this schedule", value=True)
        save_schedule = st.form_submit_button("Save report schedule")
    if save_schedule:
        if recipient_email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", recipient_email.strip()):
            st.error("Enter a valid recipient email or leave it blank.")
        else:
            db_exec("INSERT INTO report_schedules (id,owner_email,report_name,frequency,run_day,recipient_email,enabled,timezone_name,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), USER_EMAIL, report_name, frequency, int(run_day), recipient_email.strip() or None, int(enabled), timezone_name, now_iso(), now_iso()))
            record_event(USER_EMAIL, "report_schedule_created")
            st.success("Schedule saved. It will not send automatically until a scheduler and delivery provider are configured.")
            st.rerun()
    schedules = db_all("SELECT report_name,frequency,run_day,recipient_email,enabled,timezone_name,created_at FROM report_schedules WHERE owner_email=? ORDER BY created_at DESC", (USER_EMAIL,))
    if schedules:
        render_bank_table(pd.DataFrame(schedules), use_container_width=True, hide_index=True)
    if IS_ADMIN:
        st.subheader("Platform-wide schedules (administrator only)")
        admin_schedules = db_all("SELECT owner_email,report_name,frequency,run_day,recipient_email,enabled,timezone_name,created_at FROM report_schedules ORDER BY created_at DESC LIMIT 500")
        render_bank_table(pd.DataFrame(admin_schedules), use_container_width=True, hide_index=True)

elif page == "Calendar & Events":
    render_calendar(USER_EMAIL, IS_ADMIN, db_all, db_exec, record_event, full_page=True)

# Unknown page guard
else:
    st.error("This administrator page is not available for the current account.")

st.divider()

