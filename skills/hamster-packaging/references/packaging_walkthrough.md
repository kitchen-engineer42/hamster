# Packaging walkthrough

A 10-step end-to-end of one packaging session. Use as a reference if you forget what to do next.

## 0. Pre-flight check

- Your working dir has `.claude/skills/hamster-*/`, `CLAUDE.md`, plus empty `notes/`, `forks/`, `templates/` dirs.
- `$JOHARNESSBURG_PATH` is set to your local joharnessburg checkout.
- You've done the drawing-board work and know what modifications you want to make.
- (Recommended) The user has signed off on the proposed modifications via plan mode.

## 1. Scaffold the fork

```sh
python3 .claude/skills/hamster-packaging/scripts/scaffold_fork.py \
  --name my-template \
  --joharnessburg-path "$JOHARNESSBURG_PATH"
```

Result: `forks/my-template/` exists, with `.hamster-base-commit` recording the joharnessburg HEAD at clone time.

## 2. Modify the fork

Edit files in `forks/my-template/`. Examples of supported changes:

- Edit `forks/my-template/skills/chunking/SKILL.md` to retune chunking for slide-deck use.
- Create `forks/my-template/skills/slide-rendering/SKILL.md` for a new slide-rendering skill.
- Create `forks/my-template/plan_md_template.md` with a 6-phase slide-deck pipeline.
- Create `forks/my-template/claude_addon.md` with taste preferences for the produced apps.
- `rm -rf forks/my-template/skills/platform-credits/` if produced apps don't have priced operations.

Take notes in your working dir's `notes/` as you go.

## 3. Sanity-check the fork

In `forks/my-template/`:

```sh
git status     # see your changes
git diff       # eyeball the changes
```

Make sure the change set matches your design intent before packaging. If you've made changes outside `skills/`, the packager will warn — you can either revert here or proceed and triage warnings in step 5.

## 4. Package

```sh
python3 .claude/skills/hamster-packaging/scripts/package_template.py \
  --fork forks/my-template \
  --output templates/my-template \
  --description "Slide deck builder from physics textbook chapters"
```

Watch the script's output: it lists translations and any warnings.

## 5. Triage warnings (if any)

Each warning means a change in the fork couldn't be translated. For each:

- Read the warning's `reason` field in `templates/my-template/.hamster/package_summary.json`.
- Decide: revert in fork, escalate to user, or find in-scope alternative.
- If reverting: `git checkout -- <path>` in the fork, then re-run packaging (after `rm -rf templates/my-template`).
- If escalating: stop packaging, surface the proposal to the user, wait for guidance.

A clean run has zero warnings.

## 6. Eyeball the package

Look at `templates/my-template/`:

```sh
ls templates/my-template/
cat templates/my-template/template.json
cat templates/my-template/.hamster/package_summary.json
ls templates/my-template/skills/_override/   # if any overrides
ls templates/my-template/skills/               # if any additive skills
```

Confirm:

- Override skill dirs are complete (SKILL.md + references/ as needed).
- Additive skills are complete.
- `_delete` if present lists the right skills.
- `plan_md_template.md` and `claude_addon.md` are present if you shipped them.
- `template.json` description and `requires_john` are sensible.

## 7. (Optional) Smoke test

If you want a quick sanity check that `apply.sh` is executable:

```sh
python3 .claude/skills/hamster-packaging/scripts/package_template.py \
  --fork forks/my-template \
  --output templates/my-template-smoketest \
  --smoke-test
```

(Re-packages to a fresh dir so the original isn't disturbed.) The smoke test runs `apply.sh --help`; it's a "does the script run at all" check, not a real apply test.

For a real apply test, manually invoke against a temp `joharnessburg-applied` dir:

```sh
cd templates/my-template
./apply.sh --plugin-dir /tmp/joharnessburg-applied-test
ls /tmp/joharnessburg-applied-test/skills/  # confirm overrides + additions present
```

## 8. Iterate if needed

If anything's off (warnings you missed, an override missing a file, a schema field you forgot), go back to the fork:

- Edit the fork further.
- Delete the old packaged template: `rm -rf templates/my-template`.
- Re-run packaging.

The fork is the workspace; the template is regenerable from it.

## 9. Hand off

Tell the user the template is ready. Suggest:

> Template packaged at `templates/my-template/`. Base commit: `<short-hash>`. Translations: N. Warnings: 0. Ready for your review — when you're satisfied, distribute it; each user installs it at `~/.claude/plugins/joharnessburg-templates/my-template/` and runs its `apply.sh`.

The user eyeballs, possibly tests against a real joharnessburg-applied dir, then distributes.

## 10. (Later) When you need to refresh the template

If joharnessburg has had updates since you scaffolded the fork, and you want the template to track them, the safest path:

1. Scaffold a NEW fork from the updated joharnessburg.
2. Replay your modifications (mostly: copy your changed/new skills from the old fork into the new fork; verify they still make sense against the new joharnessburg).
3. Re-package to a new output dir.

A `git rebase` of the existing fork is possible but more brittle. The fork is regenerable; start fresh when in doubt.
