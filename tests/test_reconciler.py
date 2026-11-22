"""Knowledge reconciliation is independent of the CLI and survives offline edits."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from reconciler import reconcile, pending, acknowledge


class ReconcilerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ws = Path(self.temp.name) / "demo"
        subprocess.run([sys.executable, str(ROOT / "tools" / "new_project.py"),
                        "--name", "demo", "--output", self.temp.name], check=True, capture_output=True)
        self.assertTrue((self.ws / "state" / "knowledge-snapshot.json").exists())

    def write_fact(self):
        subprocess.run([sys.executable, str(ROOT / "tools" / "knowledge.py"),
                        "--workspace", str(self.ws), "put", "--key", "product.idea",
                        "--value", "Booking app", "--source-ref", "user-session",
                        "--status", "confirmed"], check=True, capture_output=True)
        return self.ws / "knowledge" / "facts" / "FACT-001.yaml"

    def test_automation_write_is_queued_once(self):
        self.write_fact()
        queued = pending(self.ws)
        self.assertEqual(1, len(queued))
        self.assertEqual("automation", queued[0]["origin"])
        self.assertEqual("knowledge.added", queued[0]["type"])
        self.assertEqual("product.idea", queued[0]["key"])
        self.assertEqual(0, reconcile(self.ws)["new_events"])

    def test_external_change_is_detected_after_cli_is_closed(self):
        path = self.write_fact()
        fact = yaml.safe_load(path.read_text())
        fact["value"] = "New booking app"
        fact["affects"] = ["mvp", "pricing"]
        path.write_text(yaml.safe_dump(fact))
        changed = reconcile(self.ws)
        self.assertEqual(1, changed["new_events"])
        event = pending(self.ws)[-1]
        self.assertEqual("external_edit", event["origin"])
        self.assertTrue(event["needs_provenance_review"])
        self.assertIn("value", event["changed_fields"])
        self.assertEqual(["mvp", "pricing"], event["affected_ids"])
        self.assertEqual("Booking app", event["before"]["value"])
        self.assertEqual("New booking app", event["after"]["value"])

    def test_invalid_record_keeps_last_valid_baseline(self):
        path = self.write_fact()
        path.write_text("key: [invalid\n")
        result = reconcile(self.ws)
        self.assertIn("knowledge/facts/FACT-001.yaml", result["invalid"])
        self.assertEqual("knowledge.invalid", pending(self.ws)[-1]["type"])
        self.assertEqual(0, reconcile(self.ws)["new_events"])
        original = json.loads((self.ws / "state" / "knowledge-snapshot.json").read_text())
        self.assertEqual("Booking app", original["files"]["knowledge/facts/FACT-001.yaml"]["data"]["value"])
        # Recover with a valid edit, compared against the last valid revision.
        original_data = original["files"]["knowledge/facts/FACT-001.yaml"]["data"]
        original_data["value"] = "Recovered"
        path.write_text(yaml.safe_dump(original_data))
        self.assertEqual(1, reconcile(self.ws)["new_events"])
        self.assertEqual("knowledge.modified", pending(self.ws)[-1]["type"])

    def test_deleted_record_is_reported(self):
        path = self.write_fact()
        path.unlink()
        self.assertEqual(1, reconcile(self.ws)["new_events"])
        event = pending(self.ws)[-1]
        self.assertEqual("knowledge.deleted", event["type"])
        self.assertEqual("Booking app", event["before"]["value"])

    def test_json_knowledge_edit_and_formatting_only_edit(self):
        path = self.ws / "knowledge" / "sources" / "interview.json"
        path.write_text('{"source": "interview-1", "notes": "First"}')
        self.assertEqual(1, reconcile(self.ws)["new_events"])
        path.write_text(json.dumps({"notes": "First", "source": "interview-1"}, indent=4))
        self.assertEqual(0, reconcile(self.ws)["new_events"])
        path.write_text(json.dumps({"source": "interview-1", "notes": "Updated"}))
        self.assertEqual(1, reconcile(self.ws)["new_events"])

    def test_acknowledge_only_marks_reviewed_events(self):
        self.write_fact()
        event = pending(self.ws)[0]
        acknowledge(self.ws, [event["id"]])
        self.assertEqual([], pending(self.ws))
        with self.assertRaises(ValueError):
            acknowledge(self.ws, ["not-an-event"])

    def test_repeated_value_changes_generate_new_events(self):
        path = self.write_fact()
        for value in ("Other", "Booking app", "Other"):
            entry = yaml.safe_load(path.read_text())
            entry["value"] = value
            path.write_text(yaml.safe_dump(entry))
            self.assertEqual(1, reconcile(self.ws)["new_events"])
        self.assertEqual(4, len(pending(self.ws)))

    def test_legacy_workspace_first_scan_is_baseline(self):
        self.write_fact()
        (self.ws / "state" / "knowledge-snapshot.json").unlink()
        result = reconcile(self.ws)
        self.assertTrue(result["initialized"])
        self.assertEqual(0, result["new_events"])


if __name__ == "__main__":
    unittest.main()
