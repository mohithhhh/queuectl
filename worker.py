import os
import signal
import subprocess
import time
from multiprocessing import Process
from job_queue import (
    claim_next_job, mark_completed, mark_retry,
    move_to_dlq, get_config_value, set_config
)
from utils import log_info, log_warn, ensure_data_dir

_SHOULD_STOP = False


def _sigint_handler(signum, frame):
    """Gracefully handle SIGINT/SIGTERM for controlled shutdown."""
    global _SHOULD_STOP
    _SHOULD_STOP = True
    log_warn("Received stop signal; finishing current job then exiting.")


def _should_global_stop() -> bool:
    """Check global stop flag from config or signal handler."""
    return (get_config_value("stop") or "0") == "1" or _SHOULD_STOP


def run_once():
    """Pick one job and execute with timeout, retry, and logging."""
    job = claim_next_job()
    if not job:
        time.sleep(0.5)  # Avoid busy loop
        return

    job_id = job["id"]
    cmd = job["command"]
    attempts = int(job["attempts"])
    max_retries = int(job["max_retries"])

    # ✅ Prepare per-job log file
    log_dir = os.path.join(ensure_data_dir(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"job_{job_id}.txt")

    log_info(f"[{job_id}] processing (attempt {attempts}/{max_retries}) -> `{cmd}`")

    # ✅ Timeout in seconds (can later be made configurable)
    timeout = 10

    try:
        # Execute the job command with timeout and output capture
        completed = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        rc = completed.returncode

        # ✅ Log output to file
        with open(log_path, "a") as f:
            f.write(f"=== Job {job_id} executed at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            f.write(f"Command: {cmd}\n")
            f.write(f"Exit Code: {rc}\n")
            f.write("----- STDOUT -----\n")
            f.write(completed.stdout or "")
            f.write("\n----- STDERR -----\n")
            f.write(completed.stderr or "")
            f.write("\n\n")

        # ✅ Evaluate result
        if rc == 0:
            mark_completed(job_id)
            log_info(f"[{job_id}] completed ✔")
        else:
            attempts += 1
            if attempts > max_retries:
                move_to_dlq(job_id, cmd, f"Exit code {rc}, retries exhausted")
                log_warn(f"[{job_id}] moved to DLQ (rc={rc})")
            else:
                mark_retry(job_id, attempts)
                log_warn(f"[{job_id}] failed (rc={rc}), scheduled retry with backoff")

    except subprocess.TimeoutExpired:
        # ✅ Handle timeout separately
        log_warn(f"[{job_id}] timed out after {timeout}s")
        attempts += 1
        if attempts > max_retries:
            move_to_dlq(job_id, cmd, f"Timeout after {timeout}s")
            log_warn(f"[{job_id}] moved to DLQ (timeout)")
        else:
            mark_retry(job_id, attempts)
            log_warn(f"[{job_id}] retrying after timeout with backoff")

    except FileNotFoundError as e:
        # ✅ Command not found handling
        attempts += 1
        if attempts > max_retries:
            move_to_dlq(job_id, cmd, f"Command not found: {e}")
            log_warn(f"[{job_id}] moved to DLQ (command not found)")
        else:
            mark_retry(job_id, attempts)
            log_warn(f"[{job_id}] command not found; scheduled retry with backoff")

    except Exception as e:
        # ✅ Generic error handling
        attempts += 1
        if attempts > max_retries:
            move_to_dlq(job_id, cmd, f"Unhandled error: {e}")
            log_warn(f"[{job_id}] moved to DLQ (error)")
        else:
            mark_retry(job_id, attempts)
            log_warn(f"[{job_id}] error: {e}; scheduled retry with backoff")


def run_worker_loop():
    """Main worker loop that continuously polls and executes jobs."""
    signal.signal(signal.SIGINT, _sigint_handler)
    signal.signal(signal.SIGTERM, _sigint_handler)
    log_info(f"Worker PID {os.getpid()} started")

    while not _should_global_stop():
        run_once()

    log_warn(f"Worker PID {os.getpid()} exiting")


def start_workers(count: int):
    """Spawn multiple worker processes."""
    procs = []
    for _ in range(count):
        p = Process(target=run_worker_loop)
        p.start()
        procs.append(p)

    try:
        for p in procs:
            p.join()
    except KeyboardInterrupt:
        # Gracefully stop all workers
        stop_workers()


def stop_workers():
    """Set global stop flag for all workers."""
    set_config("stop", "1")
    log_warn("Stop signal sent. Workers will exit after current job.")