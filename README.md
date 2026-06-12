# hamster

A bundle of skills + a CLAUDE.md that helps Claude Code build templates for [John](https://github.com/kitchen-engineer42/joharnessburg).

Hamster is loaded into a vanilla Claude Code session in a working dir. You point it at your local joharnessburg checkout, hand it raw inputs (transcripts, sample docs, product briefs), and let it build a template — a diff against original John that purpose-builds the harness for a family of knowledge-engineering apps.

## Install (per machine, once)

```sh
git clone https://github.com/kitchen-engineer42/hamster ~/hamster-cli
```

You also need a local clone of joharnessburg:

```sh
git clone https://github.com/kitchen-engineer42/joharnessburg ~/joharnessburg
```

## Per-session setup

```sh
mkdir ~/my-template-build && cd ~/my-template-build
~/hamster-cli/bootstrap_hamster.sh
```

Or manually:

```sh
mkdir ~/my-template-build && cd ~/my-template-build
mkdir -p .claude/skills notes forks templates
cp -R ~/hamster-cli/skills/* .claude/skills/
cp ~/hamster-cli/CLAUDE.md .
```

## Launch

```sh
cd ~/my-template-build
claude
```

Your first prompt should include:

- the path to your local joharnessburg checkout
- the path to your template input folder
- a name for the template
- a brief about what kind of apps the template should produce

Example:

> joharnessburg is at `~/joharnessburg`. Inputs are at `~/template-inputs/some-folder/`. Template name: `slides-from-physics-textbooks`. We want apps that take a physics chapter and produce a slide deck.

Hamster orients itself, dispatches explore subagents over your inputs, enters plan mode to propose template modifications, then forks John into `forks/<name>/`, modifies the fork, and packages the diff into `templates/<name>/`. When you're satisfied, distribute that folder however your team shares templates (its own git repo, a tarball); each user installs it at `~/.claude/plugins/joharnessburg-templates/<name>/` and runs its `apply.sh`. (The John plugin itself ships no templates — the merged-plugin flow is documented in joharnessburg's `templates/README.md`.)

## What ships in this repo

```
hamster/
├── README.md
├── LICENSE                       # MIT
├── CLAUDE.md                     # Hamster session framing (copied to your working dir)
├── VERSION                       # plain text version pointer
├── bootstrap_hamster.sh          # convenience setup script
├── skills/
│   ├── hamster-orientation/
│   ├── hamster-drawing-board/
│   ├── hamster-product-thinking/
│   ├── hamster-workshop/
│   ├── hamster-packaging/
│   └── hamster-evolution/        # v0.2.0+: evolve an existing template from its run reports
└── examples/                     # reference John templates (functional demonstrators of the diff format)
    ├── slides-from-textbook/     # lighter — 1 override + 1 addition
    └── doc-verification/         # heavier, KC-style — 2 overrides + 2 additions
```

The `examples/` dir holds complete John template directories that Hamster Claude reads as reference during the workshop phase. They live here (not in joharnessburg) because they're authoring-time references, not John runtime content — see `skills/hamster-workshop/SKILL.md` for how they're used.

## License

MIT. See [`LICENSE`](LICENSE). External contributions welcome.

## Version

See [`VERSION`](VERSION). Versioning is separate from joharnessburg's.
