"""The Chief Engineer's code review: hygiene, idiom, integrity and notes."""

from __future__ import annotations

import difflib
import re
from pathlib import Path

from .model import Finding

# (rule id, severity, regex applied to code lines with comments removed, message)
RULES = {
    ".js": [
        ("print-on-import", "warn", re.compile(r"^console\.(log|table|dir|info)\("),
         "A top-level console.log runs every time this module is imported (including by tests). "
         "Delete it, comment it out, or move demos into a separate file."),
        ("debugger-left", "warn", re.compile(r"\bdebugger\s*;"), "A `debugger;` statement was left in."),
        ("var", "info", re.compile(r"\bvar\s+\w"), "`var` is legacy: prefer `const` (or `let` when you reassign)."),
        ("loose-equality", "info", re.compile(r"[^=!<>]==[^=]|!=[^=]"),
         "Loose equality (`==`/`!=`) coerces types. Use `===` / `!==`."),
    ],
    ".py": [
        ("print-on-import", "warn", re.compile(r"^print\("),
         "A top-level print() runs on every import (including by tests). "
         "Put demo code under `if __name__ == \"__main__\":`."),
        ("breakpoint-left", "warn", re.compile(r"^\s*breakpoint\(\)"), "A `breakpoint()` was left in."),
        ("none-equality", "info", re.compile(r"[!=]=\s*None\b"), "Compare with None using `is` / `is not`."),
        ("bare-except", "warn", re.compile(r"^\s*except\s*:"), "A bare `except:` also catches Ctrl+C and bugs. Name the exception."),
        ("range-len", "info", re.compile(r"range\(len\("), "`for i in range(len(x))` is usually clearer as `for item in x` or `enumerate(x)`."),
    ],
    ".cpp": [
        ("using-namespace-std", "info", re.compile(r"^\s*using\s+namespace\s+std\s*;"),
         "`using namespace std;` pollutes the global namespace. Fine in tiny exercises; avoid it in headers and real code."),
        ("system-pause", "warn", re.compile(r"system\(\s*\"pause\"\s*\)"), "`system(\"pause\")` is Windows-only and unsafe."),
    ],
}
RULES[".mjs"] = RULES[".js"]
RULES[".h"] = RULES[".hpp"] = RULES[".cpp"]

COMMENT_PREFIX = {".py": "#", ".js": "//", ".mjs": "//", ".cpp": "//", ".h": "//", ".hpp": "//"}


def code_lines(text: str, suffix: str) -> list[tuple[int, str]]:
    """(line number, code) pairs with full-line comments and block comments removed."""
    prefix = COMMENT_PREFIX.get(suffix, "#")
    result, in_block = [], False
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if suffix != ".py":
            if in_block:
                if "*/" in stripped:
                    in_block = False
                continue
            if stripped.startswith("/*"):
                in_block = "*/" not in stripped
                continue
        if not stripped or stripped.startswith(prefix):
            continue
        result.append((number, line.split(f" {prefix} ")[0].rstrip()))
    return result


def review_file(path: Path, passed: bool) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    findings = []
    for number, line in code_lines(text, path.suffix):
        for rule, severity, pattern, message in RULES.get(path.suffix, []):
            if pattern.search(line):
                findings.append(Finding(rule, severity, message, path.name, number))
    if passed and re.search(r"(#|//)\s*TODO", text):
        findings.append(Finding("todo-left", "info", "It passes. Remove the leftover TODO comments to finish tidily.", path.name))
    return findings


def _normalise(text: str, suffix: str) -> str:
    return "\n".join(re.sub(r"\s+", " ", code).strip() for _, code in code_lines(text, suffix))


def text_similarity(a: str, b: str, suffix: str) -> float:
    return difflib.SequenceMatcher(None, _normalise(a, suffix), _normalise(b, suffix)).ratio()


def similarity(student: Path, solution: Path) -> float | None:
    """How close the student's code is to the model answer (0–1), ignoring comments and spacing."""
    try:
        a = _normalise(student.read_text(encoding="utf-8", errors="replace"), student.suffix)
        b = _normalise(solution.read_text(encoding="utf-8", errors="replace"), solution.suffix)
    except OSError:
        return None
    if len(b) < 150:  # tiny answers converge naturally, so don't judge them
        return None
    return round(difflib.SequenceMatcher(None, a, b).ratio(), 3)


def _sections(text: str) -> dict[str, set[str]]:
    sections, current = {}, "_intro"
    for line in text.splitlines():
        if line.startswith("## ") or line.startswith("### "):  # the "# Title" line isn't a section to fill
            current = line.strip("# ").strip().lower()
            sections.setdefault(current, set())
        elif line.strip():
            sections.setdefault(current, set()).add(line.strip())
    return sections


def notes_score(current: str, template: str | None) -> float:
    """Share of the template's sections that now contain something new (0–1)."""
    template_sections = _sections(template or "")
    now = _sections(current)
    headings = [h for h in template_sections if h != "_intro"] or [h for h in now if h != "_intro"]
    if not headings:
        return 0.0
    filled = 0
    for heading in headings:
        added = now.get(heading, set()) - template_sections.get(heading, set())
        # ignore lines that are only a list number like "1." or a bold label
        if any(len(re.sub(r"^\d+\.|\*\*[^*]+\*\*:?", "", line).strip()) >= 3 for line in added):
            filled += 1
    return filled / len(headings)
