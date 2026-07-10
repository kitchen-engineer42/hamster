import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import (
    JOHN_PLUGIN,
    SCRIPTS,
    add_dual_template_changes,
    build_john_repo,
    package,
    scaffold,
    summary,
)


class TestScaffold(unittest.TestCase):
    def test_scaffold_requires_clean_source_safe_slug_and_publishes_atomically(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = build_john_repo(root)
            result = scaffold(root, source)
            self.assertEqual(result.returncode, 0, result.stderr)
            fork = root / "forks/test-template"
            self.assertTrue((fork / ".hamster-base-commit").is_file())
            self.assertFalse(any((root / "forks").glob("*.stage-*")))

            (source / "dirty.txt").write_text("dirty")
            result = scaffold(root, source, "dirty-template")
            self.assertEqual(result.returncode, 1)
            self.assertIn("dirty", result.stderr)
            self.assertFalse((root / "forks/dirty-template").exists())

            result = scaffold(root, source, "../escape")
            self.assertEqual(result.returncode, 1)
            self.assertFalse((root / "escape").exists())

    def test_scaffold_rejects_source_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = build_john_repo(root)
            external = root / "external"
            external.write_text("outside")
            os.symlink(external, source / "linked")
            subprocess.run(["git", "add", "linked"], cwd=source, check=True)
            subprocess.run(["git", "commit", "-qm", "link"], cwd=source, check=True)
            result = scaffold(root, source)
            self.assertEqual(result.returncode, 1)
            self.assertIn("symlink", result.stderr)


class TestPackage(unittest.TestCase):
    def make_fork(self, root: Path) -> Path:
        source = build_john_repo(root)
        result = scaffold(root, source)
        self.assertEqual(result.returncode, 0, result.stderr)
        return root / "forks/test-template"

    def test_strict_transactional_package_and_real_smoke(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fork = self.make_fork(root)
            add_dual_template_changes(fork)
            output = root / "templates/test-template"
            result = package(fork, output, "--smoke-test")
            self.assertEqual(result.returncode, 0, result.stderr)
            metadata = json.loads((output / "template.json").read_text())
            self.assertEqual(metadata["version"], "1.2.3")
            expected_john = json.loads(
                (JOHN_PLUGIN / ".claude-plugin/plugin.json").read_text()
            )["version"]
            self.assertEqual(metadata["requires_john"], expected_john)
            self.assertEqual(metadata["providers"], ["claude", "codex"])
            self.assertFalse((output / "apply.sh").is_symlink())
            self.assertTrue(os.access(output / "apply.sh", os.X_OK))
            report = summary(fork)
            self.assertEqual(report["status"], "published")
            self.assertTrue(report["validation"]["valid"])
            self.assertEqual(
                report["apply_sha256"],
                hashlib.sha256((output / "apply.sh").read_bytes()).hexdigest(),
            )
            self.assertNotIn(str(root), json.dumps(report))

    def test_warning_validation_symlink_and_timeout_leave_no_partial_package(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fork = self.make_fork(root)
            add_dual_template_changes(fork)
            (fork / "unsupported.txt").write_text("unsupported")
            output = root / "templates/test-template"
            result = package(fork, output)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(output.exists())
            self.assertTrue(summary(fork)["warnings"])

            result = package(fork, output, "--allow-warnings")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_dir())

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fork = self.make_fork(root)
            add_dual_template_changes(fork)
            skill = fork / "plugins/joharnessburg/skills/template-feature/SKILL.md"
            skill.write_text(skill.read_text() + "\nTODO: unfinished\n")
            output = root / "templates/test-template"
            result = package(fork, output)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(output.exists())
            self.assertFalse(summary(fork)["validation"]["valid"])

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fork = self.make_fork(root)
            add_dual_template_changes(fork)
            external = root / "external"
            external.write_text("outside")
            os.symlink(external, fork / "plugins/joharnessburg/skills/template-feature/link")
            output = root / "templates/test-template"
            result = package(fork, output)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(output.exists())

    def test_nul_diff_rename_is_delete_plus_add_and_exact_pin_override(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fork = self.make_fork(root)
            plugin = fork / "plugins/joharnessburg"
            subprocess.run(
                ["git", "mv", "plugins/joharnessburg/skills/chunking", "plugins/joharnessburg/skills/renamed-chunking"],
                cwd=fork, check=True,
            )
            skill = plugin / "skills/renamed-chunking/SKILL.md"
            skill.write_text(skill.read_text().replace("name: chunking", "name: renamed-chunking", 1))
            (fork / "project_addon.md").write_text("# Shared guidance\n")
            output = root / "templates/test-template"
            result = package(fork, output, "--requires-john", "0.5.0")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("chunking", (output / "skills/_delete").read_text().splitlines())
            self.assertTrue((output / "skills/renamed-chunking/SKILL.md").is_file())
            self.assertEqual(json.loads((output / "template.json").read_text())["requires_john"], "0.5.0")

    def test_template_version_is_required(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fork = self.make_fork(root)
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "package_template.py"), "--fork", str(fork), "--output", str(root / "out")],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2)

    def test_output_traversal_and_smoke_timeout_publish_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fork = self.make_fork(root)
            add_dual_template_changes(fork)
            escaped = root / "templates/../escaped"
            result = package(fork, escaped)
            self.assertEqual(result.returncode, 1)
            self.assertFalse((root / "escaped").exists())

            output = root / "templates/test-template"
            result = package(fork, output, "--smoke-test", "--timeout", "0")
            self.assertEqual(result.returncode, 1)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
