# byteXpand Agent Skills

[![validate](https://github.com/Ro-Fo/skills/actions/workflows/validate.yml/badge.svg)](https://github.com/Ro-Fo/skills/actions/workflows/validate.yml)

Open-source Agent Skills and Claude Code plugins for engineering and platform work.

Two rules for everything in here:

1. **Every skill ships with its evidence.** Each one carries a `references/evidence.md` labelling every rule *spec / measured / vendor / reasoned*, plus a section on what isn't established. If a rule can't be argued with, it shouldn't be followed.
2. **Every skill ships with its evals.** Test prompts and trigger queries live in the plugin's `evals/` directory. Where they haven't been run, that's stated rather than implied.

---

## Install

```shell
/plugin marketplace add Ro-Fo/skills
/plugin install skill-quality@bytexpand
```

From the terminal instead of inside a session:

```bash
claude plugin marketplace add Ro-Fo/skills
claude plugin install skill-quality@bytexpand
```

Updates:

```shell
/plugin marketplace update bytexpand
```

Not using Claude Code? Every skill is a plain directory containing `SKILL.md`. Copy it into `.claude/skills/` in your project, into `~/.claude/skills/`, or upload it wherever your agent platform takes Agent Skills.

---

## Plugins

| Plugin | Skills | What it's for |
|---|---|---|
| [`skill-quality`](plugins/skill-quality) | `reviewing-agent-skills` | Adversarial review of an Agent Skill before it ships — delete list, triggering, context cost, verifiability, permissions, supply chain, interference |

---

## The guide

**[Write the skill. Then attack it.](guides/writing-agent-skills.md)** — a working guide to authoring and reviewing Agent Skills. Free, CC BY 4.0, versioned.

It's the reasoning behind `skill-quality`, and it's readable on its own. Short version:

- The failure mode that costs you isn't malformed YAML. It's a spec-compliant, well-structured skill that quietly makes the output worse.
- Across analysed public skill corpora, the dimension separating useful from useless is **novelty** — content the model doesn't already have. Most skills mainly restate what it already knew, and pay for it on every run.
- Structure is what the tools measure. Content is what decides.
- The agent that drafted a skill is the wrong agent to review it: a model given contradictory instructions doesn't raise an error, it smooths the conflict over silently.

The guide has a shelf life and says so. This whole layer is a product decision that two vendors revise on their own schedule — re-read your skills at every model or harness change.

---

## Layout

```
.claude-plugin/marketplace.json   the marketplace itself — one entry per plugin
plugins/<plugin>/                 one plugin = one thing a user installs
  .claude-plugin/plugin.json      name and version, must match the marketplace entry
  skills/<skill>/SKILL.md         the skill; references/ and scripts/ beside it
  evals/                          triggering and behaviour cases, one directory per case
guides/                           long-form prose, CC BY 4.0, versioned
.github/scripts/                  the repository checks CI runs
```

**Where a new skill goes.** Into an existing plugin's `skills/` when it belongs to the same job, or into a new `plugins/<name>/` with its own `plugin.json` and an entry in `marketplace.json` when it doesn't. CI holds both to the same bar: the plugin `source` has to resolve, the names and versions have to agree, the skill has to pass the mechanical checker in strict mode, and it has to carry its evidence plus at least one eval case tagged `negative`.

**The marketplace is read from the default branch.** A plugin sitting on a feature branch is not installable however green its CI is — merging is what publishes. If `/plugin marketplace add` finds nothing, that is usually the reason.

**What doesn't belong here.** This repository is public and curated. Skills carrying client names, rates, addresses or private research stay in `~/.claude/skills/`, or in a private repository if they need to be shared. A private marketplace is the same shape as this one — it's just a second repo, and a plugin can be installed from both.

---

## Contributing

Issues and PRs welcome. The most useful contribution isn't a new rule — it's evidence against an existing one. See [CONTRIBUTING.md](CONTRIBUTING.md).

A skill runs with your agent's privileges and can tell it what to do next, so security reports go privately rather than into the tracker — [SECURITY.md](SECURITY.md).

If you're adding a skill, the bar is the one the guide sets: it has to contain something the model doesn't already know, and it has to come with evals.

---

## Licence

- **Code and skills** (everything under `plugins/`): [MIT](LICENSE)
- **Guides** (everything under `guides/`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — copy it, fork it, teach from it, ship it internally. Attribution appreciated, permission not required.

---

Maintained by [Robert Förster](https://bytexpand.com) — Principal Cloud Architect, freelance.
