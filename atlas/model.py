"""The data ATLAS builds while assessing: exercises → lessons → modules → courses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# How much each exercise status counts towards progress.
STATUS_LABEL = {
    "passed": "✅ passed",
    "partial": "🟡 partial",
    "check": "🔎 runs, output differs",
    "failing": "❌ failing",
    "error": "💥 crashes",
    "not_started": "⬜ not started",
    "manual": "📝 manual check",
}


@dataclass
class Finding:
    rule: str
    severity: str  # "warn" | "info"
    message: str
    file: str = ""
    line: int | None = None


@dataclass
class Exercise:
    course: str
    rel: str
    dir: Path
    name: str
    kind: str  # exercise | debugging | challenge | project | exam
    lesson_rel: str
    student_files: list[Path]
    test_files: list[Path]
    solution_dir: Path | None
    status: str = "not_started"
    passed: int = 0
    total: int = 0
    failures: list[tuple[str, str]] = field(default_factory=list)
    detail: str = ""
    modified: bool = False
    dirty: bool = False
    first_activity: datetime | None = None
    last_activity: datetime | None = None
    findings: list[Finding] = field(default_factory=list)
    similarity: float | None = None

    @property
    def score(self) -> float:
        if self.status == "passed":
            return 1.0
        if self.status == "partial" and self.total:
            return self.passed / self.total
        if self.status == "check":
            return 0.5
        return 0.0

    @property
    def key(self) -> str:
        return f"{self.course}:{self.rel}"


@dataclass
class Knowledge:
    title: str = ""
    outcomes: list[str] = field(default_factory=list)
    key_terms: list[tuple[str, str]] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)


@dataclass
class Lesson:
    course: str
    rel: str
    dir: Path
    title: str
    module_id: str
    module_title: str
    kind: str  # lesson | review | orientation | exam | project
    weight: float  # planned study weeks
    order: int = 0
    exercises: list[Exercise] = field(default_factory=list)
    notes_score: float | None = None
    knowledge: Knowledge = field(default_factory=Knowledge)

    @property
    def completion(self) -> float:
        if self.exercises:
            return sum(e.score for e in self.exercises) / len(self.exercises)
        return 1.0 if (self.notes_score or 0) >= 0.6 else 0.0

    @property
    def complete(self) -> bool:
        return self.completion >= 0.999

    @property
    def touched(self) -> bool:
        return any(e.modified or e.status not in ("not_started", "manual") for e in self.exercises) or bool(self.notes_score)

    @property
    def started_at(self) -> datetime | None:
        dates = [e.first_activity for e in self.exercises if e.first_activity]
        return min(dates) if dates else None

    @property
    def completed_at(self) -> datetime | None:
        if not self.complete:
            return None
        dates = [e.last_activity for e in self.exercises if e.last_activity]
        return max(dates) if dates else None


@dataclass
class GateCheck:
    label: str
    ok: bool
    detail: str = ""
    required: bool = True


@dataclass
class Module:
    course: str
    id: str
    title: str
    lessons: list[Lesson]
    readme: Path | None = None
    explain_questions: list[str] = field(default_factory=list)
    gate_ticked: int = 0
    gate_boxes: int = 0
    verdict: str = ""
    checks: list[GateCheck] = field(default_factory=list)

    @property
    def completion(self) -> float:
        weights = [(l.completion, max(l.weight, 0.01)) for l in self.lessons if l.kind != "orientation"]
        total = sum(w for _, w in weights)
        return sum(c * w for c, w in weights) / total if total else 0.0

    @property
    def touched(self) -> bool:
        return any(l.touched for l in self.lessons)


@dataclass
class CourseReport:
    key: str
    title: str
    path: Path
    adapter: str
    lessons: list[Lesson] = field(default_factory=list)
    modules: list[Module] = field(default_factory=list)
    total_weeks: float = 0.0
    done_weeks: float = 0.0
    start: datetime | None = None
    pace: float | None = None  # planned weeks completed per calendar week
    recent_pace: float | None = None
    eta_weeks: float | None = None
    finish_date: datetime | None = None
    target_date: datetime | None = None
    confidence: str = "none"
    verdict: str = ""
    position: str = ""
    next_step: str = ""
    next_unwritten: str = ""
    dirty_files: list[str] = field(default_factory=list)
    last_activity: datetime | None = None
    activity_days: set = field(default_factory=set)
    commit_times: list = field(default_factory=list)
    plan: object = None
    error: str = ""

    @property
    def exercises(self) -> list[Exercise]:
        return [e for l in self.lessons for e in l.exercises]

    @property
    def progress(self) -> float:
        return self.done_weeks / self.total_weeks if self.total_weeks else 0.0
