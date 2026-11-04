"""Supervisor-owned transactional run memory and hash-linked execution events."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

from .policy import canonical, digest


class Memory:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, task_id TEXT NOT NULL, status TEXT NOT NULL,
                    artifact_path TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    run_id TEXT NOT NULL, seq INTEGER NOT NULL, body TEXT NOT NULL,
                    sha256 TEXT NOT NULL, PRIMARY KEY (run_id, seq));
            """)

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def create(self, run_id: str, task_id: str, path: Path):
        with self.connect() as db:
            db.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?)",
                       (run_id, task_id, "created", str(path), self.now()))

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    def event(self, run_id: str, stage: str, data: dict):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            last = db.execute("SELECT seq, sha256 FROM events WHERE run_id=? ORDER BY seq DESC LIMIT 1", (run_id,)).fetchone()
            body = {"schema_version": 1, "run_id": run_id, "seq": last[0] + 1 if last else 0,
                    "previous_sha256": last[1] if last else None, "at": self.now(),
                    "stage": stage, "data": data}
            encoded = canonical(body)
            db.execute("INSERT INTO events VALUES (?, ?, ?, ?)",
                       (run_id, body["seq"], encoded.decode(), digest(encoded)))
            db.execute("UPDATE runs SET status=?, updated_at=? WHERE id=?", (stage, self.now(), run_id))

    def export(self, run_id: str, path: Path):
        with self.connect() as db:
            rows = db.execute("SELECT body,sha256 FROM events WHERE run_id=? ORDER BY seq", (run_id,)).fetchall()
        path.write_text("".join(json.dumps({"event": json.loads(body), "sha256": sha}) + "\n" for body, sha in rows))

    def recover(self, run_id: str):
        """Explicitly abort an interrupted run. Retry creates a fresh linked run."""
        with self.connect() as db:
            row = db.execute("SELECT status FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise ValueError("unknown run")
        if row[0] in {"verified", "rejected", "failed", "aborted"}:
            raise ValueError("run is already terminal")
        self.event(run_id, "aborted", {"reason": "operator recovered interrupted run; replay in a fresh run"})

    def validate_retry(self, run_id: str, task_id: str):
        with self.connect() as db:
            row = db.execute("SELECT status, task_id FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row or row[0] not in {"failed", "rejected", "aborted"} or row[1] != task_id:
            raise ValueError("retry must reference a terminal unsuccessful run of the same task")


def check_events(path: Path) -> dict:
    previous = None
    run_id = None
    rows = path.read_text().splitlines()
    if not rows:
        raise ValueError("empty event log")
    for index, row in enumerate(rows):
        item = json.loads(row)
        event = item["event"]
        if index == 0:
            run_id = event["run_id"]
        if (event["run_id"] != run_id or event["seq"] != index
                or event["previous_sha256"] != previous or digest(canonical(event)) != item["sha256"]):
            raise ValueError("event integrity failure")
        previous = item["sha256"]
    return {"events": len(rows), "head_sha256": previous, "run_id": run_id}
