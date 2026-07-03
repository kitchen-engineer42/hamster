# loop.json — config schema and eval-adapter contract

One config per evolution loop, conventionally at `evolve/<template-name>/loop.json` in the Hamster working dir. All relative paths resolve against the working dir (the dir containing `evolve/`).

```json
{
  "template_name": "kc-in-john",
  "joharnessburg_path": "~/joharnessburg",
  "template_root": "~/.claude/plugins/joharnessburg-templates/kc-in-john",
  "fork": "forks/kc-in-john-meta",
  "evolve_dir": "evolve/kc-in-john",

  "proposer": {
    "command": ["claude", "-p", "--permission-mode", "acceptEdits",
                "--allowedTools", "Read,Glob,Grep,Edit,Write", "--max-turns", "120"],
    "timeout_minutes": 120,
    "consecutive_failures_stop": 2
  },

  "eval": {
    "command": ["python3", "evolve/kc-in-john/adapters/score_kc.py"],
    "trials": 3,
    "trial_timeout_minutes": 45,
    "retry_infra_failures": 1,
    "min_valid_trials": 2
  },

  "objective": {
    "dense_key": "score",
    "sparse_key": "all_pass",
    "tokens_key": "tokens_millions",
    "w_sparse": 0.02,
    "w_cost_per_mtok": 0.005,
    "min_delta": 1.0
  },

  "mutation_allowlist": [
    "plugins/joharnessburg/skills/**",
    "plugins/joharnessburg/scripts/**",
    "plugins/joharnessburg/agents/**",
    "plugins/joharnessburg/commands/**",
    "plan_md_template.md", "claude_addon.md", "evolution.json",
    ".claude/workflows/*.js"
  ],
  "mutation_blocklist": [
    "**/process_scorecard.py", "**/reduce_events.py", "**/apply_template.py",
    "**/hooks/**", "**/.claude-plugin/**"
  ],

  "leakage": {
    "forbidden_patterns": ["held_out", "test-split", "ground_truth_holdout"],
    "notes": "Add every held-out doc/case identifier. The audit greps candidate diffs AND proposer transcripts; a hit rejects the iteration."
  },

  "packaging": {
    "strict_warnings": true,
    "description": "meta-harness evolved candidate",
    "extra_args": []
  }
}
```

Field notes:

- `proposer.command` — argv prefix; the lab appends the rendered protocol prompt as the final argument and runs it with cwd = working dir. The proposer does not need Bash: the lab commits for it. Add `Bash(python3 *)` to allowedTools only if you want in-session self-validation.
- `objective` — blended = `mean(dense) + w_sparse·mean(sparse) − w_cost·mean(tokens)`. A valid trial missing the sparse/tokens key counts as 0 in that mean (selective reporting cannot inflate the bonus); a trial without a numeric dense value is a candidate failure, never a fabricated 0. **Scale convention: dense and sparse are percentage points (0–100)**: `min_delta: 1.0` (must be > 0). `w_sparse` must keep one lucky sparse trial below the margin: a binary all_pass swings 100/trials points in a single trial, so the lab refuses configs where `w_sparse × 100/trials ≥ min_delta` (at the defaults that means `w_sparse < 0.03`; the example uses 0.02). Want a heavier sparse influence? Emit a continuous pass *rate* instead of a 0/100 flag and size w_sparse to its real variance. `w_cost_per_mtok: 0.005` docks 0.005 points per million tokens — scale it to your adapter's token magnitudes so cost stays a tiebreaker, not a driver. The incumbent's blended score is recomputed from its stored raw trials under the *current* weights at every comparison — changing a weight mid-run cannot promote a worse harness at a boundary. The three objective keys must be pairwise distinct (dense is always recorded as `score` in trial records; the lab refuses configs that collide).
- `min_delta` — calibrate, don't guess: run the baseline eval 3× first (`init` does this as run 000), compute the single-trial std, use `std/√trials` rounded up. Too strict a margin blocks genuine stacked gains (Niklaus: a 3-point margin blocked real 1.5–1.8-point wins); too loose promotes noise.
- `mutation_allowlist` / `blocklist` — glob patterns over fork-relative diff paths. Blocklist wins. Anything outside the allowlist invalidates the candidate before any tokens are spent on eval. This is also the owner-gate enforcement: core-John paths are simply not writable surface.
- `eval.min_valid_trials` — a candidate with fewer valid (non-infra-failed) trials is rejected as unmeasurable, never scored from a partial sample.
- `packaging.mode` — set `"none"` to evolve a project working tree in place instead of a packaged template: the candidate IS the fork checkout (`fork` must point at a git repo; `init` refuses otherwise), the packaging gate does not run (`decision.json` records `"packaging": null`), and `ship` is not applicable — merge or tag `meta/frontier` in the project itself.
- `packaging.extra_args` — appended verbatim to every `package_template.py` call. Needed whenever the template declares plan phases without the phase-checkpoint helper (the packager's gate is fail-closed): e.g. for kc-in-john today set `["--allow-missing-phase-checkpoint", "--phase-checkpoint-override-reason", "meta-harness candidate; gate enforced at ship review"]` — or better, make wiring `phase_checkpoint.py` into the template your first promoted mechanism and drop the override.

## Eval-adapter contract

The adapter is the executable form of the template's `evolution` declaration. The lab invokes it once per trial:

- **Environment**: `CANDIDATE_TEMPLATE_DIR` (packaged candidate template dir), `FORK_DIR`, `RUN_DIR` (this iteration's trace dir), `TRIAL_INDEX` (0-based), `LOOP_CONFIG` (path to loop.json).
- **Stdout**: the **last line** must be one JSON object: `{"score": 78.2, "all_pass": 4.2, "tokens_millions": 1.9, "metrics": {...}}`. Only the objective keys are read by the lab; put everything else under `metrics` (stored raw in `trials/*/score.json` for future proposers to grep; the report renders only the objective keys).
- **Exit codes**: `0` = valid measurement (even a terrible score — a measured 0 is data). `2` = infrastructure failure (provider timeout, network): the lab retries once, then excludes the trial. Any other non-zero = candidate failure (broken template, crash): **one hard-error trial disqualifies the whole candidate** — the remaining trials are skipped, not run.
- The adapter owns applying the candidate (`apply_template.py --template-root $CANDIDATE_TEMPLATE_DIR --output <tmp> --force`), running whatever product/build it measures, and parsing the scorer's own output. **Parse result files, not exit codes** — real scorers often exit 0 unconditionally.

### Worked example — kc-in-john product eval

Fast adapter that re-scores the existing built product against its strict per-rule GT (no rebuild; measures template-shipped catalog/skill changes only if your mutation surface maps into the product — for full fidelity, a slow adapter would drive a sample build first):

```python
#!/usr/bin/env python3
# evolve/kc-in-john/adapters/score_kc.py
import json, os, subprocess, sys
PRODUCT = os.path.expanduser("~/Desktop/project/k-eval/john测试")
r = subprocess.run(
    ["python3", "tests/score_rules.py", "--tier", "bulk", "--workers", "8",
     "--out", os.path.join(os.environ["RUN_DIR"], f"trial-{os.environ['TRIAL_INDEX']}-score_rules.json")],
    cwd=PRODUCT, capture_output=True, text=True, timeout=2400)
if "read operation timed out" in r.stderr or "network error" in r.stderr:
    sys.exit(2)                      # infra, not a candidate failure
if r.returncode != 0:
    sys.exit(1)
rep = json.loads(open(os.path.join(os.environ["RUN_DIR"],
      f"trial-{os.environ['TRIAL_INDEX']}-score_rules.json")).read())
dense = 100.0 * (0.7 * rep["walk_away_recall"] + 0.3 * rep["severity_recall"]) \
        - 2.0 * len(rep["false_positive_walkaways"])
print(json.dumps({"score": round(dense, 2),
                  "all_pass": 100.0 if rep["walk_away_recall"] == 1.0 and not rep["false_positive_walkaways"] else 0.0,
                  "metrics": {k: rep[k] for k in
                              ("walk_away_recall", "severity_recall", "false_positive_walkaways")}}))
```

Notes that generalize: `score_rules.py` always exits 0 — the JSON is the result; bulk tier is the cheap regression option; GT rule_ids missing from a candidate's catalog score as misses (a rename silently craters recall — that is correct behavior, renames ARE regressions); never accept a self-reported score without the GT file and its split.
