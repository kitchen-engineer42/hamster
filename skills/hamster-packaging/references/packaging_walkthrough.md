# Strict packaging walkthrough

1. Confirm `$JOHARNESSBURG_PATH` names a clean, symlink-free checkout whose
   plugin is under `plugins/joharnessburg/`.
2. Scaffold with `scaffold_fork.py --name <slug> --joharnessburg-path
   "$JOHARNESSBURG_PATH"`.
3. Modify only the fork. Put shared runtime guidance in `project_addon.md`,
   Claude-only guidance in `claude_addon.md`, and Codex-only guidance in
   `agents_addon.md`.
4. For dual-provider custom agents, author canonical Claude Markdown and use
   John's sync contract to produce the Codex TOML. Preserve Claude workflow
   assets; describe Codex orchestration through John's run ledger.
5. Review `git status --short` and `git diff --no-renames` in the fork.
6. Package:

   ```sh
   python3 .claude/skills/hamster-packaging/scripts/package_template.py \
     --fork forks/my-template \
     --output templates/my-template \
     --template-version 0.1.0 \
     --provider both \
     --smoke-test
   ```

7. If strict packaging stops, read
   `forks/my-template/.hamster/package_summary.json`. Fix validation errors.
   Revert unsupported changes. Use `--allow-warnings` only when every warning
   has an explicit user decision.
8. Confirm the output has a regular executable `apply.sh`, exact
   `requires_john`, declared providers, complete skills, provider addons, and
   any intended `codex/agents/` or `workflows/` assets. The output must not
   contain `.hamster/`.
9. Re-run the standalone validator after relocating a copy if desired:

   ```sh
   python3 .claude/skills/hamster-packaging/scripts/validate_template.py \
     /relocated/my-template \
     --john-install /clean/joharnessburg/plugins/joharnessburg \
     --initialize
   ```

10. Hand off the published directory plus its version and exact John pin. The
    summary stays with the fork. Claude applies and launches with
    `--plugin-dir`; Codex activates the merged result project-locally and must
    disable vanilla John for that session.
