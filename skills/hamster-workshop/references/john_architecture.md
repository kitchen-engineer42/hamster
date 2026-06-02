# John architecture — Hamster's working summary

**Pinned to John v0.1.21 (joharnessburg) at the time of writing.** This summary captures the layout, skills, hooks, and pipeline mechanics of the joharnessburg Claude Code plugin as Hamster Claude needs to understand them to author templates. When John updates, this doc may rot — see the footer for how to recover.

## What John is

John (slug `joharnessburg`, MIT) is a Claude Code plugin that wraps Claude Code in skills + hooks + slash commands + a Python toolkit, so a single long-running session can take unstructured input (books, regulations, mixed docs) through knowledge engineering and then app building. Architecture: **horizontal phases × vertical parallel subagents**.

## Repository layout (marketplace + plugin subdir)

The joharnessburg repo is BOTH a marketplace AND a plugin. The marketplace catalog lives at the repo root; the plugin itself lives in a subdirectory:

```
joharnessburg/                       # repo root (also the marketplace root)
├── .claude-plugin/
│   └── marketplace.json             # Marketplace catalog (references the plugin below)
├── plugins/
│   └── joharnessburg/                # The plugin itself
│       ├── .claude-plugin/
│       │   └── plugin.json           # Claude Code plugin manifest
│       ├── hooks/hooks.json          # Hook declarations
│       ├── skills/<27 skills>/       # The "fat" in thin-harness-fat-skills
│       ├── commands/<slash-cmds>/    # Slash commands
│       ├── scripts/<toolkit>.py      # Small Python utilities
│       ├── agents/<subagent>.md      # Subagent role definitions
│       └── templates/                # Bundled example templates + authoring docs
├── README.md, README_ZH.md
└── LICENSE
```

When you fork via `scaffold_fork.py`, your fork mirrors this layout — you modify files inside `<fork>/plugins/joharnessburg/`, not at the fork root.

**Outside the plugin (workspace level)**, joharnessburg ships alongside `local_clients/llm/` and `local_clients/ppx/` — external FastAPI servers wrapping SiliconFlow/DeepSeek and the `memect-ppx` parser. Plugin code reaches them via env vars (`$JOHN_LLM_CLIENT_URL`, `$JOHN_PPX_CLIENT_URL`). Templates do NOT ship local_clients — they live with the platform deployment.

## The 27 skills (grouped by role)

Skills live at `plugins/joharnessburg/skills/<name>/SKILL.md` with optional `references/` subdirs. Templates can override (`skills/_override/<name>/`), add (`skills/<new>/`), or delete (`skills/_delete` file) any of these.

**Orientation + working discipline (5)**
- `using-john` — Top-level orientation. Layer-3 Claude reads this first.
- `ralph-loop` — The iterative plan-driven advancement pattern; horizontal phase driver.
- `workspace-discipline` — "Disk is truth. Never trust in-memory belief about what's done."
- `context-management` — Surviving long-running sessions where work spans hours/days.
- `subagent-dispatch` — When and how to spawn subagents for the vertical axis.

**Planning (3)**
- `plan-md-authoring` — Write the initial PLAN.md at project start.
- `plan-md-evolution` — Keep PLAN.md current as work proceeds.
- `phase-design` — Decide what phases this project actually needs.

**Knowledge engineering pipeline (6)**
- `parsing` — Turn raw inputs (PDFs, DOCX, mixed docs) into structured markdown.
- `chunking` — Break parsed markdown into a tree of progressively-disclosed chunks.
- `schema-design` — Decide what shape the knowledge takes for this project.
- `knowledge-extraction` — Sweep chunks for entries matching the project's schema; emit via event log.
- `knowledge-rewrite` — Clean, cross-link, dedupe raw event-log entries.
- `packaging` — Emit cleaned knowledge as Claude Code skills (the produced app's "fat").

**App building (3)**
- `app-design-thinking` — Runtime structure + production pipeline for the produced app. The 2app analog of schema-design.
- `subsite-builder` — Produced app's overall structure for platform-integrated projects.
- `code-quality-guardrails` — Deterministic quality checks on code John produces.

**Runtime + event coordination (3)**
- `workerllm-runtime` — How produced apps call workerLLMs at runtime.
- `event-log-and-reducer` — Append-only event log + deterministic reducer for coordinating parallel subagents.
- `vertical-workflows` — The vertical-axis execution engine: author a Claude Code dynamic workflow to run a large fan-out phase (fan out workers off-context, adversarially cross-check, write to the event log), with inline-dispatch fallback. Teaches the John-shaped fan-out *pattern*, not the workflow API.

**Platform integration — for produced apps that ship to the team's hosted platform (7)**
- `platform-auth`, `platform-credits`, `platform-deploy`, `platform-llm-proxy`, `platform-model-config`, `platform-parser`, `platform-telemetry`

Most templates won't touch the platform-* skills; they're conditional, loaded only when the produced apps need them.

## Hooks

`hooks/hooks.json` declares hooks that auto-fire during Claude Code sessions. The primary hook is `PostToolUse` with matcher `Read|Bash|Write|Edit` — used for event-log discipline and workspace tracking. There's also a `SessionStart` hook that injects PLAN.md preview + endurance goal + loaded-template info into the session's initial context. **Templates do NOT modify hooks.json** — that's core platform infrastructure.

## Scripts (Python toolkit)

`plugins/joharnessburg/scripts/` ships small stdlib-Python utilities. Notable ones Hamster Claude may need to know about:

- `init_workspace.py` — scaffolds a fresh John workspace (CLAUDE.md, PLAN.md, .john/). Reads `templates-active/plan_md_template.md` + `claude_addon.md` if present.
- `apply_template.py` — applies a template diff to John's installed plugin; produces a merged plugin at `~/.claude/plugins/joharnessburg-applied/<name>/`. Called by each template's `apply.sh`.
- `reset_john.py` — wipes all merged plugins at `~/.claude/plugins/joharnessburg-applied/`. Use to clean state between template tests.
- `reduce_events.py` — deterministic reducer for the event log; supports `--dry-run`.
- `ppx_parse.py` — thin HTTP client to the local `local_clients/ppx/` FastAPI server.
- `markitdown_parse.py` — wrapper around the `markitdown` library for non-PDF parsing.
- `parse_govcn_html.py` — gov.cn HTML fallback parser.
- `workspace_status.py` — prints workspace state + detects "loaded template" from `$CLAUDE_PLUGIN_ROOT`.
- `session_start_hook.py` + `post_tool_use_hook.py` + `precompact_hook.py` — wire into Claude Code's hook events.
- `archive_workspace.py` — bundle a finished John workspace into a zip.

Templates can ADD scripts but cannot override existing ones (additive-only; the collision policy enforces this).

## Slash commands

`plugins/joharnessburg/commands/` ships:

- `/john:init` — scaffold a workspace in cwd.
- `/john:status` — print current phase + progress.
- `/john:archive` — archive a finished workspace.
- `/endurance` — set or recall the session's endurance goal.

Templates are installed + applied via `apply.sh` and launched via `--plugin-dir`; see "Templates" below.

## Templates — the diff-script architecture

A John template is a directory at `~/.claude/plugins/joharnessburg-templates/<name>/` (user-scope install location) containing a *diff* against original John. Reference example templates live in **Hamster's own repo** at `<hamster-checkout>/examples/{slides-from-textbook,doc-verification}/` — that's your nearest place to see the diff format in practice.

Template layout:

```
<template>/
├── template.json                       # required: name, version, description, requires_john (informational)
├── apply.sh                            # required: symlink/copy of joharnessburg/plugins/joharnessburg/templates/apply.sh
├── plan_md_template.md                 # optional: starter PLAN.md skeleton
├── claude_addon.md                     # optional: appended to scaffolded CLAUDE.md
├── skills/
│   ├── <new-skill>/                    # additive: new skill not in core
│   ├── _override/<core-skill>/         # replaces a core skill (FULL replacement, not merge)
│   └── _delete                         # newline list of core skills to remove
├── scripts/<new-script>.py             # additive only (collision warns + skips)
├── commands/<new-command>.md           # additive only
├── agents/<new-agent>.md               # additive only
└── workflows/<name>.js                 # optional: saved dynamic workflows; /john:init installs them into the project's .claude/workflows/
```

The canonical flow:

1. **Install** the template at `~/.claude/plugins/joharnessburg-templates/<name>/` (user runs `cp -R` or `ln -s` manually).
2. **Apply** by running the template's `apply.sh`. This produces a merged plugin at `~/.claude/plugins/joharnessburg-applied/<name>/`. apply.sh prints the launch command on stderr at success.
3. **Launch** Claude with `claude --plugin-dir ~/.claude/plugins/joharnessburg-applied/<name>/`. The merged plugin IS John for that session — all skills load equally, no special template layer.
4. **Switch** = exit, optionally apply a different template, relaunch with a different `--plugin-dir`. Multiple merged dirs at `joharnessburg-applied/<name>/` coexist freely (parallel sessions with different templates work).
5. **Reset** = `rm -rf ~/.claude/plugins/joharnessburg-applied/` (or call `reset_john.py`).

There is **no per-workspace "active template" state**. The plugin loaded at session start IS the template — `$CLAUDE_PLUGIN_ROOT` is the source of truth.

**What templates CAN do**:
- Override existing skills (with full replacement under `skills/_override/`).
- Add new skills under `skills/<new-name>/`.
- Add new scripts, commands, agents (additive only).
- Delete core skills via `skills/_delete`.
- Ship a starter `plan_md_template.md` and `claude_addon.md`.
- Ship saved dynamic workflows under `workflows/` (research-preview; installed into the project's `.claude/workflows/` by `/john:init`). Most templates won't — John core ships the `vertical-workflows` skill so Claude authors the fan-out live. Freeze a workflow only when the sweep shape is stable; keep it shape-only and graceful (Claude re-authors if workflows are unavailable).

**What templates CANNOT do** (collision warnings or platform-level concerns):
- Override scripts, commands, agents (collision in additive-only mode → skip + warn).
- Modify `hooks/hooks.json` — core platform infrastructure.
- Modify `.claude-plugin/plugin.json` — manifest is owned by the platform.
- Modify or ship `local_clients/` — those live at workspace level, outside the plugin.

## `templates-active/` mechanism

When a template is applied, `apply_template.py` copies `plan_md_template.md` and `claude_addon.md` (if the template ships them) to `<merged-plugin>/templates-active/`. Then:

- `init_workspace.py` reads `templates-active/plan_md_template.md` (if present) as the PLAN.md skeleton — falls back to a hardcoded template otherwise.
- `init_workspace.py` reads `templates-active/claude_addon.md` (if present) and appends it under a `## From active template` section in the scaffolded CLAUDE.md.
- `apply_template.py` also copies a template's `workflows/` to `templates-active/workflows/`; `init_workspace.py` then installs those `*.js` into the project's `.claude/workflows/` (skip-if-exists), where Claude Code registers them as `/<name>` commands. (A plugin can't register saved workflows directly — they have to land in the project, which is why they route through `templates-active/`.)

This is how a template injects project-level guidance into a John runtime session without touching the layer-2 CLAUDE.md or the layer-3 skill body.

## The ralph_loop — horizontal phase driver

John's runtime is one long Claude Code session that iterates through phases declared in PLAN.md. Each phase has subagents (vertical parallelism) that emit events to an append-only event log; a deterministic reducer collapses events into state. A large, uniform fan-out phase runs as **one dynamic-workflow run** (the `vertical-workflows` skill) when the session supports it — the workflow fans the workers out off-context, cross-checks them, and writes the same events; the phase boundary is the sign-off seam between runs. When workflows aren't available it falls back to inline dispatch — same events, same reducer, same output. Templates customize the phase list (via `plan_md_template.md`), the schema-design (per project), and the subagent roles (via `agents/` or overrides). The mechanics live in `ralph-loop`, `phase-design`, `event-log-and-reducer`, `subagent-dispatch`, `vertical-workflows` skills.

## Local clients (workspace level, outside the plugin)

- **`local_clients/llm/`** — FastAPI server wrapping SiliconFlow + DeepSeek; serves OpenAI-compatible `/v1/chat/completions`. Plugin calls it via `$JOHN_LLM_CLIENT_URL` (default `http://localhost:8500`).
- **`local_clients/ppx/`** — FastAPI server wrapping `memect-ppx` (the `ppx` parser engine). Plugin calls it via `$JOHN_PPX_CLIENT_URL` (default `http://localhost:8501`).

When the tech team ships production servers, the URL env vars get swapped — no plugin code changes. Templates that need these tools assume they're available via the URL contracts; templates do NOT bundle the tools themselves.

## Subagent definitions

`plugins/joharnessburg/agents/` contains subagent role definitions used by `subagent-dispatch` and `vertical-workflows`. The worker agents are `knowledge-extractor` and `schema-designer`; the reviewer/cross-check agents are `code-quality-reviewer`, plus `coverage-auditor` (finds entries the extractor missed — MECE) and `grounding-checker` (flags entries not traceable to source) for the adversarial cross-check stage of a fan-out workflow. Templates can ADD agents (additive only); they can't override existing ones via the additive-collision policy.

## How a layer-3 John session typically flows

(For your mental model — you, Hamster Claude, are designing the template that *shapes* this flow.)

1. User has installed John (`claude plugin install john@joharnessburg`) and optionally a template at `~/.claude/plugins/joharnessburg-templates/<template>/`.
2. User has run the template's `apply.sh` (producing `~/.claude/plugins/joharnessburg-applied/<template>/`).
3. User runs `claude --plugin-dir ~/.claude/plugins/joharnessburg-applied/<template>/` in a project workspace.
4. `SessionStart` hook fires, injects PLAN.md preview + endurance goal + loaded-template info.
5. `using-john` skill triggers; layer-3 Claude reads it + PLAN.md + CLAUDE.md.
6. `init_workspace.py` (or its `/john:init` command) scaffolds `.john/`, PLAN.md, CLAUDE.md from `templates-active/`.
7. Layer-3 Claude works through the phases declared in PLAN.md, using ralph_loop to advance, dispatching subagents for parallel work per phase, writing events to the log, reading reduced state.
8. Each phase typically: read inputs (parsing skill), chunk (chunking), extract knowledge (knowledge-extraction with subagents), rewrite/dedupe (knowledge-rewrite), package as skills (packaging), eventually build the app (app-design-thinking, subsite-builder).
9. Final output: a working app shipped to the team's platform (via platform-* skills) or run locally.

Your template customizes any of these moves the apps in your family need to be done differently.

---

## When this rots

This summary is pinned to John v0.1.21. When John updates, this doc will drift. To recover:

1. Re-read live `$JOHARNESSBURG_PATH/PLAN.md` (the workspace plan in the joharnessburg repo).
2. Re-read live `$JOHARNESSBURG_PATH/README.md` and `$JOHARNESSBURG_PATH/plugins/joharnessburg/templates/README.md`.
3. `ls $JOHARNESSBURG_PATH/plugins/joharnessburg/skills/` — confirm the skill list against the grouping above. Any new skills may belong in additional categories.
4. Run `git log --oneline -20` in `$JOHARNESSBURG_PATH` to see recent changes.

If you're authoring a template against a substantially newer John, propose to the user that Hamster's `john_architecture.md` reference be refreshed in workspace `/skills/hamster-workshop/references/` and re-shipped in the next Hamster version.
