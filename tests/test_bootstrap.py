import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.helpers import REPO


class TestBootstrap(unittest.TestCase):
    def run_bootstrap(self, root: Path, provider: str = "both"):
        return subprocess.run(
            [str(REPO / "bootstrap_hamster.sh"), "--provider", provider],
            cwd=root,
            env={**os.environ, "HAMSTER_CLI": str(REPO)},
            capture_output=True,
            text=True,
        )

    def test_dual_provider_installs_byte_identical_skills_and_skips_existing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = self.run_bootstrap(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "HAMSTER.md").is_file())
            self.assertTrue((root / "CLAUDE.md").is_file())
            self.assertTrue((root / "AGENTS.md").is_file())
            for source in sorted((REPO / "skills").rglob("*")):
                if not source.is_file():
                    continue
                relative = source.relative_to(REPO / "skills")
                claude = root / ".claude/skills" / relative
                codex = root / ".agents/skills" / relative
                self.assertEqual(hashlib.sha256(claude.read_bytes()).digest(), hashlib.sha256(codex.read_bytes()).digest())
            protected = root / ".agents/skills/hamster-orientation/SKILL.md"
            protected.write_text("user-owned\n")
            shared = root / "HAMSTER.md"
            shared.write_text("user-shared\n")
            result = self.run_bootstrap(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(protected.read_text(), "user-owned\n")
            self.assertEqual(shared.read_text(), "user-shared\n")

    def test_single_provider_and_invalid_provider(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = self.run_bootstrap(root, "codex")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "HAMSTER.md").is_file())
            self.assertFalse((root / ".claude").exists())
            self.assertTrue((root / ".agents/skills").is_dir())
            self.assertFalse((root / "CLAUDE.md").exists())
            self.assertTrue((root / "AGENTS.md").is_file())
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = self.run_bootstrap(root, "claude")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "HAMSTER.md").is_file())
            self.assertTrue((root / ".claude/skills").is_dir())
            self.assertFalse((root / ".agents").exists())
            self.assertTrue((root / "CLAUDE.md").is_file())
            self.assertFalse((root / "AGENTS.md").exists())
        with tempfile.TemporaryDirectory() as td:
            result = self.run_bootstrap(Path(td), "wrong")
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
