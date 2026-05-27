"""Background daemon — runs autonomously on a schedule for proactive intelligence."""

import asyncio
import os
import json
from datetime import datetime
from typing import Callable, Dict, Any, Optional


class BackgroundDaemon:
    """Runs background tasks on a schedule for proactive intelligence."""
    
    def __init__(self, interval: int = 60):
        self.interval = interval
        self._tasks: Dict[str, dict] = {}
        self._running = False
    
    def add_task(self, name: str, fn: Callable,
                 interval: int = 300, description: str = "") -> None:
        """Register a periodic task."""
        self._tasks[name] = {
            "function": fn,
            "interval": interval,
            "description": description,
            "last_run": 0,
            "last_result": None,
        }
    
    def remove_task(self, name: str) -> bool:
        """Remove a task by name."""
        return bool(self._tasks.pop(name, None))
    
    def list_tasks(self) -> list:
        """List all registered tasks."""
        return [
            {"name": k, "interval": v["interval"],
             "description": v["description"], "last_result": v["last_result"]}
            for k, v in self._tasks.items()
        ]
    
    async def run_loop(self) -> None:
        """Main daemon loop."""
        self._running = True
        print(f"  ⏱️  Daemon started (check every {self.interval}s)")
        
        while self._running:
            now = datetime.now().timestamp()
            
            for name, task in self._tasks.items():
                if now - task["last_run"] >= task["interval"]:
                    try:
                        result = await task["function"]()
                        task["last_run"] = now
                        task["last_result"] = result
                        
                        if result and result.get("alert"):
                            print(f"\n  🔔 [{name}] {result['message']}")
                    except Exception as e:
                        print(f"  ⚠️  Task '{name}' failed: {e}")
            
            await asyncio.sleep(self.interval)
    
    def stop(self) -> None:
        """Stop the daemon."""
        self._running = False
