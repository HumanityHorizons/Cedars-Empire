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
if not LOGO.exists():
    LOGO = APP_DIR / "humanity_horizons_logo.jpg"
LOCAL_DB = Path(os.getenv("HH_DATA_DIR", tempfile.gettempdir())) / "humanity_horizons.db"
PBKDF2_ITERATIONS = 310_000

st.set_page_config(page_title="Humanity Horizons 360", page_icon="🌍", layout="wide")
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
# Public TRON receiving address requested for the Humanity Horizons treasury display.
# This is a public wallet address, NOT a private key. The app does not execute transfers.
TREASURY_ADDRESS = "TE26B7zQjMbahYAWcxEsSPC6aZEr2Hcz1u"
OPENAI_API_KEY = setting("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = setting("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_optional_ai(prompt: str) -> str | None:
