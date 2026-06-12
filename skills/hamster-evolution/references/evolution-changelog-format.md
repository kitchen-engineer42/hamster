# The evolution changelog — format

Ships inside the template as `CHANGELOG.md` (append newest version at top). It is the template's evolution record — and the upstream dataset: John's maintainers read accumulated changelogs *across* templates to spot teaching-level failures (the same class of fix recurring in different domains means core, not the templates, is wrong). Write it for both audiences.

## Format

```markdown
# <template-name> changelog

## <version> — <date>

Evidence base: <N> run reports (<M> independent runs: distinct corpora/users/devices),
John versions <range observed>; prior version <vPrev>.

### Changes

1. **<file/passage changed>** — <one-line what>.
   Chain: <symptom> → <run behavior> → <template passage that licensed it> → <this change>.
   Evidence: <k> runs (<which kind: scorecard | domain score | end-user correction>).
   Expected effect: <observable — which scorecard line or score should move>.

2. ...

### Rejected (do not re-litigate without new evidence)

- **<considered change>** — rejected because <reason: insufficient recurrence /
  failed the held-out check / belongs ad-hoc / contradicts change #N>.

### Escalations (core proposals — for the owner to file upstream)

- **<John core skill/passage>** — <the domain-invariant failure observed>; suggested
  upstream change: <one line>. Observed in <k> runs. (Not patched here — templates
  don't edit core teaching.)

### Feedback design

<unchanged | added/updated: scorer, eval set, feedback_design — and why>
```

## Rules

- **Every change has a chain and a count.** A change without evidence is a regression risk wearing a changelog entry.
- **No corpus content, ever.** Counts and kinds of evidence, never quotes, names, clause numbers, or paths. The changelog ships publicly with the template.
- **Rejected entries are load-bearing.** They are the rejected-edit memory of the next evolution cycle — omitting them guarantees re-litigation.
- **Expected effects must be observable.** "Workers extract better" is not checkable; "the extract phase's gate stops failing on table-heavy corpora" is. The next cycle's first job is comparing these predictions against the new reports — say so plainly when a prediction missed.
