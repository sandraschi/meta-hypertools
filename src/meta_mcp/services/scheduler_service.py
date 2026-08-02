import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from meta_mcp.services.base import MetaMCPService
from meta_mcp.services.tool_service import ToolService

logger = structlog.get_logger(__name__)


class SchedulerService(MetaMCPService):
    """
    Service for managing scheduled execution of MCP tools.
    Supports task persistence and context carry-over between runs.
    """

    def __init__(self):
        super().__init__()
        self.tasks_file = Path("D:/dev/repos/meta_mcp/data/tasks.json")
        self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
        self.tasks: dict[str, dict[str, Any]] = self._load_tasks()
        self.tool_service = ToolService()
        self._running = False
        self._loop_task: asyncio.Task | None = None

    def _load_tasks(self) -> dict[str, Any]:
        """Load tasks from persistent storage."""
        if self.tasks_file.exists():
            try:
                with open(self.tasks_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Failed to load tasks", error=str(e))
        return {}

    def _save_tasks(self):
        """Save tasks to persistent storage."""
        try:
            with open(self.tasks_file, "w") as f:
                json.dump(self.tasks, f, indent=2)
        except Exception as e:
            logger.error("Failed to save tasks", error=str(e))

    async def register_task(
        self,
        name: str,
        interval_seconds: int,
        server_id: str,
        tool_name: str,
        parameters: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Register a new scheduled task."""
        task_id = name.lower().replace(" ", "_")

        self.tasks[task_id] = {
            "id": task_id,
            "name": name,
            "description": description or f"Execute {tool_name} on {server_id}",
            "interval": interval_seconds,
            "server_id": server_id,
            "tool_name": tool_name,
            "parameters": parameters or {},
            "last_run": None,
            "next_run": time.time(),
            "status": "active",
            "history": [],
            "context": {},  # Carry-over context from previous runs
        }

        self._save_tasks()
        logger.info("Task registered", task_id=task_id, interval=interval_seconds)
        return self.create_response(True, f"Task '{name}' registered successfully", self.tasks[task_id])

    async def list_tasks(self) -> dict[str, Any]:
        """List all registered tasks."""
        return self.create_response(True, "Tasks retrieved", {"tasks": list(self.tasks.values())})

    async def cancel_task(self, task_id: str) -> dict[str, Any]:
        """Cancel and remove a scheduled task."""
        if task_id in self.tasks:
            task = self.tasks.pop(task_id)
            self._save_tasks()
            return self.create_response(True, f"Task '{task['name']}' cancelled successfully")
        return self.create_response(False, f"Task '{task_id}' not found")

    async def start(self):
        """Start the background scheduler loop."""
        if self._running:
            return

        self._running = True
        self._loop_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler service started")

    async def stop(self):
        """Stop the background scheduler loop."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler service stopped")

    async def _scheduler_loop(self):
        """Main background loop for executing tasks."""
        while self._running:
            now = time.time()
            for task_id, task in self.tasks.items():
                if task["status"] == "active" and now >= task["next_run"]:
                    # Schedule next run immediately to avoid drift
                    task["next_run"] = now + task["interval"]

                    # Execute task asynchronously to not block the loop
                    asyncio.create_task(self._execute_task(task_id))

            await asyncio.sleep(1)  # Check every second

    async def _execute_task(self, task_id: str):
        """Execute a single task and update its state."""
        task = self.tasks.get(task_id)
        if not task:
            return

        logger.info("Executing task", task_id=task_id, tool=task["tool_name"])

        # Inject context if available
        params = task["parameters"].copy()
        if task["context"]:
            params["_prev_context"] = task["context"]

        result = await self.tool_service.execute_tool(task["server_id"], task["tool_name"], params)

        # Update task state
        task["last_run"] = datetime.now().isoformat()

        # Keep recent history
        entry = {
            "timestamp": task["last_run"],
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "data": result.get("data", {}),
        }
        task["history"].insert(0, entry)
        task["history"] = task["history"][:10]

        # Logic for state persistence/context carry-over
        # In a real DeepAgent implementation, we'd extract context from the result
        if result.get("success") and "context" in result.get("data", {}):
            task["context"] = result["data"]["context"]

        self._save_tasks()
        logger.info("Task execution completed", task_id=task_id, success=result.get("success"))
