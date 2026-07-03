#!/usr/bin/env python3
"""meta_loop.py — the lab half of the meta-harness skill.

The proposer (a headless Claude session this script spawns) is creative;
this scaffold is strict about what counts: fork/branch mechanics, mutation
allowlist, leakage audit, packaging, N-trial evaluation, blended promotion
gate with incumbent recompute, and a full-raw trace store.

Subcommands: init | run | status | ship
Run from the Hamster working dir. See references/loop-config-format.md.
"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
GIT_ID = ["-c", "user.name=meta-harness", "-c", "user.email=meta-harness@local"]
RESERVED_TRIAL_KEYS = {"trial", "valid", "infra", "error"}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def die(msg, code=1):
    print(f"meta-harness: FATAL: {msg}", file=sys.stderr)
    sys.exit(code)


def load_json(path, default=None):
    """Tolerant read: missing file OR malformed JSON returns default."""
    p = Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def git(fork, *args, check=True, capture=True):
    cmd = ["git", "-C", str(fork)] + GIT_ID + list(args)
    r = subprocess.run(cmd, capture_output=capture, text=True)
    if check and r.returncode != 0:
        die(f"git {' '.join(args)} failed in {fork}:\n{(r.stderr or r.stdout or '').strip()}")
    return r


def glob_to_re(pattern):
    """Glob → regex with gitignore-style ** (matches whole path components)."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def path_matches(path, patterns):
    return any(glob_to_re(p).match(path) for p in patterns)


class Loop:
    def __init__(self, config_path):
        self.config_path = Path(config_path).resolve()
        if not self.config_path.exists():
            die(f"config not found: {self.config_path}")
        try:
            self.cfg = json.loads(self.config_path.read_text())
        except json.JSONDecodeError as e:
            die(f"config is not valid JSON ({self.config_path}): {e}")
        self.workdir = Path.cwd()
        self.fork = self._resolve(self.cfg["fork"])
        self.evolve_dir = self._resolve(self.cfg.get(
            "evolve_dir", str(self.config_path.parent)))
        self.runs_dir = self.evolve_dir / "runs"
        self.plugin_root = None
        self._validate_objective()

    def _validate_objective(self):
        obj = self.cfg.get("objective", {})
        sparse = obj.get("sparse_key", "all_pass")
        toks = obj.get("tokens_key", "tokens_millions")
        dense = obj.get("dense_key", "score")
        keys = {"score", sparse, toks}
        if (len(keys) != 3 or len({dense, sparse, toks}) != 3
                or (({dense} | keys) & RESERVED_TRIAL_KEYS)):
            die(f"objective keys must be pairwise distinct and outside "
                f"{sorted(RESERVED_TRIAL_KEYS)}: dense_key={dense!r}, "
                f"sparse_key={sparse!r}, tokens_key={toks!r} "
                "(dense values are always recorded under 'score')")
        if obj.get("min_delta", 1.0) <= 0:
            die("objective.min_delta must be > 0 (a zero margin promotes pure noise)")
        trials = max(1, int(self.cfg.get("eval", {}).get("trials", 3)))
        w_sparse = obj.get("w_sparse", 0.02)
        min_delta = obj.get("min_delta", 1.0)
        swing = w_sparse * 100.0 / trials
        if swing >= min_delta:
            die(f"objective.w_sparse={w_sparse} is too heavy: one lucky all-pass trial "
                f"adds w_sparse*100/trials = {swing:.2f} blended points, clearing "
                f"min_delta={min_delta} on its own — set w_sparse < "
                f"{min_delta * trials / 100.0:.3f}, or emit a continuous sparse rate "
                "instead of a 0/100 flag")

    def _resolve(self, p):
        p = Path(os.path.expanduser(str(p)))
        return p if p.is_absolute() else (self.workdir / p)

    # -- shared machinery ---------------------------------------------------

    def find_plugin_root(self):
        if self.plugin_root:
            return self.plugin_root
        hits = sorted(self.fork.glob("**/.claude-plugin/plugin.json"))
        hits = [h for h in hits if ".git" not in h.parts]
        if not hits:
            die(f"no .claude-plugin/plugin.json found under fork {self.fork}")
        self.plugin_root = hits[0].parent.parent
        return self.plugin_root

    def packaging_script(self, name):
        for cand in (self.workdir / ".claude/skills/hamster-packaging/scripts" / name,
                     SKILL_DIR.parent / "hamster-packaging/scripts" / name):
            if cand.exists():
                return cand
        die(f"hamster-packaging script not found: {name} "
            "(is hamster-packaging installed in .claude/skills/?)")

    def reset_fork(self):
        """Restore a pristine tree on meta/frontier, whatever a proposer left behind."""
        git(self.fork, "reset", "--hard")
        git(self.fork, "clean", "-fd")
        git(self.fork, "checkout", "meta/frontier")

    def state(self):
        return load_json(self.evolve_dir / "state.json",
                         {"next_iteration": 1, "consecutive_proposer_failures": 0})

    def save_state(self, st):
        save_json(self.evolve_dir / "state.json", st)

    def frontier(self):
        return load_json(self.evolve_dir / "frontier.json")

    def advance_frontier(self, run_name, blended):
        git(self.fork, "branch", "-f", "meta/frontier", "HEAD")
        fr = self.frontier() or {"branch": "meta/frontier", "lineage": []}
        fr.update(run=run_name, blended=round(blended, 3),
                  lineage=fr.get("lineage", []) + [run_name])
        save_json(self.evolve_dir / "frontier.json", fr)

    def blended_from_trials(self, trials):
        """Recompute the blended score from raw trials under CURRENT weights.

        A 'scored' trial is valid AND carries a numeric dense score; without
        at least one, no blended score exists (never fabricate 0.0)."""
        obj = self.cfg.get("objective", {})
        valid = [t for t in trials if t.get("valid")]
        scored = [t for t in valid if isinstance(t.get("score"), (int, float))]
        if not scored:
            return None, None, None
        def mean(key, pool):
            if not pool:
                return 0.0
            # a valid trial missing the key counts as 0 — selective reporting
            # must not inflate the mean
            return sum(t.get(key) if isinstance(t.get(key), (int, float)) else 0.0
                       for t in pool) / len(pool)
        dense = mean("score", scored)
        sparse = mean(obj.get("sparse_key", "all_pass"), valid)
        toks = mean(obj.get("tokens_key", "tokens_millions"), valid)
        blended = (dense + obj.get("w_sparse", 0.02) * sparse
                   - obj.get("w_cost_per_mtok", 0.005) * toks)
        var = sum((t["score"] - dense) ** 2 for t in scored) / len(scored)
        return blended, dense, var ** 0.5

    def incumbent_blended(self):
        fr = self.frontier()
        if not fr or not fr.get("run"):
            return None
        dec = load_json(self.runs_dir / fr["run"] / "decision.json")
        if not dec:
            return None
        blended, _, _ = self.blended_from_trials(dec.get("trials", []))
        return blended

    def in_place(self):
        """packaging.mode == 'none': evolve a project working tree directly —
        no template packaging; the candidate IS the fork checkout."""
        return self.cfg.get("packaging", {}).get("mode") == "none"

    def candidate_dir(self, run_dir):
        return self.fork if self.in_place() else run_dir / "candidate-template"

    def package_candidate(self, out_dir, description):
        if self.in_place():
            return True, ""
        if out_dir.exists():
            shutil.rmtree(out_dir)
        script = self.packaging_script("package_template.py")
        extra = [str(a) for a in self.cfg.get("packaging", {}).get("extra_args", [])]
        r = subprocess.run(
            ["python3", str(script), "--fork", str(self.fork),
             "--output", str(out_dir), "--description", description] + extra,
            capture_output=True, text=True)
        summary = load_json(self.fork / ".hamster/package_summary.json", {}) or {}
        warnings = summary.get("warnings", [])
        if r.returncode != 0:
            return False, f"package_template.py exit {r.returncode}: " \
                          f"{(r.stderr or r.stdout or '').strip()[:500]}"
        if self.cfg.get("packaging", {}).get("strict_warnings", True) and warnings:
            return False, f"packager warnings under strict_warnings: {warnings}"
        return True, ""

    def run_trials(self, run_dir, candidate_dir):
        ev = self.cfg["eval"]
        trials = []
        for k in range(int(ev.get("trials", 3))):
            tdir = run_dir / "trials" / f"trial-{k}"
            tdir.mkdir(parents=True, exist_ok=True)
            attempts = 1 + int(ev.get("retry_infra_failures", 1))
            rec = {"trial": k, "valid": False}
            for attempt in range(attempts):
                env = dict(os.environ,
                           CANDIDATE_TEMPLATE_DIR=str(candidate_dir),
                           FORK_DIR=str(self.fork),
                           RUN_DIR=str(run_dir),
                           TRIAL_INDEX=str(k),
                           LOOP_CONFIG=str(self.config_path))
                log = tdir / "adapter.log"
                with open(log, "a") as lf:
                    lf.write(f"--- attempt {attempt} @ {now_iso()} ---\n")
                    lf.flush()
                    proc = subprocess.Popen(
                        [str(c) for c in ev["command"]],
                        cwd=self.workdir, env=env, stdout=subprocess.PIPE,
                        stderr=lf, text=True, start_new_session=True)
                    try:
                        stdout, _ = proc.communicate(
                            timeout=60 * int(ev.get("trial_timeout_minutes", 45)))
                    except subprocess.TimeoutExpired:
                        try:
                            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        stdout, _ = proc.communicate()
                        (tdir / "stdout.log").write_text(
                            (stdout or "")
                            + f"\n--- killed: timeout at attempt {attempt} ---\n")
                        rec["infra"] = f"timeout attempt {attempt}"
                        continue
                (tdir / "stdout.log").write_text(stdout or "")
                if proc.returncode == 2:
                    rec["infra"] = f"adapter infra exit attempt {attempt}"
                    continue
                if proc.returncode != 0:
                    rec["error"] = f"adapter exit {proc.returncode}"
                    break
                last = (stdout or "").strip().splitlines()
                try:
                    payload = json.loads(last[-1]) if last else None
                except json.JSONDecodeError:
                    payload = None
                if not isinstance(payload, dict):
                    rec["error"] = "adapter stdout last line is not a JSON object"
                    break
                dense_key = self.cfg["objective"].get("dense_key", "score")
                if not isinstance(payload.get(dense_key), (int, float)):
                    rec["error"] = f"adapter output missing numeric '{dense_key}'"
                    break
                save_json(tdir / "score.json", payload)
                sparse_key = self.cfg["objective"].get("sparse_key", "all_pass")
                tokens_key = self.cfg["objective"].get("tokens_key", "tokens_millions")
                rec.pop("infra", None)
                rec.update({"valid": True, "score": payload.get(dense_key)})
                rec[sparse_key] = payload.get(sparse_key)
                rec[tokens_key] = payload.get(tokens_key)
                break
            trials.append(rec)
            if rec.get("error"):
                break  # hard error disqualifies the candidate — don't burn the rest
        return trials

    def decide(self, run_name, run_dir, trials, validation, allow_baseline=False):
        obj = self.cfg["objective"]
        dec = {"run": run_name, "weights": {"w_sparse": obj.get("w_sparse", 0.02),
                                            "w_cost_per_mtok": obj.get("w_cost_per_mtok", 0.005)},
               "min_delta": obj.get("min_delta", 1.0), "trials": trials,
               "validation": validation, "decided_at": now_iso()}
        hard_error = next((t for t in trials if t.get("error")), None)
        valid_n = sum(1 for t in trials if t.get("valid"))
        if hard_error:
            dec.update(status="invalid",
                       reason=f"candidate failure in trial {hard_error['trial']}: {hard_error['error']}")
            return dec
        if valid_n < int(self.cfg["eval"].get("min_valid_trials", 2)):
            dec.update(status="infra_failed",
                       reason=f"only {valid_n} valid trial(s); unmeasurable")
            return dec
        blended, dense, std = self.blended_from_trials(trials)
        if blended is None:
            dec.update(status="infra_failed", reason="no scored trials")
            return dec
        incumbent = self.incumbent_blended()
        dec.update(blended=round(blended, 3), dense_mean=round(dense, 3),
                   dense_std=round(std, 3),
                   incumbent_blended=None if incumbent is None else round(incumbent, 3))
        if incumbent is None:
            if allow_baseline:
                dec.update(status="baseline", reason="frontier baseline measurement")
            else:
                dec.update(status="infra_failed",
                           reason="no measured incumbent (frontier unmeasured or its "
                                  "decision.json unreadable) — run `init` to measure run 000")
        elif blended >= incumbent + obj.get("min_delta", 1.0):
            dec.update(status="promoted",
                       reason=f"blended {blended:.2f} beats incumbent "
                              f"{incumbent:.2f} by >= min_delta {obj.get('min_delta', 1.0)}")
        else:
            dec.update(status="rejected",
                       reason=f"blended {blended:.2f} vs incumbent {incumbent:.2f}: "
                              f"below min_delta {obj.get('min_delta', 1.0)}")
        return dec

    # -- init ----------------------------------------------------------------

    def apply_template_into_fork(self, template_root):
        """Apply a packaged template's diff onto the fork so the fork IS the
        template. Mirrors joharnessburg's apply_template.py semantics:
        _override replaces, everything else is additive-only (collisions skip)."""
        t = Path(os.path.expanduser(str(template_root)))
        proot = self.find_plugin_root()
        skills = t / "skills"
        if skills.exists():
            delete_file = skills / "_delete"
            if delete_file.exists():
                for line in delete_file.read_text().splitlines():
                    name = line.split("#", 1)[0].strip()
                    if name and (proot / "skills" / name).exists():
                        shutil.rmtree(proot / "skills" / name)
            for d in sorted(skills.iterdir()):
                if not d.is_dir():
                    continue
                if d.name == "_override":
                    for ov in sorted(d.iterdir()):
                        dst = proot / "skills" / ov.name
                        if dst.exists():
                            shutil.rmtree(dst)
                        shutil.copytree(ov, dst)
                else:
                    dst = proot / "skills" / d.name
                    if dst.exists():
                        print(f"WARN: additive skill {d.name} would shadow an "
                              "existing skill; skipping (matches apply_template.py)")
                        continue
                    shutil.copytree(d, dst)
        for sub in ("scripts", "commands", "agents"):
            src = t / sub
            if src.exists():
                for f in sorted(src.rglob("*")):
                    if f.is_file():
                        dst = proot / sub / f.relative_to(src)
                        if dst.exists():
                            print(f"WARN: skipping collision {dst.relative_to(self.fork)} "
                                  "(additive-only dir, matches apply_template.py)")
                            continue
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, dst)
        for root_file in ("plan_md_template.md", "claude_addon.md"):
            if (t / root_file).exists():
                shutil.copy2(t / root_file, self.fork / root_file)
        tj = load_json(t / "template.json", {}) or {}
        if tj.get("evolution"):
            save_json(self.fork / "evolution.json", tj["evolution"])
        wf = t / "workflows"
        if wf.exists():
            (self.fork / ".claude/workflows").mkdir(parents=True, exist_ok=True)
            for f in sorted(wf.iterdir()):
                if f.is_file():
                    shutil.copy2(f, self.fork / ".claude/workflows" / f.name)
        return tj

    def audit_baseline_leakage(self, candidate_dir):
        """Grep the baseline's shippable content for forbidden identifiers —
        a frontier that already contains held-out material poisons every later
        diff and defeats the per-iteration audit."""
        if self.in_place():
            files = [self.fork / n for n in
                     git(self.fork, "ls-files").stdout.splitlines() if n]
        else:
            files = [p for p in candidate_dir.rglob("*") if p.is_file()]
        hits = []
        for f in files:
            try:
                text = f.read_text(errors="strict")
            except (UnicodeDecodeError, OSError):
                continue  # binary or unreadable
            hits += self.leakage_hits({str(f): text})
            if len(hits) >= 3:
                break
        return hits

    def run_baseline(self):
        run_dir = self.runs_dir / "000-baseline"
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        ok, why = self.package_candidate(run_dir / "candidate-template",
                                         "meta-harness baseline")
        if not ok:
            die(f"baseline packaging failed: {why}")
        leak = self.audit_baseline_leakage(self.candidate_dir(run_dir))
        if leak:
            die(f"baseline contains forbidden held-out identifiers: {leak[:3]} — "
                "clean the template or fix the leakage list before init")
        trials = self.run_trials(run_dir, self.candidate_dir(run_dir))
        dec = self.decide("000-baseline", run_dir, trials,
                          {"pending_eval": True, "allowlist": True,
                           "leakage": True,
                           "packaging": None if self.in_place() else True},
                          allow_baseline=True)
        save_json(run_dir / "decision.json", dec)
        if dec["status"] != "baseline":
            die(f"baseline eval unusable ({dec['status']}): {dec['reason']} — "
                "fix the adapter before starting the loop")
        blended, _, std = self.blended_from_trials(trials)
        save_json(self.evolve_dir / "frontier.json",
                  {"branch": "meta/frontier", "run": "000-baseline",
                   "blended": round(blended, 3), "lineage": ["000-baseline"]})
        n = max(1, len([t for t in trials if t.get("valid")]))
        print(f"baseline blended {blended:.2f} (dense std {std:.2f}) — "
              f"suggested min_delta >= {max(0.5, std / (n ** 0.5)):.1f}")

    def cmd_init(self, args):
        if self.in_place() and not (self.fork / ".git").exists():
            die(f"in-place mode requires {self.fork} to be a git repo — "
                "git init it (and write a .gitignore covering secrets/large "
                "runtime dirs) before init")
        initialized = (self.evolve_dir / "state.json").exists()
        fr = self.frontier()
        if initialized and not args.force:
            if fr and not fr.get("run"):
                print("evolve dir exists with no measured baseline — "
                      "running the baseline eval only (state untouched)")
                self.run_baseline()
                return
            die(f"{self.evolve_dir} is already initialized; rerun with --force "
                "to reset loop state (runs/ history is never deleted)")
        if not self.fork.exists():
            script = self.packaging_script("scaffold_fork.py")
            r = subprocess.run(
                ["python3", str(script), "--name", self.fork.name,
                 "--joharnessburg-path",
                 os.path.expanduser(self.cfg["joharnessburg_path"]),
                 "--forks-root", str(self.fork.parent)],
                capture_output=True, text=True)
            if r.returncode != 0:
                die(f"scaffold_fork.py failed:\n{(r.stderr or r.stdout).strip()}")
            print(f"forked -> {self.fork}")
        template_root = args.template or self.cfg.get("template_root")
        tj = {}
        if template_root:
            tj = self.apply_template_into_fork(template_root)
            print(f"applied template {tj.get('name', '?')} v{tj.get('version', '?')} onto fork")
        git(self.fork, "add", "-A")
        if git(self.fork, "status", "--porcelain").stdout.strip():
            git(self.fork, "commit", "-m",
                f"meta-harness baseline: {tj.get('name', self.cfg['template_name'])} "
                f"v{tj.get('version', '?')}")
        git(self.fork, "checkout", "-B", "meta/frontier")
        self.evolve_dir.mkdir(parents=True, exist_ok=True)
        self.save_state({"next_iteration": 1, "consecutive_proposer_failures": 0})
        save_json(self.evolve_dir / "frontier.json",
                  {"branch": "meta/frontier", "run": None, "blended": None, "lineage": []})
        if args.skip_baseline_eval:
            print("init done (baseline eval skipped — rerun `init` later to "
                  "measure run 000; the loop refuses to score candidates against "
                  "an unmeasured frontier)")
            return
        self.run_baseline()

    # -- run -----------------------------------------------------------------

    def render_prompt(self, iteration):
        tmpl = (SKILL_DIR / "references/proposer-protocol.md").read_text()
        parts = tmpl.split("\n---\n", 1)
        body = parts[1] if len(parts) == 2 else tmpl
        fr = self.frontier() or {}
        subs = {"TEMPLATE_NAME": self.cfg["template_name"],
                "ITERATION": f"{iteration:03d}",
                "FORK": str(self.fork),
                "RUNS_DIR": str(self.runs_dir),
                "FRONTIER_SUMMARY": json.dumps(fr, ensure_ascii=False),
                "ALLOWLIST": ", ".join(self.cfg.get("mutation_allowlist", [])),
                "BLOCKLIST": ", ".join(self.cfg.get("mutation_blocklist", [])),
                # deliberately a pointer, not the literals: forbidden strings in
                # the prompt would self-trigger the audit under verbose logging
                "LOOP_CONFIG": str(self.config_path),
                "PENDING_PATH": str(self.evolve_dir / "pending_eval.json")}
        for k, v in subs.items():
            body = body.replace("{" + k + "}", v)
        return body

    def spawn_proposer(self, prompt, log_path):
        cmd = [str(c) for c in self.cfg["proposer"]["command"]] + [prompt]
        timeout = 60 * int(self.cfg["proposer"].get("timeout_minutes", 120))
        with open(log_path, "w") as lf:
            proc = subprocess.Popen(cmd, cwd=self.workdir, stdout=lf,
                                    stderr=subprocess.STDOUT,
                                    start_new_session=True)
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
                return "timeout"
        return "ok" if proc.returncode == 0 else f"exit {proc.returncode}"

    def leakage_hits(self, texts):
        pats = self.cfg.get("leakage", {}).get("forbidden_patterns", [])
        hits = []
        for pat in pats:
            rx = re.compile(re.escape(pat), re.IGNORECASE)
            for name, text in texts.items():
                if rx.search(text):
                    hits.append(f"{pat} in {name}")
        return hits

    def next_iteration_number(self, st):
        existing = []
        if self.runs_dir.exists():
            for d in self.runs_dir.iterdir():
                m = re.match(r"(\d{3})-", d.name)
                if m:
                    existing.append(int(m.group(1)))
        return max([st["next_iteration"]] + [e + 1 for e in existing])

    def _finish_iteration(self, st, it, run_dir, decision, proposer_failed=False):
        save_json(run_dir / "decision.json", decision)
        self.reset_fork()
        st["consecutive_proposer_failures"] = \
            st["consecutive_proposer_failures"] + 1 if proposer_failed else 0
        st["next_iteration"] = it + 1
        self.save_state(st)
        print(f"[{it:03d}] {decision['status']}: {decision.get('reason', '')[:100]}")

    def _one_iteration(self, it, st):
        git(self.fork, "checkout", "-B", f"meta/cand-{it:03d}", "meta/frontier")
        pending_path = self.evolve_dir / "pending_eval.json"
        if pending_path.exists():
            pending_path.unlink()
        run_dir = self.runs_dir / f"{it:03d}-pending"
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        print(f"[{it:03d}] proposer session starting...")
        outcome = self.spawn_proposer(self.render_prompt(it),
                                      run_dir / "proposer.log")
        pending = load_json(pending_path)
        if outcome != "ok" or not isinstance(pending, dict):
            why = (f"proposer {outcome}; pending_eval.json "
                   + ("missing or malformed" if not isinstance(pending, dict) else "present"))
            self._finish_iteration(st, it, run_dir,
                                   {"run": run_dir.name, "status": "invalid",
                                    "reason": why, "decided_at": now_iso()},
                                   proposer_failed=True)
            return
        slug = re.sub(r"[^a-z0-9-]", "-",
                      str(pending.get("mechanism", "unnamed")).lower())[:48]
        named_dir = self.runs_dir / f"{it:03d}-{slug}"
        if named_dir.exists():
            shutil.rmtree(named_dir)
        run_dir.rename(named_dir)
        run_dir = named_dir
        run_name = run_dir.name
        shutil.move(str(pending_path), run_dir / "pending_eval.json")
        meta = {"iteration": it, "branch": f"meta/cand-{it:03d}",
                "started_at": now_iso()}
        if slug == "no-op":
            self._finish_iteration(st, it, run_dir,
                                   {"run": run_name, "status": "no_op",
                                    "reason": pending.get("hypothesis", ""),
                                    "decided_at": now_iso()})
            return
        git(self.fork, "add", "-A")
        if not git(self.fork, "status", "--porcelain").stdout.strip():
            self._finish_iteration(st, it, run_dir,
                                   {"run": run_name, "status": "invalid",
                                    "reason": "empty diff (mechanism declared but "
                                              "nothing changed)",
                                    "decided_at": now_iso()})
            return
        git(self.fork, "commit", "-m", f"cand-{it:03d}: {slug}")
        meta["commit"] = git(self.fork, "rev-parse", "HEAD").stdout.strip()
        diff = git(self.fork, "diff", "--no-renames", "meta/frontier..HEAD").stdout
        (run_dir / "diff.patch").write_text(diff)
        (run_dir / "diff.stat").write_text(
            git(self.fork, "diff", "--no-renames", "--stat",
                "meta/frontier..HEAD").stdout)
        # --no-renames: a rename must audit as delete+add, or a blocklisted
        # file could be relocated onto the allowlisted surface unseen
        changed = [l.strip() for l in git(
            self.fork, "diff", "--no-renames", "--name-only", "meta/frontier..HEAD"
        ).stdout.splitlines() if l.strip()]
        validation = {"pending_eval": True}
        allow = self.cfg.get("mutation_allowlist", ["**"])
        block = self.cfg.get("mutation_blocklist", [])
        offside = [p for p in changed
                   if path_matches(p, block) or not path_matches(p, allow)]
        validation["allowlist"] = not offside
        # audit added lines only: a forbidden literal already sitting in
        # frontier code must not false-reject an innocent nearby edit via
        # diff context lines (run 000's audit guarantees the frontier is clean)
        added = "\n".join(l[1:] for l in diff.splitlines()
                          if l.startswith("+") and not l.startswith("+++"))
        hits = self.leakage_hits({
            "diff.patch (added lines)": added,
            "proposer.log": (run_dir / "proposer.log").read_text(errors="replace"),
            "pending_eval.json": json.dumps(pending, ensure_ascii=False)})
        validation["leakage"] = not hits
        status_reason = None
        if offside:
            status_reason = f"diff outside mutation surface: {offside[:5]}"
        elif hits:
            status_reason = f"leakage audit hit: {hits[:3]}"
        else:
            ok, why = self.package_candidate(
                run_dir / "candidate-template",
                self.cfg.get("packaging", {}).get("description",
                                                  "meta-harness candidate"))
            # in-place mode has no packaging gate — record null, not a pass
            validation["packaging"] = None if self.in_place() else ok
            if not ok:
                status_reason = why
        if status_reason:
            self._finish_iteration(st, it, run_dir,
                                   {"run": run_name, "status": "invalid",
                                    "reason": status_reason,
                                    "validation": validation,
                                    "decided_at": now_iso()})
            return
        print(f"[{it:03d}] {slug}: evaluating "
              f"{self.cfg['eval'].get('trials', 3)} trials...")
        trials = self.run_trials(run_dir, self.candidate_dir(run_dir))
        dec = self.decide(run_name, run_dir, trials, validation)
        if dec["status"] in ("promoted", "baseline"):
            self.advance_frontier(run_name, dec["blended"])
        meta["finished_at"] = now_iso()
        save_json(run_dir / "meta.json", meta)
        self._finish_iteration(st, it, run_dir, dec)

    def _sweep_orphans(self):
        """Record any run dir a kill left without a decision, so resume never
        silently skips an iteration."""
        if not self.runs_dir.exists():
            return
        for d in sorted(self.runs_dir.iterdir()):
            if d.is_dir() and re.match(r"\d{3}-", d.name) \
                    and not (d / "decision.json").exists():
                save_json(d / "decision.json",
                          {"run": d.name, "status": "infra_failed",
                           "reason": "interrupted before a decision was recorded",
                           "decided_at": now_iso()})
                print(f"recorded orphan run {d.name} as infra_failed")

    def cmd_run(self, args):
        if self.incumbent_blended() is None:
            die("frontier is unmeasured — run `init` (without --skip-baseline-eval) "
                "to measure run 000 first; the loop refuses to score candidates "
                "against an unmeasured frontier")
        self._sweep_orphans()
        for _ in range(args.iterations):
            st = self.state()
            stop_after = int(self.cfg["proposer"].get("consecutive_failures_stop", 2))
            if st["consecutive_proposer_failures"] >= stop_after:
                die(f"stopping: {st['consecutive_proposer_failures']} consecutive "
                    "proposer failures (clean-stop rule)")
            it = self.next_iteration_number(st)
            if git(self.fork, "status", "--porcelain").stdout.strip():
                die(f"fork has uncommitted changes — resolve before running: {self.fork}")
            try:
                self._one_iteration(it, st)
            except KeyboardInterrupt:
                print("\ninterrupted — resetting fork to meta/frontier "
                      "(the half-done run is recorded on next `run`)", file=sys.stderr)
                self.reset_fork()
                raise
            except Exception as e:  # crash-safety: record, reset, advance
                crash_dir = next(iter(sorted(self.runs_dir.glob(f"{it:03d}-*"))),
                                 self.runs_dir / f"{it:03d}-crash")
                crash_dir.mkdir(parents=True, exist_ok=True)
                save_json(crash_dir / "decision.json",
                          {"run": crash_dir.name, "status": "infra_failed",
                           "reason": f"loop exception: {type(e).__name__}: {e}",
                           "decided_at": now_iso()})
                self.reset_fork()
                st["next_iteration"] = it + 1
                self.save_state(st)
                print(f"[{it:03d}] loop exception recorded: {e}", file=sys.stderr)

    # -- status / ship -------------------------------------------------------

    def cmd_status(self, args):
        fr = self.frontier() or {}
        print(f"frontier: {fr.get('run')} blended={fr.get('blended')} "
              f"lineage={' -> '.join(fr.get('lineage', []))}")
        for d in sorted(self.runs_dir.iterdir()) if self.runs_dir.exists() else []:
            dec = load_json(d / "decision.json", {}) or {}
            print(f"  {d.name:40s} {dec.get('status', '?'):12s} "
                  f"blended={dec.get('blended')} {dec.get('reason', '')[:60]}")

    def cmd_ship(self, args):
        if self.in_place():
            die("in-place mode has nothing to package: the optimized state IS "
                "the meta/frontier branch of the project — merge or tag it there")
        changelog = self.evolve_dir / "CHANGELOG.md"
        if not changelog.exists() and not args.allow_missing_changelog:
            die(f"no CHANGELOG.md in {self.evolve_dir} — draft it from runs/ "
                "pending_eval.json + decision.json (evolution changelog format); "
                "it is the owner gate's evidence chain. Override with "
                "--allow-missing-changelog if you really must")
        out = self._resolve(args.output)
        git(self.fork, "checkout", "meta/frontier")
        ok, why = self.package_candidate(out, f"{self.cfg['template_name']} "
                                              f"v{args.version} (meta-harness evolved)")
        if not ok:
            die(f"ship packaging failed: {why}")
        tj_path = out / "template.json"
        tj = load_json(tj_path) or {}
        tj["version"] = args.version
        save_json(tj_path, tj)
        apply_sh = out / "apply.sh"
        if apply_sh.is_symlink():
            target = apply_sh.resolve()
            apply_sh.unlink()
            shutil.copy2(target, apply_sh)
        if changelog.exists():
            shutil.copy2(changelog, out / "CHANGELOG.md")
        else:
            print("WARN: shipping without CHANGELOG.md — the owner gate loses "
                  "its evidence chain")
        print(f"shipped candidate at {out} (v{args.version}) — owner sign-off is the gate")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init", help="fork + apply template + baseline eval")
    p_init.add_argument("--config", required=True)
    p_init.add_argument("--template", help="template dir to apply onto the fork "
                                           "(default: config template_root)")
    p_init.add_argument("--joharnessburg-path", help="overrides config if given")
    p_init.add_argument("--skip-baseline-eval", action="store_true")
    p_init.add_argument("--force", action="store_true",
                        help="reset loop state on an already-initialized evolve dir")
    p_run = sub.add_parser("run", help="run N loop iterations")
    p_run.add_argument("--config", required=True)
    p_run.add_argument("--iterations", type=int, default=1)
    p_st = sub.add_parser("status")
    p_st.add_argument("--config", required=True)
    p_ship = sub.add_parser("ship", help="package frontier for owner review")
    p_ship.add_argument("--config", required=True)
    p_ship.add_argument("--version", required=True)
    p_ship.add_argument("--output", required=True)
    p_ship.add_argument("--allow-missing-changelog", action="store_true",
                        help="ship without the evidence-chain changelog (discouraged)")
    args = ap.parse_args()
    loop = Loop(args.config)
    if getattr(args, "joharnessburg_path", None):
        loop.cfg["joharnessburg_path"] = args.joharnessburg_path
    getattr(loop, f"cmd_{args.cmd}")(args)


if __name__ == "__main__":
    main()
