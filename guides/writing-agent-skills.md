# Write the skill. Then attack it.

**A working guide to authoring and reviewing Agent Skills.**

| | |
|---|---|
| **Version** | 1.1 |
| **Last reviewed** | 2026-08 |
| **License** | CC BY 4.0 — copy it, fork it, teach from it, ship it internally. Attribution appreciated, permission not required. |
| **Companion skill** | [`skill-quality@bytexpand`](https://github.com/Ro-Fo/skills) — installable `.skill`, MIT, no dependencies |
| **Corrections** | Issues and PRs at the repo above. Disagreement with a rule is the most useful kind. |

---

## Shelf life — read this first

Everything below describes a layer that two vendors control and neither has finished designing.

The format is roughly a year old. Token budgets, the loading model, the directory conventions, what counts as valid frontmatter — all of it is a product decision, revisable in a single release, and some of it has already changed once. The advice that survives a format change is the reasoning, not the numbers. Where I give a number, I say where it came from so you can check whether it still holds.

The deeper instability is the model itself. **A well-built skill shrinks with every model generation**, because it only ever contained what the model couldn't know. Half the instructions in a skill written today will be redundant within a few releases — still loaded, still billed, still competing for context, just no longer doing anything. That isn't a flaw in this guide. It's the property that makes the two questions at the end the most important part of it.

So: **re-read your skills monthly, or at every model and harness change, whichever comes first.** Not this guide — your skills. This guide gets a version number so you can tell whether you're reading a stale copy; a changelog is at the bottom.

Concretely, treat as expiring:

- every token threshold and line limit — tooling convention, not physics
- every claim about what the model can't do on its own — the fastest-moving item on the list, and the one section 8 now gives you a way to test rather than guess
- the security numbers — the attack surface is a year old and actively researched
- the sentence "no lab is going to absorb this" applied to anything

Treat as durable: the division of labour between model and skill, the reason review has to happen outside the drafting loop, and the fact that verification criteria the agent can edit aren't verification.

---

## What this covers

The [format docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) are good and this guide doesn't restate them. Go there for frontmatter fields, file layout and the loading mechanics.

This is the other half: **what's allowed into a skill, and what you do to it afterwards.** The failure mode that costs you isn't malformed YAML. It's a spec-compliant, well-structured skill that quietly makes the output worse. Those are common, and nothing in the validation chain catches them.

---

## 1. Start from a failure you actually saw

Not from what you know. Run the task cold, without a skill, and write down where the model failed. Anthropic's guidance says build the evals first; the reason is that otherwise you document imagined problems.

The measurement backs it harder than the docs let on. In an [analysis of a few hundred public skills](https://agentskillreport.com/), the dimension separating useful from useless is **novelty** — content the model doesn't already have. Clarity, actionability and structure cluster tightly across the whole corpus; novelty varies independently, and most skills mainly restate common knowledge. Same work: an official vendor-authored skill measurably degraded output, and structural risk showed no correlation with actual degradation.

Structure is what the tools measure. Content is what decides.

## 2. Three lines, one of which you delete

An agent adding an endpoint to a payments service loads a skill. Three lines from it:

```text
Keep functions small and use descriptive names.
The shared auth middleware is in platform/auth-mw/v2.
Payments never write to the DB directly — they go through the ledger
service, decided after the double-charge incident.
```

**Line 1 is craft.** True at every company on earth. The model is better at it than your sentence is, and you pay for the line on every run. Test: would this be true, unchanged, at another company in another industry? Then it isn't yours. Delete it.

**Line 2 is a fact that lives in a system.** True until someone ships v3, then it's a lie that keeps working — the agent imports the old path, it compiles, you find out in review. Facts that live in a system belong in a tool that reads that system. A skill that copies data has created a second source of truth, and it's the one nobody updates.

**Line 3 pays for the skill.** It's in nobody's code, because the constraint came from an incident, not an interface. Same category: who owns which service, what a deploy needs before it goes near prod, that a service isn't done until it's in the catalogue.

The division underneath: **the model brings the craft, the skill brings the decisions** — plus the route to where the real context lives.

That route is the part people skip. Without it the model guesses paths, opens files that don't exist, and reimplements what's already in the repo next door. Every dead end billed twice: once in tokens, once in the context noise it leaves behind. The fix isn't pasting the codebase in. It's a signpost — which repo holds the shared libs, which directory has the examples worth copying, which system to ask for the rest.

## 3. Structure follows the loading model

Three levels, three load times: metadata sits in context always, the body loads on trigger, bundled files load when something reads them. The budgets fall straight out of that.

- **Body under 500 lines / ~5k tokens.** Split by domain past that.
- **References exactly one level deep from SKILL.md.** A file referenced from a referenced file gets skimmed with a partial read instead of read.
- **Table of contents on any reference over ~100 lines.** Same reason.
- **Per reference file:** warn ~10k tokens, error ~25k ([skill-validator](https://github.com/agent-ecosystem/skill-validator) thresholds).
- **Nothing at the skill root but SKILL.md.** In the corpus above, roughly half of all tokens sat in files that aren't skill content — licences, build artefacts, schemas — quietly loading.

*Expiry note: every number in this section is a current tooling convention. Re-check against the spec before quoting them.*

The description is the only thing the model sees before deciding. Third person, under 1024 chars, says what *and* when. There's a real tension nobody names: [`skill-creator`](https://github.com/anthropics/skills) tells you to write slightly pushy descriptions because models measurably under-trigger; the validators flag keyword-stuffed ones at 8+ comma fragments. Both are right. The shape that satisfies both is **one prose sentence, then one delimited trigger list** — not a sentence made of commas. If you've ever shipped a description that's 40% comma-separated trigger words: same.

## 4. Rigidity should match fragility

Fragile, sequence-dependent, high blast radius → exact command, no options. Judgement work → direction and room.

The failure is the middle: capitalised MUST and NEVER on things that need judgement. A rule with no reason gets followed literally into the edge case you didn't consider, or over-applied where it doesn't fit, and the model has nothing to reason with. `Do X because Y causes Z` survives cases you didn't anticipate. `ALWAYS DO X` doesn't. Treat your own ALL-CAPS as a prompt to write down what you were actually afraid of.

## 5. Give it a check it can run — and can't edit

A model with no way to check its work doesn't stop. It re-reads, revises, re-reads. You pay for every round; the last five change nothing. One check that returns green or red ends the loop. Two conditions, and usually neither holds:

- **It has to actually run.** If checking needs three services, a seeded DB and a VPN, the model won't check. It'll guess, and it'll sound certain.
- **The criteria can't belong to the agent.** Your test suite sits in the repo you just gave it write access to. Nothing dramatic happens — an assertion loosens, a case gets skipped with a reasonable-sounding comment, a fixture gets nudged. Agents [raise their own pass rates while true accuracy falls](https://arxiv.org/abs/2607.05904); [sealed criteria the agent can't see](https://arxiv.org/abs/2607.24300) hold their signal where unprotected ones don't.

The agent can propose a test. Merging one is a human decision. And a check only covers what you thought to write down — green is not correct, green is not-red.

## 6. A skill is a dependency

It runs with the agent's privileges *and* carries instruction authority: everything a compromised npm package gets you, plus the ability to tell the agent what to do next.

The [supply-chain research](https://arxiv.org/abs/2604.03081) is the part worth internalising. Explicit instruction injection in a skill gets caught — 0% bypass against a well-defended setup. Payloads hidden in **code examples and config templates inside the skill's own documentation** got through 11.6–33.5% of the time, with a residual evading both static scanning and model-level alignment. A vendor scan of ~4,000 shared skills found a third with at least one security issue and dozens confirmed malicious, mostly through injected instructions in the skill text (single vendor, unreplicated — take the direction, not the decimals).

Two consequences:

1. Unsigned skill into your agent = unsigned package into your build. Curated source, pinned version, review before adoption, no runtime install.
2. **Review reads the reference files and the scripts.** The security work and the quality analysis converge here from opposite ends: payloads and contamination both hide one level down, where SKILL.md-only inspection never looks.

*Expiry note: this is the section most likely to be out of date when you read it. Both the attacks and the framework defences are moving monthly.*

## 7. The author can't be the reviewer

[Arbiter](https://arxiv.org/abs/2603.08993) applied formal interference detection to three vendor coding-agent system prompts and surfaced 152 findings. The framing matters more than the count: give a model contradictory instructions and it does not raise an error. It smooths the conflict over with judgement — the same property that makes it useful — and behaviour becomes a function of which line it happened to weight that run. No warning, no log. **The component that resolves a conflict cannot be the component that detects it.**

[Instruction Bleed](https://arxiv.org/abs/2606.26356) sharpens it: perturbing one prompt module shifted an unrelated module's behaviour at medium effect size, bootstrap CI excluding zero — and no decision flipped. Sub-threshold, invisible to normal QA, compounding across every run. Attention provides no boundary between concatenated modules. Your new skill and the eleven already installed share that window.

So the review is a separate pass, ideally from a fresh session that never saw the drafting conversation. The agent that spent forty minutes rationalising each line into the draft is not neutral about whether the line belongs.

The nine passes, in the order that finds the most:

| # | Pass | Asks |
|---|---|---|
| 1 | Delete-first | Which lines are true at any company, or restate what the model does natively? |
| 2 | Second sources of truth | Which lines copy a fact that lives in a system and will go stale silently? |
| 3 | Routes | Can the agent find the real context, or must it guess? |
| 4 | Triggering | Fires when it should, quiet when it shouldn't? Test the near-misses. |
| 5 | Freedom calibration | Rigidity matched to fragility? Does every rule carry a reason? |
| 6 | Context cost | Budgets, orphans, junk at root — mechanical, so script it. |
| 7 | Verification | Checkable in one command? Can the agent reach the criteria? |
| 8 | Permissions | Does the skill imply authority it has no business granting? |
| 9 | Supply chain + interference | Bundled files doing undeclared things; collisions with installed skills. |

Pass 1 runs first because everything after it is cheaper on a smaller skill.

## 8. The companion skill

Packaged, because a checklist you have to remember to apply is one you apply twice and then stop.

### **[`skill-quality@bytexpand`](https://github.com/Ro-Fo/skills)** — MIT

- Complement to [`skill-creator`](https://github.com/anthropics/skills), not a replacement — that one owns create → test → iterate, evals, benchmarking, description optimisation. This one runs the adversarial pass afterwards and hands measurement back.
- Bundles a stdlib-only script for the mechanical half: frontmatter, budgets, orphans, broken internal links, unclosed fences, description shape.
- Output is a verdict, a **delete list before the improvement list**, and an explicit "not checked" section.
- `references/evidence.md` labels every rule *spec / measured / vendor / reasoned*, including a section on what isn't established — starting with whether adversarial skill review measurably helps at all. The mechanisms are documented; the intervention isn't.
- **It measures redundancy instead of arguing about it.** More on this below, because it's the part I'd steal if I were you.

### The self-test

Section 2 tells you to delete craft. Deciding *which* lines are craft has always been a judgement call made by the one agent least equipped to make it: the reviewer has just read the line, and a model that has read an instruction cannot report what it would have done without it. Every review therefore drifts toward "well, it's probably worth keeping."

So the skill stopped asking and started measuring. For a candidate line it runs an ablation at the granularity of one instruction — a clean agent, in a separate process with skills switched off, gets the task the instruction governs *without* the instruction, five times, and the compliant runs get counted. 5/5 means the model does it unprompted. 0/5 means the line is carrying weight. The middle is a reliability purchase and needs a decision rather than a rule.

Two things it turned up the first two times it ran, both of which I'd have got wrong by eye:

**On a writing-style skill**, a single realistic task scored six formatting rules at once. Four came back 5/5 — no emoji, no bullet lists, no hashtags, no "Great post!" opener. The model does all of that unprompted; those four lines were pure cost that read like diligence. Two came back 0/5: every single output opened with "Here's a draft:", and not one produced more than a single variant. Those two rules are the skill. The other four were decoration.

**On itself**, it found that the obvious way to run the probe doesn't work. Spawning an ordinary subagent to be the "clean" agent produced a reply in the reviewed skill's own report format — its verdict vocabulary, its blocker and delete-list structure — and the subagent said outright that it had run the skill's passes. Nobody had pasted the skill in; it had loaded it from the description alone. The run looked clean and was worthless. Isolation has to be a separate process with skills disabled, and every run has to be checked for the reviewed skill's fingerprints before it is scored.

**The guardrail is the half that keeps this from backfiring.** Compliance says what the model does by default. It says nothing about what a miss costs. Probed against itself, the instruction "read every bundled file, not just the top one" scored 5/5 — and stays, because a payload missed in a reference file is a security failure, and 5/5 is a sample, not a guarantee. Delete on high compliance **and** low blast radius. A review that deletes a safety-relevant line on a 5/5 has misused the method.

One more trap, learned the same way: if every candidate in a batch comes back 5/5, the batch is unvalidated. "All redundant" and "the task was too easy to discriminate anything" fit that data equally well. Put one instruction you're confident the model lacks into the batch and check that it scores 0/5 — otherwise you measured your prompt, not your skill.

The evidence file is where forks should start. If a rule is labelled *reasoned* and you have data, that's the PR I want.

## 9. Two questions at the next model release

Put these in the calendar, not in your head.

- **Which instruction is now redundant, because the model learned it?** Delete against the eval, not against your judgement — it's a change to the instruction layer like any other. This one now has a procedure rather than a reminder to be virtuous: section 8. That matters more than it sounds, because the question otherwise gets asked once a quarter, from memory, by the person who wrote the lines and is not neutral about them.
- **Which check is now gameable, because the model got better?** A more capable optimiser finds the slack in a test that held fine last quarter. The skill shrinks; the verification around it doesn't. Re-harden at the same cadence as the capability it measures.

And record what you reviewed against: model version, harness version, inference settings. A score, a cost figure or a quality judgement never measures a model alone — it measures model × harness × settings. Without all three pinned, two reviews can't be compared, and a regression has several plausible causes with no way to separate them.

The bias in all of this: **shrink first.** Every guide about writing skills, this one included, reads as an invitation to add. The measured failure mode is the opposite. Most of what people put in skills, the model already knew — and paid for it on every run.

---

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.1 | 2026-08 | Section 8: the companion skill now measures redundancy instead of arguing about it. Adds the redundancy probe, what it found on its first two outings, and the guardrail that keeps it from deleting cheap insurance. |
| 1.0 | 2026-08 | First public version. |

*Next review due when the model or the skill format changes, whichever is first.*
