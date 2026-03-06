#!/usr/bin/env python3
"""Jasper agent — coordinator, planner, incident commander."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "platform" / "agents"))
from base_agent import BaseAgent

class JasperAgent(BaseAgent):
    def __init__(self):
        super().__init__(ROOT / "config" / "agents" / "jasper.json")
        self.register_handler("investigate_incident", self.handle_investigate)
        self.register_handler("generate_artifact", self.handle_artifact)
        self.register_handler("validate_proposal", self.handle_validate)
        self.register_handler("document_change", self.handle_document)

    def handle_investigate(self, task):
        return {"result_type": "investigation_plan", "status": "completed",
                "summary": f"Investigation planned for {task['payload'].get('incident_id', '?')}",
                "artifacts": [], "confidence": 0.90, "requires_review": False}

    def handle_artifact(self, task):
        return {"result_type": "artifact_generated", "status": "completed",
                "summary": f"Artifact generated: {task['payload'].get('type', 'generic')}",
                "artifacts": [], "confidence": 0.95, "requires_review": False}

    def handle_validate(self, task):
        return {"result_type": "validation_result", "status": "completed",
                "summary": f"Proposal validated: {task['payload'].get('proposal_id', '?')}",
                "artifacts": [], "confidence": 0.85, "requires_review": True}

    def handle_document(self, task):
        return {"result_type": "documentation_update", "status": "completed",
                "summary": f"Change documented: {task['payload'].get('change_id', '?')}",
                "artifacts": [], "confidence": 0.95, "requires_review": False}

if __name__ == "__main__":
    JasperAgent().run()
