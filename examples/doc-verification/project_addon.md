## Active template: doc-verification

This is a verification project. The produced app accepts batches of domain documents, applies every relevant extracted rule, surfaces violations with evidence and explanations, and gives reviewers a legible results workflow.

**Knowledge format:** rules plus glossary. Each rule follows the template's locked schema; non-rule definitions belong in the glossary.

**Source-first principle:** complete a first-pass rule catalog from the source regulations before opening sample documents for validation. Reversing the order silently drops rules the samples do not exercise.

**Falsifiability:** every rule states the exact condition under which it fails. A rule without that statement is incomplete and cannot pass the machine-checkability gate.

**Per-rule packaging:** publish the same rule skill under `.claude/skills/rule-R<id>/` and `.agents/skills/rule-R<id>/`, including `SKILL.md`, the check script, references, and labeled samples.

**Build pipeline:** parse regulations, extract rules, author skills, test against labeled samples, optionally distill for lower-cost execution, run production QC, and finalize a release bundle.

Keep this template rules-focused. Surface genuinely non-rule requirements as an Open Decision instead of silently broadening the knowledge model.
