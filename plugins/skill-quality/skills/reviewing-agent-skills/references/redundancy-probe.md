# The redundancy probe

## Contents

1. What it replaces
2. Who runs it
3. Choosing candidates
4. Writing a probe that does not leak its own answer
5. Runs and thresholds
6. The guardrail: compliance is not the whole decision
7. Recording the result
8. Contamination hygiene
9. Failure modes

---

## 1. What it replaces

Pass 1 asks: does this line restate what the model already does? Answered by judgement, that question has a known bias — the agent answering it has just read the line, and a model that has read an instruction cannot introspect its way back to what it would have done without it.

The probe answers the same question by observation. Give a clean agent the task the instruction governs, without the instruction, and look at what it does.

This is an ablation at the granularity of one line. It is the same logic as `claude plugin eval --ablation with-without`, narrowed from the whole skill to a single instruction, and it exists because the answer changes over time: **a well-built skill shrinks with every model generation**, since it only ever contained what the model could not know. Judgement does not track that drift. A probe re-run does.

## 2. Who runs it

A separate process with skills disabled. Not the reviewing agent, and **not a plain subagent** — that is not clean enough, and this has been observed failing rather than merely reasoned about.

Spawning an ordinary subagent from inside the review session and handing it a probe task produced a response that used the reviewed skill's own report format — its verdict vocabulary, its blocker/delete-list structure — and said outright that it had run the skill's passes. The subagent had loaded the skill under review from its description alone. Nobody pasted it in. The run looked clean and was worthless.

In Claude Code the working isolation is a separate process with skills switched off:

```bash
claude -p --disable-slash-commands --strict-mcp-config < probe.txt
```

`--disable-slash-commands` switches off all skills; `--strict-mcp-config` removes MCP servers as a second injection route. `--bare` is stronger still — it additionally skips hooks, plugin sync and CLAUDE.md auto-discovery, all of which can carry instructions into a probe — but in at least one environment it also skips the keychain read and the run dies on authentication. Try it; fall back to the two flags above when it fails.

Five runs of that against the same task showed no trace of the skill's vocabulary. Whatever harness you are on, verify the isolation before trusting the numbers: run one probe and check the output for the reviewed skill's fingerprints. If they are there, the isolation is not real and every count you collect is noise.

## 3. Choosing candidates

Each candidate costs one model run per repetition, so do not probe everything.

**Probe these:**

- General practice statements — "write descriptive names", "handle errors", "think step by step before editing".
- Widely documented technical facts — a language idiom, a standard tool's flag, a well-known API's usage.
- Lines that restate the harness's own behaviour back to it.
- Anything the author added "just to be safe" without being able to name a failure it prevents.

**Do not probe these:**

- Organisation-specific facts. No model knows your ledger service, and a probe confirming that wastes a run. Those belong to Pass 2.
- Routes. Pass 3 already asks whether they resolve.
- Constraints that came from an incident. They exist precisely because they are not derivable from anything public.
- Anything already flagged as a second source of truth. Delete it for that reason instead.

**Rule of thumb:** if you cannot imagine the sentence appearing, near-verbatim, in public documentation or a style guide, skip it.

**Batch candidates that govern the same output.** A single realistic task usually exercises many rules at once, and one output can be scored against all of them. Six formatting rules from one prompt cost five runs rather than thirty, and the results are better than thirty separate runs would be — each rule is judged in the context the skill actually operates in, not in an artificial one built for it.

## 4. Writing a probe that does not leak its own answer

This is where the method fails in practice, and the failure is silent — a leaking probe returns a clean, confident, entirely worthless result.

Models agree with propositions put to them. Any probe shaped "should I do X?" returns yes regardless of whether the model would have done X unprompted.

### Behaviour probe — preferred

Reconstruct the task the instruction governs. Hand it over as an ordinary request. Never mention the instruction, and do not reuse its distinctive vocabulary. Then look at whether the output complies.

> **Instruction:** "Always add type hints to public functions."
>
> **Leaks:** "Should public functions have type hints?"
> **Works:** "Here is a module with three unannotated public functions. Add a fourth that parses a config file." — then check whether the new function is annotated.

### Knowledge probe — for factual lines

Ask the open question the fact answers. Supply neither the answer nor its vocabulary.

> **Instruction:** "`--strict` makes the validator treat warnings as errors."
>
> **Leaks:** "Does `--strict` treat warnings as errors?"
> **Works:** "How do I make this validator fail CI when it only emits warnings?"

### The self-check

Before running a probe, read it back and ask: could a model that knows nothing about this topic still produce the compliant answer, purely from what the prompt hands it? If yes, the probe is leaking. Rewrite it.

## 5. Runs and thresholds

One run is not evidence. Model output is stochastic, and a single compliant run is as likely to be luck as knowledge. Default to **5 runs per candidate**, more when a result sits near a boundary.

| Compliance | Reading | Default action |
|---|---|---|
| 5/5 | The model does this unprompted | Delete |
| 3–4/5 | The line buys reliability, not knowledge | Judgement — see §6 |
| 0–2/5 | The line is doing work | Keep |

**A batch where nothing scores 0/5 has not been validated.** If every candidate comes back 5/5, two explanations fit equally well: the lines are all redundant, or the task was too easy to discriminate anything. Include at least one instruction you are confident the model lacks — an invented house convention will do — and confirm it scores 0/5. Without that control the batch measures the prompt, not the skill.

The middle band is the interesting one and the reason the probe does not simply automate Pass 1. An instruction the model follows four times in five is not redundant; it is a reliability purchase, and whether it is worth its tokens depends on what the fifth run costs.

## 6. The guardrail: compliance is not the whole decision

**The probe measures what the model does by default. It does not measure what a miss costs.**

Delete on high compliance **and** low blast radius. Both halves. An instruction the model already follows 5 times in 5 is still worth keeping if a miss would write to production, drop data, or leak a credential — because 5/5 is a sample, not a guarantee, and the probe cannot see the tail.

This is Pass 5 (freedom calibration) arriving from the other direction: rigidity should match fragility, and so should redundancy. Where the blast radius is high, redundant instruction is cheap insurance. Where it is low, redundant instruction is just cost.

A review that deletes a safety-relevant line on a 5/5 probe result has misused this method.

## 7. Recording the result

A probe result is true of one model, one harness, one settings configuration, on one date. That is not a caveat — it is the entire premise. The feature exists because the answer moves.

Record, per candidate: the model ID, the harness version, the settings that differ from default, the run count, and the compliance count.

Without those pinned, the next review cannot tell whether a changed verdict means the model improved or the probe was written differently, and the two have opposite consequences.

`scripts/probe_redundancy.py --tally` refuses to produce a verdict when the model, harness or date is missing, for this reason.

`--check-run <file>` does the fingerprint check of §8 mechanically: it pulls the skill's headings and bolded labels and looks for them in a probe run. Two or more hits and the run is void. It is necessary, not sufficient — contamination through paraphrase survives any string match.

## 8. Contamination hygiene

- The probe prompt must stand alone. It must not name the skill, quote it, or reference the review.
- **Check every probe run for the reviewed skill's fingerprints before scoring it** — its report structure, its verdict words, its section names. Their presence means the probe agent found the skill and the run is void. This is the check that caught the failure in §2; it is cheap and it is not optional.
- Disguise the fixture. A probe for a skill-reviewing skill that hands over a directory shaped like `TOP.md` + `references/` + `scripts/` will be recognised as one. Re-skin it into another domain; the behaviour under test almost always generalises, and the trigger surface does not follow.
- Run the probes before writing the report. Once the reviewer has committed to a delete list in prose, probe results tend to get read as confirmation.
- **If a result is unanimous in exactly the direction the skill argues, suspect the prompt.** That is the signature of a leak, not of a strong finding.

## 9. Failure modes

| Failure | Symptom | Fix |
|---|---|---|
| Leaking probe | Suspiciously clean 5/5, and the probe restates the instruction | Rewrite as a behaviour probe; apply the §4 self-check |
| Probing the unprobeable | Every org-specific line returns 0/5 | Those were never candidates; §3 |
| Single-run verdict | A delete list built on one run each | Re-run at 5; the middle band is where most lines land |
| Blast radius ignored | A safety line deleted on 5/5 | §6 — both halves of the rule |
| Unpinned result | Two reviews disagree and nobody can say why | §7 — the tally refuses this |
| Probe drift | Re-run next quarter uses differently worded probes | Store the probe prompts alongside the counts and reuse them verbatim |

The last one matters more than it looks. The point of the probe is comparison across model generations, and a comparison only holds if the question stayed the same.
