#!/usr/bin/env python3
"""Base agent runtime — common functionality for all cluster agents."""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "platform" / "cluster"))
sys.path.insert(0, str(ROOT / "platform" / "events"))

from registry import register_agent, heartbeat as send_heartbeat
from task_bus import claim_task, start_task, complete_task, fail_task
from bus import emit as emit_event


class BaseAgent:
    """Base class for cluster agent runtimes."""

    def __init__(self, config_path):
        with open(config_path) as f:
            self.config = json.load(f)
        self.agent_id = self.config["agent_id"]
        self.role = self.config["role"]
        self.node_name = self.config.get("node_name", self.agent_id)
        self.hostname = self.config.get("hostname", self.node_name)
        self.capabilities = self.config.get("capabilities", [])
        self.execution_mode = self.config.get("execution_mode", "audit")
        self.heartbeat_interval = self.config.get("heartbeat_interval", 30)
        self.running = False
        self.task_handlers = {}

    def register(self):
        """Register with the cluster registry."""
        return register_agent(
            agent_id=self.agent_id,
            node_name=self.node_name,
            role=self.role,
            capabilities=self.capabilities,
            execution_mode=self.execution_mode,
            hostname=self.hostname,
        )

    def heartbeat(self):
        """Send heartbeat to registry."""
        return send_heartbeat(self.agent_id)

    def register_handler(self, task_type, handler_fn):
        """Register a task handler function."""
        self.task_handlers[task_type] = handler_fn

    def can_handle(self, task_type):
        """Check if this agent can handle a task type."""
        return task_type in self.task_handlers

    def execute_task(self, task):
        """Execute a claimed task."""
        task_type = task["task_type"]
        handler = self.task_handlers.get(task_type)
        if not handler:
            return {"status": "failed", "error": f"No handler for {task_type}"}

        start_task(task["task_id"], self.agent_id)
        try:
            result = handler(task)
            result["agent_id"] = self.agent_id
            result["task_id"] = task["task_id"]
            complete_task(task["task_id"], self.agent_id, result)
            return result
        except Exception as e:
            fail_task(task["task_id"], self.agent_id, str(e))
            return {"status": "failed", "error": str(e)}

    def poll_and_execute(self):
        """Poll for tasks and execute one if available."""
        task = claim_task(self.agent_id, self.capabilities, self.role)
        if task:
            return self.execute_task(task)
        return None

    def run_once(self):
        """Run one cycle: heartbeat + poll."""
        self.heartbeat()
        return self.poll_and_execute()

    def run(self):
        """Main agent loop."""
        self.register()
        self.running = True
        print(f"[{self.agent_id}] Agent started (role={self.role}, mode={self.execution_mode})")
        while self.running:
            try:
                self.run_once()
            except Exception as e:
                print(f"[{self.agent_id}] Error: {e}")
            time.sleep(self.heartbeat_interval)

    def stop(self):
        self.running = False
