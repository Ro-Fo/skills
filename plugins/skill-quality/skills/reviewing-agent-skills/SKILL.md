---
name: reviewing-agent-skills
description: Adversarially reviews a written Agent Skill before it ships — deletes instructions the model already knows, finds facts that should be a tool call instead of copied text, checks triggering, context cost, verifiability, permissions, bundled-file supply chain, and interference with already-installed skills, then returns a verdict with a line-level delete list. Use whenever a SKILL.md has just been drafted or edited, before publishing or installing a skill, when reviewing a third-party or downloaded skill, or when an existing skill is suspected of bloat, mis-triggering, or making output worse. Also use for phrasings like "review my new skill", "is this skill any good", "audit this SKILL.md", "why does my skill never trigger", "check this skill before I publish it".
license: MIT
---

# Reviewing agent skills

This skill runs the adversarial pass **after** a skill has been written. It is the complement to `skill-creator`, not a replacement: `skill-creator` runs the create → test → iterate loop and owns eval running, benchmarking and description optimisation. This skill assumes a draft exists and asks whether it should ship.

## Why a separate pass exists

An agent that writes a skill is the wrong agent to judge it. Two findings drive the whole design:

- When a model meets contradictory instructions it does not raise an error — it smooths the conflict over with judgement, silently, and the resolution varies by run. The component that resolves a conflict cannot be the component that detects it, so detection has to happen outside the drafting loop (arXiv 2603.08993).
- Modules sharing a context window interfere even with no shared variable or dependency, at effect sizes that shift behaviour without flipping any single decision — invisible to normal QA, compounding across runs (arXiv 2606.26356).

Practical consequence: **prefer a fresh session.** If this review is running in the same conversation that drafted the skill, say so once in the report and treat every "I explained why this line is needed" instinct as suspect. The drafting rationale is not evidence.

The second design constraint is empirical. Across analysed public skill corpora, structural compliance does not predict whether a skill helps: the separating dimension is novelty — how much the content adds to what the model already knows — and most skills mainly restate common knowledge. At least one documented case shows a professionally authored skill degrading output substantially. So the passes below are ordered to attack content first and structure second.

## Inputs

Before starting, establish:

1. **Path to the skill directory** (or the SKILL.md contents if no filesystem access).
2. **What the skill is supposed to fix** — the failure the author saw without the skill. If the author cannot name one, that is the first finding; a skill written from imagined problems is the most common failure mode and no later pass compensates.
3. **What else is installed** — the names and descriptions of neighbouring skills, for the interference pass. Skip only if genuinely unavailable, and say so in the report.
4. **Trust level** — authored in-house, or downloaded. Downloaded skills escalate the supply-chain pass from a check to a blocker.

Ask for anything missing in one message; do not run a half-blind review silently.

## Workflow

Copy this checklist into the response and tick items off:

```
Skill review:
- [ ] Step 1: Read every file in the skill, including references/ and scripts/
- [ ] Step 2: Run the mechanical check script
- [ ] Step 3: Redundancy probe — does a clean agent comply without the skill?
- [ ] Step 4: Content passes (delete-first, sources of truth, routes)
- [ ] Step 5: Behaviour passes (triggering, freedom, verification, permissions)
- [ ] Step 6: Risk passes (supply chain, interference)
- [ ] Step 7: Write the report — verdict, delete list, blockers
```

### Step 1: Read everything

Read SKILL.md, every file under `references/`, `assets/` and `scripts/`, and anything at the skill root. Do not review from SKILL.md alone. Both the quality research and the security research land on the same point from opposite directions: contamination and payloads sit one level down, where SKILL.md-only inspection never looks.

If the skill is large, read the reference files fully rather than previewing — a partial read is exactly the failure the one-level-deep rule exists to prevent.

### Step 2: Mechanical check

```bash
python3 scripts/check_structure.py <path-to-skill>
```

Stdlib only, no install. It reports frontmatter validity, body length and estimated tokens, per-file token counts against the community thresholds, unreferenced (orphan) files, broken internal links, unclosed code fences, deep nesting, and description shape (length, person, keyword-stuffing). Use `--json` for machine-readable output.

The script covers what is countable. It says nothing about whether the content is worth loading, which is Steps 4–6. Do not let a clean script run become the verdict.

### Step 3: Redundancy probe

Pass 1 asks whether the model already knows a line. Asking *this* agent is worthless — it has just read the line, and a model that has read an instruction cannot introspect back to what it would have done without it. Measure it instead.

```bash
python3 scripts/probe_redundancy.py <path-to-skill> --plan
```

Give a clean agent the task the instruction governs *without* the instruction, and see whether the output complies anyway. Never ask "should I do X" — models agree with whatever is put to them, and the answer is a confident, worthless yes.

**Batch it.** One task usually scores several instructions at once, because they govern the same output. Six rules from one prompt is five runs, not thirty.

**A plain subagent is not clean.** It loads the skill under review from its description and answers in that skill's own format — observed, not hypothesised. Use a separate process with skills and MCP off, then check each run before scoring it:

```bash
claude -p --disable-slash-commands --strict-mcp-config < probe.txt > run1.txt
python3 scripts/probe_redundancy.py <path-to-skill> --check-run run1.txt
python3 scripts/probe_redundancy.py <path-to-skill> --tally results.json
```

Five runs; one run is luck. **If every result comes back 5/5, the probe is unvalidated** — you cannot tell "all redundant" from "task too easy". A batch that produces no 0/5 anywhere has not shown it can detect non-compliance.

| Complies | Reading | Default |
|---|---|---|
| 5/5 | the model does this unprompted | delete |
| 3–4/5 | buys reliability, not knowledge | judgement |
| 0–2/5 | the line is doing work | keep |

**The guardrail:** compliance alone does not decide. The probe measures what the model does by default, never what a miss costs. Delete on high compliance **and** low blast radius — a line the model follows five times in five is still cheap insurance if the sixth would write to production. The tally refuses to score a result that omits the model, harness and date, because the whole point is comparing this run against the next model generation.

Skip this step only when the skill is entirely organisation-specific, and say so in the report. Full procedure, including how to write a probe that does not leak its own answer: `references/redundancy-probe.md`.

### Steps 4–6: The nine passes

Read `references/review-passes.md` and work through the passes in order. Each pass has its trigger questions, what a finding looks like, and the severity rule. The order matters — the delete-first pass shrinks the artefact that every later pass has to examine.

Summary of the passes, in order:

| # | Pass | Asks |
|---|---|---|
| 1 | Delete-first | Which lines would be true at any company, or restate what the model already does? Answered by Step 3's probe, not by opinion. |
| 2 | Second sources of truth | Which lines copy a fact that lives in a system and will silently go stale? |
| 3 | Routes | Can the agent find the real context, or must it guess? |
| 4 | Triggering | Will it fire when it should, and stay quiet when it shouldn't? |
| 5 | Freedom calibration | Is rigidity matched to fragility, and is every rule given a reason? |
| 6 | Context cost | What does this cost on every run, and does each part earn it? |
| 7 | Verification | Can the work be checked, and can the agent reach the criteria? |
| 8 | Permissions | Does it imply authority it has no business granting? |
| 9 | Supply chain and interference | Does any bundled file do something the description doesn't claim, and does it collide with installed skills? |

Do not skip a pass because it "obviously passes". Record it as checked with one line of evidence. Passes recorded without evidence are the ones that were not run.

### Step 7: Report

Use the structure in `references/report-template.md`. The core of it:

- **Verdict**: `ship`, `ship after fixes`, or `do not ship` — with the single reason that decided it.
- **Delete list**: exact lines to remove, quoted, with the pass that flagged them. This is the most valuable output; put it high.
- **Blockers**: findings that must be fixed before the skill is installed anywhere.
- **Findings**: everything else, by pass, with severity and a concrete fix.
- **Not checked**: what could not be verified and why.

Give the delete list before the improvement list. Every review tends to grow the skill; the evidence says the dominant failure is that skills are too long and too generic. If a review produces only additions, that is a signal the review was too soft, not that the skill was clean.

## Severity

- **Blocker** — ships broken or unsafe: invalid frontmatter, broken internal link, unclosed fence, instruction-shaped text in a data/reference file, bundled code doing something outside the stated purpose, agent-writable verification criteria.
- **Major** — measurably degrades output or cost: generic craft instructions, copied facts, missing route, body far over budget, description that won't trigger, rigid rules where judgement is needed.
- **Minor** — friction: inconsistent terminology, missing table of contents on a long reference, time-sensitive phrasing, naming that doesn't match convention.

Do not inflate. A report where everything is a blocker gets ignored the same way a report where nothing is.

## Re-review cadence

A skill is not reviewed once. Two questions belong in the review at every model or harness change, and both are in the passes file:

- Which instruction is now redundant because the model learned it? A well-built skill shrinks with every model generation.
- Which check is now gameable because the model got better? Verification has to be re-hardened at the same cadence as the capability it measures.

Record in the report which model and skill version the review was run against. A review with no pinned versions cannot be compared to the next one.

## Handing back to skill-creator

This skill produces findings; it does not run evals. When the report calls for measurement rather than judgement — "does this description actually trigger", "is the with-skill output better than baseline" — hand off to `skill-creator`, which owns the eval loop, the benchmark aggregation and the description optimiser. Say so explicitly in the report rather than approximating those results here.

## Reference files

- `references/review-passes.md` — the nine passes in full: questions, finding shapes, severity rules.
- `references/redundancy-probe.md` — how to measure whether the model already knows a line, without leaking the answer into the question.
- `references/report-template.md` — the report structure and a worked example.
- `references/evidence.md` — the sources behind each rule, so a rule can be argued with rather than obeyed.
