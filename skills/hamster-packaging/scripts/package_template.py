#!/usr/bin/env python3
"""Build, validate, smoke, and atomically publish a portable John template."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from hamster_safety import (
    atomic_json,
    atomic_text,
    contained,
    reject_symlinks,
    safe_slug,
    safe_version,
)
from validate_template import validate_template


JOHN_CORE_SKILLS = {
    "using-john",
    "ralph-loop",
    "event-log-and-reducer",
    "workspace-discipline",
    "context-management",
    "subagent-dispatch",
    "skill-evolution",
}
ROOT_TEMPLATE_FILES = {
    "project_addon.md",
    "claude_addon.md",
    "agents_addon.md",
    "plan_md_template.md",
}


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def git(fork: Path, *args: str, timeout: int = 60) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(fork), *args],
        capture_output=True,
        timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {result.stderr.decode('utf-8', 'replace').strip()}"
        )
    return result.stdout


def git_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "." in path.parts or "\\" in value:
        raise ValueError(f"unsafe Git path: {value!r}")
    return path.as_posix()


def base_layout(fork: Path, base: str) -> tuple[str, str, str]:
    files = [
        token.decode("utf-8")
        for token in git(fork, "ls-tree", "-r", "--name-only", "-z", base).split(b"\0")
        if token
    ]
    manifests = sorted(
        path for path in files if path.endswith(".claude-plugin/plugin.json")
    )
    for manifest_path in manifests:
        try:
            metadata = json.loads(git(fork, "show", f"{base}:{manifest_path}"))
        except (RuntimeError, json.JSONDecodeError):
            continue
        version = metadata.get("version") if isinstance(metadata, dict) else None
        if isinstance(version, str):
            safe_version(version, field="base John version")
            plugin_prefix = PurePosixPath(manifest_path).parent.parent.as_posix()
            return ("" if plugin_prefix == "." else plugin_prefix, manifest_path, version)
    raise ValueError("base commit has no versioned John plugin manifest")


def base_skills(fork: Path, base: str, plugin_prefix: str) -> set[str]:
    prefix = f"{plugin_prefix}/skills/" if plugin_prefix else "skills/"
    result: set[str] = set()
    for token in git(fork, "ls-tree", "-r", "--name-only", "-z", base).split(b"\0"):
        if not token:
            continue
        path = token.decode("utf-8")
        if path.startswith(prefix):
            name = path[len(prefix):].split("/", 1)[0]
            if name:
                result.add(name)
    return result


def changes(fork: Path, base: str) -> list[tuple[str, str]]:
    raw = git(fork, "diff", "--name-status", "-z", "--no-renames", base, "--")
    tokens = raw.split(b"\0")
    if tokens and tokens[-1] == b"":
        tokens.pop()
    if len(tokens) % 2:
        raise ValueError("unexpected NUL-delimited Git diff output")
    result: list[tuple[str, str]] = []
    for index in range(0, len(tokens), 2):
        status = tokens[index].decode("ascii")
        path = git_path(tokens[index + 1].decode("utf-8"))
        result.append((status, path))
    for token in git(fork, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0"):
        if token:
            result.append(("A", git_path(token.decode("utf-8"))))
    return [
        item
        for item in result
        if item[1] != ".hamster-base-commit" and not item[1].startswith(".hamster/")
    ]


def plugin_relative(path: str, prefix: str) -> str | None:
    if not prefix:
        return path
    marker = prefix + "/"
    return path[len(marker):] if path.startswith(marker) else None


def copy_regular_tree(source: Path, destination: Path) -> None:
    reject_symlinks(source, label=f"package source {source.name}")
    shutil.copytree(source, destination)


def clean_snapshot(fork: Path, base: str, target: Path) -> None:
    archive = git(fork, "archive", "--format=tar", base, timeout=120)
    target.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        for member in bundle.getmembers():
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"unsafe base archive member: {member.name}")
            destination = contained(target, target.joinpath(*relative.parts), label="base archive member")
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = bundle.extractfile(member)
                if source is None:
                    raise ValueError(f"cannot extract base archive member: {member.name}")
                destination.write_bytes(source.read())
                os.chmod(destination, member.mode & 0o777)
            else:
                raise ValueError(f"base commit contains unsupported link/device: {member.name}")


def read_json_if_present(path: Path) -> dict:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must be a JSON object")
    return data


def write_summary(fork: Path, summary: dict) -> None:
    atomic_json(fork / ".hamster/package_summary.json", summary, mode=0o600)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fork", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--template-version", required=True)
    parser.add_argument("--requires-john")
    parser.add_argument("--description")
    parser.add_argument("--provider", choices=("claude", "codex", "both"), default="both")
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--smoke-test", action="store_true", help="also initialize an applied template")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    summary = {
        "schema_version": "hamster.package-summary.v1",
        "status": "failed",
        "base_commit": None,
        "packaged_at": datetime.now(timezone.utc).isoformat(),
        "template_version": args.template_version,
        "requires_john": args.requires_john,
        "providers": [],
        "apply_sha256": None,
        "translations": [],
        "warnings": [],
        "validation": None,
    }
    stage: Path | None = None
    try:
        template_version = safe_version(args.template_version, field="template version")
        raw_fork = args.fork.expanduser()
        if raw_fork.is_symlink():
            raise ValueError(f"fork may not be a symlink: {raw_fork}")
        fork = raw_fork.resolve()
        if not fork.is_dir() or git(fork, "rev-parse", "--is-inside-work-tree").strip() != b"true":
            raise ValueError(f"fork is not a Git worktree: {fork}")
        base_file = fork / ".hamster-base-commit"
        base = base_file.read_text(encoding="ascii").strip()
        if not base:
            raise ValueError(".hamster-base-commit is empty")
        git(fork, "cat-file", "-e", f"{base}^{{commit}}")
        summary["base_commit"] = base
        prefix, _, base_version = base_layout(fork, base)
        requires_john = safe_version(
            args.requires_john or base_version, field="requires_john exact pin"
        )
        providers = ["claude", "codex"] if args.provider == "both" else [args.provider]
        summary["requires_john"] = requires_john
        summary["providers"] = providers

        raw_output = args.output.expanduser()
        if raw_output.is_symlink():
            raise ValueError(f"output may not be a symlink: {raw_output}")
        if ".." in raw_output.parts:
            raise ValueError(f"output path may not contain traversal: {raw_output}")
        output_parent = raw_output.parent.resolve()
        template_name = safe_slug(raw_output.name, field="output template name")
        output = contained(output_parent, output_parent / template_name, label="template output")
        if output.exists():
            raise ValueError(f"output already exists: {output}")
        output_parent.mkdir(parents=True, exist_ok=True)

        inventory = base_skills(fork, base, prefix)
        change_list = changes(fork, base)
        deletion_reasons = read_json_if_present(fork / "deletion_reasons.json")
        evolution = read_json_if_present(fork / "evolution.json")
        plugin_root = fork / prefix if prefix else fork
        reject_symlinks(plugin_root, label="modified John plugin")

        override_skills: set[str] = set()
        added_skills: set[str] = set()
        deleted_skills: set[str] = set()
        additive: set[str] = set()
        root_files: set[str] = set()
        workflows: set[str] = set()
        for status, path in change_list:
            if path in ROOT_TEMPLATE_FILES:
                if status != "D":
                    root_files.add(path)
                continue
            if path in {"evolution.json", "deletion_reasons.json"}:
                continue
            if path.startswith(".claude/workflows/"):
                remainder = path.removeprefix(".claude/workflows/")
                if status != "D" and remainder.endswith(".js") and "/" not in remainder:
                    workflows.add(remainder)
                else:
                    summary["warnings"].append({"path": path, "reason": "unsupported workflow change"})
                continue
            inner = plugin_relative(path, prefix)
            if inner is None:
                summary["warnings"].append({"path": path, "reason": "outside the John plugin subtree"})
                continue
            parts = PurePosixPath(inner).parts
            if len(parts) >= 3 and parts[0] == "skills":
                skill = safe_slug(parts[1], field="skill name")
                skill_dir = plugin_root / "skills" / skill
                if skill in inventory:
                    if skill_dir.is_dir():
                        override_skills.add(skill)
                    else:
                        deleted_skills.add(skill)
                elif status != "D":
                    added_skills.add(skill)
                continue
            allowed = (
                len(parts) >= 2 and parts[0] in {"scripts", "commands", "agents"}
            ) or (len(parts) >= 3 and parts[:2] == ("codex", "agents"))
            if allowed:
                if status == "A":
                    additive.add(inner)
                else:
                    summary["warnings"].append({"path": path, "reason": "template platform files are additive-only"})
                continue
            summary["warnings"].append({"path": path, "reason": "change cannot be translated to template format"})

        for skill in sorted(deleted_skills & JOHN_CORE_SKILLS):
            reason = deletion_reasons.get(skill)
            if not isinstance(reason, str) or not reason.strip():
                summary["warnings"].append({"path": f"skills/{skill}", "reason": "core deletion requires deletion_reasons.json"})

        if summary["warnings"] and not args.allow_warnings:
            write_summary(fork, summary)
            raise ValueError("strict packaging stopped on warnings; inspect .hamster/package_summary.json or pass --allow-warnings")

        stage = output_parent / f".{template_name}.stage-{uuid.uuid4().hex}"
        stage.mkdir()
        metadata = {
            "name": template_name,
            "version": template_version,
            "description": args.description or f"Hamster-built template: {template_name}",
            "requires_john": requires_john,
            "providers": providers,
        }
        if evolution:
            metadata["evolution"] = evolution
        atomic_json(stage / "template.json", metadata)
        summary["translations"].append({"kind": "template.json"})

        apply_bytes = git(
            fork,
            "show",
            f"{base}:{prefix + '/' if prefix else ''}templates/apply.sh",
        )
        apply_sha = hashlib.sha256(apply_bytes).hexdigest()
        apply_path = stage / "apply.sh"
        atomic_text(apply_path, apply_bytes.decode("utf-8"), mode=0o755)
        summary["apply_sha256"] = apply_sha
        summary["translations"].append({"kind": "apply.sh", "sha256": apply_sha})

        for skill in sorted(override_skills):
            source = plugin_root / "skills" / skill
            destination = stage / "skills/_override" / skill
            copy_regular_tree(source, destination)
            summary["translations"].append({"kind": "override_skill", "skill": skill})
        for skill in sorted(added_skills):
            source = plugin_root / "skills" / skill
            destination = stage / "skills" / skill
            copy_regular_tree(source, destination)
            summary["translations"].append({"kind": "add_skill", "skill": skill})
        if deleted_skills:
            lines = []
            for skill in sorted(deleted_skills):
                reason = deletion_reasons.get(skill)
                lines.append(f"{skill} # {reason.strip()}" if isinstance(reason, str) and reason.strip() else skill)
            atomic_text(stage / "skills/_delete", "\n".join(lines) + "\n")
            summary["translations"].extend({"kind": "delete_skill", "skill": skill} for skill in sorted(deleted_skills))

        for inner in sorted(additive):
            source = plugin_root / inner
            if source.is_symlink() or not source.is_file():
                raise ValueError(f"additive source must be a regular file: {inner}")
            destination = stage / inner
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            summary["translations"].append({"kind": "additive", "path": inner})
        for filename in sorted(root_files):
            source = fork / filename
            if source.is_symlink() or not source.is_file():
                raise ValueError(f"template root source must be a regular file: {filename}")
            shutil.copy2(source, stage / filename)
            summary["translations"].append({"kind": "template_root", "filename": filename})
        for filename in sorted(workflows):
            source = fork / ".claude/workflows" / filename
            if source.is_symlink() or not source.is_file():
                raise ValueError(f"workflow source must be a regular file: {filename}")
            destination = stage / "workflows" / filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            summary["translations"].append({"kind": "workflow", "filename": filename})

        if "claude" in providers and "codex" in providers:
            claude_agents = {path.stem for path in (stage / "agents").glob("*.md")} if (stage / "agents").is_dir() else set()
            codex_agents = {path.stem for path in (stage / "codex/agents").glob("*.toml")} if (stage / "codex/agents").is_dir() else set()
            if not claude_agents.issubset(codex_agents):
                raise ValueError(
                    "dual-provider template agent parity failed; generate Codex TOMLs for every added Claude agent with John's sync contract"
                )

        with tempfile.TemporaryDirectory(prefix="hamster-base-") as td:
            snapshot = Path(td) / "john"
            clean_snapshot(fork, base, snapshot)
            john_install = snapshot / prefix if prefix else snapshot
            validation = validate_template(
                stage,
                john_install=john_install,
                expected_apply_sha256=apply_sha,
                initialize=args.smoke_test,
                timeout=args.timeout,
            )
        summary["validation"] = validation
        summary["warnings"].extend(
            {"path": "validation", "reason": item} for item in validation["warnings"]
        )
        if not validation["valid"]:
            write_summary(fork, summary)
            raise ValueError("template validation failed; inspect .hamster/package_summary.json")
        if validation["warnings"] and not args.allow_warnings:
            write_summary(fork, summary)
            raise ValueError("strict packaging stopped on validation warnings")

        reject_symlinks(stage, label="staged template")
        stage.rename(output)
        stage = None
        summary["status"] = "published"
        write_summary(fork, summary)
        print(f"Packaged template: {output}", file=sys.stderr)
        print(f"Base commit: {base[:12]}", file=sys.stderr)
        print(f"Translations: {len(summary['translations'])}", file=sys.stderr)
        print(f"Warnings: {len(summary['warnings'])}", file=sys.stderr)
        return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired, UnicodeDecodeError) as exc:
        if stage is not None and stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        try:
            if "fork" in locals() and isinstance(fork, Path) and fork.is_dir():
                write_summary(fork, summary)
        except OSError:
            pass
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
