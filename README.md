# hamster

A provider-neutral bundle of byte-identical skills plus Claude/Codex guidance that helps either coding runtime build templates for [John](https://github.com/kitchen-engineer42/joharnessburg).

Hamster is loaded into a vanilla Claude Code or Codex session in a working dir. You point it at your clean local joharnessburg checkout, hand it raw inputs, and let it build a template diff against original John.

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
~/hamster-cli/bootstrap_hamster.sh --provider both
```

Or manually:

```sh
mkdir ~/my-template-build && cd ~/my-template-build
mkdir -p .claude/skills .agents/skills notes forks templates
cp -R ~/hamster-cli/skills/* .claude/skills/
cp -R ~/hamster-cli/skills/* .agents/skills/
cp ~/hamster-cli/CLAUDE.md .
cp ~/hamster-cli/AGENTS.md .
```

## Launch

```sh
cd ~/my-template-build
claude   # or start Codex in the same directory
```

Your first prompt should include:

- the path to your local joharnessburg checkout
- the path to your template input folder
- a name for the template
- a brief about what kind of apps the template should produce

Example:

> joharnessburg is at `~/joharnessburg`. Inputs are at `~/template-inputs/some-folder/`. Template name: `slides-from-physics-textbooks`. We want apps that take a physics chapter and produce a slide deck.

Hamster orients itself, studies the inputs, forks a clean John checkout into `forks/<name>/`, modifies the fork, and transactionally packages the validated diff into `templates/<name>/`. Packaging requires an explicit template version, exact-pins the base John version by default, copies canonical `apply.sh`, and performs a real application against a clean base snapshot. Strict warnings publish nothing.

Claude users keep the existing `apply.sh` + `claude --plugin-dir` flow. Codex users apply the same template, then follow John's project-local activation instructions; the applied plugin replaces vanilla John for that project session.

## What ships in this repo

```
hamster/
├── README.md
├── LICENSE                       # MIT
├── CLAUDE.md                     # Hamster session framing (copied to your working dir)
├── AGENTS.md                     # Codex session framing
├── VERSION                       # plain text version pointer
├── bootstrap_hamster.sh          # convenience setup script
├── skills/
│   ├── hamster-orientation/
│   ├── hamster-drawing-board/
│   ├── hamster-product-thinking/
│   ├── hamster-workshop/
│   ├── hamster-packaging/
│   └── hamster-evolution/        # evolve an existing template from run reports
├── tests/                        # stdlib transactional/validation tests
└── examples/                     # reference John templates (functional demonstrators of the diff format)
    ├── slides-from-textbook/     # lighter — 1 override + 1 addition
    └── doc-verification/         # heavier, KC-style — 2 overrides + 2 additions
```

The `examples/` dir holds complete dual-provider John template directories. Both are v0.1.2, exact-pin John v0.5.0, preserve their Claude guidance, and add Codex guidance/agents.

## License

MIT. See [`LICENSE`](LICENSE). External contributions welcome.

## Version

See [`VERSION`](VERSION). Versioning is separate from joharnessburg's.
