"""Tests for ATLAS's building blocks: git hashing, runners' parsing, code review, knowledge extraction."""

from pathlib import Path

from atlas import checks, knowledge
from atlas.gitinfo import blob_sha, content_variants
from atlas.runners import compare_outputs, parse_junit

# ─────────────────────────── gitinfo ───────────────────────────


def test_blob_sha_matches_git():
    # `printf 'hello\n' | git hash-object --stdin` → ce01362…
    assert blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_content_variants_cover_line_endings():
    assert blob_sha(b"a\nb\n") in content_variants(b"a\r\nb\r\n")


# ─────────────────────────── runners ───────────────────────────

NODE_JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testcase name="adds numbers" time="0.001" classname="test"/>
  <testcase name="rejects bad input" time="0.002" classname="test">
    <failure type="testCodeFailure" message="Expected values to be strictly equal:&#10;1 !== 2">details</failure>
  </testcase>
</testsuites>"""

PYTEST_JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" errors="1" failures="0" skipped="1" tests="3">
  <testcase classname="test_main" name="test_ok"/>
  <testcase classname="test_main" name="test_setup"><error message="ImportError: boom">trace</error></testcase>
  <testcase classname="test_main" name="test_skip"><skipped message="later"/></testcase>
</testsuite></testsuites>"""


def test_parse_node_junit():
    outcome = parse_junit(NODE_JUNIT)
    assert (outcome.passed, outcome.failed, outcome.total) == (1, 1, 2)
    assert outcome.failures[0][0] == "rejects bad input"
    assert "strictly equal" in outcome.failures[0][1]


def test_parse_pytest_junit_counts_errors_and_ignores_skips():
    outcome = parse_junit(PYTEST_JUNIT)
    assert (outcome.passed, outcome.failed, outcome.total) == (1, 1, 2)


def test_compare_outputs_tiers():
    assert compare_outputs("Total:   42\n", "Total: 42")[0]  # whitespace only
    ok, note = compare_outputs("Enter the change: 5c x 1", "Change owed: 5c x 1")
    assert ok and note.startswith("numbers match")
    ok, note = compare_outputs("Enter 3 numbers: the biggest is 7", "Biggest: 7")
    assert ok and note.startswith("final answer")
    assert not compare_outputs("answer 8", "answer 7")[0]
    assert compare_outputs("x at 0x7ffe12", "x at 0x99aa01")[0]  # addresses ignored


# ─────────────────────────── checks ───────────────────────────


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_js_print_on_import_and_loose_equality(tmp_path):
    js = _write(tmp_path, "main.js", "export const f = (a) => a == 1;\n// console.log('commented is fine')\nconsole.log(f(1));\n")
    rules = {f.rule for f in checks.review_file(js, passed=False)}
    assert rules == {"print-on-import", "loose-equality"}


def test_strict_equality_is_not_flagged(tmp_path):
    js = _write(tmp_path, "main.js", "export const f = (a) => a === 1 && a !== 2;\n")
    assert checks.review_file(js, passed=False) == []


def test_python_rules(tmp_path):
    py = _write(tmp_path, "main.py", "def f(x):\n    if x == None:\n        pass\n    try:\n        pass\n    except:\n        pass\n\n"
                                     "print(f(1))\n\nif __name__ == '__main__':\n    print('guarded is fine')\n")
    rules = sorted(f.rule for f in checks.review_file(py, passed=False))
    assert rules == ["bare-except", "none-equality", "print-on-import"]


def test_todo_left_only_when_passed(tmp_path):
    py = _write(tmp_path, "main.py", "def f():\n    # TODO\n    return 1\n")
    assert [f.rule for f in checks.review_file(py, passed=True)] == ["todo-left"]
    assert checks.review_file(py, passed=False) == []


def test_similarity_ignores_comments_and_short_code(tmp_path):
    body = ("def solve(items):\n    total = 0\n    for item in items:\n        total += item * 2\n"
            "    for index, item in enumerate(items):\n        total -= index\n"
            "    return total - len(items) + 1 + 2 + 3 + 4 + 5 + 6 + 7\n")
    a = _write(tmp_path, "a.py", "# my version\n" + body)
    b = _write(tmp_path, "b.py", body)
    assert checks.similarity(a, b) == 1.0
    tiny = _write(tmp_path, "t.py", "x = 1\n")
    assert checks.similarity(tiny, tiny) is None


def test_notes_score():
    template = "# My Notes\n\n## Design question\n\n## Quiz\n1.\n\n## Reflection\n**Explain it:**\n"
    assert checks.notes_score(template, template) == 0.0
    filled = template.replace("## Quiz\n1.", "## Quiz\n1. A statement performs an action") + "It clicked today.\n"
    assert checks.notes_score(filled, template) == 2 / 3


# ─────────────────────────── knowledge ───────────────────────────

LESSON = """# Lesson 01: Things

## 🎯 By the end of this lesson you can
- Explain things
- Build stuff

## 9. Short assessment

1. What is a thing?
2. Why do **things** exist?

<details><summary>Answers</summary>

1. Hidden answer.

</details>

## 🔑 Key words

| Word | Meaning |
|---|---|
| Thing | An object |
| **Stuff** | Many things |
"""

MODULE = """# Module 001

## 🎯 Mastery gate

- [x] **Explain it:** I can answer every question below.
  - What is a closure?
  - Why use one?
- [ ] **Implement it:** exercises green.
- [x] **Debug it:** fixed.
"""


def test_parse_lesson(tmp_path):
    k = knowledge.parse_lesson(_write(tmp_path, "README.md", LESSON))
    assert k.title == "Lesson 01: Things"
    assert k.outcomes == ["Explain things", "Build stuff"]
    assert k.questions == ["What is a thing?", "Why do things exist?"]
    assert k.key_terms == [("Thing", "An object"), ("Stuff", "Many things")]


def test_parse_gate(tmp_path):
    questions, ticked, total = knowledge.parse_gate(_write(tmp_path, "README.md", MODULE))
    assert questions == ["What is a closure?", "Why use one?"]
    assert (ticked, total) == (2, 3)
