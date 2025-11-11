#!/usr/bin/env python3
import json
import click
from job_queue import (
    init_db, enqueue_job, list_jobs, show_status,
    set_config, get_config_value
)
from dlq import list_dlq, retry_dlq_job
from worker import start_workers, stop_workers


@click.group(help="queuectl — minimal production-grade background job queue (CLI)")
def cli():
    init_db()


# ---------- Enqueue ----------
@cli.command("enqueue")
@click.argument("job_json")
def enqueue_cmd(job_json):
    """Add a new job to the queue.

    Example:
      queuectl enqueue '{"id":"job1","command":"echo hello"}'
    """
    try:
        payload = json.loads(job_json)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON: {e}")
    enqueue_job(payload)
    click.echo(f"Enqueued job: {payload['id']}")


# ---------- Workers ----------
@cli.group("worker")
def worker_group():
    """Manage workers."""
    pass


@worker_group.command("start")
@click.option("--count", default=1, show_default=True, type=int, help="Number of worker processes")
def worker_start(count):
    """Start worker processes. Ctrl+C to stop, or use `queuectl worker stop`."""
    # Clear stop flag before starting
    set_config("stop", "0")
    start_workers(count)


@worker_group.command("stop")
def worker_stop():
    """Request graceful stop of workers."""
    stop_workers()
    click.echo("Stop signal sent. Workers will exit after the current job.")


# ---------- Status ----------
@cli.command("status")
def status_cmd():
    """Show summary of all job states & active worker stop-flag."""
    show_status()


# ---------- List Jobs ----------
@cli.command("list")
@click.option("--state", default="pending", show_default=True,
              type=click.Choice(["pending", "processing", "completed", "failed", "dead", "any"]),
              help="Filter jobs by state")
def list_cmd(state):
    """List jobs by state."""
    list_jobs(state)


# ---------- DLQ ----------
@cli.group("dlq")
def dlq_group():
    """Dead Letter Queue operations."""
    pass


@dlq_group.command("list")
def dlq_list_cmd():
    """List DLQ jobs."""
    list_dlq()


@dlq_group.command("retry")
@click.argument("job_id")
def dlq_retry_cmd(job_id):
    """Retry a DLQ job by moving it back to the main queue."""
    retry_dlq_job(job_id)


# ---------- Config ----------
@cli.group("config")
def config_group():
    """Configuration management (retry counts, backoff base, etc.)."""
    pass


@config_group.command("set")
@click.argument("key")
@click.argument("value")
def config_set_cmd(key, value):
    """Set a configuration key.

    Examples:
      queuectl config set max_retries 3
      queuectl config set backoff_base 2
    """
    set_config(key, value)
    click.echo(f"Config set: {key} = {value}")


@config_group.command("get")
@click.argument("key")
def config_get_cmd(key):
    """Get a configuration key."""
    val = get_config_value(key)
    click.echo(val if val is not None else "(null)")


if __name__ == "__main__":
    cli()