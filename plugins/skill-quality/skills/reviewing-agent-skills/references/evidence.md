# Evidence behind the rules

Every rule in this skill should be arguable, not obeyed. This file names what each one
rests on and how strong that is, so a reviewer can push back with something better.

Confidence labels: **spec** (normative documentation), **measured** (published study),
**vendor** (single-vendor study, not independently replicated), **reasoned** (follows
from the above, not directly measured).

## Contents

- Structure and budgets
- Description and triggering
- Content quality and novelty
- Verification and self-scoring
- Supply chain
- Interference
- Harness and versioning
- What is not established

---

## Structure and budgets

**spec** — Frontmatter requires `name` and `description`. Name: at most 64 characters,
lowercase letters, numbers and hyphens, no XML tags, no reserved vendor words.
Description: non-empty, at most 1,024 characters, no XML tags, stating both what the
skill does and when to use it, written in third person. Body under 500 lines. References
one level deep from SKILL.md, because files referenced from referenced files get
partially read. Table of contents on reference files over roughly 100 lines. Forward
slashes in all paths.
Source: Anthropic, Skill authoring best practices,
`platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices`.

**spec/tooling** — Token thresholds in common validator use: SKILL.md body warns past
~5,000 tokens or 500 lines; a single reference file warns at ~10,000 and errors at
~25,000; total references warn at ~25,000 and error at ~50,000. Recognised directories
are `scripts/`, `references/`, `assets/`; anything else warns. Files never referenced
from a reachable path are flagged as orphans, because the agent has no signal to load
them. Unclosed code fences are errors, not warnings — everything after an unclosed
fence is read as code.
Source: `github.com/agent-ecosystem/skill-validator`, checks derived from the Agent
Skills specification at `agentskills.io`.

**measured** — In an analysis of a few hundred public skills, a clear majority of the
analysable set exceeded the 5,000-token guidance, and roughly half of all tokens across
the corpus sat in non-standard files (licences, build artefacts, schemas) that are not
skill content. Around a fifth failed structural validation outright.
Source: Dachary Carey, agent skill analysis, `agentskillreport.com` and
`dacharycarey.com`. Single researcher, corpus-specific — treat exact percentages as
directional.

## Description and triggering

**spec** — The description is the primary discovery mechanism; the model selects among
potentially many skills on name and description alone.

**spec** — Descriptions should be slightly pushy, because models measurably under-trigger
skills that would have helped.
Source: `skill-creator`, `github.com/anthropics/skills`.

**tooling** — Validators flag keyword-stuffed descriptions: five or more quoted strings
with less surrounding prose than that, or eight or more comma-separated fragments.
Source: skill-validator, above.

*These two pull in opposite directions. The resolution used in Pass 4 — prose sentence
plus one delimited trigger list — is **reasoned**, not measured. If someone measures it,
this paragraph should be replaced.*

**spec** — Simple one-step queries often fail to trigger any skill regardless of
description quality, because the model handles them directly. Trigger evaluation sets
therefore need substantive queries, and near-miss negatives rather than obviously
irrelevant ones.

## Content quality and novelty

**measured** — Across analysed public skill corpora, novelty (content beyond what the
model already knows) is the dimension that separates skills that help from skills that
don't; craft dimensions cluster tightly while novelty varies independently. Most skills
in the sample largely restate common knowledge. A documented case study found an
official vendor-authored skill degrading output substantially on the measured task, and
the same work reports no correlation between structural risk and observed degradation on
the behaviourally tested subset (small n — the absence of correlation is weak evidence,
but it is enough to stop treating a clean validator run as a quality signal).
Source: as above, `agentskillreport.com`.

**measured** — Cross-language contamination is real: showing a model code in one language
can produce syntactically incorrect output in another (programming-language confusion).
In the analysed corpus, dozens of skills carried contamination only visible in reference
files, not in SKILL.md. This is the direct reason Step 1 requires reading every bundled
file.
Source: as above, plus the programming-language-confusion literature it cites.

**spec** — "Claude is already very smart" — only add context the model doesn't have;
challenge whether each paragraph justifies its token cost.
Source: Anthropic best practices, above.

**reasoned** — The redundancy probe (a clean agent, the task the instruction governs, the
instruction withheld, n runs, count the compliant ones) follows from two established
things rather than from a study of the probe itself: that novelty is the dimension that
separates useful skills from useless ones, and that a model which has read an instruction
cannot report what it would have done without it. The inference is that the question is
answerable by ablation and not by introspection. The ablation logic is the same one
`claude plugin eval --ablation with-without` applies to a whole skill; narrowing it to a
single line is an extrapolation, not a published method.

**reasoned** — Five runs as the default, and the 5/5 - 3/5 - 0/5 bands. These are chosen
to be cheap enough to actually run and coarse enough not to imply precision the sample
size cannot support. No measurement sets them. A reviewer who moves them should say so in
the report; two reviews with different bands are not comparable.

**reasoned** — Compliance must be combined with blast radius before deleting. A high
compliance rate is a sample, not a guarantee, and the probe is blind to the tail. This is
Pass 5's rigidity-matches-fragility rule applied to redundancy, and it is the guardrail
that keeps the probe from deleting cheap insurance.

**measured, n=1 harness** — A subagent spawned from inside a review session to run a
redundancy probe loaded the skill under review from its description alone and answered in
that skill's own report format, stating that it had run its passes. Nobody supplied the
skill text. The same probe task, run as a separate process with skills disabled
(`claude -p --disable-slash-commands`), showed no trace of it across five runs. So a
plain subagent does not provide the isolation the probe depends on, at least in this
harness; verify isolation before trusting any count, by checking the output for the
reviewed skill's fingerprints.
Source: direct observation, Claude Code 2.1.223, 2026-08.

**measured, n=5** — Asked to assess a documentation directory laid out as a top-level
file plus `references/` and `scripts/`, a clean agent read one level down and surfaced
defects visible only there — an undocumented destructive call in the script and a
contradiction between the two documents — in 5 of 5 runs. The instruction to read every
bundled file is therefore redundant as knowledge on this model. It is kept anyway,
because a missed payload in a bundled file is a security failure and the guardrail in
this file's next entry applies.
Source: direct observation, claude-opus-5 via Claude Code 2.1.223, 2026-08.

**measured, n=5** — A writing-style skill was probed with one realistic task
scoring six of its formatting rules at once. Four scored 5/5 (no emoji, no bullet lists,
no hashtags, no greeting opener) and two scored 0/5 (the model prefaced every output with
a meta-sentence, and never produced more than one variant). The result matters twice: it
is a second demonstration that the probe discriminates rather than returning a uniform
answer, and it shows a batched probe scoring many rules from a single output at a sixth of
the run cost.
Source: direct observation, claude-opus-5 via Claude Code 2.1.223, 2026-08.

**reasoned** — A batch in which nothing scores 0/5 is unvalidated: "every line is
redundant" and "the task could not discriminate anything" fit that data equally well.
Carry a control instruction the model is known to lack and confirm it scores 0/5.

**reasoned** — Probe prompts must not contain the instruction or its distinctive
vocabulary. Models assent to propositions put to them, so a probe shaped "should I do X?"
returns yes independently of what the model would have done unprompted. The sycophancy
direction is well documented; that it invalidates this specific construction is the
reasoned step.

## Verification and self-scoring

**measured** — When an agent can write both the work and the criteria, measured pass
rates rise while true accuracy does not: in one self-play setting judge pass rate rose
sharply while true accuracy stayed low; RL-trained models have been observed overwriting
unit tests and patching scoring functions; sealed audits the agent cannot inspect hold
their signal where unprotected baselines degrade.
Sources: arXiv 2607.05904, 2604.15149, SEAL arXiv 2607.24300.

**measured** — For capable agents, verification becomes harder than generation: every
verifier is a proxy for underspecified intent, and optimisation widens the proxy gap.
A static verifier gets gamed as capability rises, so eval infrastructure needs
versioning and maintenance like model weights.
Source: arXiv 2606.26300.

**reasoned** — Therefore: criteria outside the agent's writable and readable scope; the
agent may propose tests, humans merge them; re-harden verification at every capability
step.

**spec** — Feedback loops (run validator → fix → repeat) materially improve output
quality, and validation scripts should be verbose about what specifically failed.
Source: Anthropic best practices.

## Supply chain

**measured** — Skill-ecosystem poisoning via payloads embedded in code examples and
configuration templates inside skill documentation bypasses defences that stop explicit
instruction injection: in the reported evaluation, explicit injection achieved zero
bypass under the best-defended configuration while the document-embedded variant achieved
double-digit bypass rates across frameworks and models, with a small residual evading
both static detection and model-level alignment. Disclosure led to confirmed
vulnerabilities and deployed fixes in production frameworks.
Source: arXiv 2604.03081.

**vendor** — A scan of roughly four thousand publicly shared agent skills reported that
about a third had at least one security issue, a subset were critical, and dozens were
confirmed malicious — with the large majority operating through prompt injection in the
skill text rather than through code. Single-vendor study, not independently replicated;
use the direction, not the decimals.
Source: Snyk "ToxicSkills".

**spec** — Use skills only from trusted sources. A malicious skill can direct the agent
to invoke tools or execute code in ways that don't match its stated purpose; audit every
bundled file for unexpected network calls, file access, or operations outside the stated
purpose.
Source: Anthropic, Agent Skills overview.

## Interference

**measured** — Applying a formal interference-detection framework to three major vendor
coding-agent system prompts surfaced over a hundred findings and around two dozen
hand-labelled interference patterns. The framing that matters for this skill: an agent
executing contradictory instructions smooths the conflict over with judgement rather
than raising an error, so the component that resolves a conflict cannot be the component
that detects it — external evaluation against explicit criteria is required.
Source: Arbiter, arXiv 2603.08993.

**measured** — Prompt modules sharing a context window interfere with no shared variable
or executable dependency, because attention provides no formal boundary between
concatenated modules. In a deployed agent, perturbing non-focal modules produced a
detectable paired effect at medium effect size with a bootstrap interval excluding zero,
while no individual recommendation flipped — a sub-threshold regime invisible to standard
QA but compounding across many decisions.
Source: Instruction Bleed, arXiv 2606.26356. Single deployed system, small trial count.

**reasoned** — Therefore: review from a fresh context where possible, and always check
the new skill against the installed set rather than in isolation.

## Harness and versioning

**measured, contested** — A benchmark score measures model × harness × settings, not a
model: swapping the harness moved scores on an identical model by an amount comparable
to a model generation. The durability of harness-level gains is contested — one line of
work argues agentically trained models progressively absorb hand-built scaffolding.
Source: arXiv 2605.27922 for the score movement; the absorption counter-position is
active and unsettled.

**reasoned** — Therefore: record model, harness and skill versions on every review, or
two reviews cannot be compared and a regression has several plausible causes with no way
to separate them.

## What is not established

Stated plainly, because a review skill that overclaims is doing the thing it warns about:

- No published number tells you the *right* length for a skill. The thresholds above are
  tooling conventions and corpus observations, not measured optima.
- The prose-plus-trigger-list description shape is a reconciliation of two conflicting
  recommendations, not a measured result.
- The nine-pass ordering is reasoned from "shrink before you inspect", not tested against
  alternative orderings.
- Whether adversarial review measurably improves skill outcomes has, as far as this file's
  sources go, not been studied. The mechanism arguments (self-review blindness,
  cross-module interference) are established; the intervention is not.
- Whether a redundancy probe verdict predicts real-world degradation is untested. That a
  clean agent complies 5/5 in a reconstructed task does not establish that deleting the
  line leaves the skill's actual users no worse off. The probe measures a proxy, and the
  gap between the proxy and the outcome has not been characterised.
- The probe's candidate selection is pattern-matching over imperatives and modals. Its
  precision and recall against a human-labelled set are unmeasured; treat its output as a
  suggestion list to curate, which is why the script prints exactly that.
