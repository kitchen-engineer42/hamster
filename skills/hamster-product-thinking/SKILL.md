---
name: hamster-product-thinking
description: Use when reasoning about the produced apps — who uses them, what makes them good, where the template fits between vanilla-John and overfit-to-one-app. Triggers on questions like "is this template generalizing right", "what's the user story for an app this template produces", "are we trading too far on the generalization vs domain-expertise scale", "should we lock this schema field or leave it flexible", "is this a toC or toB call", or any time you're deciding the *purpose* of a template modification rather than its content (drawing-board) or implementation (workshop).
---

# Hamster product thinking

This is the lens for reasoning about the *apps* your template will produce — who uses them, what makes them good, where the template fits between generic vanilla-John and overfit-to-one-app.

The framing: **templates + John is an AI platform that builds apps like good toC internet products**. Both halves matter and they aren't separable.

- The **toC half** — the produced apps face users. They need to be useful, fast, legible, satisfying to use. Even when the user is internal (a teammate using a doc-verification app, a student using a slide-deck), the toC lens applies — the *experience* is what the template's value compounds on.
- The **toB AI platform half** — Hamster, John, and the templates together are infrastructure for app-building. They need to be operable, repeatable, debuggable, governable. The platform's value is the *throughput* of decent apps it can produce per unit of effort.

The combined product is a toB platform optimized for shipping toC-quality apps at scale. Hold both lenses simultaneously when designing.

## The trade-off — generalization vs domain expertise

Vanilla Claude Code is fully general. John (the harness) trades some generalization for better knowledge-engineering throughput. A John template trades further generalization for *more* domain expertise — better accuracy and ergonomics inside its app-family, less ability to handle outliers.

You're one notch further on this scale than John. The danger isn't going too general (then why build a template?) — it's tipping too far toward overfit. Signs you've tipped:

- The template only produces apps that look like one specific sample input.
- A second project from the same app-family wouldn't fit the template without skill rewrites.
- Layer-3 Claude has so much pre-baked structure it can't adapt to corpus quirks.

When you spot a tipping point, surface it to the user before locking. "I'm about to fix severity to high/medium/low — but if next month's corpus has 5 severity levels, this breaks. Lock it, or keep it open?"

## The "good toC product" instincts to keep in mind

These produce a *useful* app, not just a *correct* one. They land in the template's runtime structure (the third of the four structures) and in the building pipeline (how layer-3 Claude reasons during the build).

- **First minute matters.** A user lands on a produced app — what do they see? Can they get a result in their first interaction? Templates should encourage produced apps to have a working golden path before any polish.
- **Reversibility is comfort.** Produced apps should let users undo, re-try, change their mind without losing context. When the runtime structure includes a "results page", it should include "back to inputs" — not a dead end.
- **Legibility over cleverness.** A user understanding *why* the app made a decision matters more than the decision being technically optimal. Templates whose apps surface chain-of-reasoning to the end user usually beat templates whose apps only surface verdicts.
- **Speed is a feature.** A produced app that runs in 10 seconds beats a produced app that runs in 90 seconds at slightly lower quality, for most use cases. Bias templates toward faster-cheaper workerLLMs first, escalation second.

These don't need to live as separate skills inside the template — they're decisions you make while designing the template's runtime structure. But naming them helps you check your own work.

## The toB platform instincts

These produce a *durable* template — one that doesn't rot, one that other team members can pick up, one that handles edge cases without re-authoring.

- **Operability over elegance.** A template whose `claude_addon.md` explains the failure modes is more valuable than a template with beautiful but undocumented skills.
- **Templates are contracts, not just scaffolding.** When a template fixes the schema (e.g., "every rule has source_ref"), it's promising that all downstream apps will have that field. Layer-3 Claude relies on the contract. Don't promise what you can't enforce; if a schema field can vary per project, leave it as a controlled-vocab in the template and let layer-3 Claude choose.
- **Tools belong to the platform, not the template.** ppx and llm_client come from the platform (joharnessburg + local_clients). Templates *use* them. If a template needs a tool the platform doesn't have, the template doesn't ship the tool — Hamster surfaces the gap to the user, who decides whether to add it to the platform.
- **Failure should be loud, attributable, and locally-fixable.** If a produced app fails, the failure should point at a specific skill or phase, not at "John". The template's `code-quality-guardrails` skill (per John's own scaffolding) should be tuned per template to surface this.

## Operational tactics — distilled from external PM wisdom

`references/lenny_distillation.md` collects ~11 tactical moves from Lenny's Substack canon that survived a "previously-unknown to SOTA Claude" bar. Skim it before any template design that involves user-facing apps — a few of these map directly to template decisions you'll make:

- **Collison Install** → don't ship a template by publishing it; ship by sitting with the first internal app team through their first build.
- **Eval the eval** → every template's eval rig must include a small human-labeled gold set; LLM-judge agreement is tracked, not assumed.
- **Binary not Likert** → template quality gates use pass/fail, not 1-5 scores.
- **Decision tenets reasonably-arguable opposite** → when the team writes down template-authoring tenets, each one should be a real choice, not a platitude.

Most standard PM frameworks (JTBD, ICE, North Star, etc.) are *not* in that reference — they're well-known to SOTA Claude and don't need restating. Reach for them naturally if they fit.

## Surfacing trade-offs to the user

The user is the team lead with both toC + toB PM background. They want to see the trade-offs. Some good moves:

- **"Here are three template scopes I'm considering. Each trades X for Y. Which feels right?"** AskUserQuestion with three options. Forces a real choice; they'll often surface a fourth.
- **"I'm going to fix schema field `severity` to a controlled vocab [low/medium/high]. The cost: future projects with 5 levels need a template override. The benefit: layer-3 Claude has a clean contract. Lock it?"** Surface the cost AND the benefit. Don't just ask "OK?".
- **"This is the template doing the work, not John. If we move this logic up into John itself, every template would inherit it. Worth proposing as a core-John change?"** When you spot platform-vs-template trade-offs, surface them.

The user explicitly said: overkill in discussion is fine, not in development. So discuss freely; implement tight.

## When this skill triggers

- You're designing the produced apps' UX (toC lens).
- You're deciding what to fix vs leave flexible in the template (toB platform lens).
- You're about to lock a schema field, a runtime step, or a phase definition and want to check the trade-off.
- The user asks about the template's user experience, generalization scope, or operational properties.
- You're stuck between "make it more general" and "make it more domain-specific" and need a frame.

If you're more focused on *what content goes in the template* (which skills, which schema fields, which phases), the trigger is `hamster-drawing-board`. If you're more focused on *how to actually modify John* (which file goes where, what overrides what), the trigger is `hamster-workshop`. This skill sits between them — about the *purpose* of the modifications, not their content or implementation.
