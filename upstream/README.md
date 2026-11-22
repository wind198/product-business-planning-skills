# Upstream skill registry

`skills.yaml` pins selected `SKILL.md` files from `phuryn/pm-skills` at a verified GitHub commit. The original authors own the product methodologies; **this repository does not modify their text**. `make vendor` copies only selected skills into `vendor/pm-skills/<skill-id>/SKILL.md`, accompanied by the upstream MIT LICENSE and a lock file containing downloaded SHA-256 checksums.

Upgrading upstream requires reviewing changed instructions, checking licenses/dependencies and editing the commit deliberately. Never auto-track `main` or perform silent updates.

Additional explored candidates (not vendored because licensing/fit needs further review): `deanpeters/Product-Manager-Skills`, `bmad-code-org/BMAD-METHOD`, `tronghieu/agent-skills`, `RefoundAI/lenny-skills`.
