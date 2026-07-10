#!/usr/bin/env python3
"""Transactionally scaffold a clean John fork for a Hamster template build."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from hamster_safety import atomic_text, contained, reject_symlinks, safe_slug


def git(source: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(source), *args], capture_output=True, check=False
    )


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--joharnessburg-path", required=True, type=Path)
    parser.add_argument("--forks-root", default=Path("forks"), type=Path)
    args = parser.parse_args()

    try:
        name = safe_slug(args.name, field="template name")
        raw_source = args.joharnessburg_path.expanduser()
        if raw_source.is_symlink():
            raise ValueError(f"John source may not be a symlink: {raw_source}")
        source = raw_source.resolve()
        if not source.is_dir():
            raise ValueError(f"John source is not a directory: {source}")
        if git(source, "rev-parse", "--is-inside-work-tree").returncode != 0:
            raise ValueError(f"John source is not a Git worktree: {source}")
        status = git(source, "status", "--porcelain=v1", "-z")
        if status.returncode != 0:
            raise ValueError(status.stderr.decode("utf-8", "replace").strip())
        if status.stdout:
            raise ValueError(
                "John source checkout is dirty; commit, stash, or remove all "
                "tracked and untracked changes before scaffolding"
            )
        reject_symlinks(source, label="John source checkout")

        manifests = sorted(source.glob("**/.claude-plugin/plugin.json"))
        if not manifests:
            raise ValueError("John source contains no .claude-plugin/plugin.json")

        raw_root = args.forks_root.expanduser()
        if raw_root.is_symlink():
            raise ValueError(f"forks root may not be a symlink: {raw_root}")
        root = raw_root.resolve()
        destination = contained(root, root / name, label="fork destination")
        if destination.exists():
            raise ValueError(f"fork already exists: {destination}")
    except ValueError as exc:
        return fail(str(exc))

    root.mkdir(parents=True, exist_ok=True)
    stage = root / f".{name}.stage-{uuid.uuid4().hex}"
    try:
        result = subprocess.run(
            ["git", "clone", "--no-hardlinks", "--", str(source), str(stage)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {result.stderr.strip()}")
        head = git(stage, "rev-parse", "HEAD")
        if head.returncode != 0:
            raise RuntimeError(head.stderr.decode("utf-8", "replace").strip())
        base_commit = head.stdout.decode("ascii").strip()
        atomic_text(stage / ".hamster-base-commit", base_commit + "\n", mode=0o600)
        reject_symlinks(stage, label="scaffolded fork")
        stage.rename(destination)
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as exc:
        shutil.rmtree(stage, ignore_errors=True)
        return fail(f"fork scaffold failed without publishing partial state: {exc}")

    print(f"Fork ready: {destination}", file=sys.stderr)
    print(f"Base commit: {base_commit[:12]}", file=sys.stderr)
    print(
        "Next: edit the fork, then package with --template-version X.Y.Z.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
