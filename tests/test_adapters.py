"""Discovery tests on miniature course trees."""

from pathlib import Path

from atlas.adapters import Plan, CppAdapter, FullStackAdapter, JSTSAdapter, PythonAdapter
from atlas.config import CourseConfig


def touch(root: Path, rel: str, text: str = "x") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_fullstack_units_are_weeks(tmp_path):
    base = "Year1.F/M01.Computing/W1.HowComputers"
    touch(tmp_path, f"{base}/README.md", "# Month 01 · Week 1: How Computers Run Programs")
    touch(tmp_path, f"{base}/D1.What/README.md", "# Day 1: What")
    touch(tmp_path, f"{base}/D1.What/Exercises/01_A/main.js")
    touch(tmp_path, f"{base}/D1.What/Exercises/01_A/main.test.js")
    touch(tmp_path, f"{base}/D6.Project-X/main.js")
    touch(tmp_path, f"{base}/D6.Project-X/main.test.js")
    touch(tmp_path, "00.Orientation/Exercises/01_Hello/main.test.js")
    adapter = FullStackAdapter(CourseConfig("fs", "FS", tmp_path, "fullstack"))
    plan = Plan(total_weeks=144, module_weight={"M01-W1": 1 / 7})
    lessons = adapter.discover(plan)
    by_title = {l.title: l for l in lessons}
    day1 = by_title["Day 1: What"]
    assert day1.module_id == "M01-W1" and day1.weight == 1 / 7
    assert [e.kind for e in day1.exercises] == ["exercise"]
    project = next(l for l in lessons if l.rel.endswith("D6.Project-X"))
    assert project.kind == "project" and project.exercises[0].kind == "project"
    assert lessons[0].kind == "orientation" and lessons[0].weight == 0


def test_jsts_lessons_debugging_review_and_exam(tmp_path):
    mod = "Part1.JavaScript/P01.Foundations/M001.Intro"
    touch(tmp_path, f"{mod}/README.md", "# Module 001: Intro")
    touch(tmp_path, f"{mod}/L01.First/README.md", "# Lesson 01")
    touch(tmp_path, f"{mod}/L01.First/Debugging/01_Bug/main.js")
    touch(tmp_path, f"{mod}/L01.First/Debugging/01_Bug/main.test.js")
    touch(tmp_path, f"{mod}/L02.ModuleReview/Exercises/01_Challenge/main.test.js")
    touch(tmp_path, "Part1.JavaScript/P01.Foundations/Phase-Exam/Coding/01_Task/main.test.js")
    adapter = JSTSAdapter(CourseConfig("js", "JS", tmp_path, "jsts"))
    lessons = adapter.discover(Plan(total_weeks=90, module_weight={"M001": 0.1}))
    kinds = [(l.kind, [e.kind for e in l.exercises]) for l in lessons]
    assert kinds == [("lesson", ["debugging"]), ("review", ["challenge"]), ("exam", ["exam"])]
    assert lessons[0].module_id == "M001" and lessons[-1].module_id == "P01-EXAM"
    assert lessons[-1].weight == 0


def test_python_files(tmp_path):
    ex = "Stage1.L/Lv01.F/M001.P/L01.What/Exercises/01_Zen"
    touch(tmp_path, f"{ex}/main.py")
    touch(tmp_path, f"{ex}/helper.py")
    touch(tmp_path, f"{ex}/test_main.py")
    touch(tmp_path, f"{ex}/solution/main.py")
    adapter = PythonAdapter(CourseConfig("py", "Py", tmp_path, "python"))
    lessons = adapter.discover(Plan(total_weeks=127))
    exercise = lessons[0].exercises[0]
    assert [f.name for f in exercise.student_files] == ["helper.py", "main.py"]
    assert [f.name for f in exercise.test_files] == ["test_main.py"]
    assert exercise.solution_dir.name == "solution"


def test_cpp_exercises_only_under_exercises(tmp_path):
    touch(tmp_path, "02.Thinking/README.md", "# Lesson 02: Thinking")
    touch(tmp_path, "02.Thinking/Exercises/01_Trace/main.cpp")
    touch(tmp_path, "02.Thinking/Exercises/01_Trace/solution/main.cpp")
    touch(tmp_path, "02.Thinking/Examples/01_Demo/main.cpp")
    touch(tmp_path, "02.Thinking/C++ 20 Template Project/main.cpp")
    adapter = CppAdapter(CourseConfig("cpp", "C++", tmp_path, "cpp"))
    plan = adapter.plan()
    lessons = adapter.discover(plan)
    assert plan.total_weeks == 1.0
    assert [e.name for e in lessons[0].exercises] == ["01_Trace"]
    assert lessons[0].module_id == "02"
