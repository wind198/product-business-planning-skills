"""Typer commands and Questionary prompts are tested without a real terminal."""
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from interactive import app, known, next_question, persist, summary

runner = CliRunner()


class Prompt:
    def __init__(self, response):
        self.response = response

    def ask(self):
        return self.response


class InteractiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ws = Path(self.tmp.name) / "demo"
        subprocess.run([sys.executable, str(ROOT / "tools" / "new_project.py"),
                        "--name", "demo", "--output", self.tmp.name],
                       capture_output=True, check=True)

    def test_summary_displays_known_and_missing(self):
        persist(self.ws, "product.idea", "A booking service", "fact")
        with io.StringIO() as buffer, patch("interactive.console", __import__("rich.console", fromlist=["Console"]).Console(file=buffer, force_terminal=False, width=120)):
            summary(self.ws)
            output = buffer.getvalue()
        self.assertIn("1 confirmed", output)
        self.assertIn("Product idea: A booking service", output)
        self.assertIn("Customer pain", output)
        self.assertIn("Target customers", output)
        self.assertNotIn("Still unknown: Product idea", output)

    def test_typer_help_and_commands(self):
        result = runner.invoke(app, ["--help"])
        self.assertEqual(0, result.exit_code, result.output)
        for command in ("start", "fact", "resolve", "propose", "override"):
            self.assertIn(command, result.output)

    def test_prompted_fact_and_lookup(self):
        with patch("interactive.questionary.select", return_value=Prompt("product.idea")), \
             patch("interactive.questionary.text", return_value=Prompt("An online booking app")):
            result = runner.invoke(app, ["fact", "--project", "demo", "--output", self.tmp.name])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual("An online booking app", known(self.ws, "product.idea")["value"])
        with patch("interactive.questionary.select", return_value=Prompt("product.idea")):
            result = runner.invoke(app, ["resolve", "--project", "demo", "--output", self.tmp.name])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("An online booking app", result.output)

    def test_confirmed_correction_requires_approval(self):
        persist(self.ws, "product.idea", "Original", "fact")
        with patch("interactive.questionary.confirm", return_value=Prompt(False)):
            persist(self.ws, "product.idea", "New", "override")
        self.assertEqual("Original", known(self.ws, "product.idea")["value"])
        with patch("interactive.questionary.confirm", return_value=Prompt(True)):
            persist(self.ws, "product.idea", "New", "override")
        entry = known(self.ws, "product.idea")
        self.assertEqual("New", entry["value"])
        self.assertEqual(2, entry["revision"])
        self.assertEqual("Original", entry["history"][0]["value"])

    def test_accept_same_value_proposal(self):
        persist(self.ws, "product.target_customer", "Founders", "propose")
        with patch("interactive.questionary.confirm", return_value=Prompt(True)):
            persist(self.ws, "product.target_customer", "Founders", "fact")
        entry = known(self.ws, "product.target_customer")
        self.assertEqual("confirmed", entry["status"])
        self.assertEqual(2, entry["revision"])

    def test_discovery_skips_known_answer(self):
        persist(self.ws, "product.idea", "A product", "fact")
        with patch("interactive.questionary.text", return_value=Prompt("Bad scheduling")) as prompt:
            next_question(self.ws)
        self.assertIn("Customer pain", prompt.call_args[0][0])
        self.assertEqual("Bad scheduling", known(self.ws, "product.primary_problem")["value"])

    def test_custom_key_and_proposal_no_overwrite(self):
        with patch("interactive.questionary.select", return_value=Prompt("__custom__")), \
             patch("interactive.questionary.text", side_effect=[Prompt("pricing.model"), Prompt("usage-based")]):
            result = runner.invoke(app, ["propose", "--project", "demo", "--output", self.tmp.name])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual("proposed", known(self.ws, "pricing.model")["status"])
        persist(self.ws, "pricing.model", "per-seat", "propose")
        self.assertEqual("usage-based", known(self.ws, "pricing.model")["value"])


if __name__ == "__main__":
    unittest.main()
