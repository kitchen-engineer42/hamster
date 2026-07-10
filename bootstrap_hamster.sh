#!/bin/sh
# Set up a provider-aware Hamster template-authoring workspace.

set -eu

usage() {
  echo "Usage: bootstrap_hamster.sh [--provider claude|codex|both]" >&2
}

provider=both
while [ "$#" -gt 0 ]; do
  case "$1" in
    --provider)
      [ "$#" -ge 2 ] || { usage; exit 2; }
      provider=$2
      shift 2
      ;;
    --provider=*)
      provider=${1#--provider=}
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

case "$provider" in
  claude|codex|both) ;;
  *) echo "Error: --provider must be claude, codex, or both." >&2; exit 2 ;;
esac

HAMSTER_CLI=${HAMSTER_CLI:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}
if [ ! -d "$HAMSTER_CLI/skills" ] || [ ! -f "$HAMSTER_CLI/HAMSTER.md" ] || [ ! -f "$HAMSTER_CLI/CLAUDE.md" ] || [ ! -f "$HAMSTER_CLI/AGENTS.md" ]; then
  echo "Error: $HAMSTER_CLI is missing skills/, HAMSTER.md, CLAUDE.md, or AGENTS.md." >&2
  exit 1
fi
if find "$HAMSTER_CLI/skills" -type l -print -quit | grep . >/dev/null; then
  echo "Error: Hamster skill sources may not contain symlinks." >&2
  exit 1
fi

mkdir -p notes forks templates
installed=0
skipped=0

install_skills() {
  destination=$1
  mkdir -p "$destination"
  for source in "$HAMSTER_CLI"/skills/*; do
    [ -d "$source" ] || continue
    name=${source##*/}
    target=$destination/$name
    if [ -e "$target" ] || [ -L "$target" ]; then
      skipped=$((skipped + 1))
      continue
    fi
    stage=$destination/.$name.stage-$$
    rm -rf "$stage"
    if ! cp -R "$source" "$stage"; then
      rm -rf "$stage"
      echo "Error: failed to stage $name for $destination." >&2
      exit 1
    fi
    mv "$stage" "$target"
    installed=$((installed + 1))
  done
}

install_memory() {
  source=$1
  target=$2
  if [ -e "$target" ] || [ -L "$target" ]; then
    skipped=$((skipped + 1))
  else
    cp "$source" ".$target.stage-$$"
    mv ".$target.stage-$$" "$target"
    installed=$((installed + 1))
  fi
}

install_memory "$HAMSTER_CLI/HAMSTER.md" HAMSTER.md

if [ "$provider" = claude ] || [ "$provider" = both ]; then
  install_skills .claude/skills
  install_memory "$HAMSTER_CLI/CLAUDE.md" CLAUDE.md
fi
if [ "$provider" = codex ] || [ "$provider" = both ]; then
  install_skills .agents/skills
  install_memory "$HAMSTER_CLI/AGENTS.md" AGENTS.md
fi

echo "Hamster workspace ready: $(pwd)"
echo "Provider: $provider"
echo "Installed: $installed"
echo "Skipped existing: $skipped"
echo "Next: start your selected coding provider in this directory."
