---
name: meta-harness
description: Run an automated, scaffold-enforced evolution loop over an EXISTING John template — a headless proposer rewrites the template one mechanism at a time while a Python lab (meta_loop.py) forks, packages, evaluates on a frozen dev set, gates promotion by a noise-calibrated blended score, and stores full raw traces; then render the per-iteration visual report (report.py). Use when the user says "run the meta-harness loop", "evolve it automatically", "start the loop", "让它自己进化", "跑 N 轮", or wants the Niklaus/Meta-Harness methodology applied to a template. A single manual evidence pass over run reports is hamster-evolution's job; a fresh template build is hamster-workshop's.
---

# Meta-harness

An automated evolution loop for John templates, built from two published results and one internal postmortem. Meta-Harness (Lee et al. 2026) showed the key ingredient is **raw execution traces on a filesystem the proposer can grep** — scores-only or summarized feedback collapses search quality (median 50.0 → ~34.7 in their ablation). Niklaus (2026) showed the working discipline on a legal benchmark with a frozen model: **copy the frontier byte-for-byte, add exactly one mechanism, average three trials, promote only past a noise-calibrated margin** — and that the winning mechanisms were deterministic code, not prompts. Our own evolution postmortem found the same failure the other way around: evidence discipline on paper, no fork, no held-out run, no scorer in practice.

This skill is the executable answer: **the model can be creative; the scaffold is strict about what counts.** You (or a headless session the scaffold spawns) play researcher. `meta_loop.py` plays the lab: it forks, packages, evaluates, audits leakage, decides promotion, and writes every raw artifact down. No candidate is scored by the session that proposed it.

## Two roles

- **Proposer** (a Claude session — headless `claude -p` per iteration, spawned by the loop): reads the full run history under `evolve/<name>/runs/` (raw traces, diffs, scores — grep them, don't ask for summaries), forms one hypothesis, edits the fork, writes `pending_eval.json`. Never runs the eval, never touches held-out material, never commits — the scaffold commits.
- **Lab** (`scripts/meta_loop.py`): owns fork/branch mechanics, the mutation allowlist, packaging (via hamster-packaging's `package_template.py`), the eval adapter, trials, the promotion gate, the leakage audit, and the trace store.

## The loop, one iteration

1. Lab checks out `meta/cand-NNN` from `meta/frontier` in the fork (byte-for-byte copy).
2. Lab spawns the proposer with the protocol prompt (`references/proposer-protocol.md`) pointing at the runs history.
3. Proposer edits the fork — **one mechanism** — and writes `pending_eval.json` (hypothesis, mechanism, changes, fix_tasks, regression_tasks, evidence).
4. Lab validates: pending_eval present and well-formed; diff confined to the mutation allowlist; leakage audit clean; `package_template.py` exits 0 (fail-closed phase gate included).
5. Lab runs the eval adapter N trials (default 3), retries infra failures once, and computes the blended score: `dense + w_sparse·sparse − w_cost·(tokens/M)`.
6. Promotion: candidate wins only if its blended mean beats the incumbent's — **recomputed from raw trials under current weights, never a stored number** — by at least `min_delta`. Win → `meta/frontier` advances and the mechanism compounds; lose → branch stays in history for later proposers to mine.
7. Everything lands in `runs/NNN-<slug>/`: full proposer transcript, diff.patch, per-trial adapter logs and scores, decision.json. Raw, never summarized.

## Before you start (all four, no exceptions)

1. **A template to evolve** — an installed template dir (e.g. `~/.claude/plugins/joharnessburg-templates/<name>/`) or an existing fork; or, with `packaging.mode: "none"`, any git project working tree to evolve in place. `meta_loop.py init` scaffolds the fork (via hamster-packaging's `scaffold_fork.py`), applies the template's diff so the fork IS the template, and commits that as the baseline frontier.
2. **A runnable eval adapter** — the executable form of the template's `evolution` declaration (scorer / eval_set / feedback_design). The contract is in `references/loop-config-format.md`. If the template declares evolution but the scorer isn't runnable, building the adapter is your first task — not optional; the loop refuses to start without one.
3. **A frozen dev/held-out split** — the adapter scores dev only. Held-out identifiers go in the config's leakage list; the audit rejects any iteration whose diff or transcript touches them. Score the held-out set once, at the end, by hand.
4. **`loop.json`** — the config (same reference). Calibrate `min_delta` to measured trial noise (rule of thumb: single-trial std / √trials, rounded up), don't guess it.

## Running

```sh
python3 .claude/skills/meta-harness/scripts/meta_loop.py init \
  --template ~/.claude/plugins/joharnessburg-templates/<name> \
  --joharnessburg-path "$JOHARNESSBURG_PATH" --config evolve/<name>/loop.json
python3 .claude/skills/meta-harness/scripts/meta_loop.py run --config evolve/<name>/loop.json --iterations 10
python3 .claude/skills/meta-harness/scripts/meta_loop.py status --config evolve/<name>/loop.json
python3 .claude/skills/meta-harness/scripts/report.py evolve/<name> --out evolve/<name>/report.html
python3 .claude/skills/meta-harness/scripts/meta_loop.py ship --config evolve/<name>/loop.json \
  --version 0.2.0 --output templates/<name>-v0.2.0
```

`run` is resumable — it picks up after the last completed iteration; a killed proposer or a crashed trial is recorded and retried or skipped per config, and the loop stops cleanly after `consecutive_failures_stop` proposer failures rather than burning sessions (the operational-hardening lesson: an LLM optimizer needs the same care as any long-running job).

## Promotion is not shipping

The frontier is a **dev-side** artifact. Shipping vNext to the team keeps hamster-evolution's gate intact: `ship` packages the frontier, bumps the version (the packager always stamps 0.1.0 — ship rewrites it), and expects a `CHANGELOG.md` you draft in the evolution changelog format — each promoted run's `pending_eval.json` plus its `decision.json` IS the evidence chain for one changelog entry; rejected candidates go in the Rejected section so the next loop doesn't re-litigate them. **The template owner accepts or declines.** Core-John findings become written escalations, never patches — the allowlist enforces this mechanically.

## What the scaffold enforces vs what you own

Enforced by code: fork isolation, one-candidate-one-branch, mutation allowlist (core scripts, `process_scorecard.py`, hooks, plugin manifest are out of bounds), leakage audit, N-trial averaging, blended gate with incumbent recompute, a w_sparse cap so one lucky all-pass trial cannot clear min_delta alone, full-raw trace store, packaging gates. Yours to get right: hypothesis quality (read the traces — the ablation says that's the whole game), adapter honesty (never accept a product's self-reported score; require the GT file and its split), `min_delta` calibration, and the changelog.

## What this skill does NOT do

- **Author a template from scratch** — hamster-workshop.
- **Replace the owner gate** — the loop promotes a frontier; only the owner ships a version.
- **Optimize the sparse headline metric directly** — optimize the dense rate; fold the sparse one in as a bonus (one lucky all-pass run must not clear the margin alone).
- **Trust exit codes as scores** — adapters parse result JSON; several real scorers (e.g. kc-in-john's `score_rules.py`) exit 0 regardless of score.

## Cross-references

- `hamster-packaging` — `scaffold_fork.py` / `package_template.py`, the evolution declaration, the phase-checkpoint gate
- `hamster-evolution` — the evidence rules this loop automates (chains, thresholds, changelog format, owner gate)
- `references/loop-config-format.md` — `loop.json` schema + eval-adapter contract + a worked kc-in-john adapter
- `references/proposer-protocol.md` — the exact protocol prompt each headless proposer receives
- `references/run-layout.md` — the trace-store layout the report and future proposers read
