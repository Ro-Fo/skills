#!/usr/bin/env python3
"""
Repository-level checks for the bytexpand marketplace.

`claude plugin validate` checks manifest *shape*. It does not check that a
plugin's `source` path resolves, that the marketplace entry and plugin.json
agree on name and version, or that the repository's own two rules -- every
skill ships with its evidence, every skill ships with its evals -- actually
hold. That is what this covers.

Usage:
    python3 .github/scripts/check_marketplace.py [--repo-root PATH]

Exit codes:
    0  clean
    1  one or more checks failed
    2  could not run (missing PyYAML, missing manifest)
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

CHECKER = Path("plugins/skill-quality/skills/reviewing-agent-skills/scripts/check_structure.py")
# The repository-slug placeholder is assembled from halves so this file does not
# match its own scan, and so `grep -rn` for it across the tree returns nothing.
# The template placeholder deliberately does not match GitHub Actions' `${{ … }}`
# expressions, which are legitimate and appear in the workflows.
PLACEHOLDERS = [
    ("repository slug", re.compile("OWNER" + "/" + "REPO")),
    ("template", re.compile(r"(?<!\$)\{\{[^}\n]*\}\}")),
]
PLACEHOLDER_EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", "results"}

# Mirrors the case schema the CLI parses (schema_version "1.0").
GRADER_TYPES = {"regex", "tool_order", "tool_used", "file_exists", "llm", "baseline"}
GRADER_REQUIRED = {
    "regex": {"name", "pattern"},
    "tool_order": {"name", "before", "after"},
    "tool_used": {"name", "tool"},
    "file_exists": {"name", "path"},
    "llm": {"name", "criteria"},
    "baseline": {"name", "baseline_file", "criteria"},
}

failures = []
notes = []


def fail(where, message):
    failures.append(f"{where}: {message}")


def note(message):
    notes.append(message)


def check_marketplace(root):
    """Validate the marketplace manifest and its cross-references to plugins."""
    manifest_path = root / ".claude-plugin" / "marketplace.json"
    if not manifest_path.is_file():
        print(f"error: no marketplace manifest at {manifest_path}", file=sys.stderr)
        sys.exit(2)

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: {manifest_path} is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(2)

    where = ".claude-plugin/marketplace.json"
    for field in ("name", "owner", "plugins"):
        if field not in manifest:
            fail(where, f"missing required field '{field}'")

    name = manifest.get("name")
    if name and not re.fullmatch(r"[a-z0-9-]+", str(name)):
        fail(where, f"marketplace name '{name}' must be kebab-case")
    if name and name != "bytexpand":
        # The public half of `skill-quality@bytexpand`. Renaming it breaks every
        # existing install, so it is pinned here rather than left to review.
        fail(where, f"marketplace name is '{name}', expected 'bytexpand' -- this is "
                    "the public install identifier and cannot change")

    plugins = manifest.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        fail(where, "'plugins' must be a non-empty array")
        return []

    plugin_dirs = []
    for i, entry in enumerate(plugins):
        at = f"{where} plugins[{i}]"
        if not isinstance(entry, dict):
            fail(at, "entry is not an object")
            continue

        entry_name = entry.get("name")
        source = entry.get("source")
        if not entry_name:
            fail(at, "missing 'name'")
        if not source:
            fail(at, "missing 'source'")
            continue

        # The gap: `claude plugin validate` accepts a source that points nowhere.
        plugin_dir = (root / str(source)).resolve()
        if not plugin_dir.is_dir():
            fail(at, f"source '{source}' does not resolve to a directory")
            continue
        plugin_dirs.append(plugin_dir)

        plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
        if not plugin_json.is_file():
            fail(at, f"source '{source}' has no .claude-plugin/plugin.json")
            continue

        try:
            plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(str(plugin_json.relative_to(root)), f"not valid JSON: {exc}")
            continue

        if plugin.get("name") != entry_name:
            fail(at, f"name '{entry_name}' does not match plugin.json name "
                     f"'{plugin.get('name')}'")
        if "version" in entry and entry["version"] != plugin.get("version"):
            fail(at, f"version '{entry['version']}' does not match plugin.json version "
                     f"'{plugin.get('version')}'")
        if not plugin.get("version"):
            fail(str(plugin_json.relative_to(root)), "missing 'version'")

    return plugin_dirs


def check_skills(root, plugin_dirs):
    """Every skill passes the mechanical checker in strict mode and ships evidence."""
    checker = root / CHECKER
    if not checker.is_file():
        fail(str(CHECKER), "mechanical checker is missing; skills cannot be checked")
        return

    for plugin_dir in plugin_dirs:
        rel_plugin = plugin_dir.relative_to(root)
        skills_dir = plugin_dir / "skills"
        skills = sorted(p.parent for p in skills_dir.glob("*/SKILL.md")) if skills_dir.is_dir() else []

        if not skills:
            fail(str(rel_plugin), "no skills found under skills/*/SKILL.md")
            continue

        for skill in skills:
            rel = skill.relative_to(root)
            result = subprocess.run(
                [sys.executable, str(checker), str(skill), "--strict"],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                detail = (result.stdout + result.stderr).strip()
                offenders = [ln.strip() for ln in detail.splitlines()
                             if "ERROR" in ln or "WARN" in ln]
                fail(str(rel), "check_structure.py --strict failed\n      "
                     + "\n      ".join(offenders or [detail[-400:]]))
            else:
                note(f"skill ok (strict): {rel}")

            # Rule 1 of the repository: every skill ships with its evidence.
            if not (skill / "references" / "evidence.md").is_file():
                fail(str(rel), "missing references/evidence.md -- every rule has to be "
                               "labelled so it can be argued with")


def check_evals(root, plugin_dirs):
    """Rule 2: every plugin ships evals, and each case matches the CLI's schema."""
    try:
        import yaml
    except ImportError:
        print("error: PyYAML is required to validate eval cases "
              "(pip install pyyaml)", file=sys.stderr)
        sys.exit(2)

    for plugin_dir in plugin_dirs:
        rel_plugin = plugin_dir.relative_to(root)
        cases = sorted((plugin_dir / "evals").rglob("case.yaml"))
        prompt_cases = sorted((plugin_dir / "evals").rglob("prompt.md"))

        if not cases and not prompt_cases:
            fail(str(rel_plugin), "no evals -- every skill ships with its evals")
            continue

        seen_names = {}
        for case_path in cases:
            rel = case_path.relative_to(root)
            try:
                case = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                fail(str(rel), f"not valid YAML: {exc}")
                continue
            if not isinstance(case, dict):
                fail(str(rel), "case is not a mapping")
                continue

            if str(case.get("schema_version", "")) != "1.0":
                fail(str(rel), f"schema_version is {case.get('schema_version')!r}, "
                               "expected '1.0'")
            case_name = case.get("name")
            if not case_name:
                fail(str(rel), "missing 'name'")
            elif case_name in seen_names:
                fail(str(rel), f"duplicate case name '{case_name}' (also in "
                               f"{seen_names[case_name]}); --case cannot distinguish them")
            else:
                seen_names[case_name] = str(rel)

            execution = case.get("execution")
            if not isinstance(execution, dict):
                fail(str(rel), "missing 'execution' block")
            elif not str(execution.get("prompt", "")).strip():
                fail(str(rel), "execution.prompt is empty")

            graders = case.get("graders")
            if not isinstance(graders, list) or not graders:
                fail(str(rel), "'graders' must be a non-empty array")
                continue

            grader_names = set()
            for j, grader in enumerate(graders):
                at = f"{rel} graders[{j}]"
                if not isinstance(grader, dict):
                    fail(at, "grader is not a mapping")
                    continue
                gtype = grader.get("type")
                if gtype not in GRADER_TYPES:
                    fail(at, f"unknown grader type {gtype!r}; expected one of "
                             f"{', '.join(sorted(GRADER_TYPES))}")
                    continue
                missing = GRADER_REQUIRED[gtype] - set(grader)
                if missing:
                    fail(at, f"{gtype} grader missing {', '.join(sorted(missing))}")
                gname = grader.get("name")
                if gname in grader_names:
                    fail(at, f"duplicate grader name '{gname}' within the case")
                grader_names.add(gname)

        # A negative case is what catches interference with neighbouring skills,
        # which no structural check can see.
        tags = []
        for case_path in cases:
            try:
                case = yaml.safe_load(case_path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                continue
            tags.extend(case.get("tags") or [])
        if cases and "negative" not in tags:
            fail(str(rel_plugin), "no eval case tagged 'negative' -- at least one case "
                                  "must assert the skill stays quiet when it should")


def check_repo_links(root):
    """Relative links in the human-facing markdown resolve.

    Skills are already covered by check_structure.py, which runs its own link
    check inside each skill directory. This covers everything else -- the
    READMEs and CONTRIBUTING, whose whole job is pointing at other files.
    """
    targets = [root / "README.md", root / "CONTRIBUTING.md"]
    targets += sorted((root / "plugins").glob("*/README.md"))
    targets += sorted((root / "plugins").glob("*/evals/README.md"))

    broken = 0
    checked = 0
    for path in targets:
        if not path.is_file():
            continue
        checked += 1
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
            target = m.group(1).split("#")[0].strip()
            if not target or re.match(r"^(https?:|mailto:|#)", target):
                continue
            if not (path.parent / target).resolve().exists():
                line = text[:m.start()].count("\n") + 1
                broken += 1
                fail(f"{path.relative_to(root)}:{line}",
                     f"relative link does not resolve: {target}")
    if checked and not broken:
        note(f"relative links resolve in {checked} markdown file(s)")


def check_placeholders(root):
    """No unreplaced placeholder of any kind survives anywhere in the tree."""
    hits = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        parts = set(path.relative_to(root).parts)
        if parts & PLACEHOLDER_EXCLUDE_DIRS:
            continue
        if path.name == Path(__file__).name:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), start=1):
            for label, pattern in PLACEHOLDERS:
                if pattern.search(line):
                    hits.append((f"{path.relative_to(root)}:{n}", label))
    for hit, label in hits:
        fail(hit, f"unreplaced {label} placeholder")
    if not hits:
        note("no unreplaced placeholders")


def check_guides(root):
    """Guides are published prose: links have to resolve and the version has to
    match the changelog, because the README sells them as versioned."""
    guides_dir = root / "guides"
    if not guides_dir.is_dir():
        return

    guides = sorted(guides_dir.glob("*.md"))
    if not guides:
        fail("guides/", "directory exists but contains no guide")
        return

    if not (guides_dir / "LICENSE").is_file():
        fail("guides/", "no LICENSE -- the README licenses guides CC BY 4.0, "
                        "separately from the MIT licence covering the rest")

    for path in guides:
        rel = path.relative_to(root)
        text = path.read_text(encoding="utf-8")

        for m in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
            target = m.group(1).split("#")[0].strip()
            if not target or re.match(r"^(https?:|mailto:|#)", target):
                continue
            if not (path.parent / target).resolve().exists():
                line = text[:m.start()].count("\n") + 1
                fail(f"{rel}:{line}", f"internal link does not resolve: {target}")

        header = re.search(r"^\|\s*\*\*Version\*\*\s*\|\s*([^|]+?)\s*\|", text, re.M)
        if not header:
            fail(str(rel), "no Version row in the header table")
            continue

        section = re.split(r"^##\s+Changelog\s*$", text, maxsplit=1, flags=re.M)
        if len(section) < 2:
            fail(str(rel), f"declares version {header.group(1)} but has no changelog")
            continue

        cells = [c.strip() for c in re.findall(r"^\|\s*([^|]*?)\s*\|", section[1], re.M)]
        versions = [c for c in cells
                    if c and c.lower() != "version" and not re.fullmatch(r"[-: ]+", c)]
        if not versions:
            fail(str(rel), "changelog has no entries")
        elif versions[0] != header.group(1):
            fail(str(rel), f"header says version {header.group(1)} but the newest "
                           f"changelog entry is {versions[0]}")
        else:
            note(f"guide ok: {rel} (v{header.group(1)}, links resolve)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-root", default=".", help="repository root (default: .)")
    args = ap.parse_args()
    root = Path(args.repo_root).resolve()

    plugin_dirs = check_marketplace(root)
    check_skills(root, plugin_dirs)
    check_evals(root, plugin_dirs)
    check_guides(root)
    check_repo_links(root)
    check_placeholders(root)

    for message in notes:
        print(f"  ok    {message}")
    for message in failures:
        print(f"  FAIL  {message}")

    print(f"\nResult: {len(failures)} failure(s), {len(notes)} check(s) passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
