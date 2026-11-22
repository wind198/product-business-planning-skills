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

from knowledge import facts, put, read, resolve, scope_for
from reconciler import reconcile, pending

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
        override=previous is not None, market=None, release=None, origin="cli",
    )
    put(workspace, args, read(workspace / "project.yaml")["project"])


def focused(action: str, project: str, output: Path) -> None:
    workspace = workspace_for(project, output)
    reconcile(workspace)
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


def dashboard(workspace: Path) -> None:
    reconcile(workspace)
    table = Table(title=f"Known information · {workspace.name}")
    table.add_column("Key")
    table.add_column("Value")
    table.add_column("Status")
    for _, item in facts(workspace):
        if item["status"] != "superseded":
            table.add_row(FIELDS.get(item["key"], item["key"]), str(item["value"]), item["status"])
    console.print(table)



def summary(workspace: Path) -> None:
    """Brief snapshot of collected ground truth before the next action."""
    changes = reconcile(workspace)
    console.print(f"[dim]Knowledge changes awaiting agent review: {changes['pending']}[/dim]")
    if changes["invalid"]:
        console.print(f"[yellow]Invalid knowledge files: {len(changes['invalid'])}; fix before relying on them.[/yellow]")
    entries = [item for _, item in facts(workspace) if item["status"] != "superseded"]
    confirmed = [item for item in entries if item["status"] == "confirmed"]
    proposed = [item for item in entries if item["status"] in ("proposed", "hypothesis")]
    checkpoint = read(workspace / "state" / "checkpoint.yaml")
    deferred = set(checkpoint.get("deferred_keys", []))
    missing = [key for key in CORE_KEYS if key not in deferred and known(workspace, key) is None]

    console.print(f"\n[bold]{workspace.name}[/bold] — {len(confirmed)} confirmed, "
                  f"{len(proposed)} proposed, {len(missing)} core intake gaps")
    for item in confirmed[:4]:
        label = FIELDS.get(item["key"], item["key"])
        value = str(item["value"]).replace("\n", " ")
        console.print(f"  • {label}: {value[:90]}{'…' if len(value) > 90 else ''}")
    if len(confirmed) > 4:
        console.print(f"  …and {len(confirmed) - 4} more confirmed facts")
    if missing:
        console.print("  [dim]Still unknown:[/dim] " + ", ".join(FIELDS[key] for key in missing))


@app.command()
def start(output: Path = typer.Option(Path("./work"), help="Project workspaces directory")) -> None:
    """Open the guided project workspace."""
    current = project_picker(output)
    while current is not None:
        summary(current)
        choice = questionary.select(
            f"{current.name} — what next?",
            choices=["Continue discovery", "Review answers", "Review knowledge changes",
                     "Add or correct fact", "Propose an idea", "Find an answer", "Switch project", "Exit"],
        ).ask()
        if choice in (None, "Exit"):
            break
        if choice == "Switch project":
            current = project_picker(output)
        elif choice == "Continue discovery":
            next_question(current)
        elif choice == "Review answers":
            dashboard(current)
        elif choice == "Review knowledge changes":
            reconcile(current)
            changes = pending(current)
            if not changes:
                console.print("No changes awaiting agent review.")
            for item in changes[-15:]:
                console.print(f"  {item['type']} · {item['path']} · {', '.join(item['changed_fields']) or 'file'}")
                if "validation_error" in item:
                    console.print(f"    [yellow]{item['validation_error']}[/yellow]")
            console.print("[dim]Changes are acknowledged by the agent only after review.[/dim]")
        else:
            action = {"Add or correct fact": "fact", "Propose an idea": "propose",
                      "Find an answer": "resolve"}[choice]
            focused(action, current.name, output)


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
