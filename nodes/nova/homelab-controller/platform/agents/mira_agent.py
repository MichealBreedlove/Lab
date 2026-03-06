#!/usr/bin/env python3
"""Mira agent — firewall optimizer, network/WiFi analyzer."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "platform" / "agents"))
sys.path.insert(0, str(ROOT / "platform" / "network"))
from base_agent import BaseAgent

class MiraAgent(BaseAgent):
    def __init__(self):
        super().__init__(ROOT / "config" / "agents" / "mira.json")
        self.register_handler("audit_firewall", self.handle_firewall)
        self.register_handler("audit_wifi", self.handle_wifi)

    def handle_firewall(self, task):
        from firewall_optimizer import run_audit
        report = run_audit()
        return {"result_type": "network_audit_report", "status": "completed",
                "summary": f"{report['finding_count']} findings (H:{report['high_severity']} M:{report['medium_severity']} L:{report['low_severity']})",
                "artifacts": [], "confidence": 0.93, "requires_review": report['high_severity'] > 0}

    def handle_wifi(self, task):
        from wifi_optimizer import run_audit
        report = run_audit()
        return {"result_type": "wifi_audit_report", "status": "completed",
                "summary": f"{report['finding_count']} findings, {len(report.get('suggestions', []))} suggestions",
                "artifacts": [], "confidence": 0.90, "requires_review": True}

if __name__ == "__main__":
    MiraAgent().run()
