"""Athena's link to ATLAS: notes integrity, the concept ledger, finding lessons and the context pack."""

from pathlib import Path

from atlas import brain, checks, tutor
from atlas.config import Config, CourseConfig
from atlas.model import CourseReport

TEMPLATE = "# My Notes\n\n## Quiz: my answers\n1.\n\n## Reflection\n**Still fuzzy:**\n"
LEDGER = """# Concepts

| Concept | Course | Lesson | Status | Last checked | Links |
|---|---|---|---|---|---|
| Bytecode | python | L02 | 🟢 solid | 2026-09-30 | ↔ JS engines |
| Stack machine | python | L02 | 🟡 shaky | 2026-09-30 | |
| Pointers | C++ | 13 | 🔴 confused | 2026-09-30 | |
"""


def touch(root: Path, rel: str, text: str = "x") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# ─────────────────────────── notes integrity ───────────────────────────


def test_tutor_blocks_never_count_as_the_learners_notes():
    tutored = TEMPLATE + (f"\n{checks.TUTOR_BLOCK_START}\n## 🦉 Athena\n### Bytecode\nSimple instructions for the PVM.\n"
                          f"{checks.TUTOR_BLOCK_END}\n")
    assert checks.notes_score(tutored, TEMPLATE) == 0.0
    mine = TEMPLATE.replace("1.\n", "1. Tokens, then the AST, then bytecode.\n")
    assert checks.notes_score(mine + tutored[len(TEMPLATE):], TEMPLATE) == 0.5


def test_unclosed_tutor_block_is_stripped_to_the_end():
    text = f"keep\n{checks.TUTOR_BLOCK_START}\ntutor text"
    assert checks.strip_tutor_blocks(text).strip() == "keep"


# ─────────────────────────── the concept ledger ───────────────────────────


def config_at(root: Path, courses=()) -> Config:
    return Config(learner="Test", courses=list(courses), root=root)


def test_flagged_concepts_reads_shaky_rows_and_course_aliases(tmp_path):
    touch(tmp_path, "tutor/memory/concepts.md", LEDGER)
    flags = tutor.flagged_concepts(config_at(tmp_path))
    assert flags == {"python": ["Stack machine"], "cpp": ["Pointers"]}


def test_brief_directive_names_the_tutors_shaky_concepts(tmp_path):
    touch(tmp_path, "tutor/memory/concepts.md", LEDGER)
    report = CourseReport(key="python", title="Py", path=tmp_path, adapter="python")
    out = brain.directives(report, [report], config_at(tmp_path), {})
    assert any("Athena" in d and "Stack machine" in d for d in out)


def test_no_memory_means_no_flags(tmp_path):
    assert tutor.flagged_concepts(config_at(tmp_path)) == {}


# ─────────────────────────── finding the lesson ───────────────────────────


def python_course(tmp_path) -> Config:
    course = tmp_path / "Py"
    base = "Stage1.L/Lv01.F/M001.Intro"
    touch(course, f"{base}/README.md", "# Module 001: Intro")
    touch(course, f"{base}/L01.First/README.md", "# Lesson 01: First Steps")
    touch(course, f"{base}/L02.Bytecode/README.md", "# Lesson 02: Source to Bytecode")
    touch(course, f"{base}/L02.Bytecode/MY-NOTES.md", TEMPLATE)
    touch(course, f"{base}/L02.Bytecode/Exercises/01_Dis/main.py")
    touch(course, f"{base}/L02.Bytecode/Exercises/01_Dis/test_main.py")
    touch(course, f"{base}/L02.Bytecode/Exercises/01_Dis/solution/main.py")
    touch(course, "ATLAS-STATUS.md", f"**▶ Next:** Lesson 01. Open `{base}/L01.First/README.md`\n")
    touch(course, "tools/skeleton/curriculum.py", "LEVELS = []\nPROJECTS = []\nFINALS = []\n")
    cfg = CourseConfig("python", "Python Course", course, "python")
    return config_at(tmp_path / "ATLAS", [cfg])


def test_locate_an_exercise_file_finds_lesson_and_exercise(tmp_path):
    config = python_course(tmp_path)
    ex = config.courses[0].path / "Stage1.L/Lv01.F/M001.Intro/L02.Bytecode/Exercises/01_Dis"
    found = tutor.locate(config, f"@{ex / 'main.py'}")
    assert found.lesson.title == "Lesson 02: Source to Bytecode"
    assert found.exercise.name == "01_Dis" and not found.in_solution
    assert tutor.locate(config, str(ex / "solution" / "main.py")).in_solution


def test_search_by_title_words_and_course_alias(tmp_path):
    config = python_course(tmp_path)
    assert tutor.search(config, "py bytecode").lesson.title == "Lesson 02: Source to Bytecode"
    assert len(tutor.search(config, "lesson").candidates) == 2
    assert tutor.search(config, "nothing-like-this") is None


def test_search_finds_an_exercise_by_its_name(tmp_path):
    config = python_course(tmp_path)
    found = tutor.search(config, "py dis")
    assert found.lesson.title == "Lesson 02: Source to Bytecode" and found.exercise.name == "01_Dis"


def test_module_folder_lists_its_lessons(tmp_path):
    config = python_course(tmp_path)
    found = tutor.locate(config, str(config.courses[0].path / "Stage1.L/Lv01.F/M001.Intro"))
    assert found.lesson is None and [l.title for l in found.candidates][-1] == "Lesson 02: Source to Bytecode"


def test_course_root_resolves_to_atlas_current_lesson(tmp_path):
    config = python_course(tmp_path)
    assert tutor.locate(config, str(config.courses[0].path)).lesson.title == "Lesson 01: First Steps"


def test_context_pack_names_relation_notes_session_and_run_command(tmp_path):
    config = python_course(tmp_path)
    found = tutor.search(config, "bytecode")
    pack = tutor.context_md(config, found)
    assert "AHEAD by 1" in pack
    assert "MY-NOTES.md" in pack and "01_Dis" in pack and "-m pytest" in pack
    assert "NEW: create it" in pack
    session = tutor.session_file(config, found.lesson)
    touch(session.parent, session.name, "# Session: Lesson 02\n**Status:** in progress · concept 3 of 8\n")
    assert "RESUME (in progress · concept 3 of 8)" in tutor.context_md(config, found)
    assert tutor.open_sessions(config)[0][2] == "in progress · concept 3 of 8"


def test_lesson_without_my_notes_gets_a_separate_tutor_notes_file(tmp_path):
    config = python_course(tmp_path)
    lesson = tutor.search(config, "first steps").lesson
    assert tutor.notes_file(lesson).name == tutor.TUTOR_NOTES
