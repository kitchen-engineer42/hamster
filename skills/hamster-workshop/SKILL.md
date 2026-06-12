---
name: hamster-workshop
description: Use when modifying John in your fork — overriding existing skills, adding new ones, deleting core skills, integrating platform tools (ppx, llm_client), or deciding which mechanism fits a desired change. Use when you hit an unsupported change in the fork (modifications outside `skills/`) and need to decide whether to revert, surface as a core-John proposal, or find an in-scope alternative. Use when you spot a platform-level improvement worth proposing to the user. Triggers on phrases like "time to modify John", "what can I override in the template", "what about ppx / llm_client", "is this risky change worth proposing", "how do I delete a skill", "this file isn't in skills/", or any workshop-mode work on the fork.
---

# Hamster workshop

This is where you actually modify John. The name comes from Richard Hammond's workshop on the Grand Tour — the smallest cog, but where the real building happens. You operate on a *fork* of joharnessburg (not the original), make changes freely, and let `hamster-packaging` later translate those changes into the canonical template diff format.

If you haven't read `references/john_architecture.md` yet, do that first. It's a version-pinned summary of joharnessburg layout, the 27 skills, hooks contract, templates mechanics — tighter than reading the live repo cold.

## What you operate on

You operate on a **fork** of joharnessburg, not the original. The fork is created by `scaffold_fork.py` (under `hamster-packaging`) and lives at `forks/<template-name>/`. From there you have full read-write to a complete clone of joharnessburg.

You do NOT operate directly on `templates/<name>/` — that's the output, not the workspace. The packager produces the template folder from your fork diff after you're done modifying.

Why this design: it lets you think in terms of "modify John" (which is intuitive — edit the skill file, add a script, change a phase) instead of "write a diff" (which is awkward, especially for new skills with multiple files). The packager handles the translation.

## How to read joharnessburg

Three access patterns, used together:

1. **The bundled architecture summary** (`references/john_architecture.md`) — your always-have-in-mind baseline. Read it whenever you need to recall the layout, the 21 core skills, the hooks contract, the templates diff format. Pinned to John v0.3.2. If your template adds fan-out agents, conform to the **agent event contract** section there — copy the event shapes from John core's `agents/knowledge-extractor.md` rather than inventing your own.

2. **Reference example templates** at `<hamster-checkout>/examples/{slides-from-textbook,doc-verification}/` (in your loaded Hamster repo, typically at `~/hamster-cli/examples/` or wherever the user installed Hamster). Each example is a complete template directory with `template.json`, `apply.sh`, `claude_addon.md`, `plan_md_template.md`, and `skills/_override/` + additive skill subdirs — i.e., exactly the shape your `package_template.py` output should have. Use them to ground your sense of the diff format before authoring. **Don't copy them wholesale** — they're functional demonstrators, not production-ready, and your template should be informed by your inputs, not by mimicking the example.

3. **Live reads of `$JOHARNESSBURG_PATH`** — for skill bodies, script implementations, current hook behavior. Spawn subagents for deep reads. Don't load whole skill files into your main context unless you're about to override them.

A good "read for deeper context" subagent call:

> Read `$JOHARNESSBURG_PATH/skills/knowledge-extraction/SKILL.md` and any references it lists. Background: I'm designing a Hamster template for <X>. I need to know whether to override this skill or extend it. Report: (a) what the skill currently teaches, (b) any specific decisions baked in that might not fit my template's <X> use case, (c) the file size + reference list. Skip preamble; quote where useful.

Two or three subagents in parallel for the relevant skills, then synthesize.

## The override / additive / delete checklist

When deciding how to make a change, ask:

| You want to ... | Mechanism in the fork | Becomes in template |
|---|---|---|
| Replace a core skill's content entirely | Edit `<fork>/skills/<name>/SKILL.md` (and any of its `references/`, `scripts/`) | `skills/_override/<name>/` (full replacement) |
| Add a brand-new skill | Create `<fork>/skills/<new-name>/SKILL.md` | `skills/<new-name>/` (additive) |
| Add a script, command, or subagent | Create at `<fork>/scripts/<file>.py` (or `commands/<file>.md`, `agents/<file>.md`) | Same path in template (additive) |
| Remove a core skill | Delete `<fork>/skills/<name>/` directory | `<name>` line appended to `skills/_delete` |
| Ship a starter PLAN.md skeleton | Create `<fork>/plan_md_template.md` at fork root | `plan_md_template.md` at template root |
| Ship CLAUDE.md guidance for the produced project | Create `<fork>/claude_addon.md` at fork root | `claude_addon.md` at template root |

What the platform *doesn't* support — these will produce a `package_template.py` warning + skip:

| Change in the fork | Why the packager warns |
|---|---|
| Modified script (e.g., edits to `<fork>/scripts/init_workspace.py`) | Templates can only ADD scripts, not override (additive-only collision policy) |
| Modified `hooks/hooks.json` | Hooks are platform infrastructure |
| Modified `.claude-plugin/plugin.json` | The plugin manifest belongs to the platform |
| New or modified files in `local_clients/` | Local clients live OUTSIDE the plugin |
| Modified core README, LICENSE, top-level docs | Platform-owned |

When the packager warns about a change, you have three options:

1. **Revert the change in the fork** — `git checkout -- <path>` or undo the edit.
2. **Surface to the user as a core-John proposal** — "this change would benefit all templates; should we propose it as a joharnessburg PR?"
3. **Find an in-scope alternative** — usually possible. A script change can often be achieved by adding a new script and having a skill route to it; a hook change can often be achieved by encoding the equivalent behavior into a skill that triggers on the right phrasing.

## Deletion in the fork — a gentle heads-up

Deleting a core skill is fully supported (the packager translates it to a `_delete` line). Two specific cases to be aware of:

- **You want to replace a meta skill with a more domain-specific skill** — e.g., delete `chunking` and add `slide-chunking`. Functionally similar to override-with-rename. **This is fine**, but worth a heads-up to yourself (and the user) that:
  - It looks like a deletion in git, but you're really replacing.
  - Layer-3 Claude won't find `chunking` anymore — anywhere it's referenced (other skills, `claude_addon.md`, `plan_md_template.md`) needs to point at the new name instead.
  - You're more committed than with an override — you can't easily undo by removing the new skill alone; the original is gone.

- **You want a skill gone with no replacement** — e.g., delete `platform-credits` because this template's produced apps don't have priced operations. This is the safer kind of deletion; minimal blast radius.

Every operation in the fork is git-tracked, so you can always reconstruct what you did. Just be aware that delete-plus-rename looks more dramatic in the diff than an override.

## Tool integration — when to embed ppx, llm_client, or surface a gap

See `references/tool_inventory.md` for the full inventory + when-to-use guidance. Short version:

- **Don't decide alone** — surface the tool question to the user. They know whether the produced apps will need ppx at runtime, whether workerLLM calls happen at build-time only or also at runtime, whether the input formats include PDFs the parser handles well.
- **Tools belong to the platform** — templates don't bundle tools. If the platform doesn't have what your template needs, surface the gap; the user decides whether to add a tool (via `local-clients-builder` methodology, workspace-level) or to generalize the template's input contract.
- **Embed via the appropriate skill** — `parsing` for ppx-via-skill use, `workerllm-runtime` for workerLLM-via-skill use, or override those skills with template-specific guidance if needed.

## The risky-change-proposal stance

Hamster gives you a checklist of what templates can and can't do. But you're the same SOTA model that built John. You may see a smart change outside the template scope — a new local_client, a core-John improvement, a hook contract upgrade. **Propose it.**

The user explicitly said: Hamster can propose risky-but-potentially-great changes outside scope; the user decides whether to escalate. The expected upside is rare but real — occasionally a Hamster session surfaces a platform-level idea that would have taken John itself months to land otherwise.

How to surface:

> I'd like to propose a change that's outside template scope. <One-paragraph what + why>. The blast radius: affects all templates and any in-progress John sessions until rolled out. Alternatives within template scope: <list 1-2>. Should I (a) implement within template scope using the alternatives, (b) prepare a core-John PR proposal alongside this template work, or (c) skip the platform-level change entirely?

Don't sit on the proposal silently; don't unilaterally edit `$JOHARNESSBURG_PATH`. Surface and let the user choose.

## When you genuinely have to break the rules

If a template fundamentally cannot be built without a platform-level change (e.g., it requires a new tool, or a new hook), the right path:

1. Lock the template's design with placeholders for the missing platform pieces.
2. Surface the platform-level need to the user as a separate proposal.
3. Resume template work after platform-side changes land (which is outside your scope to make).

Don't fake it by stuffing platform logic into a template skill — that's the brittleness path. Templates that depend on out-of-scope platform changes should *say so* (in `template.json` description, in `claude_addon.md`) rather than hiding the dependency.

## When this skill triggers

- You're about to make a concrete change to John (override a skill, add a new one, delete one).
- You're deciding which mechanism (override vs additive vs delete) fits a desired change.
- You hit an unsupported change (file outside `skills/`) and need to decide what to do.
- You're integrating a platform tool (ppx, llm_client) into the template.
- You spot a platform-level improvement worth proposing.

If you're still figuring out *what* the template should do (which skills, schema, phases), the trigger is `hamster-drawing-board`. If you're done modifying and ready to produce the template diff, the trigger is `hamster-packaging`.

## When you're done in the workshop

You're done with workshop-mode when:

- Every modification in your fork is one of the supported kinds (override / additive / delete / template root files). Run `git status` in the fork to check.
- For every unsupported modification, you've either reverted it or surfaced a proposal to the user.
- The skills in the fork form a coherent set (no skill references something that was deleted).
- Layer-3 Claude could read the template-applied-John, run ralph_loop, and produce an app that matches your design intent.

Then `hamster-packaging` is the natural next trigger.
