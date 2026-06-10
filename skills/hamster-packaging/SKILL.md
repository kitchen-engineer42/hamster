---
name: hamster-packaging
description: Use when scaffolding the fork at the start of workshop work (scaffold_fork.py), when producing the template diff after you're done modifying (package_template.py), when the packager emits warnings and you need to decide what to do with them, or when eyeballing the packaged template before hand-off. Triggers on phrases like "ready to fork", "scaffold the fork", "time to package", "translate the diff", "package the template", "the template is ready", "what about this warning", or any time you're operating the two Hamster packaging scripts.
---

# Hamster packaging

This is where your modified John (the fork at `forks/<name>/`) becomes a packaged template diff at `templates/<name>/`. Two scripts do the work — you mostly just invoke them at the right moments.

## scaffold_fork.py — create the fork

Run this AT THE START of workshop work, before you start modifying anything:

```sh
python3 .claude/skills/hamster-packaging/scripts/scaffold_fork.py \
  --name <template-name> \
  --joharnessburg-path "$JOHARNESSBURG_PATH"
```

What it does:

- Validates `$JOHARNESSBURG_PATH` is a real joharnessburg checkout (has `.git` + `.claude-plugin/plugin.json`).
- `git clone`s it into `forks/<template-name>/` (a local clone — same git history).
- Records the current HEAD commit hash to `<fork>/.hamster-base-commit`.
- Refuses to overwrite an existing fork — pick a different name or delete the old one first.

Output: `forks/<template-name>/` is a complete writeable John clone. Start editing.

## package_template.py — produce the template diff

Run this when you're DONE modifying the fork and ready to produce the template:

```sh
python3 .claude/skills/hamster-packaging/scripts/package_template.py \
  --fork forks/<template-name> \
  --output templates/<template-name> \
  --description "Short description for template.json (optional)"
```

Optional flags:

- `--apply-script <path>` — explicit path to `joharnessburg/templates/apply.sh` (default: `<fork>/templates/apply.sh`).
- `--smoke-test` — after packaging, runs `apply.sh --help` to confirm it's executable.

What it does:

- Reads `.hamster-base-commit` from the fork.
- Computes the diff between base commit and the fork's current state (committed AND uncommitted, including untracked files).
- Classifies each changed path:
  - Modified files inside an existing `skills/<name>/` → full skill dir copied to `skills/_override/<name>/`.
  - New `skills/<new-name>/` → `skills/<new-name>/` additive.
  - New file under `scripts/`, `commands/`, `agents/` → same path (additive).
  - New `.js` file in the fork's `.claude/workflows/` (a saved dynamic workflow) → `workflows/<name>.js` (see below).
  - Deleted `skills/<name>/` (whole dir) → `<name>` appended to `skills/_delete`. If the name is one of John's six load-bearing core skills (using-john, ralph-loop, event-log-and-reducer, workspace-discipline, context-management, subagent-dispatch), the packager stamps `# TODO: state why this core skill is deleted` on the line and warns — **replace the TODO with the actual reason before shipping**; John's apply step warns loudly on core deletions and extra-loudly when no reason is stated.
  - `plan_md_template.md` or `claude_addon.md` at fork root → template root.
  - Modifications to anything else → WARN, skip, record in summary.
- Auto-generates `template.json` (name from output dir, version `0.1.0`, requires_john from current joharnessburg version).
- Symlinks `apply.sh` from the canonical location (or copies on platforms without symlink support).
- Writes `<output>/.hamster/package_summary.json` with base commit, every translation, every warning, timestamp.

Output: `templates/<template-name>/` is a valid John template folder, ready for the user to review and distribute (each user installs it at `~/.claude/plugins/joharnessburg-templates/<name>/` and runs its `apply.sh` — the John plugin itself ships no templates).

## Shipping a saved workflow (optional, research preview)

Most templates don't need this — John core ships the `vertical-workflows` skill so layer-3 Claude authors the right fan-out live per project. But if your domain has a **stable** sweep shape (a rule × chapter sweep, a per-slide render), you can freeze it as a saved workflow and ship it.

To author one: while modifying the fork, run the sweep as a dynamic workflow, then save the run's script (Claude Code saves it to the project's `.claude/workflows/<name>.js`). The packager picks up new `.claude/workflows/*.js` files and copies them into the template's `workflows/`; at runtime `/john:init` installs them into the user's project `.claude/workflows/`, where they register as `/<name>` commands.

Keep it shape-only — encode the fan-out *structure*, not one corpus's specifics (same discipline as `plan_md_template.md`). And treat it as graceful: it requires the user's Claude Code to support workflows, and Claude can always re-author live if it's absent.

## What to do with warnings

If `package_template.py` emits warnings, it means changes in the fork couldn't be translated to the template diff format. Common cases:

- **Modified `scripts/<file>.py`** — templates can't override scripts. Revert in fork, or surface to user as a core-John PR proposal.
- **Modified `hooks/hooks.json`** — hooks are platform infrastructure. Same options.
- **Modified `.claude-plugin/plugin.json`** — the manifest belongs to the platform.
- **Deletions outside `skills/`** — `_delete` only supports whole-skill deletions.

For each warning, decide: revert in fork, escalate to user, or find an in-scope alternative. See `hamster-workshop/SKILL.md` for the in-scope alternatives.

## Reading the package summary

`templates/<name>/.hamster/package_summary.json` is your audit trail. Read it after packaging to confirm:

- `base_commit` matches what you scaffolded against (you can `git log` the fork against it).
- `translations` covers every intended change.
- `warnings` is empty, OR every warning has been consciously decided about.
- `requires_john` matches the version you actually used.

If anything's off, fix it (re-edit the fork, re-package) before handing off.

## Eyeballing the template before hand-off

After `package_template.py` succeeds, look at `templates/<name>/`:

- `template.json` — confirm name, description, requires_john are right.
- `apply.sh` — should be a symlink (or copy on Windows).
- `skills/_override/<name>/` — each override should be a complete skill dir (SKILL.md + any references/).
- `skills/<new-name>/` — same; complete skill dirs.
- `skills/_delete` — list of names, one per line; same-line `name # reason` comments supported (a reason is expected for core-skill deletions).
- `workflows/<name>.js` — any saved dynamic workflows the template ships (optional).
- `plan_md_template.md`, `claude_addon.md` — what layer-3 Claude reads at runtime.

If anything looks wrong, return to the fork, fix, delete `templates/<name>/`, re-package.

## The smoke test

`--smoke-test` invokes `apply.sh --help` and prints the exit code. It's a sanity check (does apply.sh run at all), not a real validation. For a proper test, apply the template against a real joharnessburg-applied dir manually:

```sh
cd templates/<name>
./apply.sh --plugin-dir ~/.claude/plugins/joharnessburg-applied/<name>-test
```

Confirm:

- It exits 0.
- `~/.claude/plugins/joharnessburg-applied/<name>-test/skills/` has overrides applied and additive skills present.
- `templates-active/plan_md_template.md` and `claude_addon.md` are populated if your template ships them.

`references/packaging_walkthrough.md` has the full 10-step packaging session walkthrough.

## When this skill triggers

- You're starting workshop work and need to create the fork → use `scaffold_fork.py`.
- You're done modifying the fork and want to produce the template → use `package_template.py`.
- The packager emitted warnings and you need to decide what to do.
- You want to eyeball-verify the packaged template before hand-off.

If you're still designing what to change (not done modifying), the trigger is `hamster-drawing-board` or `hamster-workshop`.

## When you're done packaging

Tell the user: "Template packaged at `templates/<template-name>/`. Base commit: `<short-hash>`. Translations: N. Warnings: 0 (or N with details in the summary). Ready for your review."

The user will eyeball, possibly test against a real joharnessburg-applied dir, and distribute it when satisfied (team users install it at `~/.claude/plugins/joharnessburg-templates/<name>/`).
