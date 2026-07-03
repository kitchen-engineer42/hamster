# Trace-store layout

Everything the loop learns lives on disk under `evolve/<template-name>/`, raw and append-only. This is the filesystem-as-feedback design: future proposers grep it, `report.py` renders it, and the ablation result it exists for is blunt — scores-only or summarized feedback collapses search quality. Store raw; never summarize in place.

```
evolve/<name>/
├── loop.json                 # config (see loop-config-format.md)
├── frontier.json             # {"branch": "meta/frontier", "run": "007-matter-audit",
│                             #  "blended": 83.3, "lineage": ["000-baseline", "003-...", ...]}
├── state.json                # loop bookkeeping: next iteration, consecutive failures
├── adapters/                 # your eval adapter(s)
├── CHANGELOG.md              # drafted at ship time, evolution-changelog format
└── runs/
    └── NNN-<mechanism-slug>/
        ├── pending_eval.json     # the proposer's declared hypothesis (verbatim)
        ├── proposer.log          # full stdout/stderr of the proposer session
        ├── diff.patch            # git diff frontier..candidate (full)
        ├── diff.stat             # git diff --stat (for the report)
        ├── candidate-template/   # packaged template (package_template.py output)
        ├── trials/
        │   └── trial-K/
        │       ├── score.json    # adapter's last-line JSON, verbatim
        │       ├── adapter.log   # adapter stderr + attempt markers
        │       └── stdout.log    # full adapter stdout
        ├── decision.json         # the lab's verdict (schema below)
        └── meta.json             # timestamps, branch, commit shas (evaluated runs only)
```

`decision.json`:

```json
{
  "run": "004-deliverable-landing-gate",
  "status": "baseline | promoted | rejected | invalid | infra_failed | no_op",
  "reason": "human-readable one-liner (gate math, or which validation failed)",
  "blended": 79.2,
  "incumbent_blended": 72.8,
  "min_delta": 1.0,
  "weights": {"w_sparse": 0.02, "w_cost_per_mtok": 0.005},
  "trials": [{"trial": 0, "valid": true, "score": 78.9, "all_pass": 0.0, "tokens_millions": 1.7}],
  "dense_mean": 78.7, "dense_std": 0.9,
  "validation": {"pending_eval": true, "allowlist": true, "leakage": true, "packaging": true}
}
```

Rules the layout encodes:

- **Run 000 is always the baseline** — the unmodified frontier evaluated with the same adapter and trial count. Every later comparison is against measured trials, not an assumed number.
- **Failed-proposer iterations persist as `runs/NNN-pending/`** (proposer.log + decision.json only) — the mechanism slug never arrived, so the dir keeps its provisional name.
- **Rejected runs are kept forever.** They are the proposer's negative dataset and the changelog's Rejected section. Deleting a rejected run re-opens it for re-litigation.
- **`decision.json` never stores a comparison as final truth** — blended numbers are recomputed from `trials` under current weights whenever compared. The stored `blended` is a convenience snapshot only.
- **Nothing under `runs/` is edited after the iteration closes** — corrections are new runs. Two scaffold exceptions: a forced re-`init` re-measures and replaces `000-baseline`, and a run dir a kill left without `decision.json` gets one recorded (`infra_failed`) on the next `run`.
- **`validation.packaging` is `null` in in-place mode** (`packaging.mode: "none"`) — no gate exists there, and the store never records a gate that didn't run as passed.
