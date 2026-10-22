"""Scheduled, idempotent incoming-deposit reconciler for the live deployment.

Requirements:
- DATABASE_URL must point to the same managed PostgreSQL database as Streamlit.
- TRON transfers are read from the official Tether TRC-20 contract on TronGrid with only_confirmed=true.
- BSC transfers are read from the configured RPC at least 20 blocks behind the head and only when explicitly enabled.
- Only consented, open payment intents matching network + token contract + treasury + source address + exact amount are credited.
- Ambiguous/unmatched transfers are stored for retry/review. No private keys, signing, or payouts are performed.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse, parse_qs

import requests

from hh_real_payments import (
    DEFAULT_BSC_PEG_USDT_CONTRACT,
    DEFAULT_BSC_RPC,
    DEFAULT_TRONGRID,
    TRON_USDT_CONTRACT,
    TRANSFER_TOPIC,
    PaymentError,
    _decimal,
    _execute,
    _get_account,
    _ledger,
    _rows,
    _set_account,
    _ensure_grid_gate_in_transaction,
    _verify_bsc,
    _verify_tron,
    ensure_payment_tables,
    sync_grid_deployment_queue,
)

TRON_TREASURY = os.getenv("TRON_TREASURY_ADDRESS", "TE26B7zQjMbahYAWcxEsSPC6aZEr2Hcz1u").strip()
BSC_TREASURY = os.getenv("BSC_TREASURY_ADDRESS", "0x0d4c2B95e8FB7Be3DB9953bAcEf3A4Be643bA77B").strip()
TRONGRID_API_KEY = os.getenv("TRONGRID_API_KEY", "").strip()
BSC_RPC_URL = os.getenv("BSC_RPC_URL", DEFAULT_BSC_RPC).strip() or DEFAULT_BSC_RPC
BSC_TOKEN = os.getenv("BSC_USDT_CONTRACT", DEFAULT_BSC_PEG_USDT_CONTRACT).strip() or DEFAULT_BSC_PEG_USDT_CONTRACT
ENABLE_BSC = os.getenv("HH_ENABLE_BSC_PEGGED_USDT", "false").strip().lower() in {"1", "true", "yes", "on"}
TRON_API_BASE = os.getenv("TRONGRID_API_URL", DEFAULT_TRONGRID).rstrip("/")
PAGE_SIZE = 200
MAX_TRON_PAGES_PER_RUN = 250
MAX_EVENTS_PER_RUN = 10000
TRON_OVERLAP_MS = 30 * 60 * 1000
BSC_CONFIRMATIONS = 20


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _to_epoch_ms(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, datetime):
        stamp = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return int(stamp.timestamp() * 1000)
    text = str(value).strip()
    try:
        stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return int(stamp.timestamp() * 1000)
    except Exception:
        return 0


def db_connect():
    import psycopg
    from psycopg.rows import dict_row
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is missing. Reconciler is fail-closed.")
    return psycopg.connect(url, row_factory=dict_row, connect_timeout=15), "postgres"


def db_exec(sql: str, params: tuple = ()) -> int:
    conn, kind = db_connect()
    try:
        cur = conn.cursor()
        cur.execute(sql.replace("?", "%s"), params)
        n = cur.rowcount
        conn.commit()
        return n
    finally:
        conn.close()


def db_all(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    conn, kind = db_connect()
    try:
        cur = conn.cursor()
        cur.execute(sql.replace("?", "%s"), params)
        return [dict(x) for x in cur.fetchall()]
    finally:
        conn.close()


def ensure_reconciler_tables() -> None:
    db_exec(
        """CREATE TABLE IF NOT EXISTS hh_deposit_reconciler_state (
            network TEXT PRIMARY KEY,
            last_scanned_block BIGINT,
            last_scanned_timestamp BIGINT,
            scan_cursor TEXT,
            updated_at TEXT NOT NULL
        )"""
    )
    db_exec(
        """CREATE TABLE IF NOT EXISTS hh_chain_incoming_events (
            network TEXT NOT NULL,
            txid TEXT NOT NULL,
            event_key TEXT NOT NULL,
            sender_address TEXT NOT NULL,
            receiving_address TEXT NOT NULL,
            token_contract TEXT NOT NULL,
            amount TEXT NOT NULL,
            block_number BIGINT,
            block_timestamp BIGINT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Unmatched',
            payment_intent_id TEXT,
            last_error TEXT,
            detected_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(network,txid,event_key)
        )"""
    )
    db_exec("CREATE INDEX IF NOT EXISTS ix_hh_chain_event_status_time ON hh_chain_incoming_events(status,block_timestamp)")


def _get_state(network: str) -> dict[str, Any] | None:
    rows = db_all("SELECT * FROM hh_deposit_reconciler_state WHERE network=?", (network,))
    return rows[0] if rows else None


def _save_tron_state(checkpoint_ms: int, cursor: str | None) -> None:
    db_exec(
        """INSERT INTO hh_deposit_reconciler_state(network,last_scanned_block,last_scanned_timestamp,scan_cursor,updated_at)
           VALUES(?,?,?,?,?) ON CONFLICT(network) DO UPDATE SET
           last_scanned_timestamp=EXCLUDED.last_scanned_timestamp,
           scan_cursor=EXCLUDED.scan_cursor,updated_at=EXCLUDED.updated_at""",
        ("TRON-TRC20", None, checkpoint_ms, cursor, utc_now()),
    )


def _save_bsc_state(block: int) -> None:
    db_exec(
        """INSERT INTO hh_deposit_reconciler_state(network,last_scanned_block,last_scanned_timestamp,scan_cursor,updated_at)
           VALUES(?,?,?,?,?) ON CONFLICT(network) DO UPDATE SET
           last_scanned_block=EXCLUDED.last_scanned_block,
           updated_at=EXCLUDED.updated_at""",
        ("BSC-BEP20", block, None, None, utc_now()),
    )


def _event_upsert_rows(events: list[dict[str, Any]]) -> int:
    if not events:
        return 0
    conn, kind = db_connect()
    try:
        cur = conn.cursor()
        cur.executemany(
            """INSERT INTO hh_chain_incoming_events
               (network,txid,event_key,sender_address,receiving_address,token_contract,amount,
                block_number,block_timestamp,status,payment_intent_id,last_error,detected_at,updated_at)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'Unmatched',NULL,NULL,%s,%s)
               ON CONFLICT(network,txid,event_key) DO NOTHING""",
            [(
                e["network"], e["txid"], e["event_key"], e["sender_address"], e["receiving_address"],
                e["token_contract"], e["amount"], e.get("block_number"), e["block_timestamp"],
                utc_now(), utc_now()
            ) for e in events]
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def _oldest_open_tron_intent_ms() -> int:
    rows = db_all(
        "SELECT MIN(created_at) AS oldest FROM hh_payment_intents "
        "WHERE network=? AND status NOT IN ('Verified','Cancelled','Expired') AND consent_accepted=1",
        ("TRON-TRC20",)
    )
    return _to_epoch_ms(rows[0].get("oldest")) if rows and rows[0].get("oldest") else 0


def scan_tron_events() -> tuple[int, bool]:
    """Fetch confirmed Tether TRC-20 events and persist them; preserve cursor on backlog."""
    started_ms = int(time.time() * 1000)
    state = _get_state("TRON-TRC20")
    checkpoint = int(state.get("last_scanned_timestamp") or 0) if state else 0
    if not checkpoint:
        checkpoint = _oldest_open_tron_intent_ms() or (started_ms - 6 * 60 * 60 * 1000)
    floor_ms = max(0, checkpoint - TRON_OVERLAP_MS)
    url = f"{TRON_API_BASE}/v1/accounts/{TRON_TREASURY}/transactions/trc20"
    params = {
        "only_confirmed": "true",
        "contract_address": TRON_USDT_CONTRACT,
        "limit": str(PAGE_SIZE),
        "order_by": "block_timestamp,desc",
        "min_timestamp": str(floor_ms),
    }
    cursor = str(state.get("scan_cursor")) if state and state.get("scan_cursor") else ""
    if cursor:
        params["fingerprint"] = cursor
    headers = {"Accept": "application/json"}
    if TRONGRID_API_KEY:
        headers["TRON-PRO-API-KEY"] = TRONGRID_API_KEY
    collected: list[dict[str, Any]] = []
    pages = 0
    complete = False
    next_cursor: str | None = None
    while pages < MAX_TRON_PAGES_PER_RUN:
        response = requests.get(url, params=params, headers=headers, timeout=25)
        response.raise_for_status()
        body = response.json()
        rows = body.get("data") or []
        pages += 1
        stamps = [int(x.get("block_timestamp") or 0) for x in rows]
        for item in rows:
            token = item.get("token_info") or {}
            if str(token.get("address") or "").lower() != TRON_USDT_CONTRACT.lower():
                continue
            if str(item.get("to") or "") != TRON_TREASURY:
                continue
            try:
                decimals = int(token.get("decimals", 6))
                amount = Decimal(str(item.get("value", "0"))) / (Decimal(10) ** decimals)
                txid = str(item["transaction_id"]).lower()
                sender = str(item["from"])
                ts = int(item.get("block_timestamp") or 0)
                ev_index = item.get("event_index")
                event_key = str(ev_index) if ev_index is not None else f"{ts}:{sender}:{format(amount,'f')}"
                if not txid or amount <= 0:
                    continue
                collected.append({
                    "network": "TRON-TRC20", "txid": txid, "event_key": event_key,
                    "sender_address": sender, "receiving_address": TRON_TREASURY,
                    "token_contract": TRON_USDT_CONTRACT, "amount": format(amount, "f"),
                    "block_number": None, "block_timestamp": ts,
                })
            except (KeyError, ValueError, TypeError):
                continue
        meta = body.get("meta") or {}
        next_cursor = meta.get("fingerprint")
        if not next_cursor:
            link = ((meta.get("links") or {}).get("next") or "")
            if link:
                query = parse_qs(urlparse(link).query)
                next_cursor = (query.get("fingerprint") or [None])[0]
        reached_checkpoint = bool(stamps and min(stamps) <= floor_ms)
        if reached_checkpoint or len(rows) < PAGE_SIZE:
            complete = True
            next_cursor = None
            break
        if not next_cursor:
            # Do not advance the checkpoint when pagination is unclear; it could skip transfers.
            complete = False
            break
        params["fingerprint"] = str(next_cursor)
    _event_upsert_rows(collected)
    if complete:
        _save_tron_state(started_ms, None)
    else:
        _save_tron_state(checkpoint, str(next_cursor) if next_cursor else cursor or None)
    return len(collected), complete


def _rpc(method: str, params: list[Any]) -> Any:
    from hh_real_payments import _rpc as payment_rpc
    return payment_rpc(BSC_RPC_URL, method, params)


def scan_bsc_events() -> tuple[int, bool]:
    """Scan token Transfer logs only after 20 block confirmations."""
    chain_id = int(str(_rpc("eth_chainId", [])), 16)
    if chain_id != 56:
        raise RuntimeError("Configured BSC RPC is not BNB Smart Chain mainnet (chain ID 56).")
    head = int(str(_rpc("eth_blockNumber", [])), 16)
    safe_head = max(0, head - BSC_CONFIRMATIONS)
    state = _get_state("BSC-BEP20")
    last_block = int(state.get("last_scanned_block") or 0) if state else 0
    start = last_block + 1 if last_block else max(0, safe_head - 20000)
    if start > safe_head:
        _save_bsc_state(safe_head)
        return 0, True
    treasury_hex = BSC_TREASURY.lower().removeprefix("0x")
    token_hex = BSC_TOKEN.lower()
    topic_to = "0x" + ("0" * 24) + treasury_hex
    collected: list[dict[str, Any]] = []
    chunk = 1000
    cursor = start
    while cursor <= safe_head:
        end = min(safe_head, cursor + chunk - 1)
        logs = _rpc("eth_getLogs", [{
            "fromBlock": hex(cursor),
            "toBlock": hex(end),
            "address": token_hex,
            "topics": [TRANSFER_TOPIC, None, topic_to],
        }])
        if not isinstance(logs, list):
            raise RuntimeError("BSC RPC returned malformed eth_getLogs data.")
        for log in logs:
            topics = log.get("topics") or []
            if len(topics) < 3 or str(topics[0]).lower() != TRANSFER_TOPIC:
                continue
            if str(log.get("address") or "").lower() != token_hex:
                continue
            sender = "0x" + str(topics[1])[-40:]
            recipient = "0x" + str(topics[2])[-40:]
            if recipient.lower() != BSC_TREASURY.lower():
                continue
            try:
                raw = int(str(log.get("data", "0x0")), 16)
                amount = Decimal(raw) / (Decimal(10) ** 18)
                txid = str(log["transactionHash"]).lower()
                event_key = str(log.get("logIndex", "0x0"))
                collected.append({
                    "network": "BSC-BEP20", "txid": txid, "event_key": event_key,
                    "sender_address": sender, "receiving_address": BSC_TREASURY,
                    "token_contract": BSC_TOKEN, "amount": format(amount, "f"),
                    "block_number": int(str(log.get("blockNumber", "0x0")), 16),
                    "block_timestamp": started_ms_for_block(log),
                })
            except (KeyError, ValueError, TypeError):
                continue
        cursor = end + 1
    _event_upsert_rows(collected)
    _save_bsc_state(safe_head)
    return len(collected), True


def started_ms_for_block(_log: dict[str, Any]) -> int:
    # BSC provider data in this scan has block numbers but not timestamps; detection time is sufficient for queue ordering.
    return int(time.time() * 1000)


def _event_match_key(network: str, sender: str, recipient: str, amount: Any) -> tuple[str, str, str, Decimal]:
    source = sender.lower() if network == "BSC-BEP20" else sender
    target = recipient.lower() if network == "BSC-BEP20" else recipient
    return network, source, target, _decimal(amount)


def _intent_wallet_is_verified(intent: dict[str, Any], verified_wallets: list[dict[str, Any]]) -> bool:
    """Return true only for a manually reviewed sender wallet linked to this same account."""
    network = str(intent.get("network") or "")
    sender = str(intent.get("sender_address") or "").strip()
    email = str(intent.get("user_email") or "").strip().lower()
    if not network or not sender or not email:
        return False
    target = sender.lower() if network == "BSC-BEP20" else sender
    for wallet in verified_wallets:
        wallet_network = str(wallet.get("network") or "")
        wallet_address = str(wallet.get("address") or "").strip()
        wallet_email = str(wallet.get("user_email") or "").strip().lower()
        candidate = wallet_address.lower() if wallet_network == "BSC-BEP20" else wallet_address
        if (wallet.get("status") == "Verified" and wallet_network == network
                and wallet_email == email and candidate == target):
            return True
    return False


def find_intent_candidates(event: dict[str, Any], intents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    target = _event_match_key(event["network"], event["sender_address"], event["receiving_address"], event["amount"])
    matches = []
    for intent in intents:
        if intent.get("consent_accepted") not in (1, True, "1"):
            continue
        if intent.get("status") in {"Verified", "Cancelled", "Expired"}:
            continue
        if intent["network"] != event["network"]:
            continue
        if intent.get("status") == "Pending confirmations" and intent.get("txid") and str(intent["txid"]).lower() != event["txid"].lower():
            continue
        if _event_match_key(intent["network"],intent.get("sender_address") or "",intent.get("receiving_address") or "",intent["amount"]) != target:
            continue
        matches.append(intent)
    return matches


def _set_event_status(conn,kind,event,status,intent_id=None,error=None):
    _execute(conn,kind,
        "UPDATE hh_chain_incoming_events SET status=?,payment_intent_id=?,last_error=?,updated_at=? "
        "WHERE network=? AND txid=? AND event_key=?",
        (status,intent_id,error,utc_now(),event["network"],event["txid"],event["event_key"]))


def process_observed_events() -> dict[str, int]:
    pending_intents = db_all(
        "SELECT * FROM hh_payment_intents WHERE consent_accepted=? AND status NOT IN ('Verified','Cancelled','Expired') ORDER BY created_at",
        (1,)
    )
    verified_wallets = db_all(
        "SELECT user_email,network,address,status FROM hh_verified_sender_wallets WHERE status=?",
        ("Verified",),
    )
    # A public address and transaction hash are not proof of wallet control.
    pending_intents = [
        intent for intent in pending_intents
        if _intent_wallet_is_verified(intent, verified_wallets)
    ]
    # Index by network + expected sender + treasury recipient + exact amount; avoid O(events × intents)
    # scans when thousands of deposits arrive in the same interval.
    intent_index: dict[tuple[str, str, str, Decimal], list[dict[str, Any]]] = {}
    for pending in pending_intents:
        key = _event_match_key(
            pending["network"], pending.get("sender_address") or "",
            pending.get("receiving_address") or "", pending["amount"])
        intent_index.setdefault(key, []).append(pending)
    events = db_all(
        "SELECT * FROM hh_chain_incoming_events WHERE status IN ('Unmatched','Ambiguous','Awaiting confirmations','Verification error') "
        "ORDER BY updated_at LIMIT ?",
        (MAX_EVENTS_PER_RUN,)
    )
    counts = {"events_considered": len(events), "credited": 0, "ambiguous": 0, "unmatched": 0, "errors": 0}
    if not events:
        return counts
    conn, kind = db_connect()
    try:
        for event in events:
            match_key = _event_match_key(event["network"], event["sender_address"], event["receiving_address"], event["amount"])
            candidates_for_key = intent_index.get(match_key, [])
            # If a previous run already credited this chain hash, reconcile the event/gate idempotently.
            already=_rows(conn,kind,
                "SELECT reference_id FROM hh_wallet_ledger WHERE network=? AND lower(txid)=lower(?) AND entry_type=?",
                (event["network"],event["txid"],"confirmed_deposit_credit"))
            if already:
                linked=_rows(conn,kind,"SELECT * FROM hh_payment_intents WHERE id=?",(already[0]["reference_id"],))
                if linked:
                    _ensure_grid_gate_in_transaction(conn,kind,linked[0],_decimal(linked[0]["amount"]),event["txid"],utc_now())
                    _set_event_status(conn,kind,event,"Verified",linked[0]["id"],None)
                    counts["credited"] += 1
                    continue
            candidates = find_intent_candidates(event,candidates_for_key)
            if len(candidates) == 0:
                _set_event_status(conn,kind,event,"Unmatched",None,"No unique open consented deposit request matches source, network, receiving address and exact amount.")
                counts["unmatched"] += 1
                continue
            if len(candidates) > 1:
                _set_event_status(conn,kind,event,"Ambiguous",None,"More than one open request matches this transfer. No automatic credit; cancel/resolve the duplicate request(s).")
                counts["ambiguous"] += 1
                continue
            intent=candidates[0]
            try:
                rows=_rows(conn,kind,"SELECT * FROM hh_payment_intents WHERE id=?"+(" FOR UPDATE" if kind=="postgres" else ""),(intent["id"],))
                if not rows:
                    _set_event_status(conn,kind,event,"Verification error",None,"Matching request disappeared before credit.")
                    counts["errors"] += 1
                    continue
                row=rows[0]
                if row.get("status") in {"Cancelled","Expired"}:
                    _set_event_status(conn,kind,event,"Unmatched",None,"Matched request is cancelled/expired.")
                    counts["unmatched"] += 1
                    continue
                if row.get("status")=="Verified":
                    ledger=_rows(conn,kind,"SELECT txid FROM hh_wallet_ledger WHERE reference_id=? AND entry_type=?",(row["id"],"confirmed_deposit_credit"))
                    if ledger and str(ledger[0].get("txid") or "").lower()==event["txid"].lower():
                        _ensure_grid_gate_in_transaction(conn,kind,row,_decimal(row["amount"]),event["txid"],utc_now())
                        _set_event_status(conn,kind,event,"Verified",row["id"],None)
                        counts["credited"] += 1
                        continue
                    _set_event_status(conn,kind,event,"Verification error",None,"Request is marked Verified but its ledger link is missing/mismatched.")
                    counts["errors"] += 1
                    continue
                if row.get("txid") and str(row["txid"]).lower()!=event["txid"].lower():
                    _set_event_status(conn,kind,event,"Verification error",None,"Request is already tracking another transaction hash.")
                    counts["errors"] += 1
                    continue
                amount=_decimal(row["amount"])
                actual=_decimal(event["amount"])
                if actual!=amount:
                    _set_event_status(conn,kind,event,"Verification error",None,"On-chain amount does not equal the requested amount.")
                    counts["errors"] += 1
                    continue
                dup=_rows(conn,kind,
                    "SELECT id FROM hh_payment_intents WHERE network=? AND lower(txid)=lower(?) AND id<>? AND status='Verified'",
                    (row["network"],event["txid"],row["id"]))
                if dup:
                    _set_event_status(conn,kind,event,"Verification error",None,"Transaction hash already credited to another request.")
                    counts["errors"] += 1
                    continue
                existing_credit=_rows(conn,kind,"SELECT txid FROM hh_wallet_ledger WHERE reference_id=? AND entry_type=?",(row["id"],"confirmed_deposit_credit"))
                now=utc_now()
                if existing_credit:
                    if str(existing_credit[0].get("txid") or "").lower()!=event["txid"].lower():
                        _set_event_status(conn,kind,event,"Verification error",None,"A different transaction is already credited to this request.")
                        counts["errors"] += 1
                        continue
                else:
                    acct=_get_account(conn,kind,row["user_email"],row["network"],now)
                    _set_account(conn,kind,row["user_email"],row["network"],_decimal(acct["available_balance"])+amount,_decimal(acct["reserved_balance"]),now)
                    _ledger(conn,kind,row["user_email"],row["network"],"confirmed_deposit_credit",amount,row["id"],event["txid"],
                            "Auto-reconciled confirmed token transfer: contract, treasury, source, exact amount and confirmations matched.",now)
                _execute(conn,kind,
                    "UPDATE hh_payment_intents SET status=?,txid=?,verification_note=?,updated_at=?,verified_at=? WHERE id=?",
                    ("Verified",event["txid"],"Auto-verified from confirmed on-chain transfer; exact request match.",now,now,row["id"]))
                row.update({"status":"Verified","txid":event["txid"]})
                _ensure_grid_gate_in_transaction(conn,kind,row,amount,event["txid"],now)
                _set_event_status(conn,kind,event,"Verified",row["id"],None)
                counts["credited"] += 1
                # Remove the completed intent from the in-memory match list to stop a second event reusing it.
                pending_intents=[p for p in pending_intents if p["id"] != row["id"]]
                intent_index[match_key]=[p for p in intent_index.get(match_key,[]) if p["id"] != row["id"]]
            except Exception as exc:
                try:
                    conn.rollback()
                except Exception:
                    pass
                # Re-open a clean transaction after an isolated event error and record a retryable outcome.
                _set_event_status(conn,kind,event,"Verification error",None,type(exc).__name__)
                conn.commit()
                counts["errors"] += 1
                continue
            if sum(counts[k] for k in ("credited","ambiguous","unmatched","errors")) % 50 == 0:
                conn.commit()
        conn.commit()
    finally:
        conn.close()
    return counts


def repair_verified_intents_missing_ledger() -> dict[str, int]:
    """Re-check old Verified records that predate atomic wallet-ledger crediting."""
    missing=db_all(
        "SELECT p.* FROM hh_payment_intents p WHERE p.status=? AND p.txid IS NOT NULL AND p.sender_address IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM hh_wallet_ledger l WHERE l.reference_id=p.id AND l.entry_type=? AND l.network=p.network AND lower(l.txid)=lower(p.txid)) "
        "ORDER BY p.verified_at LIMIT ?",
        ("Verified","confirmed_deposit_credit",MAX_EVENTS_PER_RUN)
    )
    fixed=0; errors=0
    verified_wallets = db_all(
        "SELECT user_email,network,address,status FROM hh_verified_sender_wallets WHERE status=?",
        ("Verified",),
    )
    for row in missing:
        try:
            if not _intent_wallet_is_verified(row, verified_wallets):
                errors += 1
                continue
            network=row["network"]
            if network=="TRON-TRC20":
                result=_verify_tron(row["txid"],_decimal(row["amount"]),TRON_TREASURY,"in",None,TRONGRID_API_KEY,TRON_API_BASE,minconf=20,expected_sender=row["sender_address"])
            elif network=="BSC-BEP20" and ENABLE_BSC:
                result=_verify_bsc(row["txid"],_decimal(row["amount"]),BSC_TREASURY,"in",None,BSC_TOKEN,BSC_RPC_URL,minconf=15,expected_sender=row["sender_address"])
            else:
                continue
            if result.get("status")!="Verified":
                errors+=1
                continue
            # _credit_deposit repairs a verified intent only when its matching credit-ledger row is absent.
            from hh_real_payments import _credit_deposit
            _credit_deposit(db_connect,True,row["id"],row["txid"],result,utc_now)
            fixed+=1
        except Exception:
            errors+=1
    return {"legacy_receipts_checked":len(missing),"legacy_credits_repaired":fixed,"legacy_errors":errors}


def main() -> int:
    if not os.getenv("DATABASE_URL","").strip():
        print("BLOCKED: set the GitHub Actions secret DATABASE_URL to the same managed PostgreSQL database used by Streamlit.")
        return 2
    ensure_payment_tables(db_exec,db_all)
    ensure_reconciler_tables()
    scanned_tron,tron_complete=scan_tron_events()
    scanned_bsc=0; bsc_complete=True
    if ENABLE_BSC:
        scanned_bsc,bsc_complete=scan_bsc_events()
    counts=process_observed_events()
    repaired=repair_verified_intents_missing_ledger()
    gate=sync_grid_deployment_queue(db_all,db_exec,utc_now)
    report={
        "run_started_utc":datetime.now(timezone.utc).isoformat(),
        "tron_events_discovered":scanned_tron,
        "tron_scan_complete":tron_complete,
        "bsc_events_discovered":scanned_bsc,
        "bsc_enabled":ENABLE_BSC,
        "bsc_scan_complete":bsc_complete,
        **counts,
        **repaired,
        **gate,
    }
    print(json.dumps(report,sort_keys=True))
    if not tron_complete:
        print("WARNING: TRON pagination incomplete; the saved cursor will resume on the next run. Check provider pagination/rate limits.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status":"FAILED_SAFE","error_type":type(exc).__name__,"message":str(exc)[:500]}),file=sys.stderr)
        raise
