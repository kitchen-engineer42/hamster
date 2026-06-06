# The app-type definition — template-level framing

This is Hamster's adaptation of John's **app-type definition** (formerly "the four structures"; see John's repo-root `CONTEXT.md` for the canonical glossary). John uses the four decisions to describe a *project* (one app being built). Hamster uses them to describe a *template* (a family of apps that share enough shape to share a harness).

## The four decisions

Two pairs — the knowledge pair describes the material, the app pair describes the machine. In both pairs, *format = what it is / how it works; schema = what it has / how it is built*:

- **Knowledge format**: what kinds of knowledge the corpus holds — facts/relations/rules/skills/stories/wiki/screenplays, etc. The knowledge format not only decides the knowledge schema, but also constrains the app mechanism. In KC (a sibling verification harness), the knowledge format is rules, then skills, finally workflows — and accordingly the verification apps' mechanisms are an agent runtime for skills and a python sandbox for workflows.
- **Knowledge schema**: what one entry contains — the structured-knowledge-unit shape. In KC, a rule entry carries its source in laws/regulations, trigger condition, judgement logic, a decision tree with outputs, and relevant glossary refs.
- **App mechanism**: the "main line" in every app — how it works for its users, the steps from input to output. In KC, a doc-verification app's mechanism is: user uploads a batch of docs → docs uniformly parsed and chunked → all rules applied to all corresponding chapters → all violations surfaced to the user.
- **Build pipeline**: how an app of this kind is built — the software-engineering side. In KC's case, roughly: analyze the rule doc, observe sample docs, translate business rules into code/prompts, test and modify (its 7 phases).

These four decisions affect each other, and together they define how to build a certain type of app. Once all four are settled, an app type — and hence a template — is *defined*.

## The shift — from app-thinking to template-thinking

When John builds one app, the four decisions are concrete: this rule format, this rule schema, this verification flow, these specific phases. When Hamster builds a template, they are **shapes** — categories filled in by the runtime when an app is actually being built.

Concretely: a doc-verification template fixes the knowledge format (rules), the schema shape (source / trigger / judgement / output / glossary — but field names and required-ness can vary per project), the app mechanism (parse → chunk → apply-rules → surface-violations), and the build pipeline (the phases of ralph_loop, the role of each subagent). The *content* of any specific rule, the *exact* schema field set, the *specific* glossary terms — those land at app-build time, by layer-3 Claude in a John runtime session.

So your job in Hamster is to **fix the shape, not the content**.

| Decision | Template fixes (you, layer-2) | App fills in (layer-3, future John runtime) |
|---|---|---|
| Knowledge format | The category: rules, facts, glossary, screenplays, ... | The specific entries |
| Knowledge schema | Required fields, type families, the controlled vocabularies | Field values for each entry |
| App mechanism | The pipeline of the produced app: parse → ... → output | Wiring + UI for the specific domain |
| Build pipeline | The phases ralph_loop runs through, subagent roles per phase | Per-corpus reduction, per-project notes |

## Working with the app-type definition during drawing-board

Use the four decisions as **lenses on the input**. Not as a checklist to fill out — as a way to read.

For each piece of evidence (a paragraph in a transcript, a section of a sample doc, a comment in a product brief), ask:

1. **Does this hint at a knowledge format?** ("These docs need rule extraction" → rules format. "We want a quiz at the end" → quiz/Q&A format. "Glossary first, then everything depends on it" → glossary + dependent rules.)
2. **Does this hint at the schema shape?** ("Every rule cites a regulation article" → schema requires source-ref. "Severity must be high/medium/low" → schema requires controlled-vocab severity.)
3. **Does this hint at the produced app's mechanism?** ("User uploads a batch" → batch input UI. "Real-time interaction" → chat-style UI. "Results need to be downloadable" → export step.)
4. **Does this hint at the build pipeline?** ("Each project has its own rule doc to read" → first phase reads + chunks the rule doc. "Glossary depends on context across docs" → cross-doc phase before extraction.)

A single piece of evidence often hints at multiple decisions. That's the point — they affect each other.

## Don't overfit any single decision to a sample app

You'll see specific apps in your inputs (a sample slide deck, a sample doc-verification output, a sample portfolio). Those tell you *one* way the produced apps might look. The template should produce apps that **look like the samples but also handle the variations you haven't seen yet**.

Tactically: when an input shows a specific schema field, generalize the *category* before fixing the *field*. ("`severity: low/medium/high`" — is severity always 3 levels, or does this domain sometimes have 5? Ask the user, or leave it flexible.) When an input shows a specific runtime step, generalize the *step's role* before fixing the *implementation*. ("Upload step accepts PDF" — is PDF always the format, or do future apps need DOCX too? Probably leave parser pluggable per `hamster-workshop`'s tool inventory.)

This is the "trading some generalization for domain expertise, but not tipping too far" instinct from `CLAUDE.md`. The app-type definition is how you reason about where on that spectrum each call lands.

## When to ask the user

The four decisions often surface real product decisions during drawing-board, not just modeling questions. When you spot one — "should this template support multi-corpus knowledge, or single-corpus only?" — surface it to the user before fixing it in the template. They know what apps they want to build that you haven't seen yet.
