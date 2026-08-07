# Contributing

The most useful contribution to this repository is **evidence against a rule
that is already in it**. Every rule in every skill is labelled in that skill's
`references/evidence.md` as *spec*, *measured*, *vendor* or *reasoned*. A rule
labelled *reasoned* is an argument, not a finding, and it should be possible to
lose that argument.

So, in rough order of value:

1. A counterexample, measurement or vendor change that makes an existing rule
   wrong, weaker, or no longer necessary. Open an issue; you do not need a PR.
2. A downgrade: a rule labelled *measured* whose source turns out not to support
   it, or a *spec* rule the spec no longer says.
3. A deletion. Skills get worse as they get longer. A PR that removes content and
   explains what stopped being true is easier to merge than one that adds.
4. A new rule, with its evidence label and source.
5. A new skill.

## Reporting evidence against a rule

Say which rule, in which file, and what makes it wrong. Useful shapes:

- **A model or harness changed.** The rule existed because the model needed
  telling. It no longer does. Say which model and which version, because that is
  what makes the finding checkable later.
- **The source does not say that.** Quote the source and the rule side by side.
- **It cost more than it returned.** A run where following the rule made the
  output worse, with enough detail to reproduce.

"I disagree" is fine as an issue too, as long as it is specific about which
sentence it disagrees with.

## Changing a skill

Before opening a PR:

```bash
# mechanical check — must be clean in strict mode
python3 plugins/skill-quality/skills/reviewing-agent-skills/scripts/check_structure.py \
        plugins/<plugin>/skills/<skill> --strict

# manifests — must pass with --strict
claude plugin validate .
claude plugin validate plugins/<plugin>

# everything CI runs, in one go (needs PyYAML)
python3 .github/scripts/check_marketplace.py
```

CI runs exactly these. It does not run the evals — those cost model calls.

Then, the part that matters: **run the review on your own change.** This
repository ships a skill whose whole job is to attack a skill before it ships,
and a contribution that has not been through it is asking reviewers to do work
the tool already does.

```shell
/plugin install skill-quality@bytexpand
```

Do it in a fresh session. The skill says why, and the reason applies to this
repository as much as to anything else: the agent that drafted a change is the
wrong agent to judge it, because a model given contradictory instructions
smooths the conflict over silently rather than raising it.

## Adding a skill

The bar is the one the README sets, and both halves are load-bearing:

- **It contains something the model does not already know.** Generic craft
  advice — "write clear code", "think step by step", "follow best practices" —
  is not a skill. It is context you pay for on every run. If you cannot name the
  failure you saw *without* the skill, there is nothing to build yet.
- **It comes with evals.** `evals/**/case.yaml`, including at least one negative
  case: a request that sounds like your skill's job but is not, which must not
  trigger it. Interference with neighbouring skills is the failure mode that
  structural checks cannot see.

If the evals have not been run, say so in the eval directory's README, in those
words. An unrun eval that reads as a passing eval is worse than no eval.

Also expected:

- `references/evidence.md`, with every rule labelled and a section on what is
  *not* established.
- A description in the third person, under 1024 characters, shaped as one prose
  sentence followed by one trigger list.
- Nothing at the skill root but `SKILL.md`. Supporting material goes in
  `references/`, `scripts/` or `assets/`.

## Versioning

`plugin.json` and the matching entry in `.claude-plugin/marketplace.json` carry
the same version, and CI fails if they disagree. Bump both in the same commit,
or neither.

The marketplace name `bytexpand` is the public identifier in
`skill-quality@bytexpand`. It cannot change without breaking every existing
install, so it does not change.

## Licence

Contributions to `plugins/` are MIT. Contributions to `guides/` are CC BY 4.0.
By opening a PR you agree your contribution ships under the licence covering
that part of the repository.
