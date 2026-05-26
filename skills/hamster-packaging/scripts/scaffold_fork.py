#!/usr/bin/env python3
"""Scaffold a Hamster fork — a local clone of joharnessburg for template work.

Usage:
  python3 scaffold_fork.py --name <template-name>
                            --joharnessburg-path <path>
                            [--forks-root <path>]

Creates <forks-root>/<name>/ as a git clone of <joharnessburg-path>, records
the current HEAD commit to .hamster-base-commit, and prints next steps.

The fork is your modified-John workspace. Edit files freely; package_template.py
later computes the diff between .hamster-base-commit and the fork's working
tree, and translates it into the canonical John template folder layout.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def info(msg: str) -> None:
    print(msg, file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True,
                        help="Name of the fork dir (also the template name)")
    parser.add_argument("--joharnessburg-path", required=True, type=Path,
                        help="Path to the local joharnessburg checkout")
    parser.add_argument("--forks-root", default=Path("forks"), type=Path,
                        help="Where to put the fork (default: ./forks)")
    args = parser.parse_args()

    j_path: Path = args.joharnessburg_path.resolve()
    forks_root: Path = args.forks_root.resolve()
    fork_path = forks_root / args.name

    if not j_path.exists() or not j_path.is_dir():
        err(f"joharnessburg path does not exist or isn't a dir: {j_path}")
        return 1
    if not (j_path / ".git").exists():
        err(f"joharnessburg path is not a git repo: {j_path}")
        return 1
    if not (j_path / ".claude-plugin" / "plugin.json").exists():
        err(f"joharnessburg path doesn't look like a John plugin "
            f"(missing .claude-plugin/plugin.json): {j_path}")
        return 1

    if fork_path.exists():
        err(f"fork already exists: {fork_path}")
        err("Refusing to overwrite. Either delete it or use a different --name.")
        return 1

    forks_root.mkdir(parents=True, exist_ok=True)

    info(f"Cloning {j_path} → {fork_path} ...")
    result = subprocess.run(
        ["git", "clone", str(j_path), str(fork_path)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        err(f"git clone failed: {result.stderr}")
        return 1

    result = subprocess.run(
        ["git", "-C", str(fork_path), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True
    )
    base_commit = result.stdout.strip()
    (fork_path / ".hamster-base-commit").write_text(base_commit + "\n")

    info(f"\nFork ready at: {fork_path}")
    info(f"Base commit: {base_commit[:12]}")
    info(f"\nNext: edit files in {fork_path} to design your template.")
    info(f"      When done: python3 package_template.py "
         f"--fork {fork_path} --output templates/{args.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
