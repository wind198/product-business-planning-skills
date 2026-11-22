#!/usr/bin/env python3
"""Guided terminal interface for project planning. No canonical keys or source IDs required."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

import yaml

from knowledge import facts, put, read, resolve, scope_for

ROOT = Path(__file__).resolve().parents[1]

# These are known intake concepts, not a mandatory questionnaire.
FIELDS = [
    ("product.idea", "Product idea", "In one or two sentences, what are you considering building?"),
    ("product.primary_problem", "Customer pain", "What customer problem motivated this idea?"),
    ("product.target_customer", "Target customers", "Who experiences this problem?"),
    ("product.existing_solution", "Existing product or MVP", "What already exists (product, prototype, or code)?"),
    ("product.constraints", "Important constraints", "Any constraints on budget, team, timing, or technology?"),
    ("product.success_outcome", "Desired outcome", "What would make this initiative successful?"),
]
FIELD_MAP = {key: (name, question) for key, name, question in FIELDS}
INITIAL_KEYS = ("product.idea", "product.primary_problem", "product.target_customer")


def ask(message: str, input_fn=input) -> str:
    try:
        return input_fn(message).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nSession ended.")
        raise SystemExit(0)


def project_dirs(output: Path) -> list[Path]:
    if not output.is_dir():
        return []
    return sorted(p for p in output.iterdir() if p.is_dir() and (p / "project.yaml").is_file())


def choose(options: list[str], label: str, input_fn=input, allow_back=True):
    print("\n" + label)
    for i, name in enumerate(options, 1):
        print(f"  {i}. {name}")
    if allow_back:
        print("  0. Back")
    while True:
        answer = ask("> ", input_fn)
        if allow_back and answer in ("0", "q", "quit"):
            return None
        if answer.isdecimal() and 1 <= int(answer) <= len(options):
            return int(answer) - 1
        print("Choose a displayed number.")


def create_project(output: Path, input_fn=input):
    name = ask("Project slug (letters, numbers, - or _): ", input_fn)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        print("Invalid project name; no project created.")
        return None
    path = output / name
    if path.exists():
        print("Project already exists. Select it from the list.")
        return None
    outcome = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "new_project.py"),
         "--name", name, "--output", str(output)],
        capture_output=True, text=True, check=False,
    )
    if outcome.returncode:
        print(outcome.stderr.strip() or outcome.stdout.strip())
        return None
    print(f"Created: {path}")
    return path


def select_project(output: Path, input_fn=input):
    projects = project_dirs(output)
    options = [f"Open {p.name}" for p in projects] + ["Create a new project"]
    selected = choose(options, "Select your project", input_fn, allow_back=False)
    if selected == len(projects):
        return create_project(output, input_fn)
    return projects[selected]


def current_fact(workspace: Path, key: str):
    project = read(workspace / "project.yaml")["project"]
    result = resolve(workspace, key, scope_for(project, None, None))
    return result["fact"] if result["found"] else None


def save_answer(workspace: Path, key: str, value: str, input_fn=input) -> bool:
    existing = current_fact(workspace, key)
    if existing and existing["value"] == value and existing["status"] == "confirmed":
        print("Already confirmed; nothing changed.")
        return False
    if existing:
        print(f"Previous [{existing['status']}]: {existing['value']}")
        confirmation = ask("Replace or confirm this answer? [y/N]: ", input_fn)
        if confirmation.lower() not in ("y", "yes"):
            print("Existing answer preserved.")
            return False
    session_id = "interactive-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    arguments = SimpleNamespace(
        key=key, value=value, status="confirmed", source_ref=session_id,
        override=existing is not None, market=None, release=None,
    )
    project = read(workspace / "project.yaml")["project"]
    put(workspace, arguments, project)
    print("Saved to project knowledge.")
    return True


def deferred_keys(workspace: Path) -> list[str]:
    checkpoint = read(workspace / "state" / "checkpoint.yaml")
    return checkpoint.get("deferred_keys", [])


def defer(workspace: Path, key: str):
    path = workspace / "state" / "checkpoint.yaml"
    checkpoint = read(path)
    skipped = checkpoint.setdefault("deferred_keys", [])
    if key not in skipped:
        skipped.append(key)
    path.write_text(yaml.safe_dump(checkpoint, sort_keys=False, allow_unicode=True), encoding="utf-8")


def intake(workspace: Path, input_fn=input):
    skipped = set(deferred_keys(workspace))
    missing = [key for key in INITIAL_KEYS if current_fact(workspace, key) is None and key not in skipped]
    if not missing:
        print("\nNo essential unanswered intake questions. The planning agent can investigate and propose next steps.")
        return
    key = missing[0]
    label, question = FIELD_MAP[key]
    print(f"\nNext useful question: {label}\n{question}")
    print("Press Enter to return, or type /skip to defer this question.")
    response = ask("> ", input_fn)
    if response == "/skip":
        defer(workspace, key)
        print("Deferred; it will not be asked again automatically.")
    elif response:
        save_answer(workspace, key, response, input_fn)
    else:
        print("No changes.")


def show_answers(workspace: Path):
    print("\nKnown project information")
    rows = sorted((f for _, f in facts(workspace) if f["status"] != "superseded"), key=lambda f: f["key"])
    if not rows:
        print("  No recorded answers yet.")
        return
    for entry in rows:
        label = FIELD_MAP.get(entry["key"], (entry["key"], ""))[0]
        print(f"  {label}: {entry['value']} [{entry['status']}; revision {entry['revision']}]")


def edit_answer(workspace: Path, input_fn=input):
    names = [f"{name} — {'saved' if current_fact(workspace, key) else 'not set'}"
             for key, name, _ in FIELDS]
    chosen = choose(names, "Which information would you like to add or change?", input_fn)
    if chosen is None:
        return
    key, name, question = FIELDS[chosen]
    previous = current_fact(workspace, key)
    if previous:
        print(f"Current {name}: {previous['value']} [{previous['status']}]")
    print(question)
    answer = ask("New answer (Enter to cancel): ", input_fn)
    if answer:
        save_answer(workspace, key, answer, input_fn)


def show_dashboard(workspace: Path):
    state = read(workspace / "state" / "workflow.yaml")
    recorded = sum(f["status"] == "confirmed" for _, f in facts(workspace))
    print(f"\n=== {workspace.name} ===")
    print(f"Workflow: {state['phase']} ({state['status']})")
    print(f"Confirmed facts: {recorded}")
    print(f"Next action: {state.get('next_action', 'unspecified')}")
    print("  1. Continue discovery (one question)")
    print("  2. Review existing answers")
    print("  3. Add or correct information")
    print("  4. Show document and project paths")
    print("  5. Switch project")
    print("  0. Exit")


def run(output: Path, input_fn=input):
    workspace = None
    print("Product & Business Planning — interactive workspace")
    while True:
        if workspace is None:
            workspace = select_project(output, input_fn)
            if workspace is None:
                continue
        show_dashboard(workspace)
        action = ask("> ", input_fn)
        if action in ("0", "q", "quit"):
            print("Project knowledge is saved on disk.")
            return
        if action == "1":
            intake(workspace, input_fn)
        elif action == "2":
            show_answers(workspace)
        elif action == "3":
            edit_answer(workspace, input_fn)
        elif action == "4":
            print(f"Workspace: {workspace}\nDocuments: {workspace / 'documents'}\nKnowledge: {workspace / 'knowledge'}")
        elif action == "5":
            workspace = None
        else:
            print("Choose a displayed number.")


def main():
    parser = argparse.ArgumentParser(description="Interactive planning workspace; no KEY/VALUE/REF arguments needed.")
    parser.add_argument("--output", type=Path, default=Path("./work"))
    args = parser.parse_args()
    if not sys.stdin.isatty():
        parser.error("interactive session requires a terminal; use tools/knowledge.py for scripts")
    run(args.output.expanduser().resolve())


if __name__ == "__main__":
    main()
