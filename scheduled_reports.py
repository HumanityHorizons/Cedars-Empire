"""Scheduled Humanity Horizons operations / M&E reports. Requires managed PostgreSQL and SMTP secrets."""
from __future__ import annotations
import os, smtplib, ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from zoneinfo import ZoneInfo
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER).strip()
ADMIN_EMAILS = {x.strip().lower() for x in os.environ.get("ADMIN_EMAILS", "").split(",") if x.strip()}


def send_email(to: str, subject: str, body: str) -> None:
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_FROM]):
        raise RuntimeError("Email secrets missing. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD and SMTP_FROM in GitHub Actions secrets.")
    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)


def due(schedule: dict, now_utc: datetime) -> bool:
    try:
        local = now_utc.astimezone(ZoneInfo(schedule.get("timezone_name") or "UTC"))
    except Exception:
        local = now_utc
    if local.day != int(schedule.get("run_day") or 25):
        return False
    freq = (schedule.get("frequency") or "Monthly").lower()
    if freq == "monthly": return True
    if freq == "quarterly": return local.month in (3, 6, 9, 12)
    if freq in ("semi-annual", "semiannual"): return local.month in (6, 12)
    if freq == "annual": return local.month == 12
    return False


def build_report(conn, name: str, owner_email: str) -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    lines = ["HUMANITY HORIZONS 360", name, f"Generated at {now}", "", "Internal working report. Verify underlying evidence before external submission.", ""]
    with conn.cursor() as cur:
        if name == "Project indicator / M&E report":
            cur.execute("SELECT project_name,indicator_name,indicator_type,baseline,target,current_value,unit,disaggregation,data_source,reporting_frequency,reporting_period,notes FROM project_indicators ORDER BY project_name,indicator_name")
            rows = cur.fetchall()
            lines.append(f"Indicator records: {len(rows)}")
            for r in rows:
                lines.extend([f"Project: {r['project_name']} | Indicator: {r['indicator_name']} ({r['indicator_type']})", f"Baseline: {r['baseline'] or 'Not recorded'} | Target: {r['target'] or 'Not recorded'} | Current: {r['current_value'] or 'Not recorded'} {r['unit'] or ''}", f"Period: {r['reporting_period'] or 'Not recorded'} | Frequency: {r['reporting_frequency']}", f"Data source: {r['data_source'] or 'Not recorded'} | Disaggregation: {r['disaggregation'] or 'Not recorded'}", f"Notes: {r['notes'] or 'None recorded'}", ""])
        elif name == "Donor feedback summary":
            cur.execute("SELECT category, status, COUNT(*) AS total FROM feedback GROUP BY category,status ORDER BY category,status")
            rows = cur.fetchall()
            lines.append("Feedback counts by category and status:")
            lines.extend([f"- {r['category']} / {r['status']}: {r['total']}" for r in rows] or ["- No feedback records."])
        elif name == "Treasury reconciliation summary":
            if owner_email.lower() not in ADMIN_EMAILS:
                return "Treasury report not generated: recipient is not configured in ADMIN_EMAILS."
            cur.execute("SELECT entry_type,currency,COUNT(*) AS entries FROM treasury_ledger GROUP BY entry_type,currency ORDER BY currency,entry_type")
            rows = cur.fetchall()
            lines.append("Ledger entry counts (this is not a blockchain balance):")
            lines.extend([f"- {r['entry_type']} / {r['currency']}: {r['entries']} records" for r in rows] or ["- No ledger entries."])
        else:
            cur.execute("SELECT COUNT(*) AS total FROM users")
            users = cur.fetchone()["total"]
            cur.execute("SELECT status,COUNT(*) AS total FROM tasks GROUP BY status ORDER BY status")
            tasks = cur.fetchall()
            cur.execute("SELECT status,COUNT(*) AS total FROM noticeboard GROUP BY status ORDER BY status")
            listings = cur.fetchall()
            cur.execute("SELECT COUNT(*) AS total FROM project_indicators")
            indicators = cur.fetchone()["total"]
            lines.extend([f"Registered accounts: {users}", f"Stored indicator records: {indicators}", "Task counts by status:"])
            lines.extend([f"- {r['status']}: {r['total']}" for r in tasks] or ["- No tasks."])
            lines.append("Noticeboard listings by status:")
            lines.extend([f"- {r['status']}: {r['total']}" for r in listings] or ["- No listings."])
    return "\n".join(lines)


def main() -> None:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing. Configure a managed PostgreSQL database before enabling scheduled reports.")
    now = datetime.now(timezone.utc)
    with psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=15) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id,owner_email,report_name,frequency,run_day,recipient_email,enabled,timezone_name,last_run_at FROM report_schedules WHERE enabled=1 AND recipient_email IS NOT NULL AND recipient_email <> ''")
            schedules = cur.fetchall()
        sent = 0
        for schedule in schedules:
            if not due(schedule, now):
                continue
            body = build_report(conn, schedule["report_name"], schedule["owner_email"])
            send_email(schedule["recipient_email"], f"Humanity Horizons scheduled report: {schedule['report_name']}", body)
            with conn.cursor() as cur:
                cur.execute("UPDATE report_schedules SET last_run_at=%s, updated_at=%s WHERE id=%s", (now.replace(microsecond=0).isoformat(), now.replace(microsecond=0).isoformat(), schedule["id"]))
            conn.commit()
            sent += 1
        print(f"Scheduled report job complete. Emails sent: {sent}")

if __name__ == "__main__":
    main()
