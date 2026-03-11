#!/usr/bin/env python3
"""
agent_dispatch.py — route tasks to nova/mira/orin agent VMs via the cluster API.

Usage:
  python3 agent_dispatch.py "@nova check disk usage"
  python3 agent_dispatch.py "@mira run iperf3 test to orin"
  python3 agent_dispatch.py "@orin analyze last 100 syslog lines"
  python3 agent_dispatch.py list        # show recent tasks
  python3 agent_dispatch.py status      # show all agent statuses

Agent roles:
  nova  -> proxmox_optimizer  (Proxmox/VM management)
  mira  -> network_optimizer  (networking/firewall)
  orin  -> heavy_analysis     (log analysis, heavy compute)
"""
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime

API = "http://10.1.1.21:8081"
TOKEN = "hlab_94265cc3491a9340853793f8d8e3a0611f76946f0756d350"

AGENT_MAP = {
    "nova":  {"role": "proxmox_optimizer",  "ip": "10.1.1.21"},
    "mira":  {"role": "network_optimizer",  "ip": "10.1.1.22"},
    "orin":  {"role": "heavy_analysis",     "ip": "10.1.1.23"},
}

def api(method, path, body=None):
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()}
    except Exception as e:
        return {"error": str(e)}

def dispatch(agent_name, task_text):
    if agent_name not in AGENT_MAP:
        print(f"Unknown agent '{agent_name}'. Valid: {', '.join(AGENT_MAP)}")
        sys.exit(1)

    role = AGENT_MAP[agent_name]["role"]
    payload = {
        "title": task_text,
        "description": f"Dispatched to @{agent_name} via agent_dispatch at {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "priority": "medium",
        "target_role": role,
        "created_by": "jasper"
    }
    result = api("POST", "/cluster/tasks", payload)
    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)
    task_id = result.get("id", result.get("task_id", "?"))
    print(f"Dispatched to @{agent_name} ({role})")
    print(f"Task ID: {task_id}")
    print(f"Task: {task_text}")

def list_tasks():
    result = api("GET", "/cluster/tasks")
    tasks = result if isinstance(result, list) else result.get("tasks", [])
    if not tasks:
        print("No tasks found.")
        return
    for t in tasks[-15:]:
        status = t.get("status", "?")
        role   = t.get("target_role", "any")
        title  = t.get("title", "")[:60]
        tid    = t.get("id", "?")[:8]
        print(f"  [{tid}] {status:10} {role:25} {title}")

def show_status():
    result = api("GET", "/cluster/tasks")
    tasks = result if isinstance(result, list) else result.get("tasks", [])
    summary = {}
    for t in tasks:
        role = t.get("target_role", "any")
        st   = t.get("status", "unknown")
        summary.setdefault(role, {}).setdefault(st, 0)
        summary[role][st] += 1

    print("Agent status summary:")
    for agent, info in AGENT_MAP.items():
        role = info["role"]
        counts = summary.get(role, {})
        parts = [f"{k}={v}" for k, v in counts.items()]
        print(f"  @{agent:6} ({role:25}) {', '.join(parts) if parts else 'no tasks'}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    if args[0] == "list":
        list_tasks()
    elif args[0] == "status":
        show_status()
    elif args[0].startswith("@"):
        agent = args[0][1:].lower()
        task  = " ".join(args[1:])
        if not task:
            print("Usage: agent_dispatch.py @<agent> <task description>")
            sys.exit(1)
        dispatch(agent, task)
    else:
        print(__doc__)
