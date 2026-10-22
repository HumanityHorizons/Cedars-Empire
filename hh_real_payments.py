"""Cedars Empire real-payment workflow. No private-key custody or auto-signing."""
from __future__ import annotations

from hh_table_ui import render_bank_table
import pandas as pd
import hashlib, re, uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Any, Callable
import requests

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TRON_USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
DEFAULT_BSC_PEG_USDT_CONTRACT = "0x55d398326f99059ff775485246999027b3197955"
DEFAULT_BSC_RPC = "https://bsc-dataseed.bnbchain.org"
DEFAULT_TRONGRID = "https://api.trongrid.io"
PACKAGE_AMOUNTS = {"Deposit $1 — verification": Decimal("1.00"), "Deposit $5": Decimal("5.00"),
                   "Deposit $10": Decimal("10.00"), "Deposit $25": Decimal("25.00")}
DEPOSIT_CONSENT_VERSION = "cedars-deposit-consent-v1-2026-10-21"
DEPOSIT_CONSENT_TEXT = (
    "I confirm I am making a USDT wallet deposit, not buying an investment. I understand there are no promised profits, interest, ROI, or guaranteed earnings. "
    "I will check the selected blockchain network, exact receiving address, token and amount before sending; blockchain transfers may be irreversible and network fees may apply. "
    "I understand funds are credited only after on-chain verification and required confirmations, that this wallet balance is recorded as an amount owed to my account rather than company revenue, and that withdrawals are subject to available confirmed funds and security checks. "
    "I consent to Cedars Empire recording my account email, consent version and timestamp, amount, package, selected network, receiving address, transaction hash, verification status and related audit events for reconciliation, fraud prevention and account history."
)

class PaymentError(RuntimeError):
    """Safe-to-display payment error."""

def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def _decimal(value: Any) -> Decimal:
    try: out = Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError, AttributeError): raise PaymentError("Enter a valid numeric amount.")
    if not out.is_finite(): raise PaymentError("Amount must be finite.")
    return out

def _q(amount: Decimal, decimals: int) -> Decimal:
    return amount.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_DOWN)

def _hex_address(value: str) -> str:
    value=(value or "").lower().strip()
    if value.startswith("0x"): value=value[2:]
    if not re.fullmatch(r"[0-9a-f]{40}", value): raise PaymentError("Invalid BNB Smart Chain address/token contract.")
    return value

def _base58_decode(value: str) -> bytes:
    alphabet="123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"; n=0
    for ch in value:
        try: n=n*58+alphabet.index(ch)
        except ValueError: raise PaymentError("Invalid TRON address.")
    raw=n.to_bytes((n.bit_length()+7)//8,"big") if n else b""
    return b"\x00"*(len(value)-len(value.lstrip("1")))+raw

def _tron_payload(address: str) -> bytes:
    raw=_base58_decode(address)
    if len(raw)!=25: raise PaymentError("Invalid TRON address length.")
    payload, checksum=raw[:-4], raw[-4:]
    if hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]!=checksum or len(payload)!=21 or payload[0]!=0x41:
        raise PaymentError("Invalid TRON address checksum/network prefix.")
    return payload

def validate_destination(network: str, address: str) -> bool:
    if network=="TRON-TRC20":
        try: _tron_payload((address or "").strip()); return True
        except PaymentError: return False
    if network=="BSC-BEP20": return bool(re.fullmatch(r"0x[0-9a-fA-F]{40}", (address or "").strip()))
    return False

def _json(url: str, method="GET", payload=None, headers=None) -> dict:
    try:
        r=requests.post(url,json=payload or {},headers=headers or {},timeout=20) if method=="POST" else requests.get(url,headers=headers or {},timeout=20)
        r.raise_for_status(); data=r.json()
        if not isinstance(data,dict): raise PaymentError("Blockchain provider returned an unexpected response.")
        return data
    except PaymentError: raise
    except Exception as exc: raise PaymentError(f"Blockchain verification unavailable ({type(exc).__name__}). No balance credited.")

def _rpc(url: str, method: str, params: list):
    data=_json(url,"POST",{"jsonrpc":"2.0","id":1,"method":method,"params":params},{"Content-Type":"application/json"})
    if data.get("error") or "result" not in data: raise PaymentError("BNB Smart Chain RPC error. No balance credited.")
    return data["result"]

def _topic_addr(topic: str) -> str:
    return str(topic or "").lower().replace("0x","")[-40:]

def _verify_bsc(txid, amount, treasury, direction, destination, token, rpc, minconf=15, expected_sender=None):
    if not re.fullmatch(r"0x[0-9a-fA-F]{64}",txid or ""): raise PaymentError("Enter a BNB Smart Chain TX hash (0x + 64 hex characters).")
    treasury_hex=_hex_address(treasury); dest_hex=_hex_address(destination) if destination else None; token_hex=_hex_address(token); expected_sender_hex=_hex_address(expected_sender) if expected_sender else None
    if int(str(_rpc(rpc,"eth_chainId",[])),16)!=56: raise PaymentError("RPC is not BNB Smart Chain mainnet (chain ID 56).")
    tx=_rpc(rpc,"eth_getTransactionByHash",[txid]); receipt=_rpc(rpc,"eth_getTransactionReceipt",[txid])
    if not tx or not receipt: return {"status":"Pending","message":"Transaction not yet visible on BNB Smart Chain. No credit."}
    if str(receipt.get("status","")).lower()!="0x1": return {"status":"Failed","message":"On-chain transaction failed. No credit."}
    block=int(str(receipt.get("blockNumber","0x0")),16); tip=int(str(_rpc(rpc,"eth_blockNumber",[])),16)
    conf=max(0,tip-block+1); candidates=[]
    for log in receipt.get("logs",[]):
        if str(log.get("address","")).lower()!="0x"+token_hex: continue
        topics=log.get("topics") or []
        if len(topics)<3 or str(topics[0]).lower()!=TRANSFER_TOPIC: continue
        sender, receiver=_topic_addr(topics[1]),_topic_addr(topics[2])
        try: token_amount=Decimal(int(str(log.get("data","0x0")),16))/(Decimal(10)**18)
        except Exception: continue
        if direction=="in" and receiver==treasury_hex and expected_sender_hex and sender==expected_sender_hex: candidates.append((sender,receiver,token_amount))
        elif direction=="out" and sender==treasury_hex and dest_hex and receiver==dest_hex: candidates.append((sender,receiver,token_amount))
    exact=[x for x in candidates if _q(x[2],18)==_q(amount,18)]
    if len(exact)!=1: return {"status":"Needs review","message":"No unique expected token transfer matched exact amount and destination. No balance changed."}
    if conf<minconf: return {"status":"Pending confirmations","confirmations":conf,"message":f"Transfer found; {conf}/{minconf} confirmations. No balance change yet."}
    return {"status":"Verified","confirmations":conf,"actual_amount":str(exact[0][2]),"message":f"Confirmed BNB Smart Chain token transfer ({conf} confirmations)."}

def _verify_tron(txid, amount, treasury, direction, destination, api_key="", base=DEFAULT_TRONGRID, minconf=20, expected_sender=None):
    if not re.fullmatch(r"[0-9a-fA-F]{64}",txid or ""): raise PaymentError("Enter the 64-character TRON transaction ID.")
    treasury_hex=_tron_payload(treasury)[1:].hex(); dest_hex=_tron_payload(destination)[1:].hex() if destination else None; expected_sender_hex=_tron_payload(expected_sender)[1:].hex() if expected_sender else None
    token_hex=_tron_payload(TRON_USDT_CONTRACT)[1:].hex(); headers={"Content-Type":"application/json"}
    if api_key: headers["TRON-PRO-API-KEY"]=api_key
    base=base.rstrip("/"); info=_json(base+"/wallet/gettransactioninfobyid","POST",{"value":txid},headers)
    if not info or not info.get("blockNumber"): return {"status":"Pending","message":"Transaction not yet visible/confirmed on TRON. No credit."}
    receipt_result = str((info.get("receipt") or {}).get("result", "")).upper()
    if receipt_result != "SUCCESS":
        return {"status":"Failed","message":"TRON transaction receipt is not successful/complete. No credit."}
    block=int(info.get("blockNumber",0)); nowblock=_json(base+"/wallet/getnowblock","POST",{},headers)
    tip=int((((nowblock.get("block_header") or {}).get("raw_data") or {}).get("number",0))); conf=max(0,tip-block+1); candidates=[]
    for log in info.get("log",[]) or []:
        logaddr=str(log.get("address","")).lower().removeprefix("0x")
        if len(logaddr)==42 and logaddr.startswith("41"): logaddr=logaddr[2:]
        if logaddr!=token_hex: continue
        topics=log.get("topics") or []
        if len(topics)<3 or str(topics[0]).lower().removeprefix("0x")!=TRANSFER_TOPIC[2:]: continue
        sender,receiver=_topic_addr(topics[1]),_topic_addr(topics[2])
        try: token_amount=Decimal(int(str(log.get("data","0x0")),16))/Decimal(10**6)
        except Exception: continue
        if direction=="in" and receiver==treasury_hex and expected_sender_hex and sender==expected_sender_hex: candidates.append((sender,receiver,token_amount))
        elif direction=="out" and sender==treasury_hex and dest_hex and receiver==dest_hex: candidates.append((sender,receiver,token_amount))
    exact=[x for x in candidates if _q(x[2],6)==_q(amount,6)]
    if len(exact)!=1: return {"status":"Needs review","message":"No unique official TRON USDT transfer matched expected amount and address. No balance changed."}
    if conf<minconf: return {"status":"Pending confirmations","confirmations":conf,"message":f"Transfer found; {conf}/{minconf} confirmations. No balance change yet."}
    return {"status":"Verified","confirmations":conf,"actual_amount":str(exact[0][2]),"message":f"Confirmed TRON USDT transfer ({conf} confirmations)."}

def verify_transfer(network, txid, amount, treasury, direction, destination=None,
                    bsc_token_contract=DEFAULT_BSC_PEG_USDT_CONTRACT, bsc_rpc_url=DEFAULT_BSC_RPC,
                    trongrid_api_key="", min_bsc_confirmations=15, min_tron_confirmations=20, expected_sender=None):
    amount=_decimal(amount)
    if direction not in {"in","out"} or amount<=0: raise PaymentError("Invalid direction or non-positive amount.")
    if direction=="in" and (not expected_sender or not validate_destination(network, expected_sender)):
        raise PaymentError("For deposit attribution, enter a valid self-controlled sender wallet address on the same network.")
    if direction=="in" and network=="TRON-TRC20" and _tron_payload(expected_sender)==_tron_payload(treasury):
        raise PaymentError("The sender and treasury must be different addresses; a self-transfer is not a deposit.")
    if direction=="in" and network=="BSC-BEP20" and _hex_address(expected_sender)==_hex_address(treasury):
        raise PaymentError("The sender and treasury must be different addresses; a self-transfer is not a deposit.")
    if direction=="out" and network=="TRON-TRC20" and destination and _tron_payload(destination)==_tron_payload(treasury):
        raise PaymentError("Cash-out destination must be different from the treasury address.")
    if direction=="out" and network=="BSC-BEP20" and destination and _hex_address(destination)==_hex_address(treasury):
        raise PaymentError("Cash-out destination must be different from the treasury address.")
    if network=="TRON-TRC20": return _verify_tron(txid.strip(),amount,treasury,direction,destination,trongrid_api_key,minconf=min_tron_confirmations,expected_sender=expected_sender)
    if network=="BSC-BEP20": return _verify_bsc(txid.strip(),amount,treasury,direction,destination,bsc_token_contract,bsc_rpc_url,min_bsc_confirmations,expected_sender=expected_sender)
    raise PaymentError("Unsupported network. Use TRON TRC-20 or BNB Smart Chain BEP-20.")


def ensure_payment_tables(db_exec: Callable, db_all: Callable | None = None) -> None:
    """Add schema tables without replacing any existing tables."""
    for sql in [
        """CREATE TABLE IF NOT EXISTS hh_payment_intents (
            id TEXT PRIMARY KEY, user_email TEXT NOT NULL, package_label TEXT NOT NULL,
            amount TEXT NOT NULL, network TEXT NOT NULL, receiving_address TEXT NOT NULL,
            sender_address TEXT, consent_accepted INTEGER NOT NULL DEFAULT 0, consent_version TEXT,
            consent_text TEXT, consented_at TEXT, status TEXT NOT NULL, txid TEXT, last_attempted_txid TEXT, verification_note TEXT, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, verified_at TEXT)""",
        """CREATE TABLE IF NOT EXISTS hh_verified_sender_wallets (
            id TEXT PRIMARY KEY, user_email TEXT NOT NULL, network TEXT NOT NULL, address TEXT NOT NULL,
            status TEXT NOT NULL, verification_method TEXT, evidence_reference TEXT, verified_by TEXT, verification_note TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS hh_wallet_accounts (
            user_email TEXT NOT NULL, network TEXT NOT NULL, available_balance TEXT NOT NULL DEFAULT '0',
            reserved_balance TEXT NOT NULL DEFAULT '0', updated_at TEXT NOT NULL,
            PRIMARY KEY(user_email,network))""",
        """CREATE TABLE IF NOT EXISTS hh_wallet_ledger (
            id TEXT PRIMARY KEY,user_email TEXT NOT NULL,network TEXT NOT NULL,entry_type TEXT NOT NULL,
            amount TEXT NOT NULL,reference_id TEXT,txid TEXT,notes TEXT,created_at TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS hh_cashout_requests (
            id TEXT PRIMARY KEY,user_email TEXT NOT NULL,network TEXT NOT NULL,amount TEXT NOT NULL,
            destination TEXT NOT NULL,status TEXT NOT NULL,admin_note TEXT,created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,processed_txid TEXT)""",
        """CREATE TABLE IF NOT EXISTS hh_grid_deployment_queue (
            id TEXT PRIMARY KEY, payment_intent_id TEXT NOT NULL, user_email TEXT NOT NULL,
            network TEXT NOT NULL, amount TEXT NOT NULL, txid TEXT NOT NULL, requested_scope TEXT NOT NULL,
            status TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
    ]:
        db_exec(sql)
    if db_all is not None:
        # Additive migrations preserve payment history from earlier test builds.
        migrations = [
            ("SELECT sender_address FROM hh_payment_intents LIMIT 0", "ALTER TABLE hh_payment_intents ADD COLUMN sender_address TEXT"),
            ("SELECT consent_accepted FROM hh_payment_intents LIMIT 0", "ALTER TABLE hh_payment_intents ADD COLUMN consent_accepted INTEGER NOT NULL DEFAULT 0"),
            ("SELECT consent_version FROM hh_payment_intents LIMIT 0", "ALTER TABLE hh_payment_intents ADD COLUMN consent_version TEXT"),
            ("SELECT consent_text FROM hh_payment_intents LIMIT 0", "ALTER TABLE hh_payment_intents ADD COLUMN consent_text TEXT"),
            ("SELECT consented_at FROM hh_payment_intents LIMIT 0", "ALTER TABLE hh_payment_intents ADD COLUMN consented_at TEXT"),
            ("SELECT last_attempted_txid FROM hh_payment_intents LIMIT 0", "ALTER TABLE hh_payment_intents ADD COLUMN last_attempted_txid TEXT"),
            ("SELECT verification_note FROM hh_verified_sender_wallets LIMIT 0", "ALTER TABLE hh_verified_sender_wallets ADD COLUMN verification_note TEXT"),
        ]
        for probe, alter in migrations:
            try:
                db_all(probe)
            except Exception:
                db_exec(alter)
    db_exec("CREATE UNIQUE INDEX IF NOT EXISTS uq_hh_verified_sender_wallet ON hh_verified_sender_wallets(network, lower(address))")
    db_exec("CREATE UNIQUE INDEX IF NOT EXISTS uq_hh_payment_network_txid ON hh_payment_intents(network,txid)")
    db_exec("CREATE UNIQUE INDEX IF NOT EXISTS uq_hh_ledger_network_txid ON hh_wallet_ledger(network,txid)")
    db_exec("CREATE UNIQUE INDEX IF NOT EXISTS uq_hh_cashout_network_txid ON hh_cashout_requests(network,lower(processed_txid))")
    db_exec("CREATE UNIQUE INDEX IF NOT EXISTS uq_hh_grid_queue_intent ON hh_grid_deployment_queue(payment_intent_id)")
    db_exec("CREATE UNIQUE INDEX IF NOT EXISTS uq_hh_grid_queue_txid ON hh_grid_deployment_queue(network,txid)")


def _execute(conn, kind, sql, params=()):
    # Always return a cursor. sqlite3.Connection itself has execute(), but not fetchall().
    cur = conn.cursor()
    cur.execute(sql.replace("?", "%s") if kind == "postgres" else sql, params)
    return cur


def _rows(conn, kind, sql, params=()):
    cur = _execute(conn, kind, sql, params)
    items = cur.fetchall()
    return [dict(x) if isinstance(x, dict) or hasattr(x, "keys") else dict(zip([d[0] for d in cur.description], x)) for x in items]


def _gate(durable):
    if not durable:
        raise PaymentError("Real-money actions are locked until DATABASE_URL points to managed PostgreSQL. Local SQLite storage may disappear after refresh/redeploy.")


def _get_account(conn, kind, email, network, now):
    _execute(conn,kind,"INSERT INTO hh_wallet_accounts(user_email,network,available_balance,reserved_balance,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(user_email,network) DO NOTHING",
             (email,network,"0","0",now))
    rows=_rows(conn,kind,"SELECT * FROM hh_wallet_accounts WHERE user_email=? AND network=?"+(" FOR UPDATE" if kind=="postgres" else ""),(email,network))
    if not rows: raise PaymentError("Could not read/lock wallet account.")
    return rows[0]


def _set_account(conn,kind,email,network,available,reserved,now):
    _execute(conn,kind,"UPDATE hh_wallet_accounts SET available_balance=?,reserved_balance=?,updated_at=? WHERE user_email=? AND network=?",
             (format(available,"f"),format(reserved,"f"),now,email,network))


def _ledger(conn,kind,email,network,entry,amount,ref,txid,note,now):
    _execute(conn,kind,"INSERT INTO hh_wallet_ledger(id,user_email,network,entry_type,amount,reference_id,txid,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
             (str(uuid.uuid4()),email,network,entry,format(amount,"f"),ref,txid,note,now))


def _create_intent(email, amount, network, address, sender_address, label, db_exec, db_all, durable, now_iso,
                   consent_accepted, consent_version=DEPOSIT_CONSENT_VERSION, consent_text=DEPOSIT_CONSENT_TEXT):
    _gate(durable)
    if not consent_accepted: raise PaymentError("You must accept the deposit consent before creating a request.")
    if not validate_destination(network,address): raise PaymentError("Configured treasury address is invalid for the selected network.")
    if not validate_destination(network,sender_address): raise PaymentError("Enter the valid self-controlled sending wallet address for the selected network.")
    if network=="TRON-TRC20" and _tron_payload(sender_address)==_tron_payload(address): raise PaymentError("The sender and treasury must be different addresses; a self-transfer is not a deposit.")
    if network=="BSC-BEP20" and _hex_address(sender_address)==_hex_address(address): raise PaymentError("The sender and treasury must be different addresses; a self-transfer is not a deposit.")
    amount=_decimal(amount)
    if amount<Decimal("1"): raise PaymentError("Minimum deposit is 1 USDT.")
    ensure_payment_tables(db_exec, db_all)
    # Sender address is an expected on-chain match key, not identity proof. Requiring admin approval here
    # would create a manual bottleneck for thousands of deposits; exact verified chain event matching is required later.
    now=now_iso()
    intent={"id":str(uuid.uuid4()),"user_email":email,"amount":amount,"network":network,"address":address,"label":label,
            "consent_accepted":True,"consent_version":consent_version,"consented_at":now}
    db_exec("INSERT INTO hh_payment_intents(id,user_email,package_label,amount,network,receiving_address,sender_address,consent_accepted,consent_version,consent_text,consented_at,status,txid,verification_note,created_at,updated_at,verified_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (intent["id"],email,label,format(amount,"f"),network,address,sender_address,1,consent_version,consent_text,now,
         "Awaiting payment",None,"Consent recorded; payment not yet verified",now,now,None))
    return intent


def _ensure_grid_gate_in_transaction(conn,kind,row,amount,txid,now):
    existing=_rows(conn,kind,"SELECT id FROM hh_grid_deployment_queue WHERE payment_intent_id=?",(row["id"],))
    if existing:
        return
    _execute(conn,kind,"INSERT INTO hh_grid_deployment_queue(id,payment_intent_id,user_email,network,amount,txid,requested_scope,status,reason,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
             (str(uuid.uuid4()),row["id"],row["user_email"],row["network"],format(amount,"f"),txid,"ALL GRIDS",
              "Blocked - user wallet liability",
              "Verified deposit is credited to the user's wallet and is not company revenue or deployable grid budget. A separate reconciled company-funds allocation is required.",now,now))


def _credit_deposit(db_connect, durable, intent_id, txid, result, now_iso):
    _gate(durable)
    if result.get("status") != "Verified": raise PaymentError("Cannot credit a deposit without a verified on-chain result.")
    txid=(txid or "").strip().lower()
    if not txid: raise PaymentError("Cannot credit a deposit without its on-chain TXID.")
    actual=result.get("actual_amount")
    conn,kind=db_connect()
    try:
        rows=_rows(conn,kind,"SELECT * FROM hh_payment_intents WHERE id=?"+(" FOR UPDATE" if kind=="postgres" else ""),(intent_id,))
        if not rows: raise PaymentError("Payment intent not found.")
        row=rows[0]
        amount=_decimal(row["amount"])
        if actual is None or _decimal(actual) != amount:
            raise PaymentError("Verified on-chain amount does not match the stored payment intent; no credit posted.")
        stored_txid=str(row.get("txid") or "").lower()
        if row.get("status")=="Verified" and stored_txid and stored_txid!=txid:
            raise PaymentError("This intent was already verified against another TXID.")
        # The database transaction may be from an earlier build with a Verified status but missing
        # ledger/queue rows. Repair it safely by re-verifying the chain event before this function.
        credited=_rows(conn,kind,"SELECT id,txid FROM hh_wallet_ledger WHERE reference_id=? AND entry_type=?",(intent_id,"confirmed_deposit_credit"))
        now=now_iso()
        if credited:
            if str(credited[0].get("txid") or "").lower()!=txid:
                raise PaymentError("Ledger already has a different TXID for this deposit intent; manual reconciliation required.")
            if row.get("status")!="Verified":
                raise PaymentError("Ledger credit exists but intent status is not Verified; manual reconciliation required.")
            _ensure_grid_gate_in_transaction(conn,kind,row,amount,txid,now)
            conn.commit()
            return
        dup=_rows(conn,kind,"SELECT id FROM hh_payment_intents WHERE network=? AND lower(txid)=lower(?) AND id<>? AND status=?",
                  (row["network"],txid,intent_id,"Verified"))
        if dup: raise PaymentError("TXID already credited to another payment; no new credit.")
        acct=_get_account(conn,kind,row["user_email"],row["network"],now)
        _set_account(conn,kind,row["user_email"],row["network"],_decimal(acct["available_balance"])+amount,_decimal(acct["reserved_balance"]),now)
        _ledger(conn,kind,row["user_email"],row["network"],"confirmed_deposit_credit",amount,intent_id,txid,
                "Wallet liability credited only after on-chain token/amount/address/confirmation verification.",now)
        _execute(conn,kind,"UPDATE hh_payment_intents SET status=?,txid=?,verification_note=?,updated_at=?,verified_at=? WHERE id=?",
                 ("Verified",txid,result.get("message","Verified on-chain"),now,now,intent_id))
        _ensure_grid_gate_in_transaction(conn,kind,row,amount,txid,now)
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally: conn.close()


def _verify_deposit(intent, txid, db_all, db_exec, db_connect, durable, tron_treasury, bsc_treasury,
                    bsc_token, bsc_rpc, tron_key, now_iso):
    _gate(durable); txid=(txid or "").strip().lower()
    if not txid: raise PaymentError("Enter the TXID from your sending wallet.")
    rows=db_all("SELECT * FROM hh_payment_intents WHERE id=? AND user_email=?",(intent["id"],intent["user_email"]))
    if not rows: raise PaymentError("Payment request not found for your signed-in account.")
    row=rows[0]
    if row.get("status")=="Verified": raise PaymentError("Already verified; payment cannot be credited twice.")
    if row.get("status")=="Pending confirmations" and row.get("txid") and str(row["txid"]).lower()!=txid:
        raise PaymentError("This request already tracks a matching transfer awaiting confirmations. Continue using the same TXID.")
    treasury=tron_treasury if row["network"]=="TRON-TRC20" else bsc_treasury
    sender=row.get("sender_address")
    if not sender or not validate_destination(row["network"],sender):
        raise PaymentError("This request lacks a valid recorded sender wallet. Create a new deposit request before paying.")
    result=verify_transfer(row["network"],txid,_decimal(row["amount"]),treasury,"in",expected_sender=sender,bsc_token_contract=bsc_token,
                           bsc_rpc_url=bsc_rpc,trongrid_api_key=tron_key)
    if result.get("status")=="Verified":
        _credit_deposit(db_connect,durable,row["id"],txid,result,now_iso)
    else:
        # Do not reserve the unique TXID slot for an invalid/unmatched hash. Keep it in the
        # separate attempt-history field; only a matched transfer awaiting confirmations
        # reserves hh_payment_intents.txid.
        matched_txid=txid if result.get("status")=="Pending confirmations" else None
        db_exec("UPDATE hh_payment_intents SET status=?,txid=?,last_attempted_txid=?,verification_note=?,updated_at=? WHERE id=?",
                (result.get("status","Needs review"),matched_txid,txid,result.get("message",""),now_iso(),row["id"]))
    return result


def _new_cashout(db_connect,durable,email,network,amount,destination,treasury_address,now_iso):
    _gate(durable); amount=_decimal(amount)
    if amount<Decimal("1"): raise PaymentError("Minimum cash-out request is 1 USDT.")
    if not validate_destination(network,destination): raise PaymentError("Destination address does not match selected network.")
    if network=="TRON-TRC20" and _tron_payload(destination)==_tron_payload(treasury_address): raise PaymentError("Cash-out destination must be different from the treasury address.")
    if network=="BSC-BEP20" and _hex_address(destination)==_hex_address(treasury_address): raise PaymentError("Cash-out destination must be different from the treasury address.")
    reqid=str(uuid.uuid4()); now=now_iso(); conn,kind=db_connect()
    try:
        acct=_get_account(conn,kind,email,network,now)
        available,reserved=_decimal(acct["available_balance"]),_decimal(acct["reserved_balance"])
        if amount>available: raise PaymentError(f"Only {available} USDT is currently available on {network}.")
        _set_account(conn,kind,email,network,available-amount,reserved+amount,now)
        _execute(conn,kind,"INSERT INTO hh_cashout_requests(id,user_email,network,amount,destination,status,admin_note,created_at,updated_at,processed_txid) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (reqid,email,network,format(amount,"f"),destination,"Requested","Reserved, not transferred.",now,now,None))
        _ledger(conn,kind,email,network,"cashout_reserved",Decimal("0"),reqid,None,
                f"Moved {amount} USDT from available to reserved; no transfer has happened.",now)
        conn.commit(); return reqid
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally: conn.close()


def _cashout_decision(db_connect,durable,reqid,decision,note,now_iso):
    _gate(durable)
    if decision not in {"Under review","Approved for manual processing","Rejected"}:
        raise PaymentError("A payout can only be marked paid after independent on-chain verification.")
    conn,kind=db_connect()
    try:
        rows=_rows(conn,kind,"SELECT * FROM hh_cashout_requests WHERE id=?"+(" FOR UPDATE" if kind=="postgres" else ""),(reqid,))
        if not rows: raise PaymentError("Cash-out request not found.")
        row=rows[0]
        if row["status"] in {"Paid (verified on-chain)","Rejected"}: raise PaymentError("Request is already closed.")
        now=now_iso()
        if decision=="Rejected":
            acct=_get_account(conn,kind,row["user_email"],row["network"],now); amount=_decimal(row["amount"])
            reserved=_decimal(acct["reserved_balance"])-amount
            if reserved<0: raise PaymentError("Reserved-balance integrity check failed.")
            _set_account(conn,kind,row["user_email"],row["network"],_decimal(acct["available_balance"])+amount,reserved,now)
            _ledger(conn,kind,row["user_email"],row["network"],"cashout_release_after_rejection",Decimal("0"),reqid,None,
                    f"Released {amount} USDT back to available; no payout made.",now)
        _execute(conn,kind,"UPDATE hh_cashout_requests SET status=?,admin_note=?,updated_at=? WHERE id=?",(decision,note.strip(),now,reqid))
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally: conn.close()


def _cashout_paid(db_connect,durable,reqid,txid,result,now_iso):
    _gate(durable)
    txid=(txid or "").strip().lower()
    if result.get("status") != "Verified": raise PaymentError("Cannot mark cash-out paid without a verified outgoing on-chain result.")
    if not txid: raise PaymentError("Cannot mark cash-out paid without an outgoing TXID.")
    conn,kind=db_connect()
    try:
        rows=_rows(conn,kind,"SELECT * FROM hh_cashout_requests WHERE id=?"+(" FOR UPDATE" if kind=="postgres" else ""),(reqid,))
        if not rows: raise PaymentError("Cash-out request not found.")
        row=rows[0]
        if row["status"]=="Paid (verified on-chain)":
            if str(row.get("processed_txid","")).lower()==txid.lower(): conn.commit(); return
            raise PaymentError("Request was already settled with another TXID.")
        if row["status"]!="Approved for manual processing": raise PaymentError("Request must be approved before payout verification.")
        actual=result.get("actual_amount")
        if actual is None or _decimal(actual) != _decimal(row["amount"]):
            raise PaymentError("Verified outgoing on-chain amount does not match the cash-out request; payout remains unpaid.")
        dup=_rows(conn,kind,"SELECT id FROM hh_cashout_requests WHERE network=? AND lower(processed_txid)=lower(?) AND id<>?",(row["network"],txid,reqid))
        if dup: raise PaymentError("Outgoing TXID already assigned to another request.")
        now=now_iso(); acct=_get_account(conn,kind,row["user_email"],row["network"],now)
        reserved=_decimal(acct["reserved_balance"])-_decimal(row["amount"])
        if reserved<0: raise PaymentError("Reserved-balance integrity check failed.")
        _set_account(conn,kind,row["user_email"],row["network"],_decimal(acct["available_balance"]),reserved,now)
        _ledger(conn,kind,row["user_email"],row["network"],"cashout_paid_on_chain",-_decimal(row["amount"]),reqid,txid,result.get("message","Verified outgoing transfer"),now)
        _execute(conn,kind,"UPDATE hh_cashout_requests SET status=?,processed_txid=?,admin_note=?,updated_at=? WHERE id=?",
            ("Paid (verified on-chain)",txid,result.get("message","Outgoing transfer verified"),now,reqid))
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally: conn.close()


def _qr_bytes(address):
    try:
        import qrcode
        from io import BytesIO
        out=BytesIO(); qrcode.make(address).save(out,format="PNG"); return out.getvalue()
    except Exception as exc:
        raise PaymentError(f"QR generation unavailable ({type(exc).__name__}); copy the address shown instead.")


def _network_label(network,bsc_token):
    if network=="TRON-TRC20": return "TRON mainnet · Tether-issued USDT · TRC-20"
    return f"BNB Smart Chain · Binance-Peg BSC-USD ({bsc_token}) · not native Tether-issued USDT"


def _show_address(st,network,address,bsc_token):
    st.markdown(f"**Network:** {_network_label(network,bsc_token)}")
    st.markdown("**Treasury receiving address**"); st.code(address,language=None)
    st.caption("QR contains the receiving address only. Verify the address and network before sending.")
    try:
        qr=_qr_bytes(address); st.image(qr,caption=f"{network} receiving QR",width=230)
        st.download_button("Download receiving QR (PNG)",qr,file_name=f"cedars_empire_{network.lower()}_qr.png",mime="image/png")
    except PaymentError as exc: st.warning(str(exc))
    url="https://tronscan.org/#/address/"+address if network=="TRON-TRC20" else "https://bscscan.com/address/"+address
    st.markdown(f"[Open address in blockchain explorer]({url})")


def _asset_label(network):
    if network=="TRON-TRC20":
        return "Tether-issued USDT"
    if network=="BSC-BEP20":
        return "Binance-Peg BSC-USD (not native Tether USDT)"
    return "Configured token"


def _balances(st,email,db_all):
    rows=db_all("SELECT network,available_balance,reserved_balance,updated_at FROM hh_wallet_accounts WHERE user_email=? ORDER BY network",(email,))
    if not rows:
        st.metric("Verified available balance", "0.000000 USDT")
        st.empty()
        return
    st.subheader("Verified balances by network")
    cols=st.columns(min(2,len(rows)))
    for i,row in enumerate(rows):
        network=row["network"]
        asset="USDT" if network=="TRON-TRC20" else ("BSC-USD" if network=="BSC-BEP20" else "token units")
        cols[i].metric(f"{network} · {asset}",f"{_decimal(row['available_balance']):.6f} available",
                       help=f"Asset: {_asset_label(network)}. Reserved: {_decimal(row['reserved_balance']):.6f}; updated {row.get('updated_at','—')}. Balances across different token contracts are not combined.")


def _render_deposit_history(st, email, db_all):
    rows=db_all(
        "SELECT id,package_label,amount,network,status,txid,last_attempted_txid,verification_note,consent_version,consented_at,created_at,verified_at "
        "FROM hh_payment_intents WHERE user_email=? ORDER BY created_at DESC LIMIT 50",(email,))
    st.subheader("Deposit history")
    if not rows:
        st.info("No records.")
        return
    render_bank_table(rows,use_container_width=True,hide_index=True)
    import pandas as pd
    st.download_button("Download my deposit history (CSV)",
        pd.DataFrame(rows).to_csv(index=False).encode("utf-8"),
        file_name="cedars_empire_deposit_history.csv",mime="text/csv")


def _deposit_ui(st,email,db_all,db_exec,db_connect,durable,tron_treasury,bsc_treasury,allow_bsc,bsc_token,bsc_rpc,tron_key,now_iso,record_event):
    st.title("Deposit & Packages")
    st.empty()

    networks=["TRON-TRC20"]+(["BSC-BEP20"] if allow_bsc else [])
    network=st.selectbox("Deposit network",networks,key="hh_deposit_network")
    address=tron_treasury if network=="TRON-TRC20" else bsc_treasury

    # Show the configured treasury destination and QR before storage/wallet gates.
    _show_address(st,network,address,bsc_token)
    if network=="TRON-TRC20":
        st.info("Use TRC-20 USDT; network fees may apply.")
    elif network=="BSC-BEP20":
        st.warning("Asset: Binance-Peg BSC-USD, not native Tether USDT. Verify the token contract.")

    st.subheader("Deposit amount / package")
    amount_options=["Custom amount"]+list(PACKAGE_AMOUNTS.keys())
    selected_package=st.selectbox("Choose a deposit amount",amount_options,key="hh_deposit_package")
    if selected_package=="Custom amount":
        amount_raw=st.text_input("Amount in USDT (minimum 1.00)",value="1.00",key="hh_custom_amount")
        try:
            chosen=_decimal(amount_raw)
        except PaymentError:
            chosen=Decimal("0")
        package_label="Custom deposit"
    else:
        chosen=PACKAGE_AMOUNTS[selected_package]
        package_label=selected_package
        st.metric("Selected deposit",f"{chosen:.2f} USDT")
    if chosen < Decimal("1"):
        st.warning("The minimum deposit request is 1 USDT.")

    with st.expander("Deposit terms (required)",expanded=False):
        st.empty()
        st.markdown(
            "- This is a wallet deposit, not an investment or purchase promising a return. No interest, ROI, multiplier or guaranteed earnings are offered.\n"
            "- Check the selected network, token, receiving address and amount before sending. Blockchain transfers can be irreversible and network fees may apply.\n"
            "- The app credits only a matching transfer verified on-chain after required confirmations. A screenshot or TXID alone does not prove receipt.\n"
            "- A credited wallet balance is an amount owed to your account, not company revenue; it must not be spent to activate business grids. Withdrawals remain subject to confirmed available funds and security checks.\n"
            "- Deposit history stores your account, package, amount, network, receiving address, consent version and time, transaction hash and verification status for reconciliation and fraud prevention."
        )
    consent_accepted=st.checkbox(
        "I have read and agree to the deposit consent above.",
        key="hh_deposit_consent_accepted")

    if not durable:
        st.error("REAL-MONEY ACTIONS LOCKED: managed PostgreSQL is not connected. The address and QR above are for review only; do not send money until durable storage and the wallet review gate are confirmed.")
        st.empty()
        return
    try:
        ensure_payment_tables(db_exec,db_all)
    except Exception as exc:
        st.error(f"REAL-MONEY ACTIONS LOCKED: the configured database could not be prepared ({type(exc).__name__}). The address and QR remain visible, but do not send funds until storage works.")
        return
    sender_address=st.text_input(
        "Sending wallet address (expected transaction source)",
        key="hh_expected_sender_address",
        help="Enter the public address you will send from. It is used to match the blockchain transfer automatically; never enter a private key or recovery phrase.")
    st.empty()
    if st.button("Create deposit request",type="primary",
                  disabled=(not consent_accepted or chosen<Decimal("1") or not sender_address.strip()),
                  key="hh_create_deposit_request"):
        try:
            sender_address=sender_address.strip()
            if not validate_destination(network,sender_address):
                raise PaymentError("The sending wallet address does not match the selected network.")
            same_address=(network=="TRON-TRC20" and _tron_payload(sender_address)==_tron_payload(address)) or (network=="BSC-BEP20" and _hex_address(sender_address)==_hex_address(address))
            if same_address:
                raise PaymentError("The treasury receiving address cannot be used as the sending address.")
            intent=_create_intent(email,chosen,network,address,sender_address,package_label,db_exec,db_all,durable,now_iso,
                                  consent_accepted,DEPOSIT_CONSENT_VERSION,DEPOSIT_CONSENT_TEXT)
            record_event(email,"deposit_intent_created",f"{intent['id']}:{network}:{chosen}")
            st.success(f"Deposit request {intent['id']} recorded. The scheduled reconciler can match the confirmed on-chain transfer automatically once its GitHub Actions DATABASE_URL is configured. Send exactly {chosen} on {network} to the treasury address above.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc) if isinstance(exc,PaymentError) else f"Could not create deposit request ({type(exc).__name__}).")

    recent=db_all(
        "SELECT id,user_email,package_label,amount,network,receiving_address,sender_address,status,txid,last_attempted_txid,verification_note,consent_accepted,consent_version,consent_text,consented_at,created_at,verified_at "
        "FROM hh_payment_intents WHERE user_email=? ORDER BY created_at DESC LIMIT 50",(email,))
    st.subheader("Pending deposit verification")
    pending=[x for x in recent if str(x.get("status","")).lower() not in ("verified","cancelled","expired")]
    if not pending:
        st.empty()
    else:
        labels={f"{x['package_label']} · {x['amount']} USDT · {x['network']} · {str(x['id'])[:8]}":x for x in pending}
        selected=st.selectbox("Select a pending request",list(labels),key="hh_resume_pending")
        row=labels[selected]
        intent={"id":row["id"],"user_email":row["user_email"],"amount":_decimal(row["amount"]),
                "network":row["network"],"address":row["receiving_address"],"label":row["package_label"]}
        st.caption(f"Request ID: {intent['id']} · Created: {row.get('created_at')} · Consent: {row.get('consent_version') or 'not recorded'}")
        _show_address(st,intent["network"],intent["address"],bsc_token)
        txid=st.text_input("Transaction ID from the sending wallet",key=f"hh_txid_{intent['id']}")
        if st.button("Verify deposit on-chain",type="primary",key=f"hh_verify_{intent['id']}"):
            try:
                result=_verify_deposit(intent,txid,db_all,db_exec,db_connect,durable,tron_treasury,bsc_treasury,bsc_token,bsc_rpc,tron_key,now_iso)
                (st.success if result.get("status")=="Verified" else st.warning)(result.get("message",result["status"]))
                record_event(email,"deposit_verification_result",f"{intent['id']}:{result.get('status')}")
            except Exception as exc:
                st.error(str(exc) if isinstance(exc,PaymentError) else f"Verification failed safely ({type(exc).__name__}); no balance credited.")
    _render_deposit_history(st,email,db_all)
    _balances(st,email,db_all)


def render_deposit_page(st,user_email,db_all,db_exec,db_connect,database_is_durable,tron_treasury,bsc_treasury,allow_bsc_pegged,bsc_token_contract,bsc_rpc_url,trongrid_api_key,now_iso,record_event):
    _deposit_ui(st,user_email,db_all,db_exec,db_connect,database_is_durable,tron_treasury,bsc_treasury,
                allow_bsc_pegged,bsc_token_contract,bsc_rpc_url,trongrid_api_key,now_iso,record_event)


def sync_grid_deployment_queue(db_all,db_exec,now_iso):
    """Backfill gate events for already verified deposits with a matching wallet-ledger credit."""
    verified=db_all(
        "SELECT p.id,p.user_email,p.network,p.amount,p.txid,p.created_at "
        "FROM hh_payment_intents p JOIN hh_wallet_ledger l "
        "ON l.reference_id=p.id AND l.entry_type=? AND l.network=p.network AND lower(l.txid)=lower(p.txid) "
        "WHERE p.status=? AND p.txid IS NOT NULL ORDER BY p.created_at",
        ("confirmed_deposit_credit","Verified"))
    existing={str(r["payment_intent_id"]) for r in db_all("SELECT payment_intent_id FROM hh_grid_deployment_queue")}
    created=0
    for row in verified:
        intent_id=str(row["id"])
        if intent_id in existing:
            continue
        now=now_iso()
        db_exec(
            "INSERT INTO hh_grid_deployment_queue(id,payment_intent_id,user_email,network,amount,txid,requested_scope,status,reason,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()),intent_id,row["user_email"],row["network"],str(row["amount"]),row["txid"],"ALL GRIDS",
             "Blocked - user wallet liability",
             "Recovered from a verified payment intent and matching confirmed-deposit ledger credit. Deposits remain user liabilities, not company revenue or deployable grid budget.",
             now,now))
        existing.add(intent_id)
        created+=1
    return {"verified_receipts":len(verified),"gate_events_backfilled":created}


def render_user_treasury_overview_page(st,user_email,db_all,db_exec,database_is_durable,now_iso):
    """Show the signed-in user's verified receipts, actual available balance and settled withdrawals."""
    st.title("Payments & Treasury")
    st.empty()
    st.info("Automatic deposit reconciliation runs every 5 minutes.")

    try:
        ensure_payment_tables(db_exec,db_all)
        if not database_is_durable:
            st.error("Durable storage is not configured. Displayed records may not survive a host restart; real-money actions remain locked.")
        receipt_rows=db_all(
            "SELECT p.network,COUNT(*) AS receipt_count,COALESCE(SUM(CAST(p.amount AS NUMERIC)),0) AS total "
            "FROM hh_payment_intents p JOIN hh_wallet_ledger l "
            "ON l.reference_id=p.id AND l.entry_type=? AND l.network=p.network AND lower(l.txid)=lower(p.txid) "
            "WHERE p.user_email=? AND p.status=? AND p.txid IS NOT NULL GROUP BY p.network",
            ("confirmed_deposit_credit",user_email,"Verified"))
        payout_rows=db_all(
            "SELECT c.network,COUNT(*) AS payout_count,COALESCE(SUM(CAST(c.amount AS NUMERIC)),0) AS total "
            "FROM hh_cashout_requests c JOIN hh_wallet_ledger l "
            "ON l.reference_id=c.id AND l.entry_type=? AND l.network=c.network AND lower(l.txid)=lower(c.processed_txid) "
            "WHERE c.user_email=? AND c.status=? GROUP BY c.network",
            ("cashout_paid_on_chain",user_email,"Paid (verified on-chain)"))
        receipt_count=sum(int(x["receipt_count"]) for x in receipt_rows)
        payout_count=sum(int(x["payout_count"]) for x in payout_rows)
        accounts=db_all("SELECT network,available_balance,reserved_balance,updated_at FROM hh_wallet_accounts WHERE user_email=? ORDER BY network",(user_email,))
        a,b,c=st.columns(3)
        a.metric("Verified incoming receipts",receipt_count,help="Counts include only receipts with matching verified payment-intent and wallet-ledger entries.")
        b.metric("Verified outgoing payouts",payout_count,help="Counts include only payouts with matching verified on-chain settlement ledger entries.")
        c.metric("Wallet networks",len(accounts),help="Token balances are displayed per network; different token contracts are never added together.")
        if database_is_durable:
            try:
                scanner_state=db_all("SELECT network,updated_at,last_scanned_block,last_scanned_timestamp FROM hh_deposit_reconciler_state ORDER BY network")
                if scanner_state:
                    latest_scan=max(str(x.get("updated_at") or "") for x in scanner_state)
                    st.caption(f"Automatic reconciler state found · last checkpoint update: {latest_scan}")
                else:
                    st.warning("No reconciler checkpoint found. Check the latest scheduled workflow run.")
            except Exception:
                st.warning("Reconciler checkpoint missing. Check the latest scheduled workflow run.")
        account_by_network={x["network"]:x for x in accounts}
        receipt_by_network={x["network"]:x for x in receipt_rows}
        payout_by_network={x["network"]:x for x in payout_rows}
        networks=sorted(set(["TRON-TRC20","BSC-BEP20"]) | set(account_by_network) | set(receipt_by_network) | set(payout_by_network))
        balance_view=[]
        for network in networks:
            account=account_by_network.get(network,{})
            incoming_row=receipt_by_network.get(network,{})
            outgoing_row=payout_by_network.get(network,{})
            asset="USDT (Tether TRC-20)" if network=="TRON-TRC20" else ("BSC-USD (Binance-Peg)" if network=="BSC-BEP20" else "Configured token")
            balance_view.append({
                "Network":network,"Asset":asset,
                "Verified receipts":int(incoming_row.get("receipt_count") or 0),
                "Verified incoming amount":format(_decimal(incoming_row.get("total") or 0),".6f"),
                "Verified payouts":int(outgoing_row.get("payout_count") or 0),
                "Verified outgoing amount":format(_decimal(outgoing_row.get("total") or 0),".6f"),
                "Available balance":format(_decimal(account.get("available_balance") or 0),".6f"),
                "Reserved balance":format(_decimal(account.get("reserved_balance") or 0),".6f"),
                "Last wallet update":account.get("updated_at") or "—",
            })
        st.subheader("Network-by-network receipt, payout and balance reconciliation")
        render_bank_table(balance_view,use_container_width=True,hide_index=True)
        st.empty()
        st.subheader("Verified incoming receipt history")
        deposits=db_all(
            "SELECT p.created_at,p.network,p.amount,p.status,p.txid,p.verified_at "
            "FROM hh_payment_intents p JOIN hh_wallet_ledger l "
            "ON l.reference_id=p.id AND l.entry_type=? AND l.network=p.network AND lower(l.txid)=lower(p.txid) "
            "WHERE p.user_email=? AND p.status=? ORDER BY p.verified_at DESC LIMIT 100",
            ("confirmed_deposit_credit",user_email,"Verified"))
        if deposits: render_bank_table(deposits,use_container_width=True,hide_index=True)
        else: st.info("No records.")
        st.subheader("Outgoing payments")
        payouts=db_all(
            "SELECT created_at,network,amount,status,processed_txid,updated_at "
            "FROM hh_cashout_requests WHERE user_email=? ORDER BY created_at DESC LIMIT 100",(user_email,))
        if payouts: render_bank_table(payouts,use_container_width=True,hide_index=True)
        else: st.info("No records.")
    except Exception as exc:
        st.error(f"Treasury reconciliation unavailable ({type(exc).__name__}). No unverified amount is represented as verified.")


def render_cashout_page(st,user_email,db_all,db_exec,db_connect,database_is_durable,tron_treasury,bsc_treasury,allow_bsc_pegged,bsc_token_contract,bsc_rpc_url,trongrid_api_key,now_iso,record_event):
    ensure_payment_tables(db_exec, db_all)
    st.title("Withdraw / Cash Out")
    st.caption("Confirmed balances only · payouts are sent externally and verified on-chain.")
    if not database_is_durable: st.error("LOCKED: configure managed PostgreSQL (DATABASE_URL) before cash-out."); return
    networks=["TRON-TRC20"]+(["BSC-BEP20"] if allow_bsc_pegged else [])
    network=st.selectbox("Network",networks,key="hh_cashout_network")
    ac=db_all("SELECT available_balance,reserved_balance FROM hh_wallet_accounts WHERE user_email=? AND network=?",(user_email,network))
    available=_decimal(ac[0]["available_balance"]) if ac else Decimal("0")
    reserved=_decimal(ac[0]["reserved_balance"]) if ac else Decimal("0")
    a,b=st.columns(2); a.metric("Available",f"{available:.6f} USDT"); b.metric("Reserved",f"{reserved:.6f} USDT")
    with st.form("hh_cashout_form"):
        amount_raw=st.text_input("Amount (minimum 1 USDT)",value="1.00")
        destination=st.text_input("Destination wallet address")
        confirm=st.checkbox("I verified the destination address and network.")
        submit=st.form_submit_button("Request real cash-out",type="primary",use_container_width=True)
    if submit:
        try:
            amount=_decimal(amount_raw)
            if not confirm: raise PaymentError("Confirm the destination address and network.")
            treasury=tron_treasury if network=="TRON-TRC20" else bsc_treasury
            reqid=_new_cashout(db_connect,database_is_durable,user_email,network,amount,destination,treasury,now_iso)
            record_event(user_email,"cashout_requested",f"{reqid}:{network}:{amount}")
            st.success(f"Request {reqid} created. {amount} USDT is reserved, not transferred. Admin must send the payment and verify its TXID.")
            st.rerun()
        except Exception as exc: st.error(str(exc) if isinstance(exc,PaymentError) else f"Could not create request ({type(exc).__name__}).")
    requests_list=db_all("SELECT id,network,amount,destination,status,admin_note,created_at,updated_at,processed_txid FROM hh_cashout_requests WHERE user_email=? ORDER BY created_at DESC",(user_email,))
    if requests_list: st.subheader("Your requests"); render_bank_table(requests_list,use_container_width=True,hide_index=True)
    _balances(st,user_email,db_all)


def render_payment_ops_page(st,user_email,db_all,db_exec,db_connect,database_is_durable,is_admin,tron_treasury,bsc_treasury,bsc_token_contract,bsc_rpc_url,trongrid_api_key,now_iso,record_event):
    ensure_payment_tables(db_exec, db_all)
    st.title("Payment Operations — Admin Only")
    if not is_admin: st.error("Administrator access required."); return
    st.warning("A screenshot or reference is not payment proof. Verify network, token, addresses, amount and confirmations.")
    if not database_is_durable: st.error("LOCKED: managed PostgreSQL is required."); return
    try:
        gate_sync=sync_grid_deployment_queue(db_all,db_exec,now_iso)
        if gate_sync["gate_events_backfilled"]:
            st.success(f"Reconciled {gate_sync['gate_events_backfilled']} previously verified receipt(s) into the grid gate.")
    except Exception as exc:
        st.warning(f"Receipt-to-grid-gate synchronization needs attention ({type(exc).__name__}).")
    st.subheader("Sending-wallet ownership review")
    st.empty()
    wallet_requests=db_all("SELECT * FROM hh_verified_sender_wallets WHERE status=? ORDER BY created_at",( "Pending verification",))
    if not wallet_requests: st.info("No records.")
    for wallet in wallet_requests:
        with st.container(border=True):
            st.markdown(f"**{wallet['user_email']}** · {wallet['network']} · Pending verification")
            st.code(wallet["address"],language=None)
            with st.form(f"hh_wallet_review_{wallet['id']}"):
                wallet_decision=st.selectbox("Wallet decision",["Pending verification","Verified","Rejected"],key=f"hh_wallet_decision_{wallet['id']}")
                wallet_method=st.selectbox("Ownership evidence checked",["Signed wallet challenge","Independent wallet/provider proof","Other documented ownership evidence"],key=f"hh_wallet_method_{wallet['id']}")
                evidence=st.text_input("Evidence reference (no private keys or seed phrases)",key=f"hh_wallet_evidence_{wallet['id']}")
                wallet_note=st.text_area("Review note",key=f"hh_wallet_note_{wallet['id']}")
                wallet_save=st.form_submit_button("Save wallet review")
            if wallet_save:
                try:
                    if wallet_decision=="Verified" and (not evidence.strip() or not wallet_note.strip()):
                        raise PaymentError("To approve a wallet, record an evidence reference and review note.")
                    db_exec("UPDATE hh_verified_sender_wallets SET status=?,verification_method=?,evidence_reference=?,verified_by=?,verification_note=?,updated_at=? WHERE id=?",
                        (wallet_decision,wallet_method if wallet_decision=="Verified" else None,evidence.strip() or None,user_email,wallet_note.strip() or None,now_iso(),wallet["id"]))
                    record_event(user_email,"sender_wallet_reviewed",f"{wallet['id']}:{wallet_decision}")
                    st.success("Wallet review saved."); st.rerun()
                except Exception as exc:
                    st.error(str(exc) if isinstance(exc,PaymentError) else f"Wallet review failed ({type(exc).__name__}).")
    st.divider()
    st.subheader("Cash-out review")
    cashouts=db_all("SELECT * FROM hh_cashout_requests ORDER BY created_at DESC")
    if not cashouts: st.info("No records.")
    for req in cashouts:
        with st.container(border=True):
            st.markdown(f"**{req['user_email']}** · {req['amount']} USDT · {req['network']} · **{req['status']}**")
            st.caption(f"Request {req['id']} · {req['created_at']}"); st.code(req["destination"],language=None)
            if req.get("admin_note"): st.write(req["admin_note"])
            if req["status"] in {"Requested","Under review"}:
                with st.form(f"hh_review_{req['id']}"):
                    decision=st.selectbox("Decision",["Under review","Approved for manual processing","Rejected"],key=f"hh_decision_{req['id']}")
                    note=st.text_area("Admin note",key=f"hh_note_{req['id']}")
                    save=st.form_submit_button("Save review decision")
                if save:
                    try:
                        _cashout_decision(db_connect,database_is_durable,req["id"],decision,note,now_iso)
                        record_event(user_email,"cashout_reviewed",f"{req['id']}:{decision}"); st.success("Decision saved."); st.rerun()
                    except Exception as exc: st.error(str(exc) if isinstance(exc,PaymentError) else f"Review failed ({type(exc).__name__}).")
            elif req["status"]=="Approved for manual processing":
                st.info("Send the exact amount and token from treasury. Never enter private keys or seed phrases.")
                txid=st.text_input("Outgoing TXID/hash",key=f"hh_out_txid_{req['id']}")
                if st.button("Verify outgoing transfer and mark paid",key=f"hh_out_verify_{req['id']}",type="primary"):
                    try:
                        treasury=tron_treasury if req["network"]=="TRON-TRC20" else bsc_treasury
                        result=verify_transfer(req["network"],txid.strip(),_decimal(req["amount"]),treasury,"out",destination=req["destination"],
                            bsc_token_contract=bsc_token_contract,bsc_rpc_url=bsc_rpc_url,trongrid_api_key=trongrid_api_key)
                        if result.get("status")=="Verified":
                            _cashout_paid(db_connect,database_is_durable,req["id"],txid.strip(),result,now_iso)
                            record_event(user_email,"cashout_verified_paid",f"{req['id']}:{txid.strip()}"); st.success(result["message"]); st.rerun()
                        else:
                            db_exec("UPDATE hh_cashout_requests SET admin_note=?,updated_at=? WHERE id=?",(result.get("message","Not verified"),now_iso(),req["id"]))
                            st.warning(result.get("message","Transfer not confirmed; cash-out remains unpaid."))
                    except Exception as exc: st.error(str(exc) if isinstance(exc,PaymentError) else f"Verification failed safely ({type(exc).__name__}); cash-out remains unpaid.")
    ledger=db_all("SELECT created_at,user_email,network,entry_type,amount,reference_id,txid,notes FROM hh_wallet_ledger ORDER BY created_at DESC LIMIT 200")
    if ledger:
        import pandas as pd
        st.subheader("Wallet ledger (latest 200 entries)"); render_bank_table(ledger,use_container_width=True,hide_index=True)
        st.download_button("Download ledger CSV",pd.DataFrame(ledger).to_csv(index=False).encode("utf-8"),file_name="cedars_empire_verified_wallet_ledger.csv",mime="text/csv")
    deposits=db_all("SELECT id,user_email,package_label,amount,network,status,txid,last_attempted_txid,consent_accepted,consent_version,consented_at,verification_note,created_at,verified_at FROM hh_payment_intents ORDER BY created_at DESC LIMIT 200")
    if deposits: st.subheader("Deposit verification queue"); render_bank_table(deposits,use_container_width=True,hide_index=True)
    unreconciled=db_all(
        "SELECT p.id,p.user_email,p.network,p.amount,p.txid,p.verified_at,p.verification_note "
        "FROM hh_payment_intents p WHERE p.status=? AND p.txid IS NOT NULL AND NOT EXISTS "
        "(SELECT 1 FROM hh_wallet_ledger l WHERE l.reference_id=p.id AND l.entry_type=? AND l.network=p.network AND lower(l.txid)=lower(p.txid)) "
        "ORDER BY p.verified_at DESC LIMIT 200",("Verified","confirmed_deposit_credit"))
    if unreconciled:
        st.error("Some intents are marked Verified but have no matching wallet-ledger credit. These are excluded from verified balances and the grid gate until chain re-verification repairs them.")
        render_bank_table(unreconciled,use_container_width=True,hide_index=True)

    deployment_events=db_all("SELECT created_at,user_email,network,amount,txid,requested_scope,status,reason FROM hh_grid_deployment_queue ORDER BY created_at DESC LIMIT 200")
    st.subheader("Treasury receipts → AI Grid deployment gate")
    st.caption("User deposits are wallet liabilities, not company revenue or deployable grid funds.")
    if deployment_events:
        render_bank_table(deployment_events,use_container_width=True,hide_index=True)
        st.download_button("Download treasury-to-grid event log (CSV)",pd.DataFrame(deployment_events).to_csv(index=False).encode("utf-8"),
                           file_name="cedars_empire_grid_deployment_gate.csv",mime="text/csv")
    else:
        st.info("No records.")
