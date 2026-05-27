"""Background daemon — persistent tasks that run on a schedule for proactive intelligence."""

import asyncio
import json
import os
import traceback
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Optional


class BackgroundDaemon:
    """Runs registered tasks on a schedule.

    Supports:
    - Periodic tasks with configurable intervals
    - Adding/removing tasks at runtime
    - Task alerts for proactive notifications
    - Graceful shutdown
    """

    def __init__(self, interval_sec: int = 60):
        self.interval_sec = interval_sec
        self._tasks: Dict[str, dict] = {}
        self._running = False
        self._on_alert: Optional[Callable] = None

    def set_alert_handler(self, handler: Callable) -> None:
        """Set a callback for proactive alerts."""
        self._on_alert = handler

    def add_task(self, name: str, fn: Callable,
                 interval_sec: int = 300,
                 description: str = "",
                 alert_on: str = "") -> None:
        """Register a periodic background task.

        Args:
            name: Unique task name
            fn: Async or sync callable. Returns dict with optional 'alert' key.
            interval_sec: How often to run (seconds)
            description: Human-readable description
            alert_on: Alert trigger keyword in result
        """
        self._tasks[name] = {
            "function": fn,
            "interval_sec": interval_sec,
            "description": description,
            "alert_on": alert_on,
            "last_run": 0.0,
            "last_result": None,
            "last_error": None,
            "run_count": 0,
        }

    def remove_task(self, name: str) -> bool:
        """Unregister a task."""
        return bool(self._tasks.pop(name, None))

    def list_tasks(self) -> list:
        """Get status of all registered tasks."""
        now = datetime.now().timestamp()
        results = []
        for name, task in self._tasks.items():
            secs_until_next = max(
                0, task["interval_sec"] - (now - task["last_run"])
            )
            results.append({
                "name": name,
                "interval_sec": task["interval_sec"],
                "description": task["description"],
                "next_run_sec": int(secs_until_next),
                "run_count": task["run_count"],
                "last_error": task["last_error"],
                "last_result": task["last_result"],
            })
        return results

    def get_task(self, name: str) -> Optional[dict]:
        return self._tasks.get(name)

    async def run_loop(self) -> None:
        """Main daemon loop. Runs until stop() is called."""
        self._running = True
        print(f"  ⏱️  Daemon active (check every {self.interval_sec}s)")

        while self._running:
            now = datetime.now().timestamp()

            for name, task in self._tasks.items():
                if now - task["last_run"] >= task["interval_sec"]:
                    try:
                        result = await self._run_task(name, task)
                        task["last_run"] = now
                        task["run_count"] += 1
                        task["last_result"] = result
                        task["last_error"] = None

                        self._check_alert(name, result)
                    except Exception as e:
                        error_msg = f"{type(e).__name__}: {e}"
                        task["last_error"] = error_msg
                        task["last_result"] = None

            await asyncio.sleep(self.interval_sec)

    async def _run_task(self, name: str, task: dict) -> Any:
        """Execute a task, handling sync and async functions."""
        fn = task["function"]
        if asyncio.iscoroutinefunction(fn):
            return await fn()
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, fn)

    def _check_alert(self, name: str, result: Any) -> None:
        """Check if a result should trigger an alert."""
        if not result or not self._on_alert:
            return
        task = self._tasks.get(name)
        if not task or not task["alert_on"]:
            return
        if isinstance(result, dict) and result.get(task["alert_on"]):
            self._on_alert(name, result)

    def stop(self) -> None:
        """Graceful shutdown."""
        self._running = False
