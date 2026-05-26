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
    plan_md_template.md (if present at fork root)
    claude_addon.md (if present at fork root)
    .hamster/package_summary.json (provenance)

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


def get_joharnessburg_version(jpath: Path) -> str:
    """Read version from joharnessburg's plugin.json. Returns 'unknown' if absent."""
    plugin_json = jpath / ".claude-plugin" / "plugin.json"
    if not plugin_json.exists():
        return "unknown"
    try:
        return json.loads(plugin_json.read_text()).get("version", "unknown")
    except (json.JSONDecodeError, OSError):
        return "unknown"


def classify_change(path: str, base_skills: set) -> dict:
    """Classify a changed path. Returns dict with 'kind' and supporting fields.

    kind ∈ {"override_skill", "add_skill", "additive", "template_root", "warn"}
    Note: deletion of a whole skill dir is detected later, not here.
    """
    parts = path.split("/")

    if path in ("plan_md_template.md", "claude_addon.md"):
        return {"kind": "template_root", "filename": path}

    if parts[0] == "skills" and len(parts) >= 3:
        skill_name = parts[1]
        if skill_name in base_skills:
            return {"kind": "override_skill", "skill": skill_name}
        return {"kind": "add_skill", "skill": skill_name}

    if parts[0] in ("scripts", "commands", "agents") and len(parts) >= 2:
        return {"kind": "additive", "subdir": parts[0], "path": path}

    return {"kind": "warn", "path": path}


def inventory_base_skills(fork: Path, base_commit: str) -> set:
    """Return the set of skill dir names that existed at base."""
    out = run_git(["ls-tree", "--name-only", base_commit, "skills/"], cwd=fork)
    skills = set()
    for line in out.splitlines():
        parts = line.split("/")
        if len(parts) == 2 and parts[0] == "skills" and parts[1]:
            skills.add(parts[1])
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

    if output.exists():
        err(f"output dir already exists: {output}")
        err("Refusing to overwrite. Delete it first if you want a fresh build.")
        return 1

    apply_script = args.apply_script
    if apply_script is None:
        apply_script = fork / "templates" / "apply.sh"
    apply_script = apply_script.resolve()
    if not apply_script.exists():
        err(f"apply.sh not found at: {apply_script}")
        err("Pass --apply-script if it's elsewhere.")
        return 1

    try:
        base_skills = inventory_base_skills(fork, base_commit)
        changes = collect_changes(fork, base_commit)
    except RuntimeError as e:
        err(str(e))
        return 1

    summary = {
        "base_commit": base_commit,
        "packaged_at": datetime.now(timezone.utc).isoformat(),
        "requires_john": f">={get_joharnessburg_version(fork)}",
        "translations": [],
        "warnings": [],
    }

    overridden_skills = {}    # skill_name -> True (modified, dir still exists)
    deleted_skills = set()    # skill_name (dir deleted)
    added_skills = {}         # skill_name -> True (new dir)
    additive_files = []       # list of paths
    template_root_files = []  # list of filenames

    for status, path in changes:
        c = classify_change(path, base_skills)
        kind = c["kind"]

        if kind == "override_skill":
            skill = c["skill"]
            skill_dir = fork / "skills" / skill
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
                additive_files.append(path)
        elif kind == "template_root":
            template_root_files.append(c["filename"])
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
    (output / ".hamster").mkdir()

    template_name = output.name
    description = args.description or f"Hamster-built template: {template_name}"
    template_json = {
        "name": template_name,
        "version": "0.1.0",
        "description": description,
        "requires_john": summary["requires_john"],
    }
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
    summary["translations"].append({"kind": "apply.sh", "source": str(apply_script)})

    if overridden_skills or deleted_skills:
        (output / "skills" / "_override").mkdir(parents=True, exist_ok=True)
    if added_skills:
        (output / "skills").mkdir(exist_ok=True)

    for skill in overridden_skills:
        src = fork / "skills" / skill
        dst = output / "skills" / "_override" / skill
        shutil.copytree(src, dst)
        summary["translations"].append({
            "kind": "override_skill",
            "skill": skill,
            "files_in_override": sum(1 for _ in dst.rglob("*") if _.is_file()),
        })

    for skill in added_skills:
        src = fork / "skills" / skill
        dst = output / "skills" / skill
        shutil.copytree(src, dst)
        summary["translations"].append({
            "kind": "add_skill",
            "skill": skill,
            "files": sum(1 for _ in dst.rglob("*") if _.is_file()),
        })

    if deleted_skills:
        delete_file = output / "skills" / "_delete"
        delete_file.write_text("\n".join(sorted(deleted_skills)) + "\n")
        for skill in deleted_skills:
            summary["translations"].append({
                "kind": "delete_skill",
                "skill": skill,
                "reminder": ("Deletion via _delete is supported. If you're "
                             "replacing this skill with one of a different "
                             "name, make sure references from other skills, "
                             "claude_addon.md, and plan_md_template.md point "
                             "at the new name."),
            })

    for path in additive_files:
        src = fork / path
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

    summary_path = output / ".hamster" / "package_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")

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
