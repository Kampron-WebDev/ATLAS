"""Reads lesson and module READMEs to know WHAT you should now know."""

from __future__ import annotations

import re
from pathlib import Path

from .model import Knowledge

QUESTION_HEADINGS = ("short assessment", "check yourself", "quiz")
TERM_HEADINGS = ("key words",)
OUTCOME_HEADINGS = ("by the end", "you can")


def _heading_sections(text: str) -> list[tuple[str, list[str]]]:
    sections, title, body = [], "", []
    for line in text.splitlines():
        if re.match(r"^#{2,4} ", line):
            sections.append((title, body))
            title, body = line.lstrip("#").strip().lower(), []
        else:
            body.append(line)
    sections.append((title, body))
    return sections


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


def parse_lesson(readme: Path) -> Knowledge:
    try:
        text = readme.read_text(encoding="utf-8")
    except OSError:
        return Knowledge(title=readme.parent.name)
    knowledge = Knowledge(title=next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), readme.parent.name))

    for heading, body in _heading_sections(text):
        if any(h in heading for h in TERM_HEADINGS):
            for line in body:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 2 and cells[0] and not set(cells[0]) <= set("-: ") and cells[0].lower() not in ("word", "term"):
                    knowledge.key_terms.append((_clean(cells[0]), _clean(cells[1])))
        elif any(h in heading for h in QUESTION_HEADINGS):
            for line in body:
                if "<details" in line:
                    break
                match = re.match(r"^\s*\d+\.\s+(.+)", line)
                if match:
                    knowledge.questions.append(_clean(match.group(1)))
        elif any(h in heading for h in OUTCOME_HEADINGS):
            for line in body:
                if re.match(r"^\s*[-*]\s+", line):
                    knowledge.outcomes.append(_clean(re.sub(r"^\s*[-*]\s+(\[.\]\s*)?", "", line)))
    return knowledge


def parse_gate(readme: Path) -> tuple[list[str], int, int]:
    """(explain-it questions, ticked gate boxes, total gate boxes) from a module/week/lesson README."""
    try:
        text = readme.read_text(encoding="utf-8")
    except OSError:
        return [], 0, 0
    questions, ticked, total = [], 0, 0
    in_gate, in_explain = False, False
    for line in text.splitlines():
        if re.match(r"^#{2,3} ", line):
            in_gate = "gate" in line.lower() or "done when" in line.lower()
            in_explain = False
            continue
        if not in_gate:
            continue
        box = re.match(r"^- \[( |x|X)\]\s*(.*)", line)
        if box:
            total += 1
            ticked += box.group(1) in "xX"
            in_explain = "explain it" in box.group(2).lower()
            continue
        sub = re.match(r"^\s{2,}- (.+)", line)
        if sub and in_explain:
            questions.append(_clean(sub.group(1)))
    return questions, ticked, total
