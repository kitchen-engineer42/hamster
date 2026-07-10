# AGENTS.md — Hamster session

This is a Hamster template-authoring workspace for Codex. Hamster is not John:
it reads a clean local John checkout, creates a writable fork under
`forks/<template>/`, and transactionally packages the supported diff under
`templates/<template>/`.

Read `hamster-orientation` first, then use the drawing-board, workshop, and
packaging skills. Keep the original `$JOHARNESSBURG_PATH` read-only. Write only
inside this working directory. Template skills must support the providers
declared in `template.json`; shared skill sources installed in `.agents/skills`
are byte-identical to their `.claude/skills` counterparts.

Use safe lowercase slugs, exact John pins, and the strict packager. Do not hand
edit a published package or bypass validation. For high-volume John runtime
work, consume John's `.john/runs` and event contracts; do not invent a Hamster
orchestrator.
