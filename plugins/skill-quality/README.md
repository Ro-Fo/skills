# skill-quality

Adversarial review of an Agent Skill **before it ships**.

```shell
/plugin marketplace add Ro-Fo/skills
/plugin install skill-quality@bytexpand
```

## What's in it

| | |
|---|---|
| `skills/reviewing-agent-skills/` | The skill: nine review passes, ordered to attack content first and structure second |
| `.../references/review-passes.md` | The passes in full — trigger questions, what a finding looks like, severity rule |
| `.../references/report-template.md` | Report structure and a worked example |
| `.../references/evidence.md` | Every rule labelled *spec / measured / vendor / reasoned*, plus what isn't established |
| `.../references/redundancy-probe.md` | How to measure whether the model already knows a line, without leaking the answer into the question |
| `.../scripts/check_structure.py` | The mechanical check. Stdlib only, no install |
| `.../scripts/probe_redundancy.py` | Plans and tallies the redundancy probe. Stdlib only, makes no model calls itself |
| `evals/` | Trigger and review cases. **Not yet run** — see [`evals/README.md`](evals/README.md) |

## The mechanical check on its own

The script is useful without the skill and without Claude Code:

```bash
python3 plugins/skill-quality/skills/reviewing-agent-skills/scripts/check_structure.py \
        path/to/your-skill --strict
```

Frontmatter validity, body and reference token budgets, orphan files, broken
internal links, unclosed fences, nesting depth, description shape. `--json` for
machine-readable output. Exit 0 clean, 1 errors, 2 warnings only.

It covers what is countable, and that is the point: a clean run is not a verdict.
Whether the content is worth loading is the judgement work in the nine passes.

## The reasoning behind it

**[Write the skill. Then attack it.](../../guides/writing-agent-skills.md)** — CC BY 4.0, versioned. It argues the nine passes, and labels where each rule came from so you can disagree with one on evidence rather than taste.

It is deliberately **not** linked from `SKILL.md`. The guide is written for people; `SKILL.md` is loaded into an agent's context every time the skill fires. Pointing the agent at ~3.7k tokens of human-facing prose is precisely the context cost the guide tells you to delete.

## Scope

This reviews **one** skill, once, before it goes out. It is not a periodic audit
of an installed collection, and it does not run evals — measurement (does this
description actually trigger, is the with-skill output better than baseline)
belongs to `skill-creator`, which owns the eval loop.
