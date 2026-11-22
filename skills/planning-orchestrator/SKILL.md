---
name: planning-orchestrator
description: Route product and business planning tasks to pinned open-source PM skills while preserving evidence, decisions and durable answers.
---

# Product planning orchestrator

Only this coordination skill is repository-authored. **Do not replace upstream product methodologies.** First load `upstream/skills.yaml`, then the requested pinned skill under `vendor/pm-skills/<id>/SKILL.md` (install via `make vendor`). If vendor is absent, state the limitation; use the registry for intended routing, not as a claim that its full instructions are installed.

## Session contract

Read `workflows/session.md`, `standards/evidence-policy.md`, project checkpoint and key facts. Persist every useful user answer immediately. Do not re-ask known project questions. Enter any requested workflow directly; drafts may be provisional.

1. Reuse answers and accepted decisions by canonical key and scope.
2. Investigate attachments, product analytics, competitor and MVP evidence, preserving source refs/commit IDs.
3. Route bounded research/design tasks to one or two relevant upstream skills, not all skills.
4. Propose customers, opportunities, features, pricing alternatives, experiments and channels with explicit `proposed` status. **No fabricated revenue, TAM, customer lists or validation outcomes.**
5. Ask only critical business facts, conflicting constraints, or high-impact decisions that cannot be discovered or reasonably proposed. Default maximum 3 questions per round.
6. Record hypothesis → experiment → observation → decision; link customer segment → problem → value proposition → MVP → requirement → GTM/roadmap.
7. Update relevant artifact Markdown from canonical knowledge, record stale dependencies and checkpoint.

## Representative routing

- Idea discovery: `idea-generation`, `problem-validation`, `opportunity-tree`
- Market: `market-segments`, `competitor-analysis`, `market-sizing`, `ideal-customer-profile`
- Business model/pricing: `business-model`, `lean-canvas`, `pricing-strategy`, `monetization`
- MVP/SRS: `feature-prioritization`, `prd`, `user-stories`
- Roadmap/GTM: `outcome-roadmap`, `gtm-strategy`, `gtm-motions`, `positioning`

Human acceptance is necessary for material commercial commitments and product launch approval. Never equate a successful linter with a validated business.

## Interactive terminal

Recommend `make start` as the human-facing entry point for project selection, guided capture and corrections. The menu handles project knowledge only; it does not replace agent-led market research, opportunity discovery or plan authoring. Avoid asking the user to type canonical knowledge keys, source references, or raw YAML.

## Required reconciliation before agent work

Start or resume by running `python tools/reconciler.py --workspace <project> pending`; this scans the live YAML/JSON knowledge and lists all events awaiting review. Examine each event's before/after values, provenance requirements, validation error, and explicit `affected_ids`. Do not equate an external edit of a confirmed record with verified evidence. Reconcile decisions and update potentially stale documents before acknowledging an event with `... ack <event_id>`. Never acknowledge without processing. This queue is the durable handoff between CLI/direct file editing and agent orchestration; CLI does not invoke the agent.
