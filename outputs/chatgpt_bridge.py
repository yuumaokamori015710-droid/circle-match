"""Small authenticated HTTP adapter; deploy beside chatgpt_plan on a private disk.

No X credentials, public chat UI, arbitrary URLs, tools, or paid API fallback.
The embedding web server only needs to call handle_http for this prefix.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import threading
from datetime import datetime, timedelta, timezone

import chatgpt_plan as plan

PREFIX = "/_tweet-bot/"
ROOT = Path("/var/data/tweet-bot")
JST = timezone(timedelta(hours=9))
MAX_DAILY_GENERATIONS = 8  # Three posts plus bounded setup/recovery attempts.
_gate = threading.Lock()


class BridgeError(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code


def atomic_json(path, data):
    import tempfile
    fd, name = tempfile.mkstemp(dir=path.parent, prefix="bridge-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(data, out, ensure_ascii=True)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def operate(action, payload, root=ROOT):
    store = plan.Store(root / "auth")
    if action == "bootstrap":
        # The local OAuth client has already validated the identity. Transfer only
        # that selected session over authenticated TLS, never replace a live one.
        with store.locked():
            data = store.read()
            if data["accounts"]:
                raise BridgeError(409, "already_connected")
            account = payload.get("account", {})
            required = ("client_id", "subject", "access_token", "refresh_token", "id_token", "model")
            if (not isinstance(account, dict) or any(not isinstance(account.get(k), str) or not account[k] for k in required)
                    or not account["client_id"].startswith("oaiapp_")
                    or account.get("included_only_verified") is not True
                    or plan.PLAN_SCOPE not in account.get("scopes", [])
                    or type(account.get("expires_at")) not in (int, float)):
                raise BridgeError(400, "invalid_connection")
            allowed = (*required, "email", "scopes", "expires_at", "included_only_verified")
            account = {k: account[k] for k in allowed if k in account}
            data["accounts"] = {account["client_id"]: account}
            data["active"] = account["client_id"]
            # Store.read creates this server's host ID; never copy the laptop ID.
            store.save(data)
        return {"status": "connected"}
    if action == "status":
        plan.require_ready(store)
        with store.locked():
            account = plan.active_account(store.read())
            return {"status": "ready", "model": account["model"],
                    "client_id": account["client_id"], "provider": "chatgpt", "paid_fallback": False}
    if action != "generate":
        raise BridgeError(404, "not_found")
    prompt, request_id = payload.get("prompt"), payload.get("request_id")
    if (not isinstance(prompt, str) or not prompt or len(prompt.encode("utf-8")) > 20000
            or not isinstance(request_id, str) or not re.fullmatch(r"[0-9a-f]{64}", request_id)
            or not secrets.compare_digest(request_id, hashlib.sha256(prompt.encode()).hexdigest())):
        raise BridgeError(400, "invalid_request")
    plan.require_ready(store)
    ledger_path = store.root / "generation-ledger.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    today = datetime.now(JST).date().isoformat()
    ledger = {today: ledger.get(today, {})}
    entries = ledger[today]
    if request_id in entries:
        cached = entries[request_id]
        if cached.get("status") == "complete":
            return {"provider": "chatgpt", "text": cached["text"]}
        raise BridgeError(409, "previous_generation_not_complete")
    if len(entries) >= MAX_DAILY_GENERATIONS:
        raise BridgeError(429, "daily_generation_limit")
    # Reserve durably before inference. A failed/ambiguous run is never repeated.
    entries[request_id] = {"status": "reserved"}
    atomic_json(ledger_path, ledger)
    text = plan.generate_text(prompt, store)
    entries[request_id] = {"status": "complete", "text": text}
    atomic_json(ledger_path, ledger)
    return {"provider": "chatgpt", "text": text}


def handle_http(handler, root=ROOT):
    if not handler.path.startswith(PREFIX):
        return False
    code, result = 503, {"error": "unavailable"}
    acquired = False
    try:
        key = os.environ.get("TWEETBOT_BRIDGE_KEY", "")
        if os.environ.get("TWEETBOT_BRIDGE_ENABLED") != "true" or not re.fullmatch(r"[0-9a-f]{64}", key):
            raise BridgeError(503, "not_configured")
        if not secrets.compare_digest(handler.headers.get("Authorization", ""), "Bearer " + key):
            raise BridgeError(401, "unauthorized")
        if handler.command != "POST":
            raise BridgeError(405, "method_not_allowed")
        if handler.headers.get("Transfer-Encoding") or handler.headers.get("Content-Type", "").split(";")[0] != "application/json":
            raise BridgeError(400, "invalid_request")
        try:
            size = int(handler.headers.get("Content-Length", "0"))
        except ValueError:
            raise BridgeError(400, "invalid_request") from None
        if not 2 <= size <= 64000:
            raise BridgeError(413, "request_too_large")
        acquired = _gate.acquire(blocking=False)
        if not acquired:
            raise BridgeError(429, "busy")
        handler.connection.settimeout(10)
        raw = handler.rfile.read(size)
        if len(raw) != size:
            raise BridgeError(400, "incomplete_request")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise BridgeError(400, "invalid_request")
        result = operate(handler.path[len(PREFIX):], payload, root)
        code = 200
    except BridgeError as exc:
        code, result = exc.status, {"error": exc.code}
    except (ValueError, UnicodeError):
        code, result = 400, {"error": "invalid_request_or_connection"}
    except Exception:
        # Neither HTTP error bodies nor token/SDK exceptions belong in host logs.
        code, result = 503, {"error": "generation_unavailable"}
    finally:
        if acquired:
            _gate.release()
    body = json.dumps(result, ensure_ascii=True).encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Connection", "close")
    handler.end_headers()
    handler.close_connection = True
    try:
        handler.wfile.write(body)
    except (ConnectionError, OSError):
        pass
    return True
