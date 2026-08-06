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
| `.../scripts/check_structure.py` | The mechanical check. Stdlib only, no install |
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

## Scope

This reviews **one** skill, once, before it goes out. It is not a periodic audit
of an installed collection, and it does not run evals — measurement (does this
description actually trigger, is the with-skill output better than baseline)
belongs to `skill-creator`, which owns the eval loop.
