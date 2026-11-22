import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from interactive import run, current_fact, deferred_keys, save_answer


class InteractiveTests(unittest.TestCase):
    def responses(self, *items):
        values = iter(items)
        return lambda _prompt="": next(values)

    def test_new_project_guided_answer_and_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                # New project -> project name -> one discovery answer -> review -> exit
                run(output, self.responses("1", "my-product", "1", "A community workspace app", "2", "0"))
            ws = output / "my-product"
            fact = current_fact(ws, "product.idea")
            self.assertEqual("A community workspace app", fact["value"])
            self.assertEqual(1, fact["revision"])
            with contextlib.redirect_stdout(io.StringIO()):
                run(output, self.responses("1", "1", "Users lack quiet spaces", "0"))
            self.assertEqual(1, current_fact(ws, "product.idea")["revision"])
            self.assertEqual("Users lack quiet spaces", current_fact(ws, "product.primary_problem")["value"])

    def test_edit_requires_confirmation_and_preserves_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable, str(ROOT / "tools/new_project.py"), "--name", "p", "--output", tmp], check=True, capture_output=True)
            workspace = Path(tmp) / "p"
            with contextlib.redirect_stdout(io.StringIO()):
                save_answer(workspace, "product.idea", "Old")
                self.assertFalse(save_answer(workspace, "product.idea", "New", self.responses("n")))
                self.assertTrue(save_answer(workspace, "product.idea", "New", self.responses("y")))
            record = current_fact(workspace, "product.idea")
            self.assertEqual("New", record["value"])
            self.assertEqual(2, record["revision"])
            self.assertEqual("Old", record["history"][0]["value"])

    def test_defer_avoids_reasking(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                run(output, self.responses("1", "startup", "1", "/skip", "1", "Customer cannot schedule visits", "0"))
            ws = output / "startup"
            self.assertIn("product.idea", deferred_keys(ws))
            self.assertEqual("Customer cannot schedule visits", current_fact(ws, "product.primary_problem")["value"])


if __name__ == "__main__":
    unittest.main()
