"""One full ATLAS pass over every course."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from . import brain
from .assess import assess_course
from .config import Config
from .model import CourseReport
from .state import Cache, History, Ledger


@dataclass
class Result:
    config: Config
    now: datetime
    reports: list[CourseReport]
    ledger: Ledger
    holds: dict[str, str] = field(default_factory=dict)
    auths: dict[str, brain.Authorization] = field(default_factory=dict)
    assignments: list[brain.Assignment] = field(default_factory=list)
    well: brain.Wellbeing | None = None
    changes: brain.Changes | None = None
    reviews: list = field(default_factory=list)
    snapshot: dict = field(default_factory=dict)

    def course(self, key: str) -> CourseReport | None:
        return next((r for r in self.reports if r.key == key), None)


def run(config: Config, run_tests: bool = True, only: str | None = None, save_history: bool = True) -> Result:
    now = datetime.now().astimezone()
    cache = Cache(config.root / ".cache" / "results.json")
    ledger = Ledger(config.root / "ledger" / "gates.json")
    history = History(config.root / "history")

    reports = []
    for cfg in config.courses:
        if only and cfg.key != only:
            continue
        report = assess_course(cfg, config, cache, run_tests=run_tests)
        brain.compute_pace(report, now)
        report.next_unwritten = brain.next_unwritten(report)
        for module in report.modules:
            brain.evaluate_gate(module, ledger, config)
        lesson = brain.current_lesson(report)
        report.position = f"{lesson.module_title} → {lesson.title}" if lesson else (
            f"All written lessons done. Next: {report.next_unwritten}" if report.next_unwritten else "Course complete 🎓")
        reports.append(report)
    cache.save()

    result = Result(config, now, reports, ledger)
    result.holds = brain.compute_holds(reports, now, config.hold_gap_weeks)
    result.auths = {r.key: brain.authorize(r, ledger, result.holds) for r in reports if not r.error or r.lessons}
    result.assignments = brain.plan_assignments(reports, result.holds, result.auths, config, now)
    result.well = brain.wellbeing(reports, now)
    result.reviews = brain.reviews_due(reports, config, now.date())
    result.snapshot = brain.snapshot(reports, now)
    previous = history.snapshots()
    result.changes = brain.changes_since(previous, result.snapshot, config, now)
    if save_history and not only:
        history.save(result.snapshot)
    return result
