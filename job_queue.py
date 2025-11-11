import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from utils import ensure_data_dir, utcnow_iso, pretty_print_table

DB_PATH = os.path.join(ensure_data_dir(), "queue.db")


def _connect():
    """Each process/thread gets its own SQLite connection."""
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize SQLite tables for jobs, DLQ, and config."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        command TEXT NOT NULL,
        state TEXT NOT NULL,
        attempts INTEGER NOT NULL,
        max_retries INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        next_run_at TEXT NOT NULL,
        priority INTEGER DEFAULT 0
    )
    """)
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_jobs_state_next
      ON jobs(state, next_run_at)
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS dlq (
        id TEXT PRIMARY KEY,
        command TEXT NOT NULL,
        reason TEXT,
        created_at TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)
    # Default configuration
    for k, v in [("max_retries", "3"), ("backoff_base", "2"), ("stop", "0")]:
        cur.execute("INSERT OR IGNORE INTO config(key, value) VALUES (?, ?)", (k, v))
    conn.commit()


# ------------------ Config Management ------------------

def get_config_value(key: str) -> Optional[str]:
    conn = _connect()
    row = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def set_config(key: str, value: str):
    conn = _connect()
    conn.execute("""
        INSERT INTO config(key, value)
        VALUES(?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, value))


# ------------------ Job Management ------------------

def enqueue_job(payload: Dict[str, Any]):
    """Insert a new job into the queue, supporting run_at (delay) and priority."""
    required = ["id", "command"]
    for r in required:
        if r not in payload:
            raise ValueError(f"Missing field: {r}")

    now = utcnow_iso()

    # Default max retries
    if "max_retries" not in payload:
        payload["max_retries"] = int(get_config_value("max_retries") or 3)

    # ✅ Handle 'run_at' for delayed or scheduled jobs
    run_at = now
    if "run_at" in payload:
        val = str(payload["run_at"]).strip()
        if val.lower().startswith("in "):
            # e.g. "in 5" means in 5 minutes
            try:
                minutes = int(val.split(" ")[1])
                run_at_dt = datetime.utcnow() + timedelta(minutes=minutes)
                run_at = run_at_dt.replace(microsecond=0).isoformat() + "Z"
            except Exception:
                raise ValueError("Invalid 'run_at' format (expected 'in <minutes>' or ISO timestamp)")
        else:
            run_at = val  # assume ISO8601 UTC timestamp

    # ✅ Handle priority (default 0)
    priority = int(payload.get("priority", 0))

    row = (
        payload["id"],
        payload["command"],
        "pending",
        int(payload.get("attempts", 0)),
        int(payload["max_retries"]),
        payload.get("created_at", now),
        now,
        run_at,
        priority,
    )

    conn = _connect()
    try:
        conn.execute("""
        INSERT INTO jobs(id, command, state, attempts, max_retries, created_at, updated_at, next_run_at, priority)
        VALUES(?,?,?,?,?,?,?,?,?)
        """, row)
    except sqlite3.IntegrityError:
        raise ValueError(f"Job with id '{payload['id']}' already exists.")


def list_jobs(state: str):
    """List jobs by state (or all)."""
    conn = _connect()
    if state == "any":
        rows = conn.execute("SELECT * FROM jobs ORDER BY priority DESC, created_at ASC").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE state=? ORDER BY priority DESC, created_at ASC", (state,)
        ).fetchall()
    pretty_print_table(rows)


def show_status():
    """Show summary of job states and active stop flag."""
    conn = _connect()
    counts = conn.execute("""
      SELECT state, COUNT(*) as cnt
      FROM jobs
      GROUP BY state
    """).fetchall()
    stop_flag = get_config_value("stop")
    data = [{"state": r["state"], "count": r["cnt"]} for r in counts]
    data.append({"state": "stop_flag", "count": int(stop_flag or 0)})
    pretty_print_table(data)


def _compute_next_backoff(attempts: int) -> str:
    """Exponential backoff for retry scheduling."""
    base = int(get_config_value("backoff_base") or 2)
    delay_seconds = base ** max(1, attempts)  # 2^1, 2^2, etc.
    next_time = datetime.utcnow() + timedelta(seconds=delay_seconds)
    return next_time.replace(microsecond=0).isoformat() + "Z"


def claim_next_job() -> Optional[sqlite3.Row]:
    """
    Atomically claim the next runnable job:
    - Must be 'pending'
    - Must be due (next_run_at <= now)
    - Pick highest priority first, then oldest
    """
    conn = _connect()
    cur = conn.cursor()
    now = utcnow_iso()

    cur.execute("BEGIN IMMEDIATE")  # Lock queue
    row = cur.execute("""
        SELECT id FROM jobs
        WHERE state='pending' AND next_run_at <= ?
        ORDER BY priority DESC, created_at ASC
        LIMIT 1
    """, (now,)).fetchone()
    if not row:
        cur.execute("COMMIT")
        return None

    job_id = row["id"]
    updated = cur.execute("""
        UPDATE jobs
        SET state='processing', updated_at=?
        WHERE id=? AND state='pending'
    """, (now, job_id))
    if updated.rowcount != 1:
        cur.execute("ROLLBACK")
        return None

    job = cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    cur.execute("COMMIT")
    return job


def mark_completed(job_id: str):
    """Mark job as successfully completed."""
    conn = _connect()
    conn.execute("""
        UPDATE jobs
        SET state='completed', updated_at=?
        WHERE id=?
    """, (utcnow_iso(), job_id))


def mark_retry(job_id: str, attempts: int):
    """Schedule job retry with exponential backoff."""
    conn = _connect()
    next_run = _compute_next_backoff(attempts)
    conn.execute("""
        UPDATE jobs
        SET state='pending', attempts=?, next_run_at=?, updated_at=?
        WHERE id=?
    """, (attempts, next_run, utcnow_iso(), job_id))


def move_to_dlq(job_id: str, command: str, reason: str):
    """Move permanently failed job to DLQ."""
    conn = _connect()
    conn.execute("""
        INSERT OR REPLACE INTO dlq(id, command, reason, created_at)
        VALUES(?,?,?,?)
    """, (job_id, command, reason, utcnow_iso()))
    conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))


def list_dlq():
    """List all jobs in Dead Letter Queue."""
    conn = _connect()
    rows = conn.execute("SELECT * FROM dlq ORDER BY created_at").fetchall()
    pretty_print_table(rows)


def retry_dlq_job(job_id: str):
    """Move a job back from DLQ to main queue for reprocessing."""
    conn = _connect()
    row = conn.execute("SELECT * FROM dlq WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise ValueError(f"DLQ job '{job_id}' not found")

    now = utcnow_iso()
    conn.execute("""
        INSERT INTO jobs(id, command, state, attempts, max_retries, created_at, updated_at, next_run_at, priority)
        VALUES(?,?,?,?,?,?,?,?,0)
        ON CONFLICT(id) DO UPDATE SET
          command=excluded.command,
          state='pending',
          attempts=0,
          updated_at=excluded.updated_at,
          next_run_at=excluded.next_run_at
    """, (row["id"], row["command"], "pending", 0,
          int(get_config_value("max_retries") or 3), now, now, now))
    conn.execute("DELETE FROM dlq WHERE id=?", (job_id,))