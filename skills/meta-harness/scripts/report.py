#!/usr/bin/env python3
"""report.py — render a meta-harness evolution run as a single-file HTML report.

Reads the trace store under evolve/<name>/ (see references/run-layout.md) and
produces the per-iteration view: score trajectory with one dot per candidate,
and one card per iteration answering "what changed, and did it count".

Usage:
  python3 report.py evolve/<name> --out evolve/<name>/report.html [--lang zh|en]
  python3 report.py --demo --out /tmp/meta-harness-demo.html

No dependencies, no CDN: the output is fully self-contained.
"""

import argparse
import html
import json
import re
import sys
import tempfile
from pathlib import Path

STATUS_COLOR = {"baseline": "#5b7fa6", "promoted": "#3d8b57", "rejected": "#9aa0a6",
                "invalid": "#c0564c", "infra_failed": "#c78b3b", "no_op": "#9aa0a6"}
L = {
    "zh": {"title": "meta-harness 进化报告", "baseline": "基线", "frontier": "当前前沿",
           "iters": "迭代", "promoted": "晋升", "trajectory": "混合分轨迹（每点一个候选）",
           "hypothesis": "假设", "changes": "改动", "trials": "试验",
           "verdict": "判定", "diff": "查看 diff", "files": "个文件",
           "legend": {"baseline": "基线", "promoted": "晋升", "rejected": "未达门槛",
                      "invalid": "无效", "infra_failed": "基础设施失败", "no_op": "无提案"},
           "nav": "← → 键在迭代间跳转", "gain": "较基线", "vs": "对在任",
           "evidence": "证据", "fix": "预期改善", "reg": "回归检查"},
    "en": {"title": "meta-harness evolution report", "baseline": "baseline",
           "frontier": "frontier", "iters": "iterations", "promoted": "promoted",
           "trajectory": "Blended score trajectory (one dot per candidate)",
           "hypothesis": "Hypothesis", "changes": "Changes", "trials": "Trials",
           "verdict": "Verdict", "diff": "view diff", "files": "files",
           "legend": {"baseline": "baseline", "promoted": "promoted",
                      "rejected": "below margin", "invalid": "invalid",
                      "infra_failed": "infra failed", "no_op": "no-op"},
           "nav": "Use ← → to step through iterations", "gain": "vs baseline",
           "vs": "vs incumbent", "evidence": "Evidence", "fix": "Should improve",
           "reg": "Regression checks"},
}


def esc(s):
    return html.escape(str(s if s is not None else ""))


def load(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return default


def read_runs(evolve_dir):
    runs = []
    runs_dir = Path(evolve_dir) / "runs"
    if not runs_dir.exists():
        sys.exit(f"no runs/ under {evolve_dir}")
    for d in sorted(runs_dir.iterdir()):
        if not d.is_dir():
            continue
        dec = load(d / "decision.json", {})
        pend = load(d / "pending_eval.json", {})
        stat = (d / "diff.stat").read_text() if (d / "diff.stat").exists() else ""
        patch = (d / "diff.patch").read_text(errors="replace") \
            if (d / "diff.patch").exists() else ""
        if len(patch) > 60000:
            patch = patch[:60000] + "\n... (truncated — full patch in runs/)"
        runs.append({"name": d.name, "dec": dec, "pend": pend,
                     "stat": stat, "patch": patch})
    return runs


def svg_trajectory(runs, t):
    pts = [(i, r) for i, r in enumerate(runs)
           if isinstance(r["dec"].get("blended"), (int, float))]
    W, H, PAD = 860, 240, 42
    if not pts:
        return "<p>no scored runs yet</p>"
    ys = [r["dec"]["blended"] for _, r in pts]
    lo, hi = min(ys), max(ys)
    span = (hi - lo) or 1.0
    lo, hi = lo - span * 0.12, hi + span * 0.12
    n = len(runs)
    def X(i):
        return PAD + (W - 2 * PAD) * (i / max(n - 1, 1))
    def Y(v):
        return H - PAD - (H - 2 * PAD) * ((v - lo) / (hi - lo))
    # frontier step line: running best among baseline/promoted
    front, best = [], None
    for i, r in enumerate(runs):
        if r["dec"].get("status") in ("baseline", "promoted") and \
                isinstance(r["dec"].get("blended"), (int, float)):
            best = r["dec"]["blended"]
        if best is not None:
            front.append((X(i), Y(best)))
    line = ""
    if len(front) > 1:
        dpath = f"M{front[0][0]:.1f} {front[0][1]:.1f}"
        for (x0, y0), (x1, y1) in zip(front, front[1:]):
            dpath += f" L{x1:.1f} {y0:.1f} L{x1:.1f} {y1:.1f}"
        line = (f'<path d="{dpath}" fill="none" stroke="#3d8b57" '
                'stroke-width="1.5" stroke-dasharray="1 0" opacity="0.55"/>')
    dots, labels = [], []
    for i, r in enumerate(runs):
        st = r["dec"].get("status", "invalid")
        c = STATUS_COLOR.get(st, "#9aa0a6")
        v = r["dec"].get("blended")
        y = Y(v) if isinstance(v, (int, float)) else H - PAD + 14
        shape = (f'<circle cx="{X(i):.1f}" cy="{y:.1f}" r="6" fill="{c}"'
                 if isinstance(v, (int, float)) else
                 f'<rect x="{X(i)-5:.1f}" y="{y-5:.1f}" width="10" height="10" fill="{c}"')
        dots.append(f'<a href="#run-{i}">{shape} style="cursor:pointer"><title>'
                    f'{esc(r["name"])} — {esc(st)}'
                    f'{" " + format(v, ".1f") if isinstance(v, (int, float)) else ""}'
                    f'</title></{"circle" if isinstance(v, (int, float)) else "rect"}></a>')
        if st in ("baseline", "promoted") and isinstance(v, (int, float)):
            labels.append(f'<text x="{X(i):.1f}" y="{Y(v)-11:.1f}" text-anchor="middle" '
                          f'font-size="11" fill="#444">{v:.1f}</text>')
    axis = (f'<line x1="{PAD}" y1="{H-PAD}" x2="{W-PAD}" y2="{H-PAD}" '
            'stroke="#ccc" stroke-width="0.7"/>')
    ticks = "".join(
        f'<text x="{X(i):.1f}" y="{H-PAD+16}" text-anchor="middle" font-size="10" '
        f'fill="#888">{esc(runs[i]["name"].split("-")[0])}</text>' for i in range(n))
    legend = "".join(
        f'<span class="lg"><i style="background:{STATUS_COLOR[k]}"></i>{esc(v)}</span>'
        for k, v in t["legend"].items())
    return (f'<div class="lgrow">{legend}</div>'
            f'<svg viewBox="0 0 {W} {H}" role="img">{axis}{line}'
            f'{"".join(dots)}{"".join(labels)}{ticks}</svg>')


def card(i, r, baseline, t):
    dec, pend = r["dec"], r["pend"]
    st = dec.get("status", "invalid")
    v = dec.get("blended")
    files = len([l for l in r["stat"].splitlines() if "|" in l])
    head_score = ""
    if isinstance(v, (int, float)):
        head_score = f'<span class="score">{v:.1f}'
        if isinstance(baseline, (int, float)):
            head_score += f' <em>({t["gain"]} {v-baseline:+.1f})</em>'
        head_score += "</span>"
    trials = dec.get("trials", [])
    tr_txt = " · ".join(
        (f'{x.get("score"):.1f}' if isinstance(x.get("score"), (int, float))
         else ("infra" if x.get("infra") else "err")) for x in trials) or "—"
    inc = dec.get("incumbent_blended")
    vs = (f' <em>({esc(t["vs"])} {v-inc:+.2f}, min_delta {esc(dec.get("min_delta"))})</em>'
          if isinstance(inc, (int, float)) and isinstance(v, (int, float)) else "")
    rows = []
    if pend.get("hypothesis"):
        rows.append((t["hypothesis"], esc(pend["hypothesis"])))
    if pend.get("changes"):
        rows.append((t["changes"],
                     "<br>".join(esc(c) for c in pend["changes"])
                     + f'<span class="dim"> — {files} {t["files"]}</span>'))
    if pend.get("fix_tasks"):
        rows.append((t["fix"], "; ".join(esc(x) for x in pend["fix_tasks"])))
    if pend.get("regression_tasks"):
        rows.append((t["reg"], "; ".join(esc(x) for x in pend["regression_tasks"])))
    if pend.get("evidence"):
        rows.append((t["evidence"], "; ".join(esc(x) for x in pend["evidence"])))
    rows.append((t["trials"], f'{tr_txt}'
                 + (f' <span class="dim">σ={esc(dec.get("dense_std"))}</span>'
                    if dec.get("dense_std") is not None else "")))
    rows.append((t["verdict"], esc(dec.get("reason", "")) + vs))
    body = "".join(f'<div class="row"><b>{esc(k)}</b><div>{val}</div></div>'
                   for k, val in rows)
    diff_blk = ""
    if r["patch"]:
        diff_blk = (f'<details><summary>{esc(t["diff"])} '
                    f'<span class="dim">{esc(r["stat"].strip().splitlines()[-1] if r["stat"].strip() else "")}'
                    f'</span></summary><pre>{esc(r["patch"])}</pre></details>')
    return (f'<section class="card" id="run-{i}" data-i="{i}">'
            f'<header><span class="pill" style="background:{STATUS_COLOR.get(st, "#999")}">'
            f'{esc(t["legend"].get(st, st))}</span>'
            f'<h3>{esc(r["name"])}</h3>{head_score}</header>'
            f'{body}{diff_blk}</section>')


def render(evolve_dir, out, lang):
    t = L[lang]
    runs = read_runs(evolve_dir)
    cfg = load(Path(evolve_dir) / "loop.json", {})
    fr = load(Path(evolve_dir) / "frontier.json", {})
    name = cfg.get("template_name", Path(evolve_dir).name)
    baseline = next((r["dec"].get("blended") for r in runs
                     if r["dec"].get("status") == "baseline"), None)
    frontier_v = fr.get("blended")
    n_promoted = sum(1 for r in runs if r["dec"].get("status") == "promoted")
    delta = (f'{frontier_v - baseline:+.1f}'
             if isinstance(frontier_v, (int, float)) and isinstance(baseline, (int, float))
             else "—")
    stats = [(t["baseline"], f'{baseline:.1f}' if baseline is not None else "—"),
             (t["frontier"], f'{frontier_v:.1f}' if frontier_v is not None else "—"),
             ("Δ", delta), (t["iters"], str(len(runs))),
             (t["promoted"], str(n_promoted))]
    stat_html = "".join(f'<div class="stat"><span>{esc(k)}</span><b>{esc(v)}</b></div>'
                        for k, v in stats)
    cards = "".join(card(i, r, baseline, t) for i, r in enumerate(runs))
    page = f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(t["title"])} — {esc(name)}</title><style>
body{{font:15px/1.65 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
 color:#222;max-width:920px;margin:0 auto;padding:28px 20px}}
h1{{font-size:21px;font-weight:600}} h3{{font-size:15px;margin:0;font-weight:600}}
.stats{{display:flex;gap:26px;margin:14px 0 6px;flex-wrap:wrap}}
.stat span{{display:block;font-size:12px;color:#777}} .stat b{{font-size:20px}}
.lgrow{{margin:8px 0 2px}} .lg{{font-size:12px;color:#666;margin-right:14px}}
.lg i{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}}
svg{{width:100%;height:auto;background:#fafafa;border:0.5px solid #e4e4e4;border-radius:8px}}
.card{{border:0.5px solid #ddd;border-radius:10px;padding:14px 16px;margin:14px 0}}
.card.active{{border-color:#5b7fa6;box-shadow:0 0 0 2px #5b7fa622}}
.card header{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
.pill{{color:#fff;font-size:11px;padding:2px 9px;border-radius:9px;white-space:nowrap}}
.score{{margin-left:auto;font-size:17px;font-weight:600}}
.score em{{font-size:12px;font-weight:400;color:#3d8b57;font-style:normal}}
.row{{display:grid;grid-template-columns:96px 1fr;gap:10px;padding:3px 0;font-size:13.5px}}
.row b{{color:#666;font-weight:500}} .dim{{color:#999;font-size:12px}}
details{{margin-top:8px;font-size:13px}} summary{{cursor:pointer;color:#5b7fa6}}
pre{{background:#f6f6f6;border-radius:6px;padding:10px;overflow-x:auto;font-size:11.5px;
 max-height:420px;overflow-y:auto}}
.hint{{color:#999;font-size:12px;margin:4px 0 0}}</style></head><body>
<h1>{esc(t["title"])} — {esc(name)}</h1>
<div class="stats">{stat_html}</div>
<p class="hint">{esc(t["trajectory"])} · {esc(t["nav"])}</p>
{svg_trajectory(runs, t)}
{cards}
<script>
let cur=-1;const cards=[...document.querySelectorAll('.card')];
function go(i){{if(i<0||i>=cards.length)return;if(cur>=0)cards[cur].classList.remove('active');
cur=i;cards[cur].classList.add('active');cards[cur].scrollIntoView({{behavior:'smooth',block:'center'}});}}
document.addEventListener('keydown',e=>{{if(e.key==='ArrowRight')go(cur+1);
if(e.key==='ArrowLeft')go(cur-1);}});
</script></body></html>"""
    Path(out).write_text(page)
    print(f"report -> {out}  ({len(runs)} runs)")


DEMO = [
    ("000-baseline", "baseline", 63.1, None, "", []),
    ("001-coverage-playbook", "promoted", 69.0, 63.1,
     "A per-work-type coverage playbook in the system prompt reduces missed rubric sections",
     ["skills/verification-app/SKILL.md — add coverage checklist per work type"]),
    ("002-tone-calibration-prompt", "rejected", 68.2, 69.0,
     "Softer hedging language should reduce judge penalties on over-claims",
     ["skills/compliance-judgment/SKILL.md — hedging guidance"]),
    ("003-drafting-repair", "promoted", 72.8, 69.0,
     "Detect truncated/empty deliverable sections post-solve and redraft only those sections",
     ["scripts/drafting_repair.py — new post-solve section check"]),
    ("004-deliverable-landing-gate", "promoted", 79.2, 72.8,
     "The grader only reads exact top-level filenames; a deterministic post-solve move/rename step converts good-but-misplaced work into scored work",
     ["scripts/landing_gate.py — deterministic file placement",
      "plan_md_template.md — final phase calls the gate"]),
    ("005-deliverable-finish-guard", "rejected", 78.8, 79.2,
     "Guard against empty deliverables by re-running the final write if output is under a size floor",
     ["scripts/landing_gate.py — add finish guard"]),
    ("006-toolcall-json-repair", "rejected", 79.1, 79.2,
     "Repair provider-corrupted tool-call JSON to avoid dropped actions",
     ["scripts/toolcall_repair.py — new"]),
    ("007-matter-fidelity-audit", "promoted", 81.9, 79.2,
     "On long-context tasks with a distractor matter, detect drafts about the wrong dispute and force a redraft",
     ["skills/cross-document-verification/SKILL.md — matter audit step",
      "scripts/matter_audit.py — new"]),
    ("008-markup-loop-guard", "invalid", None, 81.9,
     "Break repeated-markup loops in table rendering",
     ["hooks/hooks.json — PreToolUse guard"]),
    ("009-matter-audit-allwork", "promoted", 83.3, 81.9,
     "Extend the matter audit + a small best-of-N vote to every work product, not only drafts",
     ["scripts/matter_audit.py — best-of-N vote", "skills/verification-app/SKILL.md"]),
]


def make_demo(root):
    import random
    random.seed(7)
    evolve = Path(root) / "evolve-demo"
    runs = evolve / "runs"
    runs.mkdir(parents=True)
    (evolve / "loop.json").write_text(json.dumps(
        {"template_name": "demo-template",
         "objective": {"min_delta": 1.0, "w_sparse": 0.02, "w_cost_per_mtok": 0.005}}))
    lineage, frontier = [], None
    for name, st, v, inc, hyp, changes in DEMO:
        d = runs / name
        d.mkdir()
        trials = []
        if v is not None:
            for k in range(3):
                trials.append({"trial": k, "valid": True,
                               "score": round(v + random.uniform(-0.9, 0.9), 1),
                               "all_pass": 0.0, "tokens_millions": round(1.4 + k * 0.1, 2)})
        dec = {"run": name, "status": st, "blended": v, "incumbent_blended": inc,
               "min_delta": 1.0, "trials": trials,
               "dense_std": 0.8 if trials else None,
               "reason": {"baseline": "frontier baseline measurement",
                          "promoted": f"blended {v} beats incumbent {inc} by >= min_delta 1.0",
                          "rejected": f"blended {v} vs incumbent {inc}: below min_delta 1.0",
                          "invalid": "diff outside mutation surface: ['hooks/hooks.json']"}[st]}
        json.dump(dec, open(d / "decision.json", "w"), indent=2)
        if hyp:
            json.dump({"hypothesis": hyp, "mechanism": name.split("-", 1)[1],
                       "changes": changes,
                       "fix_tasks": ["dev pooled criterion rate"],
                       "regression_tasks": ["no drop on already-passing tasks"],
                       "evidence": [f"runs/{lineage[-1]}/trials/trial-0/adapter.log"
                                    if lineage else "runs/000-baseline"]},
                      open(d / "pending_eval.json", "w"), indent=2)
        if st != "baseline":
            (d / "diff.stat").write_text(
                "\n".join(f" {c.split(' — ')[0]} | 30 ++++----" for c in changes)
                + f"\n {len(changes)} files changed, 60 insertions(+), 20 deletions(-)\n")
            (d / "diff.patch").write_text(
                "".join(f"--- a/{c.split(' — ')[0]}\n+++ b/{c.split(' — ')[0]}\n"
                        f"@@ -1,3 +1,6 @@\n+# {c.split(' — ')[-1]}\n" for c in changes))
        if st in ("baseline", "promoted"):
            frontier, lineage = v, lineage + [name]
    json.dump({"branch": "meta/frontier", "run": lineage[-1],
               "blended": frontier, "lineage": lineage},
              open(evolve / "frontier.json", "w"), indent=2)
    return evolve


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("evolve_dir", nargs="?", help="evolve/<template-name> dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--lang", choices=["zh", "en"], default="zh")
    ap.add_argument("--demo", action="store_true",
                    help="render a fabricated sample run instead of real data")
    args = ap.parse_args()
    if args.demo:
        evolve = make_demo(tempfile.mkdtemp(prefix="meta-harness-"))
    elif args.evolve_dir:
        evolve = args.evolve_dir
    else:
        ap.error("provide evolve_dir or --demo")
    render(evolve, args.out, args.lang)


if __name__ == "__main__":
    main()
