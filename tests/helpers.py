import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "skills/hamster-packaging/scripts"
JOHN_PLUGIN = REPO.parent / "joharnessburg/plugins/joharnessburg"


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )


def build_john_repo(root: Path) -> Path:
    repo = root / "john-source"
    plugin = repo / "plugins/joharnessburg"
    shutil.copytree(JOHN_PLUGIN, plugin)
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Hamster Tests")
    git(repo, "config", "user.email", "hamster@example.invalid")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "fixture John")
    return repo


def scaffold(work: Path, source: Path, name: str = "test-template"):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "scaffold_fork.py"),
            "--name", name,
            "--joharnessburg-path", str(source),
            "--forks-root", str(work / "forks"),
        ],
        capture_output=True,
        text=True,
    )


def add_dual_template_changes(fork: Path) -> None:
    (fork / "project_addon.md").write_text("# Shared template guidance\n")
    plugin = fork / "plugins/joharnessburg"
    skill = plugin / "skills/template-feature"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: template-feature\ndescription: Provide a real template feature.\n---\n\n# Feature\n\nUse the shared John contracts.\n"
    )


def package(fork: Path, output: Path, *extra: str):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "package_template.py"),
            "--fork", str(fork),
            "--output", str(output),
            "--template-version", "1.2.3",
            *extra,
        ],
        capture_output=True,
        text=True,
    )


def summary(fork: Path) -> dict:
    return json.loads((fork / ".hamster/package_summary.json").read_text())
