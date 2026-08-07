# Evals for `skill-quality`

Four cases, in the shape `claude plugin eval` expects (`evals/**/case.yaml`,
`schema_version: "1.0"`):

| Case | Asks |
|---|---|
| `triggering/fires-on-draft-review` | Does the skill load when one drafted SKILL.md is handed over before publication? |
| `triggering/stays-quiet-on-bulk-audit` | Does it stay out of the way when the request is a collection-wide stocktake? |
| `review/produces-a-delete-list` | Does the review delete generic instructions and copied facts, or only add suggestions? |
| `review/probe-respects-blast-radius` | Does the redundancy probe delete craft but keep cheap insurance against an irreversible action? |

The negative case is the load-bearing one. A pre-publication review of a single
skill and a bulk audit across an installed collection are different jobs that
sound alike, so the two descriptions compete for the same trigger space. That
boundary is a property worth regression-testing, not a wording preference.

## Status: authored, not yet run

**These cases have not been executed.** They are written against the schema and
have not produced a score, a baseline delta, or a pass rate. Nothing in this
repository should be read as claiming a measured result for this plugin.

Two reasons, both worth stating plainly rather than implying:

- `claude plugin eval` is marked early access in the CLI (2.1.223) and its
  interface may still move.
- Running them costs model calls, which the repository's CI does not spend.

The graders are therefore also unvalidated: `tool_used` with
`input_match: reviewing-agent-skills` is the intended way to assert that the
skill did or did not load, but that assertion has not been observed passing.

## Running them

```bash
claude plugin eval skill-quality@bytexpand
```

Or against a working copy, without installing:

```bash
claude plugin eval plugins/skill-quality
```

Useful flags: `--ablation with-without` for a no-plugin baseline arm,
`--case '*trigger*'` to filter, `--runs 5` to trade cost for variance,
`--report out.html` for a readable write-up.

When a case is first run, replace this section with what it actually scored —
including the runs, the model, and the date. A result with no pinned model is
not comparable to the next one.
