#!/usr/bin/env python3
"""Strict stdlib validator for portable, dual-provider John templates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from hamster_safety import reject_symlinks, safe_slug, safe_version


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
BAD_QUALITY_RE = re.compile(r"\b(?:TODO|FIXME|TBD-STUB)\b", re.IGNORECASE)
MACHINE_PATH_RE = re.compile(r"(?:/Users/[^/\s]+/|[A-Za-z]:\\Users\\[^\\\s]+\\)")


def object_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return data


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError("missing YAML frontmatter")
    result: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#") or raw_line.startswith(" "):
            continue
        if ":" not in raw_line:
            raise ValueError(f"invalid frontmatter line: {raw_line!r}")
        key, value = raw_line.split(":", 1)
        result[key.strip()] = value.strip().strip('"\'')
    return result


def add_check(report: dict, name: str, status: str, detail: str = "") -> None:
    report["checks"].append({"name": name, "status": status, "detail": detail})


def validate_template(
    template: Path,
    *,
    john_install: Path | None = None,
    expected_apply_sha256: str | None = None,
    initialize: bool = False,
    timeout: int = 60,
) -> dict:
    report: dict = {
        "schema_version": "hamster.template-validation.v1",
        "valid": False,
        "checks": [],
        "errors": [],
        "warnings": [],
    }
    template = template.resolve()
    try:
        if not template.is_dir():
            raise ValueError(f"template is not a directory: {template}")
        reject_symlinks(template, label="template")
        add_check(report, "paths-and-symlinks", "passed")
    except (OSError, ValueError) as exc:
        report["errors"].append(str(exc))
        return report

    try:
        metadata = object_json(template / "template.json")
        name = safe_slug(metadata.get("name"), field="template name")
        if name != template.name and not template.name.startswith(f".{name}.stage-"):
            raise ValueError("template.json name must match the template directory name")
        safe_version(metadata.get("version"), field="template version")
        requires = metadata.get("requires_john")
        safe_version(requires, field="requires_john exact pin")
        if not isinstance(metadata.get("description"), str) or not metadata["description"].strip():
            raise ValueError("template description must be a non-empty string")
        providers = metadata.get("providers")
        if (
            not isinstance(providers, list)
            or not providers
            or any(item not in {"claude", "codex"} for item in providers)
            or len(providers) != len(set(providers))
        ):
            raise ValueError("providers must be a unique non-empty list of claude/codex")
        add_check(report, "metadata-and-exact-pins", "passed")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report["errors"].append(f"metadata: {exc}")
        metadata = {}
        providers = []

    apply_script = template / "apply.sh"
    try:
        if not apply_script.is_file() or apply_script.is_symlink():
            raise ValueError("apply.sh must be an executable regular file")
        if not os.access(apply_script, os.X_OK):
            raise ValueError("apply.sh is not executable")
        digest = hashlib.sha256(apply_script.read_bytes()).hexdigest()
        if expected_apply_sha256 and digest != expected_apply_sha256:
            raise ValueError("apply.sh SHA-256 does not match package provenance")
        add_check(report, "canonical-apply", "passed", f"sha256:{digest}")
    except (OSError, ValueError) as exc:
        report["errors"].append(str(exc))

    skill_dirs: list[Path] = []
    skills_root = template / "skills"
    if skills_root.is_dir():
        skill_dirs.extend(
            path for path in skills_root.iterdir() if path.is_dir() and path.name != "_override"
        )
        override = skills_root / "_override"
        if override.is_dir():
            skill_dirs.extend(path for path in override.iterdir() if path.is_dir())
    for skill_dir in sorted(skill_dirs):
        try:
            safe_slug(skill_dir.name, field="skill name")
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.is_file():
                raise ValueError("missing SKILL.md")
            header = frontmatter(skill_file)
            if header.get("name") != skill_dir.name:
                raise ValueError("frontmatter name does not match directory")
            if not header.get("description"):
                raise ValueError("frontmatter description is required")
        except (OSError, ValueError) as exc:
            report["errors"].append(f"skill {skill_dir.name}: {exc}")
    add_check(
        report,
        "skill-frontmatter",
        "passed" if not any(item.startswith("skill ") for item in report["errors"]) else "failed",
        f"{len(skill_dirs)} skill directories",
    )

    for path in sorted(template.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(template).as_posix()
        try:
            if path.suffix == ".json":
                json.loads(path.read_text(encoding="utf-8"))
            elif path.suffix == ".py":
                with tempfile.TemporaryDirectory() as compiled:
                    py_compile.compile(
                        str(path), cfile=str(Path(compiled) / "module.pyc"), doraise=True
                    )
            elif path.suffix == ".toml":
                parsed = tomllib.loads(path.read_text(encoding="utf-8"))
                if relative.startswith("codex/agents/"):
                    safe_slug(path.stem, field="Codex agent name")
                    if parsed.get("name") != path.stem:
                        raise ValueError("Codex agent name must match filename")
            elif path.suffix in {".sh", ".bash"}:
                result = subprocess.run(
                    ["bash", "-n", str(path)], capture_output=True, text=True, timeout=timeout
                )
                if result.returncode:
                    raise ValueError(result.stderr.strip())
        except (OSError, ValueError, json.JSONDecodeError, tomllib.TOMLDecodeError, subprocess.TimeoutExpired, py_compile.PyCompileError) as exc:
            report["errors"].append(f"syntax {relative}: {exc}")
    add_check(report, "json-python-shell-toml-syntax", "passed" if not any(item.startswith("syntax ") for item in report["errors"]) else "failed")

    for path in sorted(template.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(template).as_posix()
        if MACHINE_PATH_RE.search(text):
            report["errors"].append(f"machine-specific path in {relative}")
        if BAD_QUALITY_RE.search(text):
            report["errors"].append(f"unfinished TODO/stub marker in {relative}")
        for target in MARKDOWN_LINK_RE.findall(text):
            target = target.split("#", 1)[0]
            if not target or "://" in target or target.startswith(("#", "mailto:", "${", "<")):
                continue
            candidate = (path.parent / target).resolve(strict=False)
            if not candidate.is_relative_to(template) or not candidate.exists():
                report["errors"].append(f"broken or external markdown reference in {relative}: {target}")
    add_check(report, "references-and-release-quality", "passed" if not any(" in " in item and ("reference" in item or "path" in item or "marker" in item) for item in report["errors"]) else "failed")

    try:
        if "claude" in providers and not (template / "claude_addon.md").exists() and not (template / "project_addon.md").exists():
            report["warnings"].append("Claude provider has no provider/shared project addon")
        if "codex" in providers and not (template / "agents_addon.md").exists() and not (template / "project_addon.md").exists():
            report["warnings"].append("Codex provider has no provider/shared project addon")
        for agent in list((template / "agents").glob("*.md")) if (template / "agents").is_dir() else []:
            body = agent.read_text(encoding="utf-8")
            if (".john/events" in body or "event_type" in body) and "emit_event.py" not in body:
                report["errors"].append(f"agent event contract bypasses emit_event.py: {agent.name}")
        for agent in list((template / "codex/agents").glob("*.toml")) if (template / "codex/agents").is_dir() else []:
            body = agent.read_text(encoding="utf-8")
            if (".john/events" in body or "event_type" in body) and "emit_event.py" not in body:
                report["errors"].append(f"Codex agent event contract bypasses emit_event.py: {agent.name}")
        add_check(report, "provider-layouts-and-agent-contracts", "passed" if not any("agent event contract" in item for item in report["errors"]) else "failed")
    except OSError as exc:
        report["errors"].append(f"provider layout: {exc}")

    try:
        with tempfile.TemporaryDirectory(prefix="hamster relocation ") as td:
            relocated = Path(td) / template.name
            shutil.copytree(template, relocated)
            reject_symlinks(relocated, label="relocated template")
            if hashlib.sha256((relocated / "apply.sh").read_bytes()).hexdigest() != hashlib.sha256(apply_script.read_bytes()).hexdigest():
                raise ValueError("apply.sh changed during relocation")
        add_check(report, "relocation", "passed")
    except (OSError, ValueError) as exc:
        report["errors"].append(f"relocation: {exc}")

    if john_install is not None:
        try:
            john_install = john_install.resolve()
            reject_symlinks(john_install, label="clean John snapshot")
            with tempfile.TemporaryDirectory(prefix="hamster-apply-") as td:
                scratch = Path(td)
                applied = scratch / "applied" / template.name
                env = os.environ.copy()
                env["HOME"] = str(scratch / "home")
                env["CLAUDE_PLUGIN_ROOT"] = str(john_install)
                result = subprocess.run(
                    [str(apply_script), "--john-install", str(john_install), "--output", str(applied)],
                    cwd=template,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                if result.returncode != 0:
                    raise ValueError(f"real apply failed: {(result.stderr or result.stdout)[-500:]}")
                if not (applied / ".applied-metadata.json").is_file():
                    raise ValueError("real apply produced no provenance marker")
                if initialize:
                    project = scratch / "project"
                    project.mkdir()
                    init = subprocess.run(
                        [sys.executable, str(applied / "scripts/init_workspace.py")],
                        cwd=project,
                        env={**env, "CLAUDE_PLUGIN_ROOT": str(applied)},
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )
                    if init.returncode != 0:
                        raise ValueError(f"initialized apply failed: {(init.stderr or init.stdout)[-500:]}")
                    if "claude" in providers and not (project / "CLAUDE.md").is_file():
                        raise ValueError("Claude provider guidance was not initialized")
                    if "codex" in providers and not (project / "AGENTS.md").is_file():
                        raise ValueError("Codex provider guidance was not initialized")
                    for template_agent in (template / "codex/agents").glob("*.toml") if (template / "codex/agents").is_dir() else []:
                        if not (project / ".codex/agents" / template_agent.name).is_file():
                            raise ValueError(
                                f"Codex template agent was not initialized: {template_agent.name}"
                            )
            add_check(report, "real-apply-smoke", "passed", "clean John snapshot")
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            report["errors"].append(str(exc))
            add_check(report, "real-apply-smoke", "failed", str(exc))
    else:
        report["warnings"].append("real apply not run because --john-install was omitted")
        add_check(report, "real-apply-smoke", "skipped")

    report["valid"] = not report["errors"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path)
    parser.add_argument("--john-install", type=Path)
    parser.add_argument("--expected-apply-sha256")
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    report = validate_template(
        args.template,
        john_install=args.john_install,
        expected_apply_sha256=args.expected_apply_sha256,
        initialize=args.initialize,
        timeout=args.timeout,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
