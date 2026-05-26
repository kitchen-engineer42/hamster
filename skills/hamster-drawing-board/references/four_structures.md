# The four structures — template-level framing

This is Hamster's adaptation of John's spec §4 ("the four structures we have in each project of John"). John's spec uses the four structures to describe a *project* (one app being built). Hamster uses them to describe a *template* (a family of apps that share enough shape to share a harness).

## The four structures (verbatim from John spec §4)

> the format of knowledge, the schema of knowledge, the function structure of app, the building pipeline of app.
>
> - **The format of knowledge**: What forms of knowledge in this project, facts/relations/rules/skills/stories/wiki/screenplays, etc. The format of knowledge not only decides the schema of knowledge, but also the function structure of the app. In KC_CLI, the format of knowledge is rules, then skills, and finally workflows. Accordingly, the function structures of the verification apps are agent runtime for skills, and python sandbox for workflows.
>
> - **The schema of knowledge**: The specific data schemas for the SKUs (standardized/structured knowledge unit), what an entry of knowledge should contain. In KC_CLI, the schema of an entry of knowledge in the format of rules includes source in laws/regulations, trigger condition, judgement logic, decision tree with different output, relevant glossaries.
>
> - **The function structure of app**: That 'main line' in every app, basically how the app works for its users, what are the steps of processing from input to output. In KC_CLI, the function structure of a doc verification app is user upload a batch of certain type of docs, docs uniformly parsed and chunked, all rules applied to all corresponding chapters, finding all violations, showing the result to user.
>
> - **The building pipeline of app**: How an app of this kind is usually built, the software development part. In KC_CLI case, this is basically how kc works in the 7 phases. Generally speaking, we can still summarize the procedure of KC building a verification app as analyzing rule doc, observing sample docs, translate business rules into code/prompt, test and modify.
>
> These four aspects affects each other, and together they define how to build a certain type of app that can do certain things in certain order.

That's John's spec for one project. Now: how do you read these four structures when you're building a *template* — a thing that produces many apps?

## The shift — from app-thinking to template-thinking

When John builds one app, the four structures are concrete: this rule format, this rule schema, this verification flow, these specific phases. When Hamster builds a template, the four structures are **shapes** — categories filled in by the runtime when an app is actually being built.

Concretely: a doc-verification template fixes the format of knowledge (rules), the schema shape (source / trigger / judgement / output / glossary — but field names and required-ness can vary per project), the function structure (parse → chunk → apply-rules → surface-violations), and the building pipeline (the phases of ralph_loop, the role of each subagent). The *content* of any specific rule, the *exact* schema field set, the *specific* glossary terms — those land at app-build time, by layer-3 Claude in a John runtime session.

So your job in Hamster is to **fix the shape, not the content**.

| Structure | Template fixes (you, layer-2) | App fills in (layer-3, future John runtime) |
|---|---|---|
| Format of knowledge | The category: rules, facts, glossary, screenplays, ... | The specific entries |
| Schema of knowledge | Required fields, type families, the controlled vocabularies | Field values for each entry |
| Runtime structure | The pipeline of the produced app: parse → ... → output | Wiring + UI for the specific domain |
| Building pipeline | The phases ralph_loop runs through, subagent roles per phase | Per-corpus reduction, per-project notes |

## Working with the four structures during drawing-board

Use the four structures as **lenses on the input**. Not as a checklist to fill out — as a way to read.

For each piece of evidence (a paragraph in a transcript, a section of a sample doc, a comment in a product brief), ask:

1. **Does this hint at a format of knowledge?** ("These docs need rule extraction" → rules format. "We want a quiz at the end" → quiz/Q&A format. "Glossary first, then everything depends on it" → glossary + dependent rules.)
2. **Does this hint at the schema shape?** ("Every rule cites a regulation article" → schema requires source-ref. "Severity must be high/medium/low" → schema requires controlled-vocab severity.)
3. **Does this hint at the function structure of the produced app?** ("User uploads a batch" → batch input UI. "Real-time interaction" → chat-style UI. "Results need to be downloadable" → export step.)
4. **Does this hint at the building pipeline?** ("Each project has its own rule doc to read" → first phase reads + chunks the rule doc. "Glossary depends on context across docs" → cross-doc phase before extraction.)

A single piece of evidence often hints at multiple structures. That's the point — they affect each other.

## Don't overfit any single structure to a sample app

You'll see specific apps in your inputs (a sample slide deck, a sample doc-verification output, a sample portfolio). Those tell you *one* way the produced apps might look. The template should produce apps that **look like the samples but also handle the variations you haven't seen yet**.

Tactically: when an input shows a specific schema field, generalize the *category* before fixing the *field*. ("`severity: low/medium/high`" — is severity always 3 levels, or does this domain sometimes have 5? Ask the user, or leave it flexible.) When an input shows a specific runtime step, generalize the *step's role* before fixing the *implementation*. ("Upload step accepts PDF" — is PDF always the format, or do future apps need DOCX too? Probably leave parser pluggable per `hamster-workshop`'s tool inventory.)

This is the "trading some generalization for domain expertise, but not tipping too far" instinct from `CLAUDE.md`. The four structures are how you reason about where on that spectrum each call lands.

## When to ask the user

The four structures often surface real product decisions during drawing-board, not just modeling questions. When you spot one — "should this template support multi-corpus knowledge, or single-corpus only?" — surface it to the user before fixing it in the template. They know what apps they want to build that you haven't seen yet.
