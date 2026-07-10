---
name: hamster-evolution
description: Evolve an EXISTING John template from the evidence its installed base produced — run reports, shared lessons, end-user feedback — into the template's next version as a bounded, evidence-named diff. Use when the inputs are a template plus run reports/audits (not a fresh corpus), when the user says "evolve the template", "fold the run feedback in", "template vNext", "the team's runs found problems", or when accumulated reports for one template are waiting to be aggregated. A fresh template build is hamster-workshop's job; this skill is for version N → N+1.
---

# Hamster evolution

A template is the unit of domain learning: a bundle of skills used to build many apps of one type. Apps of that type generate feedback; this skill turns accumulated feedback into the template's next version. It is the semi-automated middle ring of John's evolution architecture — below it, projects log lessons; above it, John core evolves only by human analysis. **You propose; the template owner accepts.** Your edits never flow upward into John core — when the evidence points at core, you write a proposal, not a patch.

## Inputs (gather before anything else)

1. **The current template** — the real installed source, at its exact version. Note `requires_john` and which John versions the evidence ran on.
2. **Run reports** — the postmortems users assembled with `/john:report` (manifest, scorecard highlights, outcome summary, candidate lessons, deviations). These are your primary dataset. They arrive scrubbed; treat any corpus content that slipped through as radioactive — quote none of it forward.
3. **Shared lessons ledgers / audits** (optional) — richer per-run detail when a user shares it. **Ask for the full audit** when a report references one, or when the recurring problems are craft/result-quality rather than process: a 1-page report carries process evidence well and result *forensics* poorly, so on reports alone you can justify process and conformance changes but rarely craft redesigns — don't force the latter from thin evidence; request the source.
4. **The template's own evolution record** — prior changelogs, if this isn't v2. What was tried, what the evidence said, what got rejected.

Two kinds of evidence, weighted differently:

- **Runtime results** (domain scores, end-user corrections and reactions): the app's end users are competent ground truth — a domain expert using a verification app knows the rules; a player knows fun. Where the template ships a scorer, these are the *primary* signal.
- **Build-process evidence** (scorecards: skills never invoked, gates never run, silent phase skips, fan-out that never happened): reading this takes engineering judgment, and it often explains *why* outcomes disappointed. A run that produced a fine app while bypassing the methodology is still a template failure — the next run won't be lucky.

## The method: attribution before edits

For each recurring problem across reports, build the **causal chain** — name it end to end:

> symptom in the app or scorecard → the run behavior that produced it → the template passage (or absence) that licensed the behavior → the bounded change that would have prevented it.

A proposed change without a chain is a hunch; park it as an open question for the owner. One report's problem is an observation; **the same chain in ≥2 independent runs** (different corpora/users/devices) is a pattern worth an edit — except *incident-grade* failures (data loss, a gate that can never fire, shipped-app breakage), which justify action from a single occurrence.

Then decide **where each accepted lesson lands** — the classification that keeps templates lean:

- **Core asset of the template** (SKILL.md bodies, plan skeleton, reusable scripts): every project of the domain needs it.
- **Perimeter asset** (`references/`, worked examples, edge-case notes): real but conditional — loaded on demand.
- **Ad-hoc** (leave it out): a judgment call each project should make fresh. Folding everything in kills the wide tunnel; "no change" is a legitimate verdict for a lesson.
- **Not ours — core John**: apply the sufficiency test. *A skill goes into John so John thinks correctly; into a template so the John-equipped app builder doesn't have to think from scratch.* If the failing passage is domain-invariant teaching, write a **core proposal** in the changelog's "escalations" section for the owner to file upstream — never edit core or work around it by re-teaching core methodology inside the template.

## Producing vNext

Work like a workshop session, on the same machinery:

1. **Fork** the current template's John baseline (`hamster-packaging` / `scaffold_fork.py`), apply the current template's diff so the fork *is* the template, and make your changes there.
2. **Bounded diff.** Edit the passages your chains name; keep everything else byte-identical. No wholesale rewrites of skills that mostly work — unbounded rewriting is the documented way text assets collapse. If more than roughly a third of a skill needs to change, stop and check with the owner whether this is evolution or a redesign.
3. **Each change carries its evidence.** The changelog (see `references/evolution-changelog-format.md`) names, per change: the chain, the supporting runs (count, not corpus details), and the expected effect. Changes you considered and **rejected** get a line too — the next evolution session must not re-litigate them.
4. **Check the feedback design while you're in there.** If the template lacks an `evolution` declaration (scorer / eval set / feedback design — see `hamster-packaging`, "Declaring evolution"), adding one is usually the highest-value change in v2: it's what upgrades the *next* cycle from process-evidence-only to scored.
5. **Package** with required `--template-version`, the exact John pin, declared providers, and `--smoke-test`. Minor bump for behavior-shaping changes, patch for fixes. Strict warnings publish nothing.

## The gate (before hand-off)

- **Held-out check.** Re-run what can be re-run: apply vNext cleanly against the pinned John; scaffold a plan from it; run any template-shipped scorer/conformance checks; if a sample corpus is available, a sample build. Never score an edit only against the run that motivated it.
- **Adversarial pass.** A second set of eyes (subagent reviewer is fine) attacks the diff: does any change contradict another? Does an edit re-teach (or fight) core methodology? Did corpus content or user identifiers leak into template text? Does every change have its chain?
- **Conformance.** New/changed fan-out agents use John's atomic event writer and run identity; `[[refs]]` resolve; the package contains the base-commit canonical executable `apply.sh` and its recorded checksum; shared provider outputs are hash-identical.
- **Owner sign-off.** Present: the changelog, the rejected list, the escalations. The owner decides; team consensus can overwrite any threshold in this skill.

## What this skill does NOT do

- **Author a template from scratch** — that's the drawing-board → workshop → packaging path.
- **Edit John core or propose-by-patching it** — escalations are written, not applied.
- **Honor unevidenced preferences** — "I feel the skill should say X" goes to the owner as a question, not into the diff.
- **Run on one report.** Below the evidence threshold, the right output is "no change yet; here's what to watch for" — written down, so the waiting is also recorded.

## Cross-references

- `hamster-packaging` — fork + package machinery; the evolution declaration
- `hamster-workshop` — the modification rules of the road (what templates can/can't touch); the architecture summary with John's evolution-ring section
- `hamster-product-thinking` — when feedback implies the *product* (not the skills) is wrong, re-open the design conversation instead of patching skills
- John core's `skill-evolution` skill — the project-side half: where lessons and reports come from
- `references/evolution-changelog-format.md` — the vNext changelog format
