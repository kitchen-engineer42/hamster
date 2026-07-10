# John architecture — Hamster working summary

**Pinned to John v0.5.1.** Re-read the live checkout before overriding a core
asset; the footer lists the refresh path.

## Repository and plugin boundaries

John's independent repository is a marketplace whose plugin is nested:

```text
joharnessburg/
├── .claude-plugin/marketplace.json
├── .agents/plugins/marketplace.json
├── plugins/joharnessburg/
│   ├── .claude-plugin/plugin.json
│   ├── .codex-plugin/plugin.json
│   ├── hooks/hooks.json
│   ├── agents/*.md                 # canonical shared roles
│   ├── codex/agents/*.toml         # generated provider mirrors
│   ├── skills/, commands/, scripts/
│   └── templates/{apply.sh,README.md}
├── CONTEXT.md
└── README.md
```

Hamster forks the repository but template changes normally live inside
`<fork>/plugins/joharnessburg/`. The original `$JOHARNESSBURG_PATH` remains
read-only and must be clean when scaffolding.

The workspace's LLM and PPX clients are external, ignored local services—not
John dependencies and not template content. Templates consume only their URL
contracts. `/healthz` means liveness; `/readyz` means usable. Both services bind
only to loopback in this release.

## Three runtime levels

1. Hamster authors a template from a John fork.
2. A John-equipped Claude Code or Codex session applies that template while building an app.
3. workerLLMs and background jobs run inside the produced app.

Do not confuse build-session orchestration with produced-app runtime jobs.

## Shared methodology

John's horizontal axis is a PLAN.md phase sequence. Its vertical axis fans out
uniform work units. The load-bearing skills are `using-john`, `ralph-loop`,
`workspace-discipline`, `context-management`, `subagent-dispatch`,
`event-log-and-reducer`, and `skill-evolution`. Other groups cover planning,
parsing/chunking/schema/extraction/rewrite/packaging, app design and code
guardrails, workerLLM/job runtimes, reporting, and provider adapters.

Templates may fully override a skill, add a skill, or delete a whole skill.
They may add scripts, commands, and agents but not replace existing platform
files. Core-skill deletions carry an explicit same-line reason.

## Event, audit, and run contracts

All parallel producers use the append-only event ledger under
`.john/events/<phase>/`. Producers pipe one JSON object through
`scripts/emit_event.py`; that writer adds a unique event ID, UTC timestamp,
agent ID, and audit-run ID and atomically publishes a unique filename. Agents
must not handcraft retry-prone event filenames.

Extraction ends only after separate extraction, coverage, grounding,
adjudication, and reduction stages. Shipped guidance runs:

```sh
python3 scripts/reduce_events.py extract \
  --expect-entries <N-or-range> --verify-knowledge \
  --require-extraction-audits
```

Exit 3 is count-gate failure. Exit 4 is audit-gate failure. The checkpoint's
additive `quality_gate` gives reasons and accepted IDs; a failing chunk is
excluded as a whole. Generic legacy reduction remains available when the audit
flag is omitted.

For durable high-volume work, `john_run.py` stores immutable input, attempts,
and reconciliation under `.john/runs/<phase>/<run-id>/`. Completion requires
referenced events to exist, parse, match run/item identity, and contain the
required terminal event. Defaults are depth 1, concurrency 6, 1,800-second
worker timeout, and three attempts. Both native subagent waves and the
capability-detected experimental CSV engine consume this same ledger.

## Provider surfaces

Claude Code and Codex are equal recommended runtimes over the shared John
state. Their execution adapters remain distinct.

Claude Code:

- slash commands live in `commands/`;
- custom agents are canonical `agents/*.md`;
- stable high-volume work may use Claude dynamic workflows;
- an applied template launches with `claude --plugin-dir <merged-plugin>`.

Codex:

- command equivalents are skills;
- `sync_codex_agents.py --check|--write` deterministically derives shipped and
  development TOMLs from canonical Claude agents, with a small Codex-only
  override map;
- `/john:init` installs missing project `.codex/agents/*.toml` and never
  overwrites a user file, even with force;
- Codex vertical work uses `john_run.py` and native waves by default;
- a template's merged plugin is activated under
  `.john-codex/plugins/<template>/` with a repository marketplace at
  `.agents/plugins/marketplace.json`.

Codex activation prints install/enable/restart instructions and never mutates a
personal marketplace or global enablement. Applied John replaces vanilla John
for that project session.

`hooks/hooks.json` is the sole shipped hook declaration. Claude receives
`updatedToolOutput`; Codex-compatible calls receive `additionalContext`
pointing at the same trace. Skill invocation telemetry is Claude-only and is
reported as unsupported on Codex, not as zero. Hooks execute local code with
the coding session's permissions and must be reviewed before trusting a fork.

## Template format

```text
<template>/
├── template.json                 # exact John pin + providers
├── apply.sh                      # canonical executable regular copy
├── project_addon.md              # optional shared guidance
├── claude_addon.md               # optional Claude appendix
├── agents_addon.md               # optional Codex appendix
├── plan_md_template.md
├── skills/{<new>,_override,_delete}
├── scripts/, commands/, agents/  # additive only
├── codex/agents/*.toml           # additive Codex agents
└── workflows/*.js                # preserved Claude workflow assets
```

Safe template/skill names use lowercase letter/digit segments separated by
single hyphens. `providers` absence means legacy Claude-only. New Hamster
templates declare both providers and exact-pin John until a compatibility
matrix exists.

`apply_template.py` validates names, containment, and symlinks; builds in a
same-parent stage; and atomically publishes. On force it replaces only marked
state and restores prior state on failure. The Claude output and launch flow do
not change for dual-provider templates.

At initialization, `project_addon.md` appends to new CLAUDE.md and AGENTS.md;
the provider appendices affect only their matching file. Legacy templates that
ship only `claude_addon.md` preserve their prior Claude output. Claude workflow
assets install skip-if-exists into `.claude/workflows/`. Codex agents similarly
install skip-if-exists.

## Important deterministic tools

- `init_workspace.py` — transactional `.john/`, PLAN.md, provider guidance,
  workflow, and agent initialization.
- `apply_template.py` / `archive_workspace.py` — transactional template and
  archive publication with containment/symlink checks.
- `emit_event.py` / `reduce_events.py` — append-only emission and typed/audited
  reduction.
- `john_run.py` — create, record, reconcile, retry CSV, status, and cancel.
- `process_scorecard.py` / `emit_manifests.py` — provider-neutral scorecard and
  provenance/self-eval manifests; SELF_EVAL v2 uses argv arrays.
- `app_first_contracts.py` — app contracts and `scan-ui-leaks`, explicitly a
  source heuristic. A real rendered/browser inspection is still required.
- `ppx_parse.py` — loopback-aware PPX client that does not pre-create output
  destinations.
- `activate_codex_template.py` — project-local Codex activation.

## Template authoring rules

- Preserve Claude assets unless fixing an identified shared correctness defect.
- Use John's agent generator; do not maintain a second converter in Hamster.
- New fan-out agents that emit events must call `emit_event.py` and carry stable
  run/item identity required by the ledger.
- Shared produced skills are byte-identical in `.claude/skills/` and
  `.agents/skills/`; reporting compares hashes and accepted events/checkpoints,
  not provider prompts or timing.
- Templates may use PPX/workerLLM URL contracts but never bundle the ignored
  local clients.

## Refreshing this pin

When John moves beyond v0.5.1:

1. Read live `CONTEXT.md`, `README.md`, and
   `plugins/joharnessburg/templates/README.md`.
2. Inspect both plugin manifests, `hooks/hooks.json`, `scripts/`, canonical
   agents, generated Codex agents, and the skill list.
3. Run John's full tests and `sync_codex_agents.py --check`.
4. Update this reference and Hamster's tool inventory together; record the new
   exact pin in examples.
