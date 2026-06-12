#!/usr/bin/env python3
"""Translate a Hamster fork into a John template diff.

Reads a fork at <fork> (which has .hamster-base-commit recording the commit
the fork was created from), computes the diff between base and current state,
and writes the canonical John template folder layout to <output>.

Usage:
  python3 package_template.py --fork forks/<name>/ --output templates/<name>/
                              [--description "<text>"]
                              [--apply-script <path>]
                              [--smoke-test]

Output structure (per joharnessburg/templates/README.md):
  <output>/
    template.json
    apply.sh (symlink to canonical apply.sh)
    skills/<new-name>/ ... (additive)
    skills/_override/<core-name>/ ... (full skill dir copied)
    skills/_delete (if applicable)
    scripts/<new-file>.py ... (additive only)
    commands/<new-file>.md ... (additive only)
    agents/<new-file>.md ... (additive only)
    workflows/<new-file>.js ... (saved dynamic workflows, from the fork's .claude/workflows/)
    plan_md_template.md (if present at fork root)
    claude_addon.md (if present at fork root)

Build provenance is written to <fork>/.hamster/package_summary.json (the fork is
the builder's scratch), NOT into the shipped template — so built templates carry
no dev-history or dev-machine paths. The fork's John copy may use either the flat
(<=v0.1.12) or marketplace (v0.1.14+, plugins/<name>/) layout; paths are resolved
accordingly. apply.sh defaults to <plugin-root>/templates/apply.sh.

Exit codes:
  0 — success (warnings may have been emitted, see package_summary.json)
  1 — fatal error (couldn't read fork, couldn't write output, etc.)
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


# John's load-bearing core skills (annotated copy — the authoritative set
# lives in joharnessburg's scripts/apply_template.py as CORE_SKILLS; keep in
# sync). Deleting one of these from a template is allowed but must carry a
# same-line `# reason` in skills/_delete, or apply_template.py nags loudly.
JOHN_CORE_SKILLS = {
    "using-john",
    "ralph-loop",
    "event-log-and-reducer",
    "workspace-discipline",
    "context-management",
    "subagent-dispatch",
    "skill-evolution",
}


def err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def warn(msg: str) -> None:
    print(f"WARN: {msg}", file=sys.stderr)


def info(msg: str) -> None:
    print(msg, file=sys.stderr)


def run_git(args: list, cwd: Path) -> str:
    """Run a git command in cwd and return stdout. Raises on nonzero exit."""
    result = subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {result.stderr.strip()}"
        )
    return result.stdout


def resolve_plugin_root(fork: Path) -> tuple[Path | None, Path | None]:
    """Locate the plugin dir inside a fork, layout-agnostically.

    Returns (plugin_root, manifest_path). `plugin_root` is the dir that holds
    skills/, scripts/, commands/, agents/, templates/ — i.e. the parent of the
    `.claude-plugin/` that carries a plugin.json with a "version".

    Handles both the pre-v0.1.14 flat layout (plugin.json at <fork>/.claude-plugin/)
    and the v0.1.14+ marketplace layout (<fork>/plugins/<name>/.claude-plugin/),
    where the top-level .claude-plugin/ holds only marketplace.json.
    """
    flat = fork / ".claude-plugin" / "plugin.json"
    if flat.is_file():
        return fork, flat
    for manifest in sorted(fork.glob("plugins/*/.claude-plugin/plugin.json")):
        return manifest.parent.parent, manifest
    return None, None


def get_joharnessburg_version(manifest: Path | None) -> str:
    """Read version from a resolved plugin.json. Returns 'unknown' if absent."""
    if manifest is None or not manifest.is_file():
        return "unknown"
    try:
        return json.loads(manifest.read_text(encoding="utf-8")).get("version", "unknown")
    except (json.JSONDecodeError, OSError):
        return "unknown"


def strip_plugin_prefix(path: str, rel_prefix: str) -> str | None:
    """Drop the leading `plugins/<name>/` prefix from a repo-relative diff path.

    Returns the plugin-relative remainder, or None if `path` lies outside the
    plugin subtree (e.g. a workspace file, when rel_prefix is non-empty).
    """
    if not rel_prefix:
        return path
    pfx = rel_prefix + "/"
    if path.startswith(pfx):
        return path[len(pfx):]
    return None


def classify_change(path: str, base_skills: set, rel_prefix: str) -> dict:
    """Classify a changed (repo-relative) path. Returns dict with 'kind' + fields.

    kind ∈ {"override_skill", "add_skill", "additive", "template_root", "evolution_declaration", "internal", "workflow", "warn"}
    Note: deletion of a whole skill dir is detected later, not here.
    """
    # Template-root files live at the fork root, outside the plugin subtree.
    if path in ("plan_md_template.md", "claude_addon.md"):
        return {"kind": "template_root", "filename": path}

    # The evolution declaration is folded into the generated template.json
    # later in main(); the diff itself needs no translation.
    if path == "evolution.json":
        return {"kind": "evolution_declaration", "filename": path}

    # The packager's own provenance dir inside the fork — never template
    # content; repeated packaging runs would otherwise warn about it forever.
    if path.startswith(".hamster/"):
        return {"kind": "internal", "filename": path}

    # Saved dynamic workflows: Claude Code stores them in the project's
    # .claude/workflows/. In a fork that's <fork>/.claude/workflows/<name>.js —
    # at the fork root, outside the plugin subtree. They ride in the template's
    # workflows/ dir; /john:init installs them into the user's .claude/workflows/.
    wf_prefix = ".claude/workflows/"
    if path.startswith(wf_prefix):
        remainder = path[len(wf_prefix):]
        if remainder and "/" not in remainder:
            return {"kind": "workflow", "filename": remainder}
        # Only flat .js files in .claude/workflows/ are supported.
        return {"kind": "warn", "path": path}

    inner = strip_plugin_prefix(path, rel_prefix)
    if inner is None:
        return {"kind": "warn", "path": path}
    parts = inner.split("/")

    if parts[0] == "skills" and len(parts) >= 3:
        skill_name = parts[1]
        if skill_name in base_skills:
            return {"kind": "override_skill", "skill": skill_name}
        return {"kind": "add_skill", "skill": skill_name}

    if parts[0] in ("scripts", "commands", "agents") and len(parts) >= 2:
        return {"kind": "additive", "subdir": parts[0], "path": inner}

    return {"kind": "warn", "path": path}


def inventory_base_skills(fork: Path, base_commit: str, rel_prefix: str) -> set:
    """Return the set of skill dir names that existed at base (layout-agnostic)."""
    pfx = f"{rel_prefix}/skills/" if rel_prefix else "skills/"
    out = run_git(["ls-tree", "--name-only", base_commit, pfx], cwd=fork)
    skills = set()
    for line in out.splitlines():
        if line.startswith(pfx):
            name = line[len(pfx):].split("/")[0]
            if name:
                skills.add(name)
    return skills


def collect_changes(fork: Path, base_commit: str) -> list:
    """Get all changes between base and current working tree.

    Returns list of (status, path) tuples. Includes untracked files as ('A', path).
    Filters out Hamster-internal files (.hamster-*) which exist in the fork
    for provenance but aren't part of the template diff.
    """
    diff_out = run_git(["diff", "--name-status", base_commit], cwd=fork)
    untracked_out = run_git(
        ["ls-files", "--others", "--exclude-standard"], cwd=fork
    )

    def is_internal(path: str) -> bool:
        # Filter Hamster's own provenance files at the fork root
        return path.startswith(".hamster-")

    changes = []
    for line in diff_out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 2 and not is_internal(parts[1]):
            changes.append((parts[0], parts[1]))
    for path in untracked_out.splitlines():
        path = path.strip()
        if path and not is_internal(path):
            changes.append(("A", path))
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--fork", required=True, type=Path,
                        help="Path to the Hamster fork dir")
    parser.add_argument("--output", required=True, type=Path,
                        help="Path to write the template folder")
    parser.add_argument("--description", default=None,
                        help="Description for template.json")
    parser.add_argument("--apply-script", default=None, type=Path,
                        help="Path to apply.sh (default: <fork>/templates/apply.sh)")
    parser.add_argument("--smoke-test", action="store_true",
                        help="After packaging, run apply.sh --help to verify executability")
    args = parser.parse_args()

    fork: Path = args.fork.resolve()
    output: Path = args.output.resolve()

    if not fork.exists() or not fork.is_dir():
        err(f"fork does not exist or isn't a dir: {fork}")
        return 1
    if not (fork / ".git").exists():
        err(f"fork is not a git repo: {fork}")
        return 1

    base_commit_file = fork / ".hamster-base-commit"
    if not base_commit_file.exists():
        err(f"missing .hamster-base-commit in fork: {fork}")
        err("This file should have been created by scaffold_fork.py")
        return 1
    base_commit = base_commit_file.read_text().strip()

    plugin_root, manifest = resolve_plugin_root(fork)
    if plugin_root is None:
        err(f"could not find a plugin (.claude-plugin/plugin.json) inside fork: {fork}")
        err("Expected either <fork>/.claude-plugin/plugin.json (flat) or "
            "<fork>/plugins/<name>/.claude-plugin/plugin.json (marketplace layout).")
        return 1
    rel_prefix = plugin_root.relative_to(fork).as_posix()
    rel_prefix = "" if rel_prefix == "." else rel_prefix

    if output.exists():
        err(f"output dir already exists: {output}")
        err("Refusing to overwrite. Delete it first if you want a fresh build.")
        return 1

    apply_script = args.apply_script
    if apply_script is None:
        apply_script = plugin_root / "templates" / "apply.sh"
    apply_script = apply_script.resolve()
    if not apply_script.exists():
        err(f"apply.sh not found at: {apply_script}")
        err("Pass --apply-script if it's elsewhere.")
        return 1

    try:
        base_skills = inventory_base_skills(fork, base_commit, rel_prefix)
        changes = collect_changes(fork, base_commit)
    except RuntimeError as e:
        err(str(e))
        return 1

    summary = {
        "base_commit": base_commit,
        "packaged_at": datetime.now(timezone.utc).isoformat(),
        "requires_john": f">={get_joharnessburg_version(manifest)}",
        "plugin_root": rel_prefix or ".",
        "translations": [],
        "warnings": [],
    }

    overridden_skills = {}    # skill_name -> True (modified, dir still exists)
    deleted_skills = set()    # skill_name (dir deleted)
    added_skills = {}         # skill_name -> True (new dir)
    additive_files = []       # list of paths
    template_root_files = []  # list of filenames
    workflow_files = []       # saved-workflow basenames (from .claude/workflows/)

    for status, path in changes:
        c = classify_change(path, base_skills, rel_prefix)
        kind = c["kind"]

        if kind == "override_skill":
            skill = c["skill"]
            skill_dir = plugin_root / "skills" / skill
            if not skill_dir.exists():
                deleted_skills.add(skill)
            else:
                overridden_skills[skill] = True
        elif kind == "add_skill":
            added_skills[c["skill"]] = True
        elif kind == "additive":
            if status == "D":
                summary["warnings"].append({
                    "path": path,
                    "reason": ("Templates don't support deleting platform "
                               "files under scripts/, commands/, agents/. "
                               "Revert the deletion or surface as a core-John change.")
                })
                warn(f"deletion of {path} not template-supported; skipping")
            elif status == "M":
                summary["warnings"].append({
                    "path": path,
                    "reason": (f"Templates can only ADD files under "
                               f"{c['subdir']}/, not modify existing ones. "
                               f"Revert the change or surface as a core-John change.")
                })
                warn(f"modification of {path} not template-supported; skipping")
            else:
                additive_files.append(c["path"])
        elif kind == "template_root":
            template_root_files.append(c["filename"])
        elif kind in ("evolution_declaration", "internal"):
            pass  # evolution.json folds into template.json below; .hamster/ is packager provenance
        elif kind == "workflow":
            if status == "D":
                summary["warnings"].append({
                    "path": path,
                    "reason": ("Removing a shipped workflow isn't a template "
                               "operation; just don't ship it. Skipping."),
                })
                warn(f"deletion of {path} not template-supported; skipping")
            else:
                workflow_files.append(c["filename"])
        elif kind == "warn":
            summary["warnings"].append({
                "path": path,
                "status": status,
                "reason": ("Templates cannot modify files outside skills/, "
                           "scripts/, commands/, agents/. Revert the change "
                           "in the fork or propose as a core-John PR.")
            })
            warn(f"{status} {path} not template-supported; skipping")

    output.mkdir(parents=True, exist_ok=False)

    template_name = output.name
    description = args.description or f"Hamster-built template: {template_name}"
    template_json = {
        "name": template_name,
        "version": "0.1.0",
        "description": description,
        "requires_john": summary["requires_john"],
    }

    # Evolution declaration (John v0.3.x): a template that wants Ring-1
    # evolution ships its feedback design. Authors declare it in a fork-root
    # evolution.json; it folds into template.json as the `evolution` block.
    # Warn-only — a template without one still works, but its worker skills
    # can't be trained and evolution runs on process evidence + lessons only.
    evolution_src = fork / "evolution.json"
    if evolution_src.is_file():
        try:
            evolution = json.loads(evolution_src.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            evolution = None
            warn(f"evolution.json present but unreadable ({exc}); skipping")
        if isinstance(evolution, dict):
            missing = [k for k in ("scorer", "feedback_design") if not evolution.get(k)]
            if missing:
                warn(
                    "evolution.json is missing: " + ", ".join(missing)
                    + " — a template declaring evolution should name its scorer/eval set "
                    + "and its feedback design (see John's skill-evolution skill)"
                )
            template_json["evolution"] = evolution
            summary["translations"].append({"kind": "evolution.json", "auto": False})
    else:
        info(
            "note: no evolution.json at the fork root — template ships no scorer; "
            "its worker skills can't be trained and Ring-1 evolution will run on "
            "process evidence + lessons only (fine for a first version)"
        )

    (output / "template.json").write_text(
        json.dumps(template_json, indent=2) + "\n"
    )
    summary["translations"].append({"kind": "template.json", "auto": True})

    apply_dest = output / "apply.sh"
    try:
        apply_dest.symlink_to(apply_script)
    except OSError:
        shutil.copy2(apply_script, apply_dest)
        info(f"  (apply.sh copied instead of symlinked; OK on platforms without symlink support)")
    # Record the source relative to the fork when possible, to avoid leaking an
    # absolute dev-machine path into provenance.
    try:
        apply_src_record = str(apply_script.relative_to(fork))
    except ValueError:
        apply_src_record = apply_script.name
    summary["translations"].append({"kind": "apply.sh", "source": apply_src_record})

    if overridden_skills or deleted_skills:
        (output / "skills" / "_override").mkdir(parents=True, exist_ok=True)
    if added_skills:
        (output / "skills").mkdir(exist_ok=True)

    for skill in overridden_skills:
        src = plugin_root / "skills" / skill
        dst = output / "skills" / "_override" / skill
        shutil.copytree(src, dst)
        summary["translations"].append({
            "kind": "override_skill",
            "skill": skill,
            "files_in_override": sum(1 for _ in dst.rglob("*") if _.is_file()),
        })

    for skill in added_skills:
        src = plugin_root / "skills" / skill
        dst = output / "skills" / skill
        shutil.copytree(src, dst)
        summary["translations"].append({
            "kind": "add_skill",
            "skill": skill,
            "files": sum(1 for _ in dst.rglob("*") if _.is_file()),
        })

    if deleted_skills:
        delete_file = output / "skills" / "_delete"
        lines = []
        for skill in sorted(deleted_skills):
            if skill in JOHN_CORE_SKILLS:
                # John's apply_template.py wants core deletions to carry a
                # same-line `# reason`; stamp a TODO the author must replace.
                lines.append(f"{skill} # TODO: state why this core skill is deleted")
            else:
                lines.append(skill)
        delete_file.write_text("\n".join(lines) + "\n")
        for skill in deleted_skills:
            entry = {
                "kind": "delete_skill",
                "skill": skill,
                "reminder": ("Deletion via _delete is supported. If you're "
                             "replacing this skill with one of a different "
                             "name, make sure references from other skills, "
                             "claude_addon.md, and plan_md_template.md point "
                             "at the new name."),
            }
            if skill in JOHN_CORE_SKILLS:
                entry["core_skill_warning"] = (
                    f"'{skill}' is one of John's load-bearing core skills. "
                    "apply_template.py will warn loudly on deletion; replace the "
                    "TODO comment in skills/_delete with the actual reason before "
                    "shipping this template."
                )
                print(f"WARNING: template deletes John core skill '{skill}' — "
                      f"state why in skills/_delete (a '# reason' comment was "
                      f"stamped as TODO).", file=sys.stderr)
            summary["translations"].append(entry)

    for path in additive_files:
        # `path` is plugin-relative (e.g. "scripts/foo.py"); read from the plugin
        # subtree, write at the template root.
        src = plugin_root / path
        dst = output / path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        summary["translations"].append({"kind": "additive", "path": path})

    for filename in template_root_files:
        src = fork / filename
        dst = output / filename
        shutil.copy2(src, dst)
        summary["translations"].append({
            "kind": "template_root",
            "filename": filename,
        })

    for filename in workflow_files:
        src = fork / ".claude" / "workflows" / filename
        dst = output / "workflows" / filename
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        summary["translations"].append({
            "kind": "workflow",
            "filename": filename,
        })

    # Provenance lives with the fork (the builder's scratch), NOT inside the
    # shipped template — keeping built templates free of dev-history/paths.
    hamster_dir = fork / ".hamster"
    hamster_dir.mkdir(exist_ok=True)
    summary_path = hamster_dir / "package_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    info(f"\nPackaged template: {output}")
    info(f"Base commit: {base_commit[:12]}")
    info(f"Translations: {len(summary['translations'])}")
    info(f"Warnings: {len(summary['warnings'])}")
    if summary["warnings"]:
        info("\nWarnings (also recorded in .hamster/package_summary.json):")
        for w in summary["warnings"]:
            info(f"  - {w.get('path', w)}: {w.get('reason', '')[:120]}")

    if args.smoke_test:
        info("\nSmoke test: invoking apply.sh --help to verify executability...")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                result = subprocess.run(
                    [str(output / "apply.sh"), "--help"],
                    capture_output=True, text=True, cwd=tmp, timeout=30
                )
                info(f"  apply.sh --help exit code: {result.returncode}")
                if result.stdout:
                    info(f"  stdout (first 200 chars): {result.stdout[:200]}")
                if result.stderr:
                    info(f"  stderr (first 200 chars): {result.stderr[:200]}")
                info("  (For a full apply test, run apply.sh against a "
                     "real joharnessburg-applied dir manually.)")
        except (OSError, subprocess.TimeoutExpired) as e:
            warn(f"  smoke test could not run: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
