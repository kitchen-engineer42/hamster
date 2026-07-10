# HAMSTER.md — template-authoring session

This directory is a Hamster working directory. Hamster helps a coding agent turn raw domain inputs into a validated, distributable template for [John](https://github.com/kitchen-engineer42/joharnessburg).

Hamster is not John. You work *over* a clean John checkout: study it read-only, clone it into a sandboxed fork, modify that fork, and let the strict packager compute the template diff. A future John-equipped session applies the template to build actual apps.

## Three layers

1. **Hamster source** — the people and repository that maintain these skills; not the active build workspace.
2. **Hamster-equipped session** — you, using Claude Code or Codex in this directory to author a John template.
3. **John-equipped session** — a future coding agent with John plus the produced template, building one knowledge-dense app.

workerLLMs and background jobs run below these layers inside produced apps. Name the layer when a distinction matters.

## Working agreements

- Trust the active coding agent: use a thin harness and focused skills, and avoid over-specifying the template.
- Surface uncertain product choices to the user; keep implementation tight.
- Use subagents for large reading tasks and give each one the project brief plus a focused question.
- Take free-form notes under `notes/` and return to them as the design evolves.
- Treat provider-specific behavior as an adapter branch. Shared methodology and template domain knowledge belong in provider-neutral files.
- Produce a family-level template, not a copy of one sample app.

## Read and write boundaries

Read freely:

- `HAMSTER.md`, the active provider adapter, and the installed `hamster-*` skills.
- `$JOHARNESSBURG_PATH`, the user-provided clean John checkout. It is strictly read-only.
- The user-provided input folder.
- `forks/<template-name>/` after the scaffold tool creates it.

Write only inside this working directory:

- `forks/<template-name>/` — the writable John clone and real authoring surface.
- `templates/<template-name>/` — atomic output from the strict packager; never hand-edit it.
- `notes/` — scratch analysis and decisions.

Do not modify `$JOHARNESSBURG_PATH`, installed Hamster skills, or paths outside this working directory. Propose any needed John-core or external-tool change to the user instead of applying it out of scope.

## Workflow

1. **Orient** — read `HAMSTER.md`, the provider adapter, and `hamster-orientation`.
2. **Design** — use `hamster-drawing-board` and `hamster-product-thinking` to classify inputs and settle the app-type definition: knowledge format, knowledge schema, app mechanism, and build pipeline.
3. **Fork** — use `hamster-packaging` to run `scaffold_fork.py`; the source checkout must be clean and symlink-free.
4. **Workshop** — use `hamster-workshop` to change only the fork. Put shared runtime guidance in `project_addon.md`; reserve `claude_addon.md` and `agents_addon.md` for provider execution differences.
5. **Package** — use `hamster-packaging` with an explicit template version, provider selection, exact John pin, and `--smoke-test`.
6. **Validate and hand off** — inspect `forks/<name>/.hamster/package_summary.json`; distribute only the published directory under `templates/<name>/`.

The design and workshop steps naturally interleave. Use the active runtime's planning surface as the seam for user approval, not as a rigid phase boundary.

## Path map

| Path | Purpose |
|---|---|
| `$JOHARNESSBURG_PATH` | Clean original John checkout; read-only |
| `<inputs>/` | User-provided source material; read-only |
| `forks/<name>/` | Writable John clone |
| `forks/<name>/.hamster/package_summary.json` | Builder-only package provenance |
| `templates/<name>/` | Validated distributable template |
| `notes/` | Free-form working notes |
| `.claude/skills/hamster-*/` | Claude Code skill discovery |
| `.agents/skills/hamster-*/` | Codex skill discovery |

## Provider output contract

Shared template skills and `project_addon.md` must work for both providers. Keep produced project skills byte-identical under `.claude/skills/` and `.agents/skills/`. Preserve Claude dynamic-workflow assets as Claude-specific files; describe Codex high-volume execution through John's native waves and `.john/runs/` ledger. Both branches must converge on the same John events, audits, checkpoints, and deliverables.

When in doubt, re-read `hamster-orientation`, inspect the relevant source, write a note, and ask the user about any choice that would materially narrow the template.
