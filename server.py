from flask import Flask, request, jsonify
from job_queue import enqueue_job, list_jobs, show_status, list_dlq, retry_dlq_job, get_config_value, set_config
from worker import start_workers, stop_workers
import threading

app = Flask(__name__) 
 
# ---------------------- JOB MANAGEMENT ----------------------

@app.route("/enqueue", methods=["POST"])
def enqueue():
    try:
        payload = request.json
        enqueue_job(payload)
        return jsonify({"status": "success", "job_id": payload["id"]}), 201
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 400


@app.route("/jobs", methods=["GET"])
def get_jobs():
    state = request.args.get("state", "any")
    from job_queue import _connect
    conn = _connect()
    if state == "any":
        rows = conn.execute("SELECT * FROM jobs ORDER BY priority DESC, created_at ASC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM jobs WHERE state=? ORDER BY priority DESC, created_at ASC", (state,)).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/status", methods=["GET"])
def get_status():
    from job_queue import _connect
    conn = _connect()
    counts = conn.execute("""
        SELECT state, COUNT(*) as count
        FROM jobs
        GROUP BY state
    """).fetchall()
    data = {r["state"]: r["count"] for r in counts}
    data["stop_flag"] = int(get_config_value("stop") or 0)
    return jsonify(data)

# ---------------------- DLQ MANAGEMENT ----------------------

@app.route("/dlq", methods=["GET"])
def get_dlq():
    from job_queue import _connect
    conn = _connect()
    rows = conn.execute("SELECT * FROM dlq ORDER BY created_at").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/dlq/retry/<job_id>", methods=["POST"])
def retry_dlq(job_id):
    try:
        retry_dlq_job(job_id)
        return jsonify({"status": "success", "message": f"DLQ job {job_id} retried"}), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 400


# ---------------------- WORKER CONTROL ----------------------

@app.route("/workers/start", methods=["POST"])
def start_worker():
    data = request.get_json(silent=True) or {}
    count = int(data.get("count", 1))
    threading.Thread(target=start_workers, args=(count,), daemon=True).start()
    return jsonify({"status": "started", "workers": count}), 200


@app.route("/workers/stop", methods=["POST"])
def stop_worker():
    stop_workers()
    return jsonify({"status": "stopping", "message": "Workers will stop after current job"}), 200


# ---------------------- CONFIGURATION ----------------------

@app.route("/config", methods=["GET", "POST"])
def config():
    if request.method == "GET":
        key = request.args.get("key")
        val = get_config_value(key)
        return jsonify({key: val})
    else:
        data = request.json
        key, value = data.get("key"), data.get("value")
        set_config(key, value)
        return jsonify({"status": "updated", key: value})

import os

@app.route("/logs/<job_id>", methods=["GET"])
def get_job_log(job_id):
    """Fetch job execution logs by ID."""
    log_path = f"/Users/mohithdk/.queuectl/logs/job_{job_id}.txt"
    if not os.path.exists(log_path):
        return jsonify({"error": f"No log found for job {job_id}"}), 404
    with open(log_path, "r") as f:
        content = f.read()
    return jsonify({
        "job_id": job_id,
        "log": content
    })

@app.route("/metrics", methods=["GET"])
def get_metrics():
    """Return job processing metrics."""
    from job_queue import _connect
    conn = _connect()

    total = conn.execute("SELECT COUNT(*) as c FROM jobs").fetchone()["c"]
    completed = conn.execute("SELECT COUNT(*) as c FROM jobs WHERE state='completed'").fetchone()["c"]
    failed = conn.execute("SELECT COUNT(*) as c FROM dlq").fetchone()["c"]
    pending = conn.execute("SELECT COUNT(*) as c FROM jobs WHERE state='pending'").fetchone()["c"]

    success_rate = round((completed / total) * 100, 2) if total > 0 else 0.0

    return {
        "total_jobs": total,
        "completed_jobs": completed,
        "pending_jobs": pending,
        "failed_jobs": failed,
        "success_rate": f"{success_rate}%",
        "active_workers": int(get_config_value("stop") == "0")
    }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
