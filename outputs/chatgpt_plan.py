"""Opt-in ChatGPT plan usage through the public Sign in with ChatGPT flow.

Credentials stay in protected local storage. No API-key or paid-provider fallback.
GitHub-hosted credential persistence is deliberately not implemented.
"""

import argparse
import base64
from contextlib import contextmanager
import hashlib
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
from urllib.parse import parse_qs, urlencode, urlparse
from uuid import uuid4

import requests

ISSUER = "https://auth.openai.com"
AUTHORIZE = ISSUER + "/api/accounts/authorize"
TOKEN_ENDPOINT = ISSUER + "/api/accounts/oauth/token"
JWKS = ISSUER + "/.well-known/jwks.json"
RESOURCE = "https://api.openai.com/v1"
PLAN_SCOPE = "chatgpt.tokens.use.direct"
SCOPES = "openid profile email offline_access resource.invoke " + PLAN_SCOPE
USAGE_URL = "https://chatgpt.com/settings/usage"
DEFAULT_ROOT = Path(__file__).resolve().parent / ".chatgpt-auth"


class ChatGPTUnavailable(ValueError):
    """Safe, fixed messages only; never include token endpoint or SDK bodies."""


def local_only():
    if os.environ.get("GITHUB_ACTIONS") == "true":
        raise ChatGPTUnavailable("chatgpt_hosted_runtime_not_configured")


class Store:
    def __init__(self, root=None):
        local_only()
        self.root = Path(root) if root is not None else DEFAULT_ROOT
        if self.root.is_symlink():
            raise ChatGPTUnavailable("unsafe_credential_directory")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name == "nt":
            owner = subprocess.check_output(["whoami"], text=True, timeout=10).strip()
            result = subprocess.run(["icacls", str(self.root), "/inheritance:r", "/grant:r",
                                     owner + ":(OI)(CI)F"], capture_output=True, timeout=10)
            if result.returncode:
                raise ChatGPTUnavailable("credential_permissions_failed")
        else:
            self.root.chmod(0o700)
        self.path = self.root / "accounts.json"

    @contextmanager
    def locked(self):
        path = self.root / "session.lock"
        if os.name != "nt":
            import fcntl
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            try:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise ChatGPTUnavailable("chatgpt_session_busy") from None
                yield
            finally:
                os.close(fd)  # OS lock releases even when the host kills a process.
            return
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            raise ChatGPTUnavailable("chatgpt_session_busy") from None
        try:
            os.close(fd)
            yield
        finally:
            path.unlink()

    def read(self):
        if not self.path.exists():
            return {"version": 1, "host_id": "urn:uuid:" + str(uuid4()), "accounts": {}, "active": None}
        if self.path.is_symlink():
            raise ChatGPTUnavailable("unsafe_credential_file")
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data["version"] != 1 or not isinstance(data["accounts"], dict):
                raise ValueError()
            return data
        except (KeyError, TypeError, ValueError):
            raise ChatGPTUnavailable("invalid_credential_store") from None

    def save(self, data):
        fd, name = tempfile.mkstemp(dir=self.root, prefix="session-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            Path(name).unlink(missing_ok=True)


def active_account(data):
    account = data["accounts"].get(data.get("active"))
    if not account:
        raise ChatGPTUnavailable("chatgpt_login_required")
    if account.get("transferred_to"):
        raise ChatGPTUnavailable("chatgpt_session_moved_to_persistent_host")
    return account


def verify_identity(id_token, client_id, nonce=None, subject=None):
    import jwt

    try:
        response = requests.get(JWKS, timeout=20, allow_redirects=False)
        if response.status_code != 200:
            raise ChatGPTUnavailable("chatgpt_signing_keys_unavailable")
        header = jwt.get_unverified_header(id_token)
        if header.get("alg") not in {"RS256", "ES256"}:
            raise ChatGPTUnavailable("chatgpt_id_token_algorithm_rejected")
        keys = [key for key in response.json()["keys"] if key.get("kid") == header.get("kid")]
        if len(keys) != 1:
            raise ChatGPTUnavailable("chatgpt_id_token_signing_key_missing")
        key = jwt.PyJWK.from_dict(keys[0]).key
        claims = jwt.decode(id_token, key, algorithms=[header["alg"]], issuer=ISSUER,
                            audience=client_id, options={"require": ["exp", "iss", "sub", "aud"]})
        if nonce is not None and not secrets.compare_digest(claims.get("nonce", ""), nonce):
            raise ChatGPTUnavailable("chatgpt_id_token_nonce_mismatch")
        if subject is not None and claims["sub"] != subject:
            raise ChatGPTUnavailable("chatgpt_id_token_account_mismatch")
        return claims
    except ChatGPTUnavailable:
        raise
    except jwt.ExpiredSignatureError:
        raise ChatGPTUnavailable("chatgpt_id_token_expired") from None
    except jwt.ImmatureSignatureError:
        raise ChatGPTUnavailable("chatgpt_id_token_not_yet_valid_check_clock") from None
    except jwt.InvalidAudienceError:
        raise ChatGPTUnavailable("chatgpt_id_token_audience_mismatch") from None
    except jwt.InvalidIssuerError:
        raise ChatGPTUnavailable("chatgpt_id_token_issuer_mismatch") from None
    except jwt.InvalidSignatureError:
        raise ChatGPTUnavailable("chatgpt_id_token_signature_mismatch") from None
    except jwt.MissingRequiredClaimError:
        raise ChatGPTUnavailable("chatgpt_id_token_missing_required_claim") from None
    except jwt.InvalidTokenError:
        raise ChatGPTUnavailable("chatgpt_id_token_invalid") from None
    except Exception:
        raise ChatGPTUnavailable("chatgpt_identity_validation_failed") from None


def exchange(fields):
    try:
        response = requests.post(TOKEN_ENDPOINT, data=fields, timeout=30, allow_redirects=False)
        if response.status_code != 200:
            raise ChatGPTUnavailable("chatgpt_reauthorization_required")
        return response.json()
    except requests.RequestException:
        raise ChatGPTUnavailable("chatgpt_auth_network_error") from None


def token_record(tokens, client_id, nonce=None, previous=None):
    previous = previous or {}
    try:
        if tokens["token_type"].lower() != "bearer" or not 60 <= int(tokens["expires_in"]) <= 86400:
            raise ValueError()
        if not all(isinstance(tokens[k], str) and tokens[k] for k in ("access_token", "refresh_token")):
            raise ValueError()
        scopes = tokens.get("scope", " ".join(previous.get("scopes", []))).split()
        if PLAN_SCOPE not in scopes:
            raise ChatGPTUnavailable("chatgpt_plan_permission_missing")
        id_token = tokens.get("id_token")
        if nonce is not None and not id_token:
            raise ValueError()
        identity = (verify_identity(id_token, client_id, nonce, previous.get("subject"))
                    if id_token else {"sub": previous["subject"], "email": previous.get("email", "")})
        return {**previous, "client_id": client_id, "subject": identity["sub"],
                "email": identity.get("email", previous.get("email", "")), "scopes": scopes,
                "access_token": tokens["access_token"], "refresh_token": tokens["refresh_token"],
                "id_token": id_token or previous.get("id_token"),
                "expires_at": time.time() + int(tokens["expires_in"]),
                "included_only_verified": previous.get("included_only_verified", False)}
    except ChatGPTUnavailable:
        raise
    except (KeyError, TypeError, ValueError):
        raise ChatGPTUnavailable("invalid_chatgpt_token_response") from None


def fresh_account(store, data):
    account = active_account(data)
    if PLAN_SCOPE not in account.get("scopes", []):
        raise ChatGPTUnavailable("chatgpt_plan_permission_missing")
    if account["expires_at"] <= time.time() + 120:
        tokens = exchange({"grant_type": "refresh_token", "client_id": account["client_id"],
                           "refresh_token": account["refresh_token"], "resource": RESOURCE})
        account = token_record(tokens, account["client_id"], previous=account)
        data["accounts"][account["client_id"]] = account
        # Persist the rotating refresh token before using the replacement access token.
        store.save(data)
    return account


def available_models(account):
    try:
        response = requests.get(RESOURCE + "/models", timeout=20, allow_redirects=False,
                                headers={"Authorization": "Bearer " + account["access_token"]})
        if response.status_code != 200:
            raise ChatGPTUnavailable("chatgpt_model_catalog_unavailable")
        return [{"slug": row["slug"], "display_name": row["display_name"]}
                for row in response.json()["models"] if row.get("visibility") == "list"]
    except (requests.RequestException, KeyError, TypeError, ValueError):
        raise ChatGPTUnavailable("chatgpt_model_catalog_unavailable") from None


def require_ready(store=None):
    local_only()
    store = store or Store()
    with store.locked():
        account = active_account(store.read())
        if PLAN_SCOPE not in account.get("scopes", []):
            raise ChatGPTUnavailable("chatgpt_plan_permission_missing")
        if account.get("included_only_verified") is not True:
            raise ChatGPTUnavailable("disable_chatgpt_paid_credit_usage_first")
        if not account.get("model"):
            raise ChatGPTUnavailable("choose_available_chatgpt_model_first")


def generate_text(prompt, store=None):
    from openai import OpenAI, Omit

    local_only()
    if not isinstance(prompt, str) or len(prompt.encode("utf-8")) > 20000:
        raise ChatGPTUnavailable("chatgpt_prompt_too_large")
    store = store or Store()
    with store.locked():
        data = store.read()
        account = active_account(data)
        if account.get("included_only_verified") is not True:
            raise ChatGPTUnavailable("disable_chatgpt_paid_credit_usage_first")
        if not account.get("model"):
            raise ChatGPTUnavailable("choose_available_chatgpt_model_first")
        account = fresh_account(store, data)
        try:
            # This route must not inherit OPENAI_API_KEY, project, or custom API URLs.
            with OpenAI(api_key=account["access_token"], base_url=RESOURCE, organization="", project="",
                        default_headers={"OpenAI-Organization": Omit(), "OpenAI-Project": Omit()},
                        max_retries=0, timeout=45) as client:
                with client.responses.create(model=account["model"], store=False, stream=True,
                                             input=[{"role": "user", "content": prompt}]) as stream:
                    chunks, size, completed, start = [], 0, False, time.monotonic()
                    for event in stream:
                        if time.monotonic() - start > 90:
                            raise ChatGPTUnavailable("chatgpt_generation_timed_out")
                        if event.type == "response.output_text.delta":
                            size += len(event.delta)
                            if size > 8000:
                                raise ChatGPTUnavailable("chatgpt_output_too_large")
                            chunks.append(event.delta)
                        elif event.type == "response.completed":
                            completed = True
                        elif event.type in {"response.failed", "response.incomplete", "error"}:
                            raise ChatGPTUnavailable("chatgpt_generation_unavailable_or_limit_reached")
                    if not completed or not chunks:
                        raise ChatGPTUnavailable("chatgpt_generation_incomplete")
                    return "".join(chunks)
        except ChatGPTUnavailable:
            raise
        except Exception:
            raise ChatGPTUnavailable("chatgpt_generation_unavailable_or_limit_reached") from None


class LoginAttempt:
    def __init__(self, data, redirect_uri, account_id=None, remember_client=None):
        self.account = data["accounts"].get(account_id) if account_id else None
        if account_id and not self.account:
            raise ChatGPTUnavailable("unknown_chatgpt_account")
        self.client_id = self.account["client_id"] if self.account else data.get("pending_client_id", "dynamic_agent_client")
        self.remember_client = remember_client
        self.state, self.nonce, self.verifier = (secrets.token_urlsafe(32) for _ in range(3))
        self.deadline = time.monotonic() + 600
        self.consumed = False
        self.redirect_uri = redirect_uri
        fields = {"client_id": self.client_id, "ext_agent_host_id": data["host_id"],
                  "response_type": "code", "redirect_uri": redirect_uri, "scope": SCOPES,
                  "resource": RESOURCE, "state": self.state, "nonce": self.nonce,
                  "code_challenge_method": "S256", "code_challenge": base64.urlsafe_b64encode(
                      hashlib.sha256(self.verifier.encode()).digest()).decode().rstrip("=")}
        if self.client_id == "dynamic_agent_client":
            fields["agent_name_hint"] = "tweet-bot"
        # No retained ID token in the URL: account selection remains explicit on sign-in.
        self.url = AUTHORIZE + "?" + urlencode(fields)

    def complete(self, query):
        if self.consumed or time.monotonic() > self.deadline:
            raise ChatGPTUnavailable("chatgpt_login_expired")
        params = parse_qs(query, keep_blank_values=True)
        if any(len(value) != 1 for value in params.values()):
            raise ChatGPTUnavailable("invalid_chatgpt_callback")
        state = params.get("state", [""])[0]
        if not secrets.compare_digest(state, self.state):
            raise ChatGPTUnavailable("chatgpt_login_state_mismatch")
        self.consumed = True
        if "error" in params:
            raise ChatGPTUnavailable("chatgpt_login_declined")
        issued = params.get("client_id", [self.client_id])[0]
        if (not issued or issued == "dynamic_agent_client"
                or (self.client_id != "dynamic_agent_client" and issued != self.client_id)):
            raise ChatGPTUnavailable("chatgpt_client_mismatch")
        code = params.get("code", [""])[0]
        if not code:
            raise ChatGPTUnavailable("invalid_chatgpt_callback")
        if self.remember_client and not self.account:
            self.remember_client(issued)
        tokens = exchange({"grant_type": "authorization_code", "client_id": issued, "code": code,
                           "code_verifier": self.verifier, "redirect_uri": self.redirect_uri, "resource": RESOURCE})
        return token_record(tokens, issued, self.nonce, self.account)


def login(store, account_id=None):
    with store.locked():
        data = store.read()
        store.save(data)
        result = {}
        entry = "/connect/" + secrets.token_urlsafe(24)

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass  # The OAuth callback URL contains a one-time code.

            def page(self, status, body):
                content = ("<!doctype html><meta charset='utf-8'><title>tweet-bot: ChatGPT</title>"
                           "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                           "<main><h1>tweet-bot</h1>" + body + "</main>").encode()
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Content-Security-Policy", "default-src 'none'; base-uri 'none'; frame-ancestors 'none'")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            def do_GET(self):
                if self.headers.get("Host") != f"127.0.0.1:{server.server_port}":
                    self.page(400, "Invalid host")
                    return
                path = urlparse(self.path)
                if path.path == entry:
                    self.page(200, "<p>Use your ChatGPT plan for tweet drafts. No API key is used.</p>"
                              "<p>Keep paid-credit usage disabled in ChatGPT Settings.</p>"
                              f"<p><a href='{entry}/start'>Continue with ChatGPT</a></p>"
                              f"<p><a href='{USAGE_URL}' target='_blank' rel='noreferrer'>Manage usage</a></p>")
                elif path.path == entry + "/start":
                    self.send_response(302)
                    self.send_header("Location", attempt.url)
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Referrer-Policy", "no-referrer")
                    self.end_headers()
                elif path.path == "/auth/callback":
                    try:
                        account = attempt.complete(path.query)
                        data["accounts"][account["client_id"]] = account
                        data["active"] = account["client_id"]
                        data.pop("pending_client_id", None)
                        store.save(data)
                        result["status"] = "connected"
                        self.page(200, "<p>ChatGPT connection saved. You may close this window.</p>"
                                  "<p>Posting remains disabled until setup and checks complete.</p>")
                    except ChatGPTUnavailable as exc:
                        if attempt.consumed:
                            result["status"] = str(exc)
                        self.page(400, "<p>Connection not completed: " + escape(str(exc)) + "</p>")
                else:
                    self.page(404, "Not found")

        with HTTPServer(("127.0.0.1", 0), Handler) as server:
            server.timeout = 1
            def remember_client(client_id):
                data["pending_client_id"] = client_id
                store.save(data)
            attempt = LoginAttempt(data, f"http://127.0.0.1:{server.server_port}/auth/callback", account_id, remember_client)
            print(json.dumps({"status": "login_required", "url": f"http://127.0.0.1:{server.server_port}{entry}"}), flush=True)
            while not result and time.monotonic() <= attempt.deadline:
                server.handle_request()
        return result or {"status": "chatgpt_login_expired"}


def main():
    parser = argparse.ArgumentParser(description="Use the ChatGPT plan; never a paid API-key fallback")
    parser.add_argument("command", choices=["login", "status", "models", "select-model", "confirm-included-only"])
    parser.add_argument("--account", help="Saved client ID for reauthorization")
    parser.add_argument("--model")
    args = parser.parse_args()
    store = Store()
    if args.command == "login":
        result = login(store, args.account)
    else:
        with store.locked():
            data = store.read()
            if args.command == "status":
                result = {"active": data["active"], "accounts": [
                    {k: account.get(k) for k in ("client_id", "email", "model", "included_only_verified")}
                    for account in data["accounts"].values()], "manage_usage": USAGE_URL}
            elif args.command == "confirm-included-only":
                account = active_account(data)
                account["included_only_verified"] = True
                store.save(data)
                result = {"status": "included_only_attested", "manage_usage": USAGE_URL}
            else:
                account = fresh_account(store, data)
                models = available_models(account)
                if args.command == "select-model":
                    if args.model not in {row["slug"] for row in models}:
                        raise ChatGPTUnavailable("chatgpt_model_not_available")
                    account["model"] = args.model
                    store.save(data)
                    result = {"status": "model_selected", "model": args.model}
                else:
                    result = {"models": models}
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(str(exc) if isinstance(exc, ChatGPTUnavailable) else "chatgpt_setup_failed") from None
