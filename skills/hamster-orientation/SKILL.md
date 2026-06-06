---
name: hamster-orientation
description: Read this at the start of every Hamster session. Use this skill when you're opening a new session (user has just provided a joharnessburg path + an input folder + a template name + a brief), when you need to recall the three Hamster layers (Workspace, You, John runtime) or the read/write scope boundaries, when you're deciding what move to make next, or when you want to avoid common session-start mistakes (modifying joharnessburg directly, reading all 26 John skills upfront, writing the template diff by hand, identifying as John instead of as a Hamster user).
---

# Hamster orientation

You're vanilla Claude Code in a Hamster session. Hamster's job: build a John template — a diff against the original John plugin that purpose-builds the harness for a family of knowledge-engineering apps. This skill is the first thing to read when a session opens.

`CLAUDE.md` at the working-dir root has the framing (three layers, scope, working agreements). Read it once, then come back here for the operational specifics — how to *start* a session well.

## Three layers (vocabulary — this matters)

1. **Workspace** — the people who built Hamster's skills. Not in your session.
2. **You** — vanilla Claude Code, Hamster skills loaded, building a John template.
3. **John runtime** — Claude Code + joharnessburg + your template applied, in a future session, building an actual app.

When you discuss with the user (or write code), name the layer. The user works with all three; sloppy references here cause real confusion downstream.

## The session-start moves

When the user gives you the initial prompt (joharnessburg path + inputs path + template name + intent), do this — roughly in order, but with momentum:

1. **Read this skill + `CLAUDE.md`** if you haven't fully. They take a few minutes and prevent hours of misalignment.
2. **Inventory the inputs** — `ls -la` the input folder. Note file types, sizes, names. Write your first note in `notes/` (any filename). Don't read the inputs deeply yet — dispatch subagents for that.
3. **Skim joharnessburg's top-level structure** — but don't go deep. Confirm `$JOHARNESSBURG_PATH` exists and has `skills/`, `scripts/`, `templates/`, `.claude-plugin/`. Don't start reading 26 skill bodies one-by-one — that's later, under `hamster-workshop`.
4. **Trigger `hamster-drawing-board`** by topic, not by command. Once you start classifying inputs as meta-vs-specific, the drawing-board skill should kick in. If it doesn't, read it manually.
5. **Take notes liberally** as you go. Names are yours to choose. You'll come back.

This is not a rigid checklist — momentum and curiosity carry through. The point is *don't skip orientation just because the input looks obvious*.

## Where things live (operational reminder)

| Path | Role | You write here? |
|---|---|---|
| `$JOHARNESSBURG_PATH` (user-provided) | Original John | No. Strictly read-only. |
| `<inputs>/` (user-provided) | Raw material from the user | No, just read. |
| `forks/<template-name>/` | Your sandboxed John clone | **Yes, freely.** Created later by `scaffold_fork.py`. |
| `templates/<template-name>/` | Packaged template diff | Yes, but produced by `package_template.py`, not by hand. |
| `notes/` | Your scratch | **Yes, freely.** Free-form names. |
| `.claude/skills/hamster-*/` | Hamster skills loaded into your session | No. Your own skills are sacred at runtime. |

The fork is your modified John. The template is the diff packaged for someone else to apply. You don't write the diff directly — you modify a clone, and the packager computes the diff.

## The five Hamster skills — when each wants to run

- **`hamster-orientation`** (this one) — session start, "where am I" moments, "what can you do" queries from the user.
- **`hamster-drawing-board`** — when ingesting raw inputs, classifying material as meta-vs-specific, thinking in the app-type definition (knowledge format / knowledge schema / app mechanism / build pipeline).
- **`hamster-product-thinking`** — when reasoning about the apps the template will produce: who's the user, what's the experience, is the template generalizing without overfitting.
- **`hamster-workshop`** — when modifying John in the fork: what can a template override vs add vs delete, when to embed `ppx`/`llm_client`, when to flag a tool gap to the user.
- **`hamster-packaging`** — when scaffolding the fork (`scaffold_fork.py`) or producing the template (`package_template.py`), or when reviewing the package summary.

These aren't strict phases. The drawing-board / workshop divide isn't a wall — momentum carries through. You'll re-enter the drawing board after starting the workshop. That's fine. Use Claude Code's **plan mode** as the natural seam between "thinking" and "implementing", not as a phase boundary.

## Common session-start mistakes — avoid these

- **Don't modify `$JOHARNESSBURG_PATH`.** Modifications go in the *fork*, which doesn't exist yet at session start. If you find yourself about to Edit a file under `$JOHARNESSBURG_PATH`, stop and run `scaffold_fork.py` first (per `hamster-packaging`).
- **Don't read all 26 John skills at session start.** You don't need them yet. Use the architecture summary in `hamster-workshop/references/john_architecture.md` when workshop triggers; spawn subagents for deep-dives on specific skills only when the template needs to override them.
- **Don't identify as John.** You're using Hamster, building *for* John. The framing matters — Hamster's skills speak to *you*, not to layer-3 Claude running inside John. If your reasoning starts to sound like "John would do X here", check whether you've confused layer 2 with layer 3.
- **Don't skip the drawing board because the input "looks obvious".** What looks like a specific app sample often hides meta clues about the template's shape (rule docs ↔ doc-verification template; sample slides ↔ slide-rendering template). Classification is content-level, not input-type-level.
- **Don't write the template diff by hand.** You modify the fork; `package_template.py` produces the diff. Writing `templates/<name>/skills/_override/...` directly skips the verification path and breaks the audit trail.

## When to ask the user

The user is available. Use AskUserQuestion (or just prose) when:

- A classification call is genuinely ambiguous (meta vs specific, in vs out of template scope).
- You're about to propose a risky change outside the template scope (e.g., a new shared local_client, a core-John change). Surface it; let them decide.
- You hit a translatable-but-undesirable change in the fork that `package_template.py` would warn on. Ask "do you want me to revert this, or escalate it as a core-John proposal?"

Overkill in discussion is fine. Surface uncertain options; they'll choose.

## When you're ready

Once oriented, the natural next move is to dispatch one or two subagents to inventory the inputs (with full context — the user's brief, where to find things, what to report back). While they read, you skim joharnessburg's top-level structure. When the subagents come back, the drawing-board skill should be the natural trigger.

From there: drawing board → plan mode → workshop → packaging → hand off. With re-entries to the drawing board whenever a new question surfaces. Don't force a linear path.
