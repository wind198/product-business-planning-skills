#!/usr/bin/env python3
"""Product planning CLI: Typer commands + Questionary prompts, no homegrown terminal UI."""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import questionary
import typer
from rich.console import Console
from rich.table import Table
import yaml
from intake_catalog import GROUPS, ALL_FIELDS, BY_KEY

from knowledge import facts, put, read, resolve, scope_for

ROOT = Path(__file__).resolve().parents[1]
app = typer.Typer(help="Interactive product knowledge and project planning.", no_args_is_help=True)
console = Console()

FIELDS = {
    "product.idea": "Product idea",
    "product.primary_problem": "Customer pain",
    "product.target_customer": "Target customers",
    "product.existing_solution": "Existing product or MVP",
    "product.constraints": "Important constraints",
    "product.success_outcome": "Desired outcome",
}
CORE_KEYS = tuple(FIELDS)[:3]
SLUG = re.compile(r"[A-Za-z0-9_-]+")
KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


def timestamp() -> str:
    return "interactive-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def workspace_for(project: str, output: Path) -> Path:
    if not SLUG.fullmatch(project):
        raise typer.BadParameter("Project must contain only letters, numbers, '-' or '_'.")
    workspace = output.expanduser().resolve() / project
    if not (workspace / "project.yaml").is_file():
        raise typer.BadParameter(f"Unknown project '{project}'. Create it with 'make new PROJECT={project}' or 'make start'.")
    return workspace


def known(workspace: Path, key: str) -> dict | None:
    project = read(workspace / "project.yaml")["project"]
    result = resolve(workspace, key, scope_for(project, None, None))
    return result["fact"] if result["found"] else None


def pick_key(workspace: Path) -> str | None:
    existing = {item["key"] for _, item in facts(workspace) if item["status"] != "superseded"}
    options = list(dict.fromkeys([*FIELDS, *sorted(existing)]))
    choices = [
        questionary.Choice(
            title=f"{FIELDS.get(key, key)} · {key}" + (" [saved]" if key in existing else ""),
            value=key,
        )
        for key in options
    ]
    choices.append(questionary.Choice(title="Other key…", value="__custom__"))
    key = questionary.select("Which information?", choices=choices).ask()
    if key is None:
        return None
    if key == "__custom__":
        key = questionary.text("Canonical key (e.g. pricing.model):").ask()
        if not key:
            return None
        if not KEY.fullmatch(key):
            console.print("[red]Invalid canonical key.[/red]")
            return None
    return key


def show_fact(workspace: Path, key: str) -> None:
    entry = known(workspace, key)
    if entry is None:
        console.print(f"No saved answer for [bold]{FIELDS.get(key, key)}[/bold].")
        return
    console.print(f"[bold]{FIELDS.get(key, key)}[/bold]: {entry['value']}")
    console.print(f"Status: {entry['status']} · Revision: {entry['revision']} · Source: {entry['source']['ref']}")


def persist(workspace: Path, key: str, value: str, mode: str) -> None:
    previous = known(workspace, key)
    status = "proposed" if mode == "propose" else "confirmed"
    if previous is not None:
        if mode == "propose":
            console.print("[yellow]Existing knowledge preserved; proposals cannot replace it.[/yellow]")
            return
        if previous["value"] == value and previous["status"] == "confirmed":
            console.print("Already confirmed; unchanged.")
            return
        console.print(f"Previous ({previous['status']}): {previous['value']}")
        if not questionary.confirm("Confirm correction or acceptance?", default=False).ask():
            console.print("No changes.")
            return
    args = SimpleNamespace(
        key=key, value=value, status=status, source_ref=timestamp(),
        override=previous is not None, market=None, release=None,
    )
    put(workspace, args, read(workspace / "project.yaml")["project"])


def focused(action: str, project: str, output: Path) -> None:
    workspace = workspace_for(project, output)
    key = pick_key(workspace)
    if key is None:
        return
    if action == "resolve":
        show_fact(workspace, key)
        return
    console.print(f"Selected: [bold]{FIELDS.get(key, key)}[/bold]")
    value = questionary.text("Value (leave empty to cancel):", default="").ask()
    if value:
        persist(workspace, key, value, action)


def projects(output: Path) -> list[Path]:
    if not output.is_dir():
        return []
    return sorted(p for p in output.iterdir() if p.is_dir() and (p / "project.yaml").is_file())


def create_project(output: Path) -> Path | None:
    name = questionary.text("New project slug:").ask()
    if not name:
        return None
    if not SLUG.fullmatch(name):
        console.print("[red]Invalid project slug.[/red]")
        return None
    dest = output.resolve() / name
    if dest.exists():
        console.print("[yellow]Project already exists.[/yellow]")
        return None
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "new_project.py"),
         "--name", name, "--output", str(output.resolve())],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        console.print(f"[red]{result.stderr.strip() or result.stdout.strip()}[/red]")
        return None
    return dest


def project_picker(output: Path) -> Path | None:
    found = projects(output)
    choices = {p.name: p for p in found}
    choices["Create new project…"] = None
    selection = questionary.select("Select a project", choices=list(choices)).ask()
    if selection is None:
        return None
    return create_project(output) if choices[selection] is None else choices[selection]


def next_question(workspace: Path) -> None:
    checkpoint_path = workspace / "state" / "checkpoint.yaml"
    checkpoint = read(checkpoint_path)
    deferred = set(checkpoint.get("deferred_keys", []))
    key = next((key for key in CORE_KEYS if key not in deferred and known(workspace, key) is None), None)
    if key is None:
        console.print("No essential unanswered intake questions. Continue research/proposals with the agent.")
        return
    answer = questionary.text(f"{FIELDS[key]} (optional; /skip to defer):").ask()
    if answer == "/skip":
        checkpoint.setdefault("deferred_keys", []).append(key)
        import yaml
        checkpoint_path.write_text(yaml.safe_dump(checkpoint, sort_keys=False), encoding="utf-8")
    elif answer:
        persist(workspace, key, answer, "fact")


def checkpoint_keys(workspace: Path) -> set[str]:
    return set(read(workspace / "state" / "checkpoint.yaml").get("deferred_keys", []))


def defer(workspace: Path, key: str) -> None:
    path = workspace / "state" / "checkpoint.yaml"
    checkpoint = read(path)
    keys = checkpoint.setdefault("deferred_keys", [])
    if key not in keys:
        keys.append(key)
        path.write_text(yaml.safe_dump(checkpoint, sort_keys=False, allow_unicode=True), encoding="utf-8")


def input_keys(workspace: Path) -> list[str]:
    """Include previously saved custom/agent question keys in the same status list."""
    others = sorted({item["key"] for _, item in facts(workspace) if item["key"] not in BY_KEY})
    questions = (workspace / "knowledge" / "questions").glob("*.yaml")
    for path in questions:
        entry = read(path)
        if entry.get("status") == "open" and entry.get("key") and entry["key"] not in BY_KEY:
            others.append(entry["key"])
    return [*BY_KEY, *sorted(set(others))]


def input_status(workspace: Path, key: str) -> str:
    entry = known(workspace, key)
    if entry is not None:
        return "confirmed" if entry["status"] == "confirmed" else entry["status"]
    return "deferred" if key in checkpoint_keys(workspace) else "unanswered"


def next_discovery_key(workspace: Path) -> str | None:
    deferred = checkpoint_keys(workspace)
    for key in input_keys(workspace):
        if key not in deferred and input_status(workspace, key) != "confirmed":
            return key
    return None


def input_label(key: str) -> str:
    return BY_KEY[key].label if key in BY_KEY else FIELDS.get(key, key)


def input_overview(workspace: Path) -> str | None:
    """Display every collected, missing, deferred or proposed item; stay in discovery."""
    keys = input_keys(workspace)
    statuses = {key: input_status(workspace, key) for key in keys}
    confirmed = sum(v == "confirmed" for v in statuses.values())
    deferred = sum(v == "deferred" for v in statuses.values())
    console.print(f"\\n[bold]{workspace.name} · Discovery inputs[/bold] — "
                  f"{confirmed}/{len(keys)} confirmed, {deferred} deferred, "
                  f"{len(keys) - confirmed - deferred} other")
    choices = []
    if next_discovery_key(workspace):
        choices.append(questionary.Choice("Continue next unanswered input", value="__next__"))
    for topic, fields in GROUPS.items():
        choices.append(questionary.Separator(topic))
        for field in fields:
            entry = known(workspace, field.key)
            current = str(entry["value"]).replace("\\n", " ")[:50] if entry else "—"
            choices.append(questionary.Choice(
                f"[{statuses[field.key]}] {field.label}: {current}", value=field.key))
    extra = [key for key in keys if key not in BY_KEY]
    if extra:
        choices.append(questionary.Separator("Other saved / agent-requested information"))
        for key in extra:
            entry = known(workspace, key)
            current = str(entry["value"]).replace("\\n", " ")[:50] if entry else "—"
            choices.append(questionary.Choice(
                f"[{statuses[key]}] {input_label(key)}: {current}", value=key))
    choices.append(questionary.Choice("Exit discovery", value="__exit__"))
    return questionary.select("Choose an input to review or continue", choices=choices).ask()


def ask_input(workspace: Path, key: str) -> None:
    entry = known(workspace, key)
    if entry is not None:
        console.print(f"Current {input_label(key)}: {entry['value']} [{entry['status']}]")
    field = BY_KEY.get(key)
    if field and field.hint:
        console.print(f"[dim]{field.hint}[/dim]")
    answer = questionary.text(f"{input_label(key)} (Enter or /skip to defer):").ask()
    if answer is None:
        return
    if not answer.strip() or answer.strip() == "/skip":
        defer(workspace, key)
        console.print(f"[dim]Deferred {input_label(key)}. It remains unresolved.[/dim]")
        return
    persist(workspace, key, answer.strip(), "fact")
    # An answer accepted by the user takes precedence over an earlier defer;
    # the fact remains authoritative even if the checkpoint still lists the key.


def discovery(workspace: Path, *, guided: bool = True) -> None:
    """Continuous workflow. Only an explicit exit returns to the project menu."""
    while True:
        if guided:
            key = next_discovery_key(workspace)
            if key is not None:
                before = input_status(workspace, key)
                ask_input(workspace, key)
                after = input_status(workspace, key)
                if before != after:
                    continue
            guided = False
        choice = input_overview(workspace)
        if choice == "__exit__":
            return
        if choice == "__next__":
            guided = True
            continue
        if choice is None:
            # Cancelled selection stays in discovery rather than returning to main.
            continue
        ask_input(workspace, choice)
        # After manual selection, show the updated status overview again.


def dashboard(workspace: Path) -> None:
    table = Table(title=f"Known information · {workspace.name}")
    table.add_column("Information")
    table.add_column("Saved value")
    table.add_column("Status")
    for key in input_keys(workspace):
        entry = known(workspace, key)
        table.add_row(input_label(key), str(entry["value"]) if entry else "—", input_status(workspace, key))
    console.print(table)


@app.command()
def start(output: Path = typer.Option(Path("./work"), help="Project workspaces directory")) -> None:
    """Open the guided project workspace."""
    current = project_picker(output)
    while current is not None:
        confirmed = sum(input_status(current, key) == "confirmed" for key in input_keys(current))
        console.print(f"\\n[bold]{current.name}[/bold] · {confirmed}/{len(input_keys(current))} discovery inputs confirmed")
        choice = questionary.select(
            f"{current.name} — what next?",
            choices=["Continue discovery", "Review answers", "Add or correct fact",
                     "Propose an idea", "Find an answer", "Switch project", "Exit"],
        ).ask()
        if choice in (None, "Exit"):
            break
        if choice == "Switch project":
            current = project_picker(output)
        elif choice == "Continue discovery":
            discovery(current)
        elif choice == "Review answers":
            dashboard(current)
        else:
            action = {"Add or correct fact": "fact", "Propose an idea": "propose",
                      "Find an answer": "resolve"}[choice]
            focused(action, current.name, output)


@app.command()
def discover(project: str = typer.Option(..., help="Existing project slug"),
             output: Path = typer.Option(Path("./work"))) -> None:
    """Continue a persistent guided discovery session."""
    discovery(workspace_for(project, output))


@app.command()
def fact(project: str = typer.Option(..., help="Existing project slug"),
         output: Path = typer.Option(Path("./work"))) -> None:
    """Prompt for a key and value, then persist a confirmed answer."""
    focused("fact", project, output)


@app.command(name="resolve")
def resolve_fact(project: str = typer.Option(..., "--project", help="Existing project slug"),
                 output: Path = typer.Option(Path("./work"))) -> None:
    """Select an existing fact and show its saved answer."""
    focused("resolve", project, output)


@app.command()
def propose(project: str = typer.Option(..., help="Existing project slug"),
            output: Path = typer.Option(Path("./work"))) -> None:
    """Prompt for an explicitly proposed value."""
    focused("propose", project, output)


@app.command()
def override(project: str = typer.Option(..., help="Existing project slug"),
             output: Path = typer.Option(Path("./work"))) -> None:
    """Correct or accept an answer with confirmation and revision history."""
    focused("override", project, output)


if __name__ == "__main__":
    app()
