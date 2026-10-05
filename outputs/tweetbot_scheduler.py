"""Opt-in Render clock for one fixed GitHub workflow, without X credentials."""

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sqlite3
import threading

import requests

JST = timezone(timedelta(hours=9))
TIMES = ("07:30", "08:30", "12:10", "13:10", "21:15", "22:15")
DISPATCH_URL = "https://api.github.com/repos/yuumaokamori015710-droid/tweet-bot/actions/workflows/growth.yml/dispatches"
ROOT = Path("/var/data/tweet-bot/scheduler")
_thread = None
_start_lock = threading.Lock()


def configured():
    return (os.environ.get("TWEETBOT_SCHEDULER_ENABLED") == "true"
            and os.environ.get("TWEETBOT_GITHUB_DISPATCH_TOKEN", "").startswith("github_pat_"))


def due_times(now):
    if now.tzinfo is None:
        raise ValueError("A timezone-aware clock is required")
    now = now.astimezone(JST)
    due = []
    for value in TIMES:
        hour, minute = map(int, value.split(":"))
        at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if timedelta(0) <= now - at <= timedelta(minutes=10):
            due.append(at)
    return due


class Scheduler:
    def __init__(self, root=ROOT, send=None):
        self.root = Path(root)
        self.send = send or requests.post

    def connection(self):
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = self.root / "dispatches.sqlite3"
        conn = sqlite3.connect(path, timeout=5)
        os.chmod(path, 0o600)
        conn.execute("CREATE TABLE IF NOT EXISTS dispatches "
                     "(event_id TEXT PRIMARY KEY, at TEXT NOT NULL, mode TEXT NOT NULL, "
                     "status TEXT NOT NULL, http_status INTEGER)")
        conn.commit()
        return conn

    def dispatch(self, event_id, mode, now):
        if not configured():
            return {"status": "disabled"}
        if mode not in {"run", "preview"}:
            raise ValueError("Unsupported scheduler mode")
        now = now.astimezone(JST)
        conn = self.connection()
        try:
            # A committed claim precedes the HTTP side effect. An ambiguous
            # response cannot trigger a second dispatch after a process restart.
            with conn:
                inserted = conn.execute("INSERT OR IGNORE INTO dispatches VALUES (?, ?, ?, 'claimed', NULL)",
                                        (event_id, now.isoformat(), mode)).rowcount
            if not inserted:
                return {"status": "already_attempted", "event_id": event_id}
            status, http_status = "uncertain", None
            try:
                response = self.send(DISPATCH_URL, timeout=20, allow_redirects=False, headers={
                    "Authorization": "Bearer " + os.environ["TWEETBOT_GITHUB_DISPATCH_TOKEN"],
                    "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
                    json={"ref": "main", "inputs": {"mode": mode, "source": "render"}})
                http_status = response.status_code
                status = "dispatched" if http_status == 204 else "rejected"
            except requests.RequestException:
                pass
            with conn:
                conn.execute("UPDATE dispatches SET status=?, http_status=? WHERE event_id=?",
                             (status, http_status, event_id))
            return {"status": status, "event_id": event_id, "http_status": http_status}
        finally:
            conn.close()

    def tick(self, now):
        if not configured():
            return []
        return [self.dispatch(at.isoformat(), "run", now) for at in due_times(now)]

    def probe(self, now):
        # Diagnostics never publish. Repeated HTTP requests cannot create an
        # unbounded workflow queue; there is one preview probe per Japan day.
        return self.dispatch("probe:" + now.astimezone(JST).date().isoformat(), "preview", now)

    def status(self, now):
        now = now.astimezone(JST)
        future = [now.replace(hour=int(t[:2]), minute=int(t[3:]), second=0, microsecond=0) + timedelta(days=d)
                  for d in (0, 1) for t in TIMES]
        latest = []
        if (self.root / "dispatches.sqlite3").exists():
            conn = self.connection()
            try:
                latest = [dict(zip(("event_id", "at", "mode", "status", "http_status"), row))
                          for row in conn.execute("SELECT * FROM dispatches ORDER BY at DESC LIMIT 8")]
            finally:
                conn.close()
        return {"configured": configured(), "worker_alive": bool(_thread and _thread.is_alive()),
                "next_dispatch_at": min(t for t in future if t > now).isoformat(), "latest": latest}


def start_worker(root=ROOT):
    global _thread
    stop = threading.Event()
    if not configured():
        return stop, None
    with _start_lock:
        if _thread and _thread.is_alive():
            raise RuntimeError("Scheduler worker is already running")
        scheduler = Scheduler(root)

        def run():
            previous_error = None
            while not stop.is_set():
                try:
                    for result in scheduler.tick(datetime.now(JST)):
                        if result["status"] != "already_attempted":
                            print("[tweet-bot-scheduler]", result, flush=True)
                    previous_error = None
                except Exception as exc:
                    name = type(exc).__name__
                    if name != previous_error:
                        print("[tweet-bot-scheduler] paused tick:", name, flush=True)
                    previous_error = name
                stop.wait(15)

        _thread = threading.Thread(target=run, name="tweet-bot-scheduler", daemon=True)
        _thread.start()
    return stop, _thread
