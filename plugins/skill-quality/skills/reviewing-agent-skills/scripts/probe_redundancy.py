#!/usr/bin/env python3
"""
Plan and tally the redundancy probe for an Agent Skill.

The probe asks whether a clean agent already complies with an instruction it was
never given. This script does the mechanical halves -- selecting candidates and
counting results -- and deliberately does not do the two halves that need
judgement: writing a probe that does not leak its own answer, and deciding what
a miss would cost. Those are in references/redundancy-probe.md.

Usage:
    python3 probe_redundancy.py <path-to-skill> --plan [--json]
    python3 probe_redundancy.py <path-to-skill> --tally <results.json> [--json]

Results file: a JSON list, one object per probed line.

    [
      {
        "line": 42,
        "probe": "Here is a module with three unannotated public functions ...",
        "runs": 5,
        "complied": 5,
        "blast_radius": "low",           # low | high -- what a miss costs
        "model": "claude-opus-5",
        "harness": "Claude Code 2.1.223",
        "date": "2026-08-06"
      }
    ]

Exit codes:
    0  clean
    1  the tally found something that blocks a verdict
    3  usage error

Standard library only. Makes no model calls and no network calls -- the agent
runs the probes, this script only frames and counts them.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Compliance bands. Sources and the reasoning are in
# references/redundancy-probe.md section 5; these are reasoned defaults, not
# measured optima, and a reviewer may move them with a stated reason.
DELETE_AT = 1.0        # complies every time
JUDGEMENT_AT = 0.6     # complies most of the time
DEFAULT_RUNS = 5

# A line is worth probing only if it could plausibly appear in public
# documentation. These markers say it could not.
LOCAL_MARKERS = re.compile(
    r"\b(our|we|us|the team|in this (repo|repository|codebase|company)|"
    r"internal|in-house|legacy|incident|postmortem|outage)\b", re.I)
ROUTE_MARKERS = re.compile(
    r"(https?://|`[^`]*/[^`]*`|\b\w+/\w+\b\.(py|ts|js|go|java|rb|md|json|yaml|yml)\b|"
    r"\bsee `|\bin the \w+ (directory|repo|repository|service|catalogue)\b)", re.I)
REASON_MARKERS = re.compile(r"\b(because|since|after the|so that|otherwise)\b", re.I)

# Instruction-shaped: an imperative or a modal obligation.
IMPERATIVE = re.compile(
    r"^\s*(?:[-*+]\s+|\d+\.\s+)?"
    r"(always|never|do not|don't|avoid|prefer|use|write|keep|add|ensure|make sure|"
    r"check|run|include|handle|follow|apply|treat|split|read|call|set|return|"
    r"you (should|must)|it (should|must))\b", re.I)
MODAL = re.compile(r"\b(must|should|always|never|required to)\b", re.I)
# A modal only signals an instruction inside a list item. In running prose it is
# usually descriptive -- "this skill asks whether it should ship" is not a rule.
LIST_ITEM = re.compile(r"^\s*(?:[-*+]\s+|\d+\.\s+)")

SKIP_LINE = re.compile(r"^\s*(#|\||```|---|\d+\s*\|)")


def parse_body(skill_md):
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n.*?\n---\s*\n?(.*)$", text, re.DOTALL)
    return m.group(1) if m else text


def strip_fences(body):
    """Blank out fenced blocks so code examples are not read as instructions."""
    out, fence = [], None
    for line in body.split("\n"):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)[0]
            fence = None if fence == token else (fence or token)
            out.append("")
            continue
        out.append("" if fence else line)
    return out


def classify(line):
    """Return (verdict, reason). Only 'probe' lines are worth a model run."""
    if LOCAL_MARKERS.search(line):
        return "skip", "organisation-specific -- Pass 2, not a probe candidate"
    if ROUTE_MARKERS.search(line):
        return "skip", "route or path -- Pass 3, not a probe candidate"
    if REASON_MARKERS.search(line):
        return "skip", "carries a reason -- craft with a house reason is a decision"
    return "probe", "could plausibly appear in public documentation"


def find_candidates(body):
    candidates = []
    for n, raw in enumerate(strip_fences(body), start=1):
        line = raw.strip()
        if not line or SKIP_LINE.match(raw) or len(line.split()) < 4:
            continue
        if not (IMPERATIVE.match(raw) or (LIST_ITEM.match(raw) and MODAL.search(line))):
            continue
        verdict, reason = classify(line)
        candidates.append({"line": n, "text": line, "verdict": verdict, "reason": reason})
    return candidates


def plan(skill_path, as_json):
    body = parse_body(skill_path / "SKILL.md")
    candidates = find_candidates(body)
    probes = [c for c in candidates if c["verdict"] == "probe"]
    skipped = [c for c in candidates if c["verdict"] == "skip"]

    if as_json:
        print(json.dumps({
            "skill": str(skill_path),
            "runs_per_candidate": DEFAULT_RUNS,
            "probe": probes,
            "skipped": skipped,
        }, indent=2))
        return 0

    print(f"Redundancy probe plan: {skill_path.name}\n")
    if not probes:
        print("  No probe candidates found. Either the skill is already free of")
        print("  general-practice lines, or it states them in a shape this script")
        print("  does not recognise -- read it yourself before concluding the first.\n")
    else:
        print(f"  {len(probes)} candidate(s), {DEFAULT_RUNS} runs each "
              f"= {len(probes) * DEFAULT_RUNS} model runs\n")
        for c in probes:
            print(f"  SKILL.md:{c['line']}")
            print(f"    {c['text']}")
            print(f"    probe: give a clean agent the task this governs, WITHOUT this")
            print(f"           line, and check whether the output complies anyway.")
            print(f"           Do not ask 'should I ...' -- that leaks the answer.\n")
    if skipped:
        print(f"  Skipped {len(skipped)} line(s) not worth a model run:")
        for c in skipped:
            print(f"    SKILL.md:{c['line']:<4} {c['reason']}")
        print()
    print("  Candidates are suggestions. Drop any that are not instructions about how")
    print("  to do the work, and add any this pattern-matching missed.")
    print("  The script cannot tell whether your probe leaks its own answer;")
    print("  section 4 of references/redundancy-probe.md is the part that matters.")
    return 0


def fingerprints(skill_path):
    """Distinctive vocabulary of the skill: headings and bolded labels.

    If these turn up in a probe run, the probe agent found the skill and the run
    is void. Short and common tokens are dropped -- a hit on 'the report' proves
    nothing.
    """
    terms = set()
    for md in [skill_path / "SKILL.md"] + sorted((skill_path / "references").glob("*.md")):
        if not md.is_file():
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"^#{2,4}\s+(.+?)\s*$", text, re.M):
            terms.add(m.group(1).strip())
        for m in re.finditer(r"\*\*([^*\n]{4,40})\*\*", text):
            terms.add(m.group(1).strip())
    cleaned = set()
    for t in terms:
        t = re.sub(r"[`*_:]", "", t).strip()
        # Multi-word phrases, or single words long enough to be distinctive.
        if len(t) >= 8 and not re.fullmatch(r"[\d\W]+", t):
            cleaned.add(t)
    return sorted(cleaned, key=len, reverse=True)


def check_run(skill_path, run_path, as_json):
    try:
        run_text = Path(run_path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"error: cannot read {run_path}: {exc}", file=sys.stderr)
        return 3

    hits = [t for t in fingerprints(skill_path)
            if re.search(re.escape(t), run_text, re.I)]
    contaminated = len(hits) >= 2

    if as_json:
        print(json.dumps({"run": str(run_path), "contaminated": contaminated,
                          "fingerprints": hits}, indent=2))
        return 1 if contaminated else 0

    print(f"Contamination check: {Path(run_path).name}\n")
    if contaminated:
        print(f"  VOID -- {len(hits)} fingerprint(s) of {skill_path.name} in the output:")
        for h in hits[:8]:
            print(f"    {h!r}")
        print("\n  The probe agent found the skill under review. Do not score this run.")
        print("  Tighten the isolation and re-skin the fixture out of the skill's")
        print("  trigger surface, then run it again.")
    elif hits:
        print(f"  Weak signal -- 1 fingerprint: {hits[0]!r}")
        print("  One hit on a common phrase is not proof. Read the run before scoring it.")
    else:
        print("  Clean -- no fingerprints of the skill under review in the output.")
    print("\n  This check is necessary, not sufficient. A run can be contaminated")
    print("  through paraphrase, which no string match catches.")
    return 1 if contaminated else 0


def tally(skill_path, results_path, as_json):
    try:
        results = json.loads(Path(results_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {results_path}: {exc}", file=sys.stderr)
        return 3
    if not isinstance(results, list) or not results:
        print("error: results must be a non-empty JSON list", file=sys.stderr)
        return 3

    rows, blocked = [], []
    for i, r in enumerate(results):
        where = f"results[{i}]"
        if not isinstance(r, dict):
            blocked.append(f"{where}: not an object")
            continue

        # A probe result that is not pinned to a model, harness and date cannot be
        # compared to the next one, which is the only reason to run it. Refuse.
        missing = [k for k in ("model", "harness", "date") if not r.get(k)]
        if missing:
            blocked.append(f"{where} (SKILL.md:{r.get('line', '?')}): "
                           f"missing {', '.join(missing)} -- a probe result that is not "
                           f"pinned cannot be compared to the next run")
            continue

        runs, complied = r.get("runs"), r.get("complied")
        if not isinstance(runs, int) or not isinstance(complied, int) or runs < 1:
            blocked.append(f"{where}: runs and complied must be integers, runs >= 1")
            continue
        if complied > runs:
            blocked.append(f"{where}: complied ({complied}) exceeds runs ({runs})")
            continue
        if runs < DEFAULT_RUNS:
            blocked.append(f"{where} (SKILL.md:{r.get('line', '?')}): {runs} run(s) -- "
                           f"one run is not evidence, {DEFAULT_RUNS} is the default")
            continue

        blast = str(r.get("blast_radius", "")).lower()
        if blast not in ("low", "high"):
            blocked.append(f"{where} (SKILL.md:{r.get('line', '?')}): blast_radius must "
                           f"be 'low' or 'high' -- compliance alone does not decide")
            continue

        rate = complied / runs
        if rate >= DELETE_AT and blast == "low":
            action, why = "DELETE", "complies every run, low blast radius"
        elif rate >= DELETE_AT:
            action, why = "KEEP", "complies every run, but a miss is expensive -- cheap insurance"
        elif rate >= JUDGEMENT_AT:
            action, why = ("KEEP", "reliability purchase, and a miss is expensive") \
                if blast == "high" else \
                ("DELETE", f"complies {complied}/{runs}, low blast radius -- note the rate")
        else:
            action, why = "KEEP", "the line is doing work"

        rows.append({"line": r.get("line"), "rate": rate, "runs": runs,
                     "complied": complied, "blast_radius": blast,
                     "action": action, "reason": why,
                     "model": r["model"], "harness": r["harness"], "date": r["date"]})

    if as_json:
        print(json.dumps({"verdicts": rows, "blocked": blocked}, indent=2))
        return 1 if blocked else 0

    print(f"Redundancy probe tally: {skill_path.name}\n")
    for row in rows:
        print(f"  {row['action']:<7} SKILL.md:{row['line']:<4} "
              f"{row['complied']}/{row['runs']} ({row['rate']:.0%}), "
              f"blast radius {row['blast_radius']}")
        print(f"          {row['reason']}")
    if rows:
        pinned = {(r["model"], r["harness"], r["date"]) for r in rows}
        print(f"\n  Pinned to: {'; '.join(sorted(' / '.join(p) for p in pinned))}")
        deletes = [r for r in rows if r["action"] == "DELETE"]
        print(f"  {len(deletes)} line(s) to delete, {len(rows) - len(deletes)} to keep.")
    for b in blocked:
        print(f"  BLOCKED {b}")
    if blocked:
        print(f"\n  {len(blocked)} result(s) could not be scored. Fix them and re-tally;")
        print("  a partial tally quietly becomes a partial delete list.")
    return 1 if blocked else 0


def main():
    ap = argparse.ArgumentParser(description="Plan and tally the redundancy probe.")
    ap.add_argument("path", help="path to the skill directory")
    ap.add_argument("--plan", action="store_true", help="list probe candidates")
    ap.add_argument("--check-run", metavar="RUN.TXT",
                    help="check one probe run for the skill's fingerprints")
    ap.add_argument("--tally", metavar="RESULTS.JSON", help="score probe results")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    skill_path = Path(args.path).resolve()
    if not skill_path.is_dir() or not (skill_path / "SKILL.md").is_file():
        print(f"error: no SKILL.md in {skill_path}", file=sys.stderr)
        return 3
    chosen = [bool(args.plan), bool(args.check_run), bool(args.tally)]
    if sum(chosen) != 1:
        print("error: pass exactly one of --plan, --check-run or --tally", file=sys.stderr)
        return 3

    if args.plan:
        return plan(skill_path, args.json)
    if args.check_run:
        return check_run(skill_path, args.check_run, args.json)
    return tally(skill_path, args.tally, args.json)


if __name__ == "__main__":
    sys.exit(main())
