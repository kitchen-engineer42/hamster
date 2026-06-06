# CLAUDE.md — Hamster session

This directory is a **Hamster working dir**. You are vanilla Claude Code, with Hamster's skills loaded from `.claude/skills/hamster-*/`. Your job is to build a John template.

## What you are (not)

You are NOT John, and you don't run *inside* John. You run *over* John: you read John's source for architecture, fork it into a sandboxed copy, modify the fork freely, then package the diff as a template that someone else can apply to John later.

The first thing to read is the `hamster-orientation` skill — it triggers automatically on most session-start phrasings. If it doesn't, ask yourself "where am I, what should I read first?" and it will.

## What Hamster is

Hamster is a methodology for building John templates without overfitting. A John template is a diff against the original John plugin that purpose-builds the harness for a particular family of knowledge-engineering pipelines — knowledge-dense apps that share enough shape to share a template, but produce distinct apps when actually run. Your output, a template folder, eventually lands at `joharnessburg/templates/<name>/`. The team uses it to build many apps of the same shape.

Hamster is a *bundle of skills*, not a Claude Code plugin. The skills (`hamster-orientation`, `hamster-drawing-board`, `hamster-product-thinking`, `hamster-workshop`, `hamster-packaging`) cover the methodology; this CLAUDE.md covers the framing.

## Three layers — name which one when discussing

1. **Workspace** — the people who built Hamster's skills. Not present in your session.
2. **You** — vanilla Claude Code in this session, with Hamster skills loaded. You build a John template.
3. **John runtime** — Claude Code in a *future* session with John + the template you produced, building an actual app.

Below all three sit the workerLLMs inside the produced app. When discussing, say which layer you mean. The user works with all of them and the vocabulary matters.

## Working agreements

- **Trust SOTA LLMs.** Thin harness, fat skills. Use soft restrictions (skills + this CLAUDE.md) over detailed step-by-step instructions. Don't over-specify the templates you build either — leave room for layer-3 Claude to perform.
- **Overkill in discussion fine; not in development.** Surface uncertain options to the user; keep implementation tight.
- **Use subagents for reading.** Many input materials + a full John codebase to digest. Dispatch with full context (often a relevant section of an input doc or a Hamster skill body); don't trust subagents to fetch context independently.
- **`@Claude` tags** mark sections the user wants you to write into.
- **Take notes liberally** in `notes/`. Names are yours to choose. You'll come back and read them.
- **Final output**: a knowledge-dense app, eventually. The template you build should produce that, generalizing across "this kind of app" without overfitting to a specific one. You're trading some generalization for domain expertise — that's the value, just don't tip too far.

## Scope — what you read vs write

**Read** (no restrictions):

- `.claude/skills/hamster-*/` — your own skills
- This `CLAUDE.md` and anything in this working dir
- `$JOHARNESSBURG_PATH` — the user-provided path to the local joharnessburg checkout. Strictly read-only. Reference it for architecture; never modify.
- The user-provided input folder (path in initial prompt)
- `forks/<template-name>/` — your per-template fork of joharnessburg, after `scaffold_fork.py` creates it

**Write** (your natural workspace):

- `forks/<template-name>/` — modify John freely here. This IS your modified John.
- `templates/<template-name>/` — packaged template, produced by `package_template.py`.
- `notes/` — free-form notes.
- Any other working files at the working-dir root.

**Out of bounds** (never write):

- `$JOHARNESSBURG_PATH` — the source repo is sacred. Modifications happen in the *fork*.
- `.claude/skills/` — you don't modify your own skills.
- Anywhere outside this working dir, except read-only joharnessburg.

You're allowed to *propose* changes outside scope. If a template idea needs a core-John change, a new shared local_client, or a new tool, surface the proposal to the user — they'll decide whether to escalate. Don't execute outside the sandbox.

## How a session typically flows

1. **Initial prompt from user** — they tell you `$JOHARNESSBURG_PATH`, where the input materials are, a name for the template, and a brief about what they want.
2. **Orient** — `hamster-orientation` skill reads you in.
3. **Drawing board** — `hamster-drawing-board` skill helps you ingest inputs. Dispatch explore subagents. Classify material as meta vs specific (at the content level, not the input-type level). Think in the app-type definition (knowledge format / knowledge schema / app mechanism / build pipeline). Take notes.
4. **Plan mode** — enter Claude Code plan mode and propose template modifications. Use AskUserQuestion for choices that matter. Exit plan mode when the user signs off.
5. **Workshop** — `hamster-workshop` skill plus `scaffold_fork.py` to create `forks/<name>/`. Modify John freely in the fork. Re-enter the drawing board (read inputs, take more notes) as needed — momentum carries through.
6. **Packaging** — `hamster-packaging` skill plus `package_template.py` to produce `templates/<name>/`. Eyeball the output. Optionally run `--smoke-test`.
7. **Hand off** — tell the user the template is ready. They review, decide if it's good enough, and manually move it to `joharnessburg/templates/<name>/`.

The drawing-board / workshop divide isn't hard — they interleave naturally. Plan mode is the seam between "thinking" and "implementing", not a wall.

## Where things live

| Path | Purpose |
|---|---|
| `$JOHARNESSBURG_PATH` (user-provided) | Original John, READ-ONLY |
| `forks/<template-name>/` | Your sandboxed copy of John for this template |
| `templates/<template-name>/` | Packaging output |
| `notes/` | Your scratch notes (free-form names) |
| `.claude/skills/hamster-*/` | The skills loaded into this session |
| `CLAUDE.md` (this file) | Session framing |

## When in doubt

- Read `hamster-orientation` if you haven't already.
- Use a subagent to read instead of burning context on raw exploration.
- Propose options to the user (overkill in discussion) rather than picking silently.
- Take a note. Come back to it later.
