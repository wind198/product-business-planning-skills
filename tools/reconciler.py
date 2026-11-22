#!/usr/bin/env python3
"""Validate editable knowledge and journal changes for the planning agent."""
import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml
from jsonschema import ValidationError
from knowledge import validate_record

SNAPSHOT = Path("state/knowledge-snapshot.json")
JOURNAL = Path("history/knowledge-changes.jsonl")
ACKS = Path("state/agent-reviewed.json")
KINDS = {"facts": "fact", "questions": "question", "decisions": "decision",
         "hypotheses": "hypothesis", "experiments": "experiment"}


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as out:
        tmp = out.name
        json.dump(data, out, indent=2, ensure_ascii=False, sort_keys=True)
        out.write("\n")
    os.replace(tmp, path)


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def paths(workspace):
    candidates = [workspace / "project.yaml", *(workspace / "knowledge").rglob("*")]
    return {p.relative_to(workspace).as_posix(): p for p in candidates
            if p.is_file() and p.suffix.lower() in (".yaml", ".yml", ".json")}


def inspect(path, relative):
    raw = path.read_bytes()
    result = {"hash": hashlib.sha256(raw).hexdigest()}
    try:
        data = json.loads(raw) if path.suffix.lower() == ".json" else yaml.safe_load(raw)
        if not isinstance(data, dict):
            raise ValueError("expected mapping/object")
        parts = Path(relative).parts
        if len(parts) > 2 and parts[0] == "knowledge" and parts[1] in KINDS:
            validate_record(data, KINDS[parts[1]])
        if relative == "project.yaml" and not isinstance(data.get("project"), str):
            raise ValueError("missing project name")
        result["data"] = data
    except (ValueError, UnicodeError, yaml.YAMLError, ValidationError) as exc:
        result["error"] = str(exc).splitlines()[0]
    return result


def journal(workspace):
    path = workspace / JOURNAL
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def pending(workspace):
    acked = set(load_json(workspace / ACKS, {"ids": []})["ids"])
    return [event for event in journal(workspace) if event["id"] not in acked]


def acknowledge(workspace, ids):
    known = {event["id"] for event in journal(workspace)}
    if not set(ids) <= known:
        raise ValueError("unknown event ID")
    acked = set(load_json(workspace / ACKS, {"ids": []})["ids"])
    acked.update(ids)
    save_json(workspace / ACKS, {"ids": sorted(acked)})


def reconcile(workspace, origin="external_edit"):
    current = {name: inspect(path, name) for name, path in paths(workspace).items()}
    filename = workspace / SNAPSHOT
    prior = load_json(filename, None)
    errors = {name: entry["error"] for name, entry in current.items() if "error" in entry}
    if prior is None:
        # No historical comparison is possible for pre-existing workspaces.
        save_json(filename, {"version": 1, "generation": 0, "files": {k: v for k, v in current.items() if "data" in v}})
        return {"initialized": True, "new_events": 0, "invalid": errors, "pending": len(pending(workspace))}

    previous = prior["files"]
    updated = dict(previous)
    recorded = {item["id"] for item in journal(workspace)}
    created = []
    changed = False
    generation = prior.get("generation", 0)
    for name in sorted(set(previous) | set(current)):
        before, after = previous.get(name), current.get(name)
        if after and "error" in after:
            change = "invalid"
        elif after is None:
            change = "deleted"
            updated.pop(name, None)
        elif before is None:
            change = "added"
            updated[name] = after
        elif before["data"] != after["data"]:
            change = "modified"
            updated[name] = after
        else:
            # Ignore formatting-only changes while refreshing their hash.
            updated[name] = after
            continue

        changed = changed or change != "invalid"
        old = before.get("data") if before else None
        new = after.get("data") if after and "data" in after else None
        fingerprint = json.dumps([generation, name, before["hash"] if before else None,
                                  after["hash"] if after else None, change])
        identifier = hashlib.sha256(fingerprint.encode()).hexdigest()[:24]
        if identifier in recorded:
            continue
        record = new or old or {}
        fields = sorted(set(old or {}) | set(new or {}))
        fields = [key for key in fields if (old or {}).get(key) != (new or {}).get(key)]
        created.append({
            "id": identifier, "at": datetime.now(timezone.utc).isoformat(),
            "type": "knowledge." + change, "origin": origin, "path": name,
            "entity_id": record.get("id"), "key": record.get("key"),
            "changed_fields": fields, "before": old, "after": new,
            "affected_ids": sorted(set((old or {}).get("affects", []) + (new or {}).get("affects", []))),
            "needs_agent_review": True,
            "needs_provenance_review": origin == "external_edit",
            **({"validation_error": errors[name]} if name in errors else {}),
        })
        recorded.add(identifier)

    if created:
        dest = workspace / JOURNAL
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("a", encoding="utf-8") as out:
            for event in created:
                out.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    save_json(filename, {"version": 1, "generation": generation + int(changed), "files": updated})
    return {"initialized": False, "new_events": len(created),
            "invalid": errors, "pending": len(pending(workspace))}


def watch(workspace):
    """Optional live alerts; reconciliation at startup also catches offline edits."""
    from threading import Event
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
    changed = Event()

    class Handler(FileSystemEventHandler):
        def on_any_event(self, event):
            if not event.is_directory and Path(event.src_path).suffix.lower() in (".yaml", ".yml", ".json"):
                changed.set()

    observer = Observer()
    observer.schedule(Handler(), str(workspace), recursive=True)
    observer.start()
    reconcile(workspace)
    print("Watching knowledge; press Ctrl+C to stop.", flush=True)
    try:
        while True:
            if changed.wait(0.5):
                changed.clear()
                result = reconcile(workspace)
                if result["new_events"] or result["invalid"]:
                    print(json.dumps(result), flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("scan", "pending", "watch"):
        sub.add_parser(name)
    ack = sub.add_parser("ack")
    ack.add_argument("ids", nargs="+")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if not (workspace / "project.yaml").is_file():
        parser.error("project workspace not found")
    if args.action == "scan":
        print(json.dumps(reconcile(workspace), indent=2))
    elif args.action == "pending":
        reconcile(workspace)
        print(json.dumps(pending(workspace), indent=2))
    elif args.action == "ack":
        acknowledge(workspace, args.ids)
        print(f"Acknowledged {len(args.ids)} event(s)")
    else:
        watch(workspace)


if __name__ == "__main__":
    main()
