# CLI framework references and decisions

## Adopt, do not rewrite

- **Typer** — command routing, options, built-in help, and testing with Click's CLI runner. Upstream: https://github.com/fastapi/typer — MIT.
- **Questionary** — interactive select/text/confirm prompts; uses prompt_toolkit. Upstream: https://github.com/tmbo/questionary — MIT.
- **Rich** — formatted tables and helpful result output; installed as a Typer dependency.

FastAPI CLI itself uses Typer and Rich-related tooling, but its application discovery and Uvicorn integration are unrelated to this repo, so **do not** depend on fastapi-cli directly.

## Boundaries

`tools/interactive.py`: thin Typer commands + Questionary prompts and rendering. No manual `input()` menus, numeric parsing, or reusable homegrown prompt engine.

`tools/knowledge.py`: authoritative persistence, scope validation, schema validation and revision rules. No terminal I/O assumptions.

`tools/new_project.py`: workspace creation. The CLI delegates to it rather than duplicating project scaffolding.

`tests/test_interactive.py`: Typer CliRunner; patch Questionary prompts to make tests deterministic and work without a TTY.

Focused commands accept `PROJECT` through Make; keys and values are prompted. Scripted agents retain the low-level deterministic API.

## Source quality

- Typer docs: https://typer.tiangolo.com/tutorial/prompt/
- Questionary docs: https://questionary.readthedocs.io/en/stable/
- FastAPI CLI dependency declaration: https://github.com/fastapi/fastapi-cli/blob/main/pyproject.toml

Only existing library UI functionality is used. Do not copy their code into this repository.
