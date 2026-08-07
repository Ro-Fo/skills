# Security

An Agent Skill is a dependency with two properties an npm package doesn't have:
it runs with the agent's privileges, **and** it carries instruction authority —
it can tell the agent what to do next. That is the threat model this file is
written against, and it is why the repository ships review tooling rather than
just skill text.

## Reporting a vulnerability

**Do not open a public issue.** Use GitHub's private vulnerability reporting on
this repository: **Security → Report a vulnerability**. That opens a private
advisory visible only to the maintainer.

If that is unavailable to you, email the address in
[`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) with
`SECURITY` in the subject.

This is a single-maintainer project. You will get a human rather than a rota, so
please include enough to reproduce without a follow-up round:

- which file and which version or commit
- what an agent does when it loads it, and what it should have done
- whether the payload survives inspection of `SKILL.md` alone

Please give a reasonable window before disclosing publicly. Credit in the
advisory unless you'd rather not be named.

## In scope

- **Instructions in skill text or bundled files that do something the
  description doesn't claim.** Includes payloads hidden in code examples and
  config templates inside a skill's own documentation — the case that evades
  both static scanning and model-level alignment most often.
- **`scripts/check_structure.py` doing anything beyond reading the directory it
  is pointed at.** It is stdlib-only and makes no network calls. If it does
  anything else, that is a vulnerability.
- **A marketplace or plugin manifest resolving somewhere unexpected** — a
  `source` path escaping the repository, a name that shadows another
  marketplace's plugin.
- **Anything in `.github/`** that runs on contributor input.

## Out of scope

- The model deciding to do something unwise with a correctly-described skill.
  That is a capability question, not a vulnerability in this repository.
- Skills you install from elsewhere. Report those to their maintainer.
- Trigger collisions or a skill firing when it shouldn't — that is a bug, and a
  normal issue is the right place.

## What this repository does to earn trust

- **Everything is plain text in git.** No build step, no install script, no
  post-install hook, no runtime download. What you read in the diff is what
  runs.
- **The one executable, `check_structure.py`, is standard library only.** No
  dependencies to resolve, nothing fetched at run time.
- **Review reads bundled files, not just `SKILL.md`.** The skill this repository
  ships treats a bundled file doing something outside the stated purpose as a
  blocker, not a finding — because contamination and payloads both sit one level
  down, where `SKILL.md`-only inspection never looks.
- **CI checks that every plugin `source` resolves inside the repository**, which
  the plugin spec validator does not.

## What you should do

The same thing you would do with any unsigned dependency, and for the same
reasons:

1. **Pin a version.** Install a tagged release rather than tracking a branch.
2. **Read the diff before updating**, including `references/` and `scripts/` —
   not only `SKILL.md`.
3. **Don't install skills at runtime**, from an agent, mid-task.
4. **Give the agent the privileges the task needs and no more.** A skill cannot
   grant authority it wasn't given, and that is the strongest control available.

Section 6 of [the guide](guides/writing-agent-skills.md) sets out the research
behind each of these, with the caveat that it is the section most likely to be
out of date by the time you read it.
