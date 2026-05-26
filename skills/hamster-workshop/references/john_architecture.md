# John architecture — Hamster's working summary

**Pinned to John v0.1.12 (joharnessburg) at the time of writing.** This summary captures the layout, skills, hooks, and pipeline mechanics of the joharnessburg Claude Code plugin as Hamster Claude needs to understand them to author templates. When John updates, this doc may rot — see the footer for how to recover.

## What John is

John (slug `joharnessburg`, AGPL-3.0) is a Claude Code plugin that wraps Claude Code in skills + hooks + slash commands + a Python toolkit, so a single long-running session can take unstructured input (books, regulations, mixed docs) through knowledge engineering and then app building. Architecture: **horizontal phases × vertical parallel subagents**.

## Top-level layout (the only files inside the plugin)

```
joharnessburg/
├── .claude-plugin/
│   ├── plugin.json        # Claude Code plugin manifest
│   └── marketplace.json   # Lets the repo also act as a marketplace
├── hooks/hooks.json       # Hook declarations
├── skills/<26 skills>/    # The "fat" in thin-harness-fat-skills
├── commands/<slash-cmds>/ # Slash commands
├── scripts/<toolkit>.py   # Small Python utilities
├── agents/<subagent>.md   # Subagent role definitions
├── templates/             # Template-authoring docs + bundled examples
└── README.md, LICENSE
```

**Outside the plugin (workspace level)**, joharnessburg ships alongside `local_clients/llm/` and `local_clients/ppx/` — external FastAPI servers wrapping SiliconFlow/DeepSeek and the `memect-ppx` parser. Plugin code reaches them via env vars (`$JOHN_LLM_CLIENT_URL`, `$JOHN_PPX_CLIENT_URL`). Templates do NOT ship local_clients — they live with the platform deployment.

## The 26 skills (grouped by role)

Skills live at `joharnessburg/skills/<name>/SKILL.md` with optional `references/` subdirs. Templates can override (`skills/_override/<name>/`), add (`skills/<new>/`), or delete (`skills/_delete` file) any of these.

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

**Runtime + event coordination (2)**
- `workerllm-runtime` — How produced apps call workerLLMs at runtime.
- `event-log-and-reducer` — Append-only event log + deterministic reducer for coordinating parallel subagents.

**Platform integration — for produced apps that ship to the team's hosted platform (7)**
- `platform-auth`, `platform-credits`, `platform-deploy`, `platform-llm-proxy`, `platform-model-config`, `platform-parser`, `platform-telemetry`

Most templates won't touch the platform-* skills; they're conditional, loaded only when the produced apps need them.

## Hooks

`hooks/hooks.json` declares hooks that auto-fire during Claude Code sessions. As of v0.1.12, the primary hook is `PostToolUse` with matcher `Read|Bash|Write|Edit` — used for event-log discipline and workspace tracking. **Templates do NOT modify hooks.json** — that's core platform infrastructure.

## Scripts (Python toolkit)

`joharnessburg/scripts/` ships small stdlib-Python utilities. Notable ones Hamster Claude may need to know about:

- `init_workspace.py` — scaffolds a fresh John workspace (CLAUDE.md, PLAN.md, .john/). Reads `templates-active/plan_md_template.md` + `claude_addon.md` if present.
- `apply_template.py` — applies a template diff to John's installed plugin; produces a merged plugin at `~/.claude/plugins/joharnessburg-applied/<name>/`.
- `set_template.py` — manages which template is active in a workspace (atomic apply + workspace.json update).
- `reduce_events.py` — deterministic reducer for the event log; supports `--dry-run`.
- `ppx_parse.py` — thin HTTP client to the local `local_clients/ppx/` FastAPI server.
- `markitdown_parse.py` — wrapper around the `markitdown` library for non-PDF parsing.
- `parse_govcn_html.py` — gov.cn HTML fallback parser.

Templates can ADD scripts but cannot override existing ones (additive-only; the collision policy added in v0.1.9 enforces this).

## Templates — the diff-script architecture (v0.1.7+)

A John template is a directory at `joharnessburg/templates/<name>/` containing a *diff* against original John. Layout:

```
templates/<name>/
├── template.json                       # required: name, version, description, requires_john (informational)
├── apply.sh                            # required: symlink to joharnessburg/templates/apply.sh
├── plan_md_template.md                 # optional: starter PLAN.md skeleton
├── claude_addon.md                     # optional: appended to scaffolded CLAUDE.md
├── skills/
│   ├── <new-skill>/                    # additive: new skill not in core
│   ├── _override/<core-skill>/         # replaces a core skill (FULL replacement, not merge)
│   └── _delete                         # newline list of core skills to remove
├── scripts/<new-script>.py             # additive only (collision warns + skips)
├── commands/<new-command>.md           # additive only
└── agents/<new-agent>.md               # additive only
```

`apply_template.py` produces `~/.claude/plugins/joharnessburg-applied/<name>/` — a merged plugin Claude Code launches with `claude --plugin-dir <merged-dir>`. The merge copies original John wholesale, then layers the template's diffs on top. Multiple templates can coexist as separate merged dirs (v0.1.8 per-session isolation).

**What templates CAN do**:
- Override existing skills (with full replacement under `skills/_override/`).
- Add new skills under `skills/<new-name>/`.
- Add new scripts, commands, agents (additive only).
- Delete core skills via `skills/_delete`.
- Ship a starter `plan_md_template.md` and `claude_addon.md`.

**What templates CANNOT do** (collision warnings or platform-level concerns):
- Override scripts, commands, agents (collision in additive-only mode → skip + warn).
- Modify `hooks/hooks.json` — core platform infrastructure.
- Modify `.claude-plugin/plugin.json` — manifest is owned by the platform.
- Modify or ship `local_clients/` — those live at workspace level, outside the plugin.

## `templates-active/` mechanism

When a template is applied, `apply_template.py` copies `plan_md_template.md` and `claude_addon.md` (if the template ships them) to `<merged-plugin>/templates-active/`. Then:

- `init_workspace.py` reads `templates-active/plan_md_template.md` (if present) as the PLAN.md skeleton — falls back to a hardcoded template otherwise.
- `init_workspace.py` reads `templates-active/claude_addon.md` (if present) and appends it under a `## From active template` section in the scaffolded CLAUDE.md.

This is how a template injects project-level guidance into a John runtime session without touching the layer-2 CLAUDE.md or the layer-3 skill body.

## The ralph_loop — horizontal phase driver

John's runtime is one long Claude Code session that iterates through phases declared in PLAN.md. Each phase has subagents (vertical parallelism) that emit events to an append-only event log; a deterministic reducer collapses events into state. Templates customize the phase list (via `plan_md_template.md`), the schema-design (per project), and the subagent roles (via `agents/` or overrides). The mechanics live in `ralph-loop`, `phase-design`, `event-log-and-reducer`, `subagent-dispatch` skills.

## Local clients (workspace level, outside the plugin)

- **`local_clients/llm/`** — FastAPI server wrapping SiliconFlow + DeepSeek; serves OpenAI-compatible `/v1/chat/completions`. Plugin calls it via `$JOHN_LLM_CLIENT_URL` (default `http://localhost:8500`).
- **`local_clients/ppx/`** — FastAPI server wrapping `memect-ppx` (the `ppx` parser engine). Plugin calls it via `$JOHN_PPX_CLIENT_URL` (default `http://localhost:8501`).

When the tech team ships production servers, the URL env vars get swapped — no plugin code changes. Templates that need these tools assume they're available via the URL contracts; templates do NOT bundle the tools themselves.

## Subagent definitions

`joharnessburg/agents/` contains subagent role definitions used by `subagent-dispatch`. Notable ones include `knowledge-extractor`, `schema-designer`, `code-quality-reviewer`. Templates can ADD agents (additive only); they can't override existing ones via the additive-collision policy.

## How a layer-3 John session typically flows

(For your mental model — you, Hamster Claude, are designing the template that *shapes* this flow.)

1. User runs `claude` in a project workspace where `joharnessburg-applied/<template>` is installed.
2. `using-john` skill triggers; layer-3 Claude reads it + PLAN.md + CLAUDE.md.
3. `init_workspace.py` (or its `/joharnessburg-init` command) scaffolds `.john/`, PLAN.md, CLAUDE.md from `templates-active/`.
4. Layer-3 Claude works through the phases declared in PLAN.md, using ralph_loop to advance, dispatching subagents for parallel work per phase, writing events to the log, reading reduced state.
5. Each phase typically: read inputs (parsing skill), chunk (chunking), extract knowledge (knowledge-extraction with subagents), rewrite/dedupe (knowledge-rewrite), package as skills (packaging), eventually build the app (app-design-thinking, subsite-builder).
6. Final output: a working app shipped to the team's platform (via platform-* skills) or run locally.

Your template customizes any of these moves the apps in your family need to be done differently.

---

## When this rots

This summary is pinned to John v0.1.12. When John updates, this doc will drift. To recover:

1. Re-read live `$JOHARNESSBURG_PATH/PLAN.md` (the workspace plan in the joharnessburg repo).
2. Re-read live `$JOHARNESSBURG_PATH/README.md` and `$JOHARNESSBURG_PATH/templates/README.md`.
3. `ls $JOHARNESSBURG_PATH/skills/` — confirm the skill list against the grouping above. Any new skills since v0.1.12 may belong in additional categories.
4. Run `git log --oneline -20` in `$JOHARNESSBURG_PATH` to see recent changes.

If you're authoring a template against a substantially newer John, propose to the user that Hamster's `john_architecture.md` reference be refreshed in workspace `/skills/hamster-workshop/references/` and re-shipped in the next Hamster version.
