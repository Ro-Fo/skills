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

## Status: two cases measured, two not

The two triggering cases have been run. The two review cases have not.

| Case | Runs | Result |
|---|---|---|
| `triggering/stays-quiet-on-bulk-audit` | 3 | **pass** — the skill did not load in any run |
| `triggering/fires-on-draft-review` | 3 | **2/3 by tool call, 3/3 by behaviour** — see below |
| `review/produces-a-delete-list` | — | not run |
| `review/probe-respects-blast-radius` | — | not run |

Pinned to: claude-opus-5, Claude Code 2.1.223, default settings, 2026-08.

Method: `claude -p --output-format stream-json --verbose`, counting `Skill` tool
invocations naming this skill. Not the eval runner — `claude plugin eval` is
gated as early access — but a direct observation of the same signal, and a
stronger one than a grader reading the final message.

**The disagreement between the two numbers is the finding.** In the run that
made no `Skill` tool call, the agent still asked for the skill directory, asked
what failure the skill was written to fix, asked whether it was authored
in-house or downloaded, and said it would read every reference file and run the
structural checker before giving a verdict. That is this skill's Inputs section,
followed without the tool being invoked.

So a `tool_used` grader undercounts triggering: a model can act on a description
without calling the tool that loads it. The `tool_used` graders in these cases
inherit that blind spot and should be read as a lower bound, not as a
measurement of whether the skill influenced the run.

One caveat on the positive case: its prompt describes a SKILL.md but supplies no
path, so every run correctly stops to ask for one. That makes it a test of
triggering only, not of the review itself.

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
