"""Course adapters: how each course is laid out, and its planned study weeks.

Every adapter answers the same questions:
  * which folders are lessons, and which module/gate unit does a lesson belong to?
  * which folders are exercises, and what are the student's files?
  * how many planned study weeks is each lesson worth, and how long is the whole course?
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .config import CourseConfig
from .model import Exercise, Lesson

SKIP_DIRS = {".git", ".vscode", "node_modules", ".venv", "__pycache__", "tools", "solution", "Examples",
             "C++ 20 Template Project", ".cache", "build", "dist"}


def first_heading(readme: Path) -> str:
    try:
        for line in readme.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    except OSError:
        pass
    return readme.parent.name


@dataclass
class Plan:
    total_weeks: float
    module_titles: dict[str, str] = field(default_factory=dict)
    module_order: list[str] = field(default_factory=list)  # every planned gate unit, in order
    module_weight: dict[str, float] = field(default_factory=dict)  # planned weeks per lesson, by module


class Adapter:
    kind = "node"  # node | pytest | cpp
    code_exts = (".js", ".mjs")

    def __init__(self, cfg: CourseConfig):
        self.cfg = cfg
        self.root = cfg.path

    # ── structure ────────────────────────────────────────────────
    def lesson_index(self, parts: tuple[str, ...]) -> int | None:
        raise NotImplementedError

    def module_of(self, parts: tuple[str, ...], index: int) -> tuple[str, str]:
        raise NotImplementedError

    def lesson_kind(self, name: str) -> str:
        if name == "00.Orientation":
            return "orientation"
        if "Exam" in name or "Assessment" in name:
            return "exam"
        if "ModuleReview" in name or "ReviewAndQuiz" in name:
            return "review"
        if "Project" in name:
            return "project"
        return "lesson"

    def module_readme(self, lesson: Lesson) -> Path | None:
        readme = lesson.dir.parent / "README.md"
        return readme if readme.exists() else None

    def is_exercise_dir(self, path: Path, files: list[str]) -> bool:
        return any(f.endswith(".test.js") for f in files)

    def student_files(self, path: Path) -> list[Path]:
        return sorted(p for p in path.iterdir() if p.is_file() and p.suffix in self.code_exts and not p.name.endswith(".test.js"))

    def test_files(self, path: Path) -> list[Path]:
        return sorted(p for p in path.iterdir() if p.is_file() and p.name.endswith(".test.js"))

    # ── plan ─────────────────────────────────────────────────────
    def plan(self) -> Plan:
        raise NotImplementedError

    def lesson_weight(self, plan: Plan, module_id: str, kind: str) -> float:
        if kind in ("orientation", "exam"):
            return 0.0
        return plan.module_weight.get(module_id, 0.0)

    # ── discovery ────────────────────────────────────────────────
    def discover(self, plan: Plan) -> list[Lesson]:
        lessons: dict[str, Lesson] = {}
        pending: list[tuple[Path, tuple[str, ...], list[str]]] = []

        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
            path = Path(dirpath)
            parts = path.relative_to(self.root).parts
            if not parts:
                continue
            index = self.lesson_index(parts)
            if index is not None and index == len(parts) - 1:
                self._make_lesson(lessons, plan, parts, index)
            if index is not None and self.is_exercise_dir(path, filenames):
                pending.append((path, parts, filenames))

        for path, parts, _ in pending:
            index = self.lesson_index(parts)
            lesson_rel = "/".join(parts[: index + 1])
            lesson = lessons.get(lesson_rel) or self._make_lesson(lessons, plan, parts, index)
            lesson.exercises.append(self._make_exercise(path, parts, lesson))

        ordered = sorted(lessons.values(), key=lambda l: self.sort_key(l.rel))
        for i, lesson in enumerate(ordered):
            lesson.order = i
            lesson.exercises.sort(key=lambda e: e.rel)
        return ordered

    def sort_key(self, rel: str) -> tuple:
        # Exams sort after the modules they belong to.
        return tuple((1 if "Exam" in p else 0, p) for p in rel.split("/"))

    def _make_lesson(self, lessons, plan, parts, index) -> Lesson:
        rel = "/".join(parts[: index + 1])
        directory = self.root.joinpath(*parts[: index + 1])
        module_id, module_title = self.module_of(parts, index)
        kind = self.lesson_kind(parts[index])
        lesson = Lesson(
            course=self.cfg.key,
            rel=rel,
            dir=directory,
            title=first_heading(directory / "README.md"),
            module_id=module_id,
            module_title=module_title,
            kind=kind,
            weight=self.lesson_weight(plan, module_id, kind),
        )
        lessons[rel] = lesson
        return lesson

    def _make_exercise(self, path: Path, parts: tuple[str, ...], lesson: Lesson) -> Exercise:
        rel = "/".join(parts)
        if "Debugging" in parts:
            kind = "debugging"
        elif lesson.kind == "exam":
            kind = "exam"
        elif lesson.kind == "review":
            kind = "challenge"
        elif path == lesson.dir:
            kind = "project"
        else:
            kind = "exercise"
        solution = path / "solution"
        return Exercise(
            course=self.cfg.key,
            rel=rel,
            dir=path,
            name=path.name,
            kind=kind,
            lesson_rel=lesson.rel,
            student_files=self.student_files(path),
            test_files=self.test_files(path),
            solution_dir=solution if solution.is_dir() else None,
        )


def _node_json(expression: str, module_path: Path) -> dict:
    """Import an ES module with Node and return JSON produced from it (`m` is the module)."""
    url = module_path.resolve().as_uri()
    script = f"import('{url}').then(m => console.log(JSON.stringify({expression})))"
    out = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[:300])
    return json.loads(out.stdout)


# ─────────────────────────────── Full-Stack ───────────────────────────────
class FullStackAdapter(Adapter):
    """YearN.*/MNN.*/WN.*/DN.* — the gate unit is a WEEK (each week ends with a review + gate)."""

    def lesson_index(self, parts):
        if parts[0] == "00.Orientation":
            return 0
        for i, p in enumerate(parts):
            if re.match(r"^D\d\.", p) and i >= 3 and re.match(r"^W\d\.", parts[i - 1]):
                return i
        return None

    def module_of(self, parts, index):
        if parts[0] == "00.Orientation":
            return "00", "Orientation"
        month = parts[index - 2][:3]  # "M01"
        week = parts[index - 1].split(".")[0]  # "W1"
        title = first_heading(self.root.joinpath(*parts[:index]) / "README.md")
        return f"{month}-{week}", title

    def plan(self):
        data = _node_json("{months: m.months.map(x => ({n: x.n, title: x.title, weeks: x.weeks.map(w => w.title)}))}",
                          self.root / "tools" / "skeleton" / "curriculum.mjs")
        plan = Plan(total_weeks=0.0)
        for month in data["months"]:
            for w, week_title in enumerate(month["weeks"], start=1):
                unit = f"M{month['n']:02d}-W{w}"
                plan.module_order.append(unit)
                plan.module_titles[unit] = f"Month {month['n']:02d} · Week {w}: {week_title}"
                plan.module_weight[unit] = 1 / 7  # 7 day-lessons per study week
                plan.total_weeks += 1
        return plan


# ─────────────────────────────── JS / TS ───────────────────────────────
class JSTSAdapter(Adapter):
    """PartN.*/PNN.*/MNNN.*/LNN.* plus PNN.*/Phase-Exam."""

    def lesson_index(self, parts):
        if parts[0] == "00.Orientation":
            return 0
        for i, p in enumerate(parts):
            if re.match(r"^L\d\d\.", p) and i >= 1 and re.match(r"^M\d{3}\.", parts[i - 1]):
                return i
            if p in ("Phase-Exam", "Level-Exam"):
                return i
        return None

    def module_of(self, parts, index):
        if parts[0] == "00.Orientation":
            return "00", "Orientation"
        if parts[index] in ("Phase-Exam", "Level-Exam"):
            group = parts[index - 1]
            return f"{group.split('.')[0]}-EXAM", f"{first_heading(self.root.joinpath(*parts[:index]) / 'README.md')} · exam"
        module = parts[index - 1]
        return module.split(".")[0], first_heading(self.root.joinpath(*parts[:index]) / "README.md")

    def plan(self):
        data = _node_json(
            "{phases: m.phases.map(p => ({n: p.n, weeks: p.weeks, modules: m.phases.find(q => q.n === p.n).modules"
            ".map(x => ({n: x.n, title: x.title, lessons: x.lessons.length}))})),"
            " projects: m.projects.map(p => p.weeks), finals: m.finals.map(f => f.weeks)}",
            self.root / "tools" / "skeleton" / "curriculum.mjs",
        )
        plan = Plan(total_weeks=sum(data["projects"]) + sum(data["finals"]))
        for phase in data["phases"]:
            plan.total_weeks += phase["weeks"]
            lessons_in_phase = sum(m["lessons"] for m in phase["modules"]) or 1
            for module in phase["modules"]:
                mid = f"M{module['n']:03d}"
                plan.module_order.append(mid)
                plan.module_titles[mid] = f"Module {module['n']:03d}: {module['title']}"
                plan.module_weight[mid] = phase["weeks"] / lessons_in_phase
        return plan


# ─────────────────────────────── Python ───────────────────────────────
class PythonAdapter(JSTSAdapter):
    """StageN.*/LvNN.*/MNNN.*/LNN.* plus LvNN.*/Level-Exam; tests are pytest."""

    kind = "pytest"
    code_exts = (".py",)

    def is_exercise_dir(self, path, files):
        return any(f.startswith("test_") and f.endswith(".py") for f in files)

    def student_files(self, path):
        return sorted(p for p in path.iterdir()
                      if p.is_file() and p.suffix == ".py" and not p.name.startswith("test_") and p.name != "conftest.py")

    def test_files(self, path):
        return sorted(p for p in path.iterdir() if p.is_file() and p.name.startswith("test_") and p.suffix == ".py")

    def plan(self):
        path = self.root / "tools" / "skeleton" / "curriculum.py"
        spec = importlib.util.spec_from_file_location("atlas_python_curriculum", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules.pop("atlas_python_curriculum", None)
        spec.loader.exec_module(module)

        plan = Plan(total_weeks=sum(p[4] for p in module.PROJECTS) + sum(f[3] for f in module.FINALS))
        for level in module.LEVELS:
            weeks, modules = level[5], level[7]
            plan.total_weeks += weeks
            lessons_in_level = sum(len(m[4]) for m in modules) or 1
            for m in modules:
                mid = f"M{m[0]:03d}"
                plan.module_order.append(mid)
                plan.module_titles[mid] = f"Module {m[0]:03d}: {m[2]}"
                plan.module_weight[mid] = weeks / lessons_in_level
        return plan


# ─────────────────────────────── C++ ───────────────────────────────
class CppAdapter(Adapter):
    """NN.LessonName/Exercises/NN_Name/{*.cpp, solution/}. Each lesson folder is its own gate unit."""

    kind = "cpp"
    code_exts = (".cpp", ".h", ".hpp", ".ixx", ".cppm")

    def lesson_index(self, parts):
        return 0 if re.match(r"^\d\d\.", parts[0]) else None

    def module_of(self, parts, index):
        return parts[0].split(".")[0], parts[0]

    def module_readme(self, lesson):
        readme = lesson.dir / "README.md"
        return readme if readme.exists() else None

    def is_exercise_dir(self, path, files):
        return path.parent.name == "Exercises" and any(f.endswith(".cpp") for f in files)

    def student_files(self, path):
        return sorted(p for p in path.iterdir() if p.is_file() and p.suffix in self.code_exts)

    def test_files(self, path):
        return []

    def plan(self):
        folders = sorted(p.name for p in self.root.iterdir() if p.is_dir() and re.match(r"^\d\d\.", p.name))
        plan = Plan(total_weeks=len(folders) * self.cfg.weeks_per_lesson)
        for name in folders:
            mid = name.split(".")[0]
            plan.module_order.append(mid)
            plan.module_titles[mid] = name
            plan.module_weight[mid] = self.cfg.weeks_per_lesson
        return plan


ADAPTERS = {"fullstack": FullStackAdapter, "jsts": JSTSAdapter, "python": PythonAdapter, "cpp": CppAdapter}


def adapter_for(cfg: CourseConfig) -> Adapter:
    return ADAPTERS[cfg.adapter](cfg)
