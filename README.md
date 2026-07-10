# Hamster

> 中文版: [`README_ZH.md`](README_ZH.md)

Hamster produces a **versioned, validated John template**: a portable diff that teaches John how to build one family of knowledge-dense apps. You provide a clean John checkout, raw domain inputs, a template name, and the intended app experience. Hamster creates a writable fork, packages only supported changes, exact-pins John, and real-applies the result before publishing it.

Use Hamster with **Claude Code, Codex, or both**. Shared skills and methodology are byte-identical; only provider execution guidance differs.

## Install and update

Clone both repositories once:

```sh
git clone https://github.com/kitchen-engineer42/hamster ~/hamster-cli
git clone https://github.com/kitchen-engineer42/joharnessburg ~/joharnessburg
```

Update both clean clones when you want the latest release for a new workspace:

```sh
git -C ~/hamster-cli pull --ff-only
git -C ~/joharnessburg pull --ff-only
```

Hamster v0.3.1 is aligned with John v0.5.1.

## Bootstrap a workspace

Create an empty working directory, then choose a provider. The default is `both`.

```sh
mkdir -p ~/my-template-build
cd ~/my-template-build

# Both providers (default)
~/hamster-cli/bootstrap_hamster.sh
# Equivalent: ~/hamster-cli/bootstrap_hamster.sh --provider both

# Claude Code only
~/hamster-cli/bootstrap_hamster.sh --provider claude

# Codex only
~/hamster-cli/bootstrap_hamster.sh --provider codex
```

Every selection installs `HAMSTER.md`. Claude receives `CLAUDE.md` plus `.claude/skills/`; Codex receives `AGENTS.md` plus `.agents/skills/`. Existing files and skill directories are skipped, never overwritten.

## Launch and first prompt

Launch the provider you bootstrapped:

```sh
cd ~/my-template-build
claude
```

```sh
cd ~/my-template-build
codex
```

Use the same first prompt in either runtime:

> John is at `~/joharnessburg`. Inputs are at `~/template-inputs/some-folder/`. Template name: `slides-from-physics-textbooks`. Build a template for apps that turn a physics chapter into an interactive slide deck.

## Workflow and outputs

Hamster follows one provider-neutral authoring loop:

1. **Orient** — load `HAMSTER.md` and `hamster-orientation`.
2. **Design** — classify inputs and settle the knowledge format, knowledge schema, app mechanism, and build pipeline.
3. **Fork** — clone the clean John source into `forks/<name>/`.
4. **Package** — translate supported fork changes into `templates/<name>/` with an explicit template version and exact John pin.
5. **Validate** — check syntax/contracts, relocation, canonical `apply.sh`, real application, and project initialization before atomic publication.

Builder-only provenance stays at `forks/<name>/.hamster/package_summary.json`; distribute only `templates/<name>/`.

Claude users apply the template and launch the merged plugin with `claude --plugin-dir`. Codex users apply the same template, activate that merged plugin project-locally through John's `codex-template-activation` skill, disable vanilla John for that project, review hooks, and restart.

## Snapshot and update model

Bootstrapped workspaces are **non-overwriting snapshots**. Updating the Hamster or John clones changes what a newly bootstrapped workspace receives; it does not mutate an existing build.

Keep an active build pinned when reproducibility matters. To adopt new shared guidance, deliberately create a fresh workspace and recreate the build against the new John version. Hamster provides no destructive refresh or automatic migration flag.

## Examples and layout

`examples/slides-from-textbook/` and `examples/doc-verification/` are complete dual-provider format demonstrations. Both are v0.1.3 and exact-pin John v0.5.1.

```text
HAMSTER.md                         shared session guide
CLAUDE.md / AGENTS.md             thin provider adapters
bootstrap_hamster.sh              non-overwriting workspace installer
skills/hamster-*/                 authoring methodology and strict tooling
examples/                         dual-provider John templates
tests/                            bootstrap, packaging, relocation, apply tests
VERSION                           Hamster release version
```

## Version and license

Current version: **0.3.1**. Hamster is released under the MIT License; see [`LICENSE`](LICENSE).
