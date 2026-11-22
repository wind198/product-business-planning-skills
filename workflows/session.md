# Incremental session and resume protocol

1. Open `state/workflow.yaml`, `state/checkpoint.yaml`, `knowledge/` and active artifact. Load only related evidence (hot/warm/cold context).
2. Resolve canonical keys and previous answers; deduplicate semantically before asking. The CLI handles exact keys only; the agent handles synonyms.
3. Select narrow upstream skill(s) through `upstream/skills.yaml`. If not installed, run `make vendor` if network permits; do not claim to have executed an absent skill.
4. Investigate existing MVP repositories at pinned commit and record findings in `investigations/` as AS-IS evidence; do not confuse implementation with running deployment.
5. Generate proposals with alternatives, rationale and assumptions; only critical project-specific gaps lead to user questions, max 3 per batch by default.
6. Record answers/accepted decisions and candidate/observed claims with provenance. Persist checkpoint and identify artifacts invalidated by change.
7. Draft or revise only relevant Markdown outputs. Review critical financial, privacy, product and market risks. Never auto-approve.

Context budget: hot = current task/checkpoint; warm = relevant facts/decisions; cold = full transcripts, files, historical research. Do not replay entire chat to resume.
