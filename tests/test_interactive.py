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
from interactive import app, known, next_question, persist

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

    def test_typer_help_and_commands(self):
        result = runner.invoke(app, ["--help"])
        self.assertEqual(0, result.exit_code, result.output)
        for command in ("start", "discover", "fact", "resolve", "propose", "override"):
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


    def test_discovery_advances_after_each_answer_and_stays_on_status(self):
        from interactive import discovery, input_status
        from intake_catalog import BY_KEY
        with patch("interactive.questionary.text", side_effect=[
            Prompt("New idea"), Prompt("Hard to discover options"), Prompt("Founders"),
        ]), patch("interactive.questionary.select", return_value=Prompt("__exit__")) as menu:
            # Only 3 fields are enabled for this flow; the rest are deliberately deferred.
            from interactive import defer
            for key in BY_KEY:
                if key not in ("product.idea", "product.primary_problem", "product.target_customer"):
                    defer(self.ws, key)
            discovery(self.ws)
        self.assertEqual("confirmed", input_status(self.ws, "product.idea"))
        self.assertEqual("confirmed", input_status(self.ws, "product.primary_problem"))
        self.assertEqual("confirmed", input_status(self.ws, "product.target_customer"))
        menu.assert_called_once()
        options = menu.call_args.kwargs["choices"]
        self.assertTrue(any(getattr(option, "value", None) == "product.idea" for option in options))
        self.assertTrue(any(getattr(option, "value", None) == "__exit__" for option in options))

    def test_all_inputs_complete_still_shows_editable_status_list(self):
        from interactive import discovery, defer
        from intake_catalog import BY_KEY
        for key in BY_KEY:
            defer(self.ws, key)
        with patch("interactive.questionary.select", side_effect=[
            Prompt("product.idea"), Prompt("__exit__"),
        ]) as menus, patch("interactive.questionary.text", return_value=Prompt("Updated idea")):
            discovery(self.ws)
        self.assertEqual("Updated idea", known(self.ws, "product.idea")["value"])
        self.assertEqual(2, menus.call_count)
        self.assertTrue(any(getattr(option, "value", None) == "product.idea"
                            for option in menus.call_args_list[0].kwargs["choices"]))

    def test_next_discovery_skips_saved_and_deferred(self):
        from interactive import next_discovery_key, defer
        persist(self.ws, "product.idea", "Existing", "fact")
        defer(self.ws, "product.primary_problem")
        self.assertEqual("product.target_customer", next_discovery_key(self.ws))

    def test_direct_yaml_edit_reflected_in_status_view(self):
        from interactive import input_status, input_overview
        from pathlib import Path
        import yaml
        persist(self.ws, "product.idea", "Original", "fact")
        path = next((self.ws / "knowledge" / "facts").glob("*.yaml"))
        fact = yaml.safe_load(path.read_text())
        fact["value"] = "Manually updated"
        path.write_text(yaml.safe_dump(fact))
        with patch("interactive.questionary.select", return_value=Prompt("__exit__")) as menu:
            input_overview(self.ws)
        titles = [getattr(choice, "title", str(choice)) for choice in menu.call_args.kwargs["choices"]]
        self.assertTrue(any("Manually updated" in title for title in titles))

    def test_direct_discover_command_and_skip_do_not_return_to_main_menu(self):
        from interactive import defer
        from intake_catalog import BY_KEY
        for key in BY_KEY:
            if key != "product.idea":
                defer(self.ws, key)
        with patch("interactive.questionary.text", return_value=Prompt("/skip")), \
             patch("interactive.questionary.select", return_value=Prompt("__exit__")) as select:
            result = runner.invoke(app, ["discover", "--project", "demo", "--output", self.tmp.name])
        self.assertEqual(0, result.exit_code, result.output)
        select.assert_called_once()
        self.assertIsNone(known(self.ws, "product.idea"))

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
