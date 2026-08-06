#!/usr/bin/env python3
"""
Mechanical checks for an Agent Skill directory.

Covers what is countable: frontmatter validity, body and reference budgets, orphan
files, broken internal links, unclosed code fences, nesting depth, and description
shape. It says nothing about whether the content is worth loading -- that is the
judgement work in references/review-passes.md.

Usage:
    python3 check_structure.py <path-to-skill> [--json] [--strict]

Exit codes:
    0  clean
    1  errors present
    2  warnings only
    3  usage error (bad path, no SKILL.md)

Standard library only. PyYAML is used if importable, otherwise a minimal frontmatter
parser handles the flat key/value shape that skill frontmatter uses in practice.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Thresholds. Sources for each are in references/evidence.md; they are tooling
# conventions and corpus observations, not measured optima, so they warn rather
# than error wherever a breach is a judgement call.
BODY_LINES_WARN = 500          # spec guidance: keep SKILL.md body under 500 lines
BODY_TOKENS_WARN = 5_000
REF_TOKENS_WARN = 10_000       # per reference file
REF_TOKENS_ERROR = 25_000
REFS_TOTAL_TOKENS_WARN = 25_000
REFS_TOTAL_TOKENS_ERROR = 50_000
TOC_LINES_WARN = 100           # reference files past this need a table of contents
DESC_MAX_CHARS = 1_024
NAME_MAX_CHARS = 64
DESC_COMMA_SEGMENTS_WARN = 8   # keyword-stuffing heuristic
DESC_QUOTED_STRINGS_WARN = 5

RECOGNISED_DIRS = {"scripts", "references", "assets"}
TOLERATED_DIRS = {"evals"}  # conventional for eval sets; not part of the spec's three
HUMAN_FILES = {"README.md", "CHANGELOG.md", "LICENSE", "LICENSE.txt", "LICENSE.md",
               "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "AGENTS.md", "CLAUDE.md"}
RESERVED_NAME_WORDS = ("anthropic", "claude")
TEXT_SUFFIXES = {".md", ".txt", ".py", ".sh", ".js", ".ts", ".json", ".yaml", ".yml",
                 ".toml", ".cfg", ".ini", ".sql", ".tex", ".css", ".html"}
SKIP_DIR_NAMES = {"__pycache__", "node_modules", ".git", ".score_cache"}

# Tokens are estimated at 4 characters each. This is a rough proxy, not a tokeniser;
# it is accurate enough to tell a 900-token file from a 30,000-token one, which is
# the only distinction the thresholds above actually need.
CHARS_PER_TOKEN = 4


class Report:
    def __init__(self):
        self.results = []

    def add(self, level, category, message, file=None, line=None):
        entry = {"level": level, "category": category, "message": message}
        if file:
            entry["file"] = file
        if line:
            entry["line"] = line
        self.results.append(entry)

    def error(self, *a, **kw):
        self.add("error", *a, **kw)

    def warn(self, *a, **kw):
        self.add("warning", *a, **kw)

    def ok(self, *a, **kw):
        self.add("pass", *a, **kw)

    def info(self, *a, **kw):
        self.add("info", *a, **kw)

    @property
    def errors(self):
        return sum(1 for r in self.results if r["level"] == "error")

    @property
    def warnings(self):
        return sum(1 for r in self.results if r["level"] == "warning")


def est_tokens(text):
    return max(1, round(len(text) / CHARS_PER_TOKEN))


def parse_frontmatter(content):
    """Return (frontmatter_dict, body, error_message)."""
    if not content.startswith("---"):
        return None, content, "SKILL.md does not start with YAML frontmatter"
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
    if not match:
        return None, content, "frontmatter block is not closed with a '---' line"
    raw, body = match.group(1), match.group(2)

    try:
        import yaml  # optional; the fallback below handles the flat shape
        data = yaml.safe_load(raw)
        if not isinstance(data, dict):
            return None, body, "frontmatter is not a mapping"
        return data, body, None
    except ImportError:
        pass
    except Exception as exc:  # malformed YAML is a real finding, not a crash
        return None, body, f"frontmatter is not valid YAML: {exc}"

    data, key = {}, None
    for raw_line in raw.split("\n"):
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw_line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            data[key] = value
        elif key and raw_line.startswith((" ", "\t")):
            data[key] = f"{data[key]} {raw_line.strip()}".strip()
    return data, body, None


def check_frontmatter(fm, err, skill_dir_name, rep):
    if err:
        rep.error("Frontmatter", err, file="SKILL.md")
        return
    if fm is None:
        rep.error("Frontmatter", "could not parse frontmatter", file="SKILL.md")
        return

    name = str(fm.get("name", "") or "")
    if not name:
        rep.error("Frontmatter", "name is required", file="SKILL.md")
    else:
        if len(name) > NAME_MAX_CHARS:
            rep.error("Frontmatter",
                      f"name is {len(name)} chars, max {NAME_MAX_CHARS}", file="SKILL.md")
        if not re.fullmatch(r"[a-z0-9-]+", name):
            rep.error("Frontmatter",
                      f"name '{name}' must be lowercase letters, numbers and hyphens only",
                      file="SKILL.md")
        for word in RESERVED_NAME_WORDS:
            if word in name.lower():
                rep.error("Frontmatter",
                          f"name contains reserved word '{word}'", file="SKILL.md")
        if name != skill_dir_name:
            rep.warn("Frontmatter",
                     f"name '{name}' does not match directory '{skill_dir_name}'; "
                     "some platforms resolve skills by directory",
                     file="SKILL.md")
        if re.fullmatch(r"[a-z0-9-]{1,%d}" % NAME_MAX_CHARS, name):
            rep.ok("Frontmatter", f"name: '{name}'", file="SKILL.md")

    desc = str(fm.get("description", "") or "")
    if not desc:
        rep.error("Frontmatter", "description is required and is the only thing the "
                                 "model sees when deciding whether to trigger",
                  file="SKILL.md")
        return

    if len(desc) > DESC_MAX_CHARS:
        rep.error("Frontmatter",
                  f"description is {len(desc)} chars, max {DESC_MAX_CHARS}", file="SKILL.md")
    else:
        rep.ok("Frontmatter", f"description: {len(desc)} chars", file="SKILL.md")

    if re.search(r"<[A-Za-z/][^>]*>", desc):
        rep.error("Frontmatter", "description contains XML-like tags", file="SKILL.md")

    if re.match(r"^\s*(I |I'|You |Your |We |Use this to )", desc):
        rep.warn("Frontmatter",
                 "description should be third person ('Extracts…', 'Reviews…'); "
                 "first/second person hurts discovery",
                 file="SKILL.md")

    quoted = len(re.findall(r"[\"'][^\"']{2,}[\"']", desc))
    prose_words = len(re.sub(r"[\"'][^\"']*[\"']", "", desc).split())
    if quoted >= DESC_QUOTED_STRINGS_WARN and prose_words < quoted:
        rep.warn("Frontmatter",
                 f"description has {quoted} quoted strings and only {prose_words} words "
                 "of surrounding prose — reads as a keyword dump",
                 file="SKILL.md")

    segments = [s for s in re.sub(r"[\"'][^\"']*[\"']", "", desc).split(",") if s.strip()]
    short_segments = [s for s in segments if len(s.split()) <= 4]
    if len(short_segments) >= DESC_COMMA_SEGMENTS_WARN:
        rep.warn("Frontmatter",
                 f"description has {len(short_segments)} short comma-separated fragments; "
                 "prefer one prose sentence plus a single delimited trigger list",
                 file="SKILL.md")

    first_sentence = re.split(r"(?<=[.!?])\s", desc.strip())[0]
    if len(first_sentence.split()) < 5:
        rep.warn("Frontmatter",
                 "description does not open with a prose sentence stating what the skill does",
                 file="SKILL.md")

    if not re.search(r"\b(use|trigger|when|whenever|apply)\b", desc, re.I):
        rep.warn("Frontmatter",
                 "description states what the skill does but not when to use it",
                 file="SKILL.md")

    allowed = fm.get("allowed-tools")
    if allowed:
        rep.info("Frontmatter",
                 f"allowed-tools declared ({allowed}) — check against least privilege "
                 "in review pass 8",
                 file="SKILL.md")

    unknown = set(fm) - {"name", "description", "license", "compatibility", "metadata",
                         "allowed-tools", "version"}
    if unknown:
        rep.warn("Frontmatter",
                 f"non-spec frontmatter fields: {', '.join(sorted(unknown))}; "
                 "portability across platforms is not guaranteed",
                 file="SKILL.md")


def unclosed_fences(text):
    """Return the 1-based line number of an unclosed fence opener, or None."""
    fence = None
    fence_line = None
    for i, line in enumerate(text.split("\n"), start=1):
        m = re.match(r"^\s*(`{3,}|~{3,})", line)
        if not m:
            continue
        marker = m.group(1)[0]
        if fence is None:
            fence, fence_line = marker, i
        elif marker == fence:
            fence, fence_line = None, None
    return fence_line


def collect_files(skill_path):
    files = []
    for p in sorted(skill_path.rglob("*")):
        if not p.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in p.relative_to(skill_path).parts):
            continue
        files.append(p)
    return files


def read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def check_structure(skill_path, files, body, rep):
    root_names = {p.name for p in files if p.parent == skill_path}
    for name in sorted(root_names - {"SKILL.md"}):
        if name in HUMAN_FILES:
            rep.warn("Structure",
                     f"{name} at skill root is for human readers; it can be pulled into "
                     "context without adding anything the agent needs",
                     file=name)
        else:
            rep.warn("Structure",
                     f"{name} sits at the skill root; move it into references/, scripts/ "
                     "or assets/ so platforms load it predictably",
                     file=name)

    dirs = {p.relative_to(skill_path).parts[0] for p in files
            if len(p.relative_to(skill_path).parts) > 1}
    for d in sorted(dirs & TOLERATED_DIRS):
        rep.info("Structure",
                 f"'{d}/' is not one of the three recognised directories but is a "
                 "conventional development directory; it is not packaged on some platforms",
                 file=f"{d}/")
    for d in sorted(dirs - RECOGNISED_DIRS - TOLERATED_DIRS):
        count = sum(1 for p in files if p.relative_to(skill_path).parts[0] == d)
        rep.warn("Structure",
                 f"unrecognised directory '{d}/' with {count} file(s); the spec recognises "
                 "scripts/, references/ and assets/",
                 file=f"{d}/")

    for p in files:
        rel = p.relative_to(skill_path)
        if len(rel.parts) > 3:
            rep.warn("Structure", f"deeply nested file ({len(rel.parts)} levels)",
                     file=str(rel))

    fence_line = unclosed_fences(body)
    if fence_line:
        rep.error("Markdown",
                  "unclosed code fence — everything after it reads as code",
                  file="SKILL.md", line=fence_line)
    for p in files:
        if p.suffix == ".md" and p.name != "SKILL.md":
            line = unclosed_fences(read_text(p))
            if line:
                rep.error("Markdown", "unclosed code fence",
                          file=str(p.relative_to(skill_path)), line=line)
    if not any(r["category"] == "Markdown" for r in rep.results):
        rep.ok("Markdown", "no unclosed code fences")


def check_links(skill_path, files, rep):
    md_files = [p for p in files if p.suffix == ".md"]
    broken = 0
    for p in md_files:
        text = read_text(p)
        for m in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
            target = m.group(1).split("#")[0].strip()
            if not target or re.match(r"^(https?:|mailto:|#)", target):
                continue
            resolved = (p.parent / target).resolve()
            if not resolved.exists():
                broken += 1
                line = text[:m.start()].count("\n") + 1
                rep.error("Links", f"internal link does not resolve: {target}",
                          file=str(p.relative_to(skill_path)), line=line)
    if broken == 0:
        rep.ok("Links", "all internal links resolve")


def check_reachability(skill_path, files, body, rep):
    """Orphan detection plus depth-of-reference detection.

    A file counts as referenced if its path appears anywhere in the text of a file
    already reached, starting from the SKILL.md body. Reachability is transitive,
    which is also how the two-levels-deep problem becomes visible: a file reached
    only through another reference gets skimmed rather than read.
    """
    candidates = [p for p in files
                  if p.name != "SKILL.md" and p.parent != skill_path
                  and p.relative_to(skill_path).parts[0] not in TOLERATED_DIRS]
    if not candidates:
        return

    texts = {p: (read_text(p) if p.suffix in TEXT_SUFFIXES else "") for p in files}
    direct, indirect = set(), set()

    def referenced_in(text):
        hits = set()
        for p in candidates:
            rel = p.relative_to(skill_path).as_posix()
            if rel in text or p.name in text:
                hits.add(p)
        return hits

    direct = referenced_in(body)
    frontier = set(direct)
    reached = set(direct)
    while frontier:
        nxt = set()
        for p in frontier:
            for q in referenced_in(texts.get(p, "")):
                if q not in reached:
                    nxt.add(q)
                    indirect.add(q)
        reached |= nxt
        frontier = nxt

    for p in sorted(set(candidates) - reached):
        rel = str(p.relative_to(skill_path))
        rep.warn("Reachability",
                 "never referenced from SKILL.md or anything reachable from it — the "
                 "agent has no signal to load it",
                 file=rel)

    for p in sorted(indirect):
        rel = p.relative_to(skill_path)
        if rel.suffix == ".md":
            rep.warn("Reachability",
                     "reachable only through another reference file; keep references one "
                     "level deep from SKILL.md or this gets partially read",
                     file=str(rel))

    if not any(r["category"] == "Reachability" for r in rep.results):
        rep.ok("Reachability", "every bundled file is referenced directly from SKILL.md")


def check_budgets(skill_path, files, body, rep):
    body_lines = body.count("\n") + 1
    body_tokens = est_tokens(body)
    counts = {"SKILL.md body": body_tokens}

    if body_lines > BODY_LINES_WARN:
        rep.warn("Tokens",
                 f"SKILL.md body is {body_lines} lines (guidance: under {BODY_LINES_WARN}); "
                 "split by domain into references/",
                 file="SKILL.md")
    if body_tokens > BODY_TOKENS_WARN:
        rep.warn("Tokens",
                 f"SKILL.md body is ~{body_tokens} tokens (guidance: under {BODY_TOKENS_WARN})",
                 file="SKILL.md")
    if body_lines <= BODY_LINES_WARN and body_tokens <= BODY_TOKENS_WARN:
        rep.ok("Tokens", f"SKILL.md body: {body_lines} lines, ~{body_tokens} tokens",
               file="SKILL.md")

    refs_total = 0
    for p in files:
        rel = p.relative_to(skill_path)
        if rel.parts[0] != "references" or p.suffix not in TEXT_SUFFIXES:
            continue
        text = read_text(p)
        tokens = est_tokens(text)
        counts[str(rel)] = tokens
        refs_total += tokens
        if tokens > REF_TOKENS_ERROR:
            rep.error("Tokens", f"~{tokens} tokens; split this file", file=str(rel))
        elif tokens > REF_TOKENS_WARN:
            rep.warn("Tokens", f"~{tokens} tokens; consider splitting", file=str(rel))
        lines = text.count("\n") + 1
        if lines > TOC_LINES_WARN and not re.search(r"^##?#?\s*(Contents|Table of contents)",
                                                    text, re.I | re.M):
            rep.warn("Structure",
                     f"{lines} lines with no table of contents; a partial read will miss "
                     "what is in here",
                     file=str(rel))

    if refs_total > REFS_TOTAL_TOKENS_ERROR:
        rep.error("Tokens", f"references total ~{refs_total} tokens")
    elif refs_total > REFS_TOTAL_TOKENS_WARN:
        rep.warn("Tokens", f"references total ~{refs_total} tokens")

    other = 0
    for p in files:
        rel = p.relative_to(skill_path)
        if rel.parts[0] in RECOGNISED_DIRS | TOLERATED_DIRS or str(rel) == "SKILL.md":
            continue
        if p.suffix in TEXT_SUFFIXES:
            other += est_tokens(read_text(p))
    if other:
        rep.warn("Tokens",
                 f"~{other} tokens sit in files outside SKILL.md and the recognised "
                 "directories; in analysed public corpora this is where roughly half of "
                 "all skill tokens end up wasted")
    return counts


def main():
    ap = argparse.ArgumentParser(description="Mechanical checks for an Agent Skill.")
    ap.add_argument("path", help="path to the skill directory")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args()

    skill_path = Path(args.path).resolve()
    if not skill_path.is_dir():
        print(f"error: {skill_path} is not a directory", file=sys.stderr)
        return 3
    skill_md = skill_path / "SKILL.md"
    if not skill_md.is_file():
        print(f"error: no SKILL.md in {skill_path}", file=sys.stderr)
        return 3

    rep = Report()
    content = read_text(skill_md)
    fm, body, fm_err = parse_frontmatter(content)

    check_frontmatter(fm, fm_err, skill_path.name, rep)
    files = collect_files(skill_path)
    check_structure(skill_path, files, body, rep)
    check_links(skill_path, files, rep)
    check_reachability(skill_path, files, body, rep)
    counts = check_budgets(skill_path, files, body, rep)

    passed = rep.errors == 0 and (not args.strict or rep.warnings == 0)

    if args.json:
        print(json.dumps({
            "skill_dir": str(skill_path),
            "passed": passed,
            "errors": rep.errors,
            "warnings": rep.warnings,
            "results": rep.results,
            "token_estimates": counts,
        }, indent=2))
    else:
        print(f"Mechanical check: {skill_path.name}\n")
        order = {"error": 0, "warning": 1, "info": 2, "pass": 3}
        symbol = {"error": "ERROR  ", "warning": "WARN   ", "info": "INFO   ", "pass": "OK     "}
        for r in sorted(rep.results, key=lambda x: order[x["level"]]):
            where = r.get("file", "")
            if r.get("line"):
                where += f":{r['line']}"
            where = f" [{where}]" if where else ""
            print(f"  {symbol[r['level']]} {r['category']}: {r['message']}{where}")
        print(f"\n  Token estimates (~4 chars/token):")
        for name, tokens in counts.items():
            print(f"    {name:<44} {tokens:>7,}")
        print(f"\nResult: {rep.errors} error(s), {rep.warnings} warning(s)")
        print("This covers what is countable. Content quality is passes 1-9 in "
              "references/review-passes.md.")

    if rep.errors or (args.strict and rep.warnings):
        return 1
    if rep.warnings:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
