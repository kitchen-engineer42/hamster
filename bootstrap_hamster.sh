#!/bin/sh
# bootstrap_hamster.sh — set up a Hamster working dir.
#
# Run from inside the empty working dir you want to use for one template build:
#   cd /path/to/empty-working-dir
#   /path/to/hamster-cli/bootstrap_hamster.sh
#
# Or set HAMSTER_CLI explicitly:
#   HAMSTER_CLI=/path/to/hamster-cli /path/to/hamster-cli/bootstrap_hamster.sh

set -eu

HAMSTER_CLI="${HAMSTER_CLI:-$(cd "$(dirname "$0")" && pwd)}"

if [ ! -d "$HAMSTER_CLI/skills" ] || [ ! -f "$HAMSTER_CLI/CLAUDE.md" ]; then
  echo "Error: $HAMSTER_CLI doesn't look like a Hamster checkout." >&2
  echo "  Expected: $HAMSTER_CLI/skills/ and $HAMSTER_CLI/CLAUDE.md" >&2
  exit 1
fi

if [ -e CLAUDE.md ] || [ -e .claude/skills ]; then
  echo "Error: this working dir is not empty (CLAUDE.md or .claude/skills/ already exists)." >&2
  echo "  Bootstrap refuses to overwrite. Use a fresh dir, or copy manually." >&2
  exit 1
fi

mkdir -p .claude/skills notes forks templates

cp -R "$HAMSTER_CLI/skills/"* .claude/skills/
cp "$HAMSTER_CLI/CLAUDE.md" CLAUDE.md

echo "Hamster working dir ready at: $(pwd)"
echo
echo "Next:"
echo "  claude"
echo
echo "Your first prompt should include:"
echo "  - path to your local joharnessburg checkout"
echo "  - path to your template input folder"
echo "  - a name for the template"
echo "  - a brief about what kind of apps the template should produce"
