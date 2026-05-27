"""Scheduling tools — persistent cron-like scheduling.
Uses the Memory DB for durable storage across restarts.
"""

import json
import uuid
from datetime import datetime, timedelta
from skynet.registry import registry
from skynet.memory import Memory
from skynet.config import load_config


def _get_memory() -> Memory:
    return Memory(load_config().memory_db_path)


def cron_create(name: str, schedule: str, prompt: str) -> str:
    """Create a scheduled job that runs on a recurring schedule.

    Args:
        name: Human-readable name for this job
        schedule: '30m', '2h', 'every monday 9am', or cron '0 9 * * *'
        prompt: What the agent should do when this job runs
    """
    job_id = str(uuid.uuid4())[:8]

    # Parse simple schedule formats
    next_run = _parse_schedule(schedule)

    mem = _get_memory()
    mem.save_cron(job_id, name, schedule, prompt, next_run)
    mem.close()

    return json.dumps({
        "job_id": job_id,
        "name": name,
        "schedule": schedule,
        "next_run": next_run,
        "status": "created",
    })


def cron_list() -> str:
    """List all scheduled jobs."""
    mem = _get_memory()
    import sqlite3
    rows = mem._conn.execute(
        "SELECT id, name, schedule, prompt, last_run, next_run, enabled "
        "FROM cron_jobs ORDER BY created_at DESC"
    ).fetchall()
    mem.close()
    jobs = [dict(r) for r in rows]
    return json.dumps({"jobs": jobs, "count": len(jobs)})


def _parse_schedule(schedule: str) -> str:
    """Parse a human-friendly schedule into an ISO datetime."""
    now = datetime.now()

    schedule = schedule.strip().lower()

    if schedule.endswith("m") and schedule[:-1].isdigit():
        minutes = int(schedule[:-1])
        return (now + timedelta(minutes=minutes)).isoformat()
    elif schedule.endswith("h") and schedule[:-1].isdigit():
        hours = int(schedule[:-1])
        return (now + timedelta(hours=hours)).isoformat()
    elif schedule.endswith("d") and schedule[:-1].isdigit():
        days = int(schedule[:-1])
        return (now + timedelta(days=days)).isoformat()
    elif "every" in schedule and "hour" in schedule:
        return (now + timedelta(hours=1)).isoformat()
    elif "every" in schedule and "day" in schedule:
        return (now + timedelta(days=1)).isoformat()
    elif "every" in schedule and "monday" in schedule:
        days_ahead = (7 - now.weekday() + 0) % 7  # Monday=0
        if days_ahead == 0:
            days_ahead = 7
        return (now + timedelta(days=days_ahead)).isoformat()
    else:
        # Default: 1 hour
        return (now + timedelta(hours=1)).isoformat()


# ─── Register ────────────────────────────────────────────────────────────

registry.register("cron_create", cron_create, {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Job name"},
        "schedule": {"type": "string", "description": "Schedule (e.g. '30m', '2h', 'every day')"},
        "prompt": {"type": "string", "description": "What the agent should do"},
    },
    "required": ["name", "schedule", "prompt"],
}, "Create a scheduled recurring job", "scheduling")

registry.register("cron_list", cron_list, {
    "type": "object",
    "properties": {},
}, "List all scheduled jobs", "scheduling")
