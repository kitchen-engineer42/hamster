---
name: hamster-drawing-board
description: Use when ingesting raw input materials at the start of a Hamster session, when classifying material as meta vs specific (at the content level, not the input-type level), when using the four-structures framework (format of knowledge / schema / runtime / building pipeline) to read input, when re-entering "back to the drawing board" mid-session because something doesn't fit, or when you're tempted to skip past the drawing board because the input looks obvious. Triggers on phrases like "let me read the inputs", "what kind of template is this", "is this meta or specific", "what's the format/schema/runtime/pipeline here", "back to the drawing board", or any time you're inventorying or classifying input material.
---

# Hamster drawing board

This is where you ingest raw inputs and figure out what kind of template you're building. "Back to the drawing board" — the Grand Tour line — captures the vibe: when something doesn't fit, come back here and re-read with fresh eyes. The drawing board isn't a *phase* you exit, it's a mode you re-enter throughout the session.

## What "drawing board" means

Your inputs are messy: team-meeting transcripts, competitor research, product briefs, sample documents, mock-ups. Maybe some of it is *meta* (ideas about the template itself — "we want apps that do X, generally"); maybe some is *specific* (sample materials of the type the apps will process — "here's a rule doc the apps need to read"). Often both are mixed inside a single source. Your job here is to:

1. Read enough to understand what's there (without burning context — use subagents).
2. Classify each piece of evidence as meta or specific (at the content level).
3. Think in the four structures (format of knowledge / schema of knowledge / runtime structure / building pipeline) to *shape* the template.
4. Take notes as you go. Free-form. You'll re-read them.

You aren't writing the template yet. You're sharpening your understanding of what the template needs to be.

## How to read the inputs

Spawn explore subagents. Don't read every file in the main thread — you'll burn context on raw exploration and lose the synthesis bandwidth you actually need.

A good subagent call looks like:

> Read the files at `<inputs>/<sub-path>/`. Background: the user wants a Hamster template for apps that <one-line brief>. Specifically look for: (a) what format of knowledge appears (rules, facts, glossary, screenplays, ...), (b) what schema shape any structured data has, (c) any hints about how the produced apps should work for end users, (d) any mention of how this kind of app has been built before. Report findings in under 500 words with file paths and exact quotes where it matters. Skip preamble.

The subagent's report comes back as the tool result. You decide what's worth a note. For high-value source material, dispatch a second pass with a sharper focus — a single subagent miss can lose information that won't surface again.

**Two or three subagents in parallel** is the usual move for an unfamiliar input bundle. Each gets a focused area and full context (the user's brief, plus the relevant section of this skill or `references/four_structures.md`).

## Meta vs specific — at the content level

You'll see this distinction in `initial_spec_hamster.md` if you read it: *meta* means "ideas about the template itself" and *specific* means "sample materials for what apps process." The classification matters because:

- **Meta** content gets distilled into the template's design directly. ("We want a glossary-first ontology" → the template fixes glossary as the first knowledge format.)
- **Specific** content gets explored, summarized, distilled, *then* used to shape the template. ("Here's a sample rule doc" → you don't ship that doc in the template, but you might fix the schema shape based on what fields the rules tend to have.)

The trap: classifying inputs by **type** rather than **content**. A team-meeting transcript can contain specific app samples (one teammate read a chunk of a rule doc aloud); a sample doc can contain meta clues (its very form — "every rule cites an article number" — tells you the schema must have a `source_ref` field).

So: classify each piece of evidence, not each input file. A subagent reading a transcript might come back with "section 1 is meta — they're discussing the template's scope; section 2 is specific — Bob's reading a sample rule out loud."

When you're not sure: ask the user. Overkill in discussion is fine.

## The four structures — the read-lens

For each piece of evidence (or each subagent finding), ask: which of the four structures does this hint at?

1. **Format of knowledge** — rules, facts, glossary, skills, stories, wiki, screenplays, ...
2. **Schema of knowledge** — what fields each knowledge entry has, what controlled vocabularies apply.
3. **Runtime structure** — the pipeline of the *produced apps* (parse → chunk → apply → output).
4. **Building pipeline** — the phases John's ralph_loop runs through to build each app, what each phase's subagents do.

`references/four_structures.md` has the full framing — read it once before going deep. The key shift from John's spec §4 is that **you fix the shape, the runtime fills in content**.

Often a single piece of evidence hints at multiple structures. That's the point — they affect each other. The format of knowledge constrains the schema; the schema constrains the runtime; the runtime constrains the building pipeline.

## Notes — free-form, named by you

Take notes in `notes/`. Any filename you like. Some sessions use one big file; some use a file per topic; some use a file per piece of evidence. There's no convention — pick what serves *you*.

Examples of notes that turn out useful later:

- A list of every input file with a one-line summary of what's in it.
- A "questions for the user" file you append to as questions come up.
- Per-structure files: `format_of_knowledge.md`, `schema.md`, `runtime.md`, `building_pipeline.md`.
- A "things that don't fit yet" file for evidence you can't classify.

Don't try to name notes upfront — you'll know what to write *when you have something to write*.

## When to surface decisions to the user

The drawing board surfaces real product decisions, not just modeling questions. When you spot one, surface it. Examples:

- **Scope decisions**: "Should this template support multi-corpus knowledge, or single-corpus only?" The user knows what apps they want to build that you haven't seen yet.
- **Generalization calls**: "I see severity as low/medium/high in the samples — should we fix that, or leave it as a controlled-vocab where each project picks its own levels?"
- **Format / schema gaps**: "The inputs hint at both rules and a glossary, but never together — are these meant to be the same template, or two?"

Use AskUserQuestion or just prose. Don't sit on a decision waiting for it to clarify itself.

## Re-entering the drawing board

You'll come back here mid-workshop. Examples:

- While modifying a skill in the fork, you realize the schema should have an extra field. Come back, re-read the inputs to confirm.
- After running `package_template.py --smoke-test`, you notice the four structures don't quite fit the input you were targeting. Come back, classify again, adjust the fork.
- The user provides a new input mid-session. Come back, re-classify, see if the template's shape needs to change.

"Back to the drawing board" isn't failure — it's the natural rhythm of working in something this open-ended. Plan mode is the natural seam: pause the workshop, re-enter plan mode, re-read inputs, propose changes, exit plan mode, resume workshop.

## When the drawing board has done enough for now

You'll feel it when:

- You can articulate the four structures for the template in 1-2 sentences each.
- You have a list of 2-5 specific modifications to John you want to make (overrides, additions, deletes).
- You have a clear sense of the runtime apps' user experience.
- The user has signed off on the proposed template shape (via plan mode).

That's when `hamster-workshop` is the natural next trigger. But "done for now" is the right framing — you'll be back.
