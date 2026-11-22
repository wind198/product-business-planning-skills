# Product & Business Planning Skills

An **evidence-aware, proposal-first** agent workspace for moving between an idea, market validation, business model, MVP, product requirements, pricing, roadmap, and go-to-market. It is **not** a solution-architecture/SAD repository.

## Reuse before invention

Domain methodologies are selected from [Paweł Huryn's open-source PM Skills](https://github.com/phuryn/pm-skills) (MIT), **pinned to a source commit**. Use `make vendor` to install the upstream skills verbatim into `vendor/pm-skills/`; attribution and license travel with the installed skills. The repository itself only adds an orchestration layer, project state, evidence policy, templates, and deterministic tooling. The upstream source is pinned in `upstream/skills.yaml`; edits to source methodology belong upstream, not in wrappers.

Read `skills/planning-orchestrator/SKILL.md` and `workflows/session.md` to drive the agent. Until `make vendor` succeeds, the catalog is a manifest of upstream sources; it is **not** a local copy of their instructions.

## Quick start — Typer + Questionary CLI

The CLI uses [Typer](https://typer.tiangolo.com/) (the framework behind FastAPI CLI's command layer) and [Questionary](https://github.com/tmbo/questionary) (interactive selection, text, confirmation). No custom terminal prompt engine or menu-selection parser is maintained.

```bash
make install
make start
```

Keep the short Make commands and project name; prompts handle keys and values:

```bash
make fact PROJECT=coffee-shop
make resolve PROJECT=coffee-shop
make propose PROJECT=coffee-shop
make override PROJECT=coffee-shop
```

Choose from existing/human-readable fact keys, or select **Other key**. Existing confirmed answers are reused and can only change after confirmation, with preserved revision history. Missing core intake questions are optional; skipping does not block product planning.

`python tools/interactive.py --help` lists all commands. The non-interactive `tools/knowledge.py` interface remains available for agents/CI. This CLI handles persistent knowledge, not autonomous product research or document synthesis.

## Deliverables

| Artifact | Purpose | Templates |
|---|---|---|
| Idea brief | Problem, opportunity, value hypothesis | `templates/idea-brief.md` |
| Market/customer analysis | Segments, competitors, demand evidence | `templates/market-analysis.md` |
| Business model / plan | Revenue mechanism, strategy, finances and risks | `templates/business-model.md`, `templates/business-plan.md` |
| Pricing strategy | Value metric, packaging, alternatives, experiments | `templates/pricing-strategy.md` |
| MVP definition | Smallest valuable test, scope, success criteria | `templates/mvp-definition.md` |
| Product requirements (SRS) | Functional behavior, business rules and acceptance tests | `templates/srs.md` |
| Product roadmap | Outcome-first priorities and release hypotheses | `templates/product-roadmap.md` |
| GTM/marketing | Positioning, ICP, channels, acquisition and measurement | `templates/gtm-strategy.md` |

All Markdown files are *views*. `knowledge/` YAML is authoritative for reusable project information; `state/` YAML is authoritative for execution progress. Never overwrite accepted knowledge just to make a template complete.

## Core principles

1. **Reuse → investigate → research → propose → ask.** Ask mainly for the real customer pain, intended audience, resource constraints, existing evidence and irreversible choices. Usually 1–3 targeted questions per round.
2. **No invented facts.** A proposed TAM, pricing tier, user persona, business capability or roadmap is welcome if labeled `proposed`; it is not a confirmed market observation or approval.
3. **Test the riskiest assumption.** Experiments have hypothesis, method, sample, success criterion, results and learning. Interviews show reported behavior, not proof of purchase.
4. **One project memory across outputs.** Reuse facts across business plan, SRS, MVP and GTM. Changes invalidate dependent proposals and draft sections for re-review.
5. **Short hot context.** Checkpoint → relevant facts/decisions → summaries of pinned investigations. Full transcripts/code are cold evidence.
6. **Explicit provenance.** Web sources have retrieval date; code findings have commit SHA and path; user answers have session/ref. Do not store credentials or unneeded PII.
7. **Agent specialists, not document silos.** Route to upstream domain skills as needed; do not automatically invoke the entire catalog.

## Workflow entry points

`workflows/idea-to-mvp.md`, `market-validation.md`, `pricing.md`, `requirements.md`, `roadmap.md`, `go-to-market.md` and `session.md`. Users may enter any workflow; no fixed linear gate. Formal approval belongs to a human.

## Common commands

Run `make help`. 

```bash
make new PROJECT=my-product
make validate PROJECT=my-product
make check                    # tests + schemas + templates
make vendor-check             # upstream skill manifest consistency; no network
make vendor                   # fetch pinned skills, with LICENSE
```

## Provenance and licensing

See `upstream/skills.yaml` for the exact upstream paths, commit and adoption rationale. `tools/vendor_skills.py` downloads only selected MIT-licensed files and the matching LICENSE, and fails rather than silently importing a different revision. No assumptions about the licensing of other candidate repositories are made here.

## Scope and limitations

- `tools/knowledge.py` provides **exact canonical-key resolution** and revision tracking; semantic synonyms, cross-artifact change propagation, synthesis and skill routing are agent responsibilities in this version.
- `make new` scaffolds a project; it does not fabricate content or independently interview customers.
- Research requires available external access; financial and market claims require sources, methodology and dates.
- This starter framework is suitable for a solo founder / small team; it is not a CRM, finance system or legal/compliance approval engine.
