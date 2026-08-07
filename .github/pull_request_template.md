## What this changes

<!-- One or two sentences. If this deletes content, say what stopped being true. -->

## Why

<!-- For a new or changed rule: what failed without it, and what makes it worth
     the tokens it costs on every run. For a deletion: what makes it safe to
     lose. Link the issue if there is one. -->

## Checks

- [ ] `python3 .github/scripts/check_marketplace.py` passes
- [ ] `claude plugin validate .` and `claude plugin validate plugins/<plugin>` pass
- [ ] Skills changed here pass `check_structure.py --strict`
- [ ] `references/evidence.md` updated if a rule changed, with its label
- [ ] Evals updated if behaviour or triggering changed
- [ ] `plugin.json` and the marketplace entry agree on version, or neither moved

## Reviewed by the skill

<!-- This repository ships a skill whose job is to attack a skill before it
     ships. Run it on your own change, in a fresh session — the agent that
     drafted a change is not neutral about whether it belongs.

     Paste the verdict, or say why it doesn't apply to this change. -->

## Evals

<!-- If you ran them: the scores, the model, and the date. If you didn't: say
     so plainly. An unrun eval that reads as a passing eval is worse than no
     eval. -->
