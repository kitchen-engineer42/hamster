# Lenny-Skills Distillation

Distilled from refoundai/lenny-skills, surveyed 2026-05-26. Items below cleared a high bar: non-obvious to a strong coding agent, operationally crisp, and load-bearing for the combined toC product UX + toB platform lens that templates+John applies. Standard PM frameworks are deliberately omitted.

## The Collison Install — ship the implementation, not the contract

Dalton Caldwell on early Stripe: the founders "would just install Stripe into the customer's website... they basically would not go away until you finish the implementation." Treat a deal as un-closed until the product is in production use — manually do the integration if needed. For Hamster: when a template lands with an internal app team, the template author sits with them through first build. Don't measure shipping by "template published," measure by "first app built on it." (`skills/founder-sales/SKILL.md`)

## Self-serve ceiling: ~$10K per credit card

Elena Verna: "Self-serve monetization has a cap of about $10,000... credit cards start getting flagged and declined." Concrete threshold for when toC self-serve flips to toB sales-assisted. Applied to John templates: any template whose downstream apps deliver value above this band requires manual install/champion-arming, not a markdown README. Below it, polish the docs and let the team self-onboard. (`skills/pricing-strategy/SKILL.md`)

## Lack of outrage during outages = no PMF

Jeff Weinstein: "During those 20 minutes our customers weren't furious. That was the signal we did not have product market fit." Cleaner operational PMF test than retention curves for B2B platforms. For templates: if a template breaks and no app-team yells, that template isn't load-bearing — kill it or fold it into a more-used one. (`skills/measuring-product-market-fit/SKILL.md`)

## Eval the eval — validate the LLM judge against humans

Hamel Husain: "If using LLM-as-judge, you must eval the eval. Measure agreement with human experts. Iterate until it aligns." Most AI shops skip this and trust the judge model on faith. For John (an AI platform whose templates produce AI apps), every template's eval rig must include a small human-labeled gold set, and the LLM-judge's agreement rate against it tracked over time. (`skills/ai-evals/SKILL.md`, `skills/building-with-llms/SKILL.md`)

## Binary pass/fail beats Likert for eval scoring

Hamel Husain again: "Force Pass/Fail, not 1-5 scores. Scales produce meaningless averages like '3.7'. Binary forces real decisions." Operational rule for template-level quality gates — never let "rate this app 1-5" creep into a template's review checklist. (`skills/ai-evals/SKILL.md`)

## Start with vibes, evolve to evals once use cases converge

Howie Liu: for novel products, open-ended vibes testing first; only move to formal evals once you can name the recurring use cases. Sequencing rule for template lifecycle: a brand-new template gets reviewed by a human looking at full outputs; once 5+ apps are built on it and failure modes repeat, harden those into a regression eval set. Skipping the vibes phase produces brittle evals that test the wrong things. (`skills/building-with-llms/SKILL.md`)

## Weak-positioning diagnostic: customers ask sales to "back up and start over"

April Dunford: "Monitor for customers asking sales reps to 'back up and start over' during pitches — this signals positioning problems." Specific observable, not a vague "users don't get it." For templates: if an internal app team keeps asking "wait, so what is this template FOR?" mid-walkthrough, the template's description block is broken — fix the framing before fixing the substance. (`skills/positioning-messaging/SKILL.md`)

## Pivots are usually 10% when they need to be 200%

Todd Jackson: most founders pivot too small. When a template isn't getting picked up, the instinct is to tweak the prompt or rename the slash command; the right move is usually to question whether the template's *problem framing* is wrong. Pair with the Four Ps (Problem, Persona, Product, Positioning) check — the issue is usually a combination, not one of them. (`skills/startup-pivoting/SKILL.md`)

## Decision tenets must be reasonably-arguable in the opposite direction

Bob Baxley: a good tenet is specific enough that "someone could reasonably argue the opposite." A tenet like "we value users" is useless — nobody would argue against it. A tenet like "we ship template skeletons with placeholder skills rather than blank dirs" is good — a reasonable engineer could prefer blank dirs. Template-authoring teams should write these down once and stop re-debating. (`skills/evaluating-trade-offs/SKILL.md`)

## Cost-of-analysis-exceeds-upside test

Stewart Butterfield: "The cost of doing the analysis was this much. So it's guaranteed to be a loser." Before commissioning a benchmark, a comparison doc, or a research interview round for a template decision, estimate the person-hours and compare to the maximum-possible upside of the better choice. If person-hours > max upside, just pick. (`skills/evaluating-trade-offs/SKILL.md`)

## Compounding engineering — save every prompt that works

Dan Shipper: "For every unit of work, make the next unit easier. Save prompts that work. Build a library." Templates ARE this discipline crystallized at the org level. The operational implication: every John template should ship with a `prompts/` folder of the prompts the template author found load-bearing during their own dogfooding pass, not just the final SKILL.md. The "what didn't work" notes are equally valuable. (`skills/building-with-llms/SKILL.md`)
