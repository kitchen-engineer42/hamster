---
name: hamster-packaging
description: Scaffold a clean John fork and transactionally package its supported diff as a strict, portable, dual-provider template. Use when creating the fork, translating a finished fork, choosing exact versions/providers, resolving packager warnings, validating relocation and real application, or reviewing `.hamster/package_summary.json` before handoff.
---

# Hamster packaging

Hamster treats the fork as editable source and the template as a reproducible
release artifact. Never edit a published template by hand.

## Scaffold a clean fork

```sh
HAMSTER_PACKAGING_DIR=
for candidate in .claude/skills/hamster-packaging .agents/skills/hamster-packaging; do
  [ -d "$candidate/scripts" ] && HAMSTER_PACKAGING_DIR=$candidate && break
done
test -n "$HAMSTER_PACKAGING_DIR" || { echo "hamster-packaging skill not loaded" >&2; exit 1; }
python3 "$HAMSTER_PACKAGING_DIR/scripts/scaffold_fork.py" \
  --name <safe-template-slug> \
  --joharnessburg-path "$JOHARNESSBURG_PATH"
```

The source checkout must be clean and symlink-free. The script validates the
nested `plugins/<name>/.claude-plugin/plugin.json` layout, clones into a
same-parent stage, records the immutable base commit, then atomically publishes
`forks/<name>/`. A failure leaves no fork.

## Package the fork

```sh
HAMSTER_PACKAGING_DIR=
for candidate in .claude/skills/hamster-packaging .agents/skills/hamster-packaging; do
  [ -d "$candidate/scripts" ] && HAMSTER_PACKAGING_DIR=$candidate && break
done
test -n "$HAMSTER_PACKAGING_DIR" || { echo "hamster-packaging skill not loaded" >&2; exit 1; }
python3 "$HAMSTER_PACKAGING_DIR/scripts/package_template.py" \
  --fork forks/<name> \
  --output templates/<name> \
  --template-version 0.1.0 \
  --provider both \
  --smoke-test
```

`--template-version` is required. `--requires-john` is optional and defaults to
the exact version from the base-commit manifest. `--provider` is
`claude|codex|both` and defaults to `both`. Use `--allow-warnings` only after the
user explicitly accepts every recorded warning; strict mode publishes nothing
when any warning exists.

The packager:

- reads NUL-delimited Git output with rename detection disabled, so a rename is
  an explicit delete plus add;
- rejects traversal and all source symlinks;
- translates full skill overrides, additive skills/platform files, whole-skill
  deletions, provider addons, Codex agents, and Claude workflow assets;
- copies the base-commit canonical `apply.sh` as an executable regular file and
  records its SHA-256;
- validates metadata, exact pins, frontmatter, references, JSON/Python/shell/
  TOML syntax, provider layouts, agent event contracts, release quality, and
  relocation;
- applies the staged template to a clean base-commit snapshot, and with
  `--smoke-test` initializes a project from that applied plugin;
- atomically publishes only after every gate passes.

Warnings, every validation result, the base commit, translations, and apply
checksum live only at `forks/<name>/.hamster/package_summary.json`. That file is
builder-side provenance and never ships in the template. It contains no machine
paths.

## Supported fork changes

| Fork change | Template output |
|---|---|
| Modify existing `plugins/<john>/skills/<name>/` | `skills/_override/<name>/` full replacement |
| Add a skill | `skills/<name>/` |
| Delete a whole skill | `skills/_delete` |
| Add scripts, commands, or canonical Markdown agents | same additive path |
| Add `plugins/<john>/codex/agents/*.toml` | `codex/agents/*.toml` |
| Add root `project_addon.md` | shared CLAUDE.md + AGENTS.md guidance |
| Add root `claude_addon.md` / `agents_addon.md` | provider-specific guidance |
| Add root `plan_md_template.md` | starter PLAN.md |
| Add `.claude/workflows/*.js` | preserved Claude workflow asset |

Platform files are additive-only. Hook, manifest, existing script/command/agent,
local-client, and repository-doc modifications become warnings. Revert them or
surface a core-John proposal.

For a load-bearing core-skill deletion, put the rationale in a fork-root
`deletion_reasons.json`, keyed by skill name. The packager writes it as the
same-line `_delete` reason and does not ship the declaration file.

## Provider contract

Do not convert Claude assets with a Hamster-specific converter. Claude
`agents/*.md` remain canonical; use John's deterministic agent sync contract to
produce matching template `codex/agents/*.toml`. A dual-provider package
requires a Codex counterpart for every additive Claude agent, while allowing
Codex-only agents. Shared produced skills must be byte-identical under
`.claude/skills/` and `.agents/skills/`.

Claude workflows remain untouched. Codex high-volume guidance consumes John's
`.john/runs` manifest/receipt/event barriers and native wave engine; it may use
the experimental CSV engine only after capability detection.

## Review and handoff

Read the builder-side summary and confirm `status: published`, zero unaccepted
warnings, a passing `validation`, the intended exact John pin/providers, and
the expected apply checksum. Then inspect the published template. The Claude
flow remains `apply.sh` plus `claude --plugin-dir`; the Codex flow applies first,
then uses John's project-local activation skill. Applied John replaces vanilla
John in that project session.

See `references/packaging_walkthrough.md` for a complete command sequence.
