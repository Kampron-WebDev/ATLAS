"""Assesses ONE course: discover → compare with starters → run your code → review → group."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from . import checks, knowledge
from .adapters import Plan, adapter_for
from .config import Config, CourseConfig
from .gitinfo import Repo
from .model import CourseReport, Exercise, Finding, Module
from .runners import Outcome, run_cpp, run_node, run_pytest
from .state import Cache, fingerprint

NOTE_FILES = ("MY-NOTES.md", "MY-EXAM.md")


def _status(outcome: Outcome, adapter_kind: str) -> str:
    if adapter_kind == "cpp":
        if outcome.compiled is None:
            return "manual"
        if not outcome.compiled:
            return "failing"
        return "passed" if outcome.output_matches or outcome.passed else "check"
    if outcome.crashed:
        return "error"
    if outcome.total and outcome.passed == outcome.total:
        return "passed"
    return "partial" if outcome.passed else "failing"


def assess_course(cfg: CourseConfig, config: Config, cache: Cache, run_tests: bool = True) -> CourseReport:
    report = CourseReport(key=cfg.key, title=cfg.title, path=cfg.path, adapter=cfg.adapter)
    if not cfg.path.exists():
        report.error = f"course folder not found: {cfg.path}"
        return report

    adapter = adapter_for(cfg)
    try:
        plan = adapter.plan()
    except Exception as err:  # the course can still be assessed without its plan
        plan = Plan(total_weeks=0.0)
        report.error = f"could not read the course plan ({err}); ETA unavailable"
    report.total_weeks = plan.total_weeks
    report.lessons = adapter.discover(plan)
    report.plan = plan
    repo = Repo(cfg.path)
    report.start = repo.start_date()
    report.commit_times = list(repo.commit_dates)

    exercises = [e for lesson in report.lessons for e in lesson.exercises]

    # Which exercises did the student change? (Compared with the ORIGINAL starters in the first commit.)
    for ex in exercises:
        ex.modified = (not repo.ok) or any(not repo.is_original(f) for f in ex.student_files)
        ex.dirty = any(repo.is_dirty(f) for f in ex.student_files)
        dates = [d for f in ex.student_files for d in repo.activity(f)]
        ex.first_activity = min(dates) if dates else None
        ex.last_activity = max(dates) if dates else None

    # C++ work may pre-date the first commit, so assess every lesson up to the furthest one touched.
    frontier = -1
    if adapter.kind == "cpp":
        touched_prefixes = {p.split("/")[0] for p in list(repo.touches) + list(repo.dirty)}
        for lesson in report.lessons:
            if lesson.rel in touched_prefixes or any(e.modified for e in lesson.exercises):
                frontier = max(frontier, lesson.order)
    lesson_order = {l.rel: l.order for l in report.lessons}

    def should_assess(ex: Exercise) -> bool:
        return bool(ex.student_files) and (ex.modified or lesson_order[ex.lesson_rel] <= frontier)

    def job(ex: Exercise) -> tuple[Exercise, Outcome | None]:
        files = ex.student_files + ex.test_files
        if adapter.kind == "cpp" and ex.solution_dir:
            files += list(ex.solution_dir.glob("*.cpp"))
        fp = fingerprint(files, extra=adapter.kind + cfg.stdin)
        cached = cache.get(ex.key, fp)
        if cached is not None:
            return ex, Outcome.from_dict(cached)
        if not run_tests:  # --no-tests: only reuse results for code that hasn't changed
            return ex, None
        if adapter.kind == "node":
            outcome = run_node(ex.dir, ex.test_files, config.test_timeout)
        elif adapter.kind == "pytest":
            outcome = run_pytest(ex.dir, ex.test_files, cfg.python, config.test_timeout)
        else:
            outcome = run_cpp(ex.dir, ex.solution_dir, cfg.gxx, cfg.stdin, config.test_timeout)
        cache.put(ex.key, fp, outcome.to_dict())
        return ex, outcome

    to_run = [ex for ex in exercises if should_assess(ex)]
    with ThreadPoolExecutor(max_workers=config.workers) as pool:
        for ex, outcome in pool.map(job, to_run):
            if outcome is None:
                ex.status, ex.detail = "manual", "changed since the last full review. Run `atlas` without --no-tests"
                continue
            ex.passed, ex.total = outcome.passed, outcome.total
            ex.failures, ex.detail = outcome.failures, outcome.detail
            ex.status = _status(outcome, adapter.kind)
            # An untouched starter isn't "failing": it's waiting for you. (C++ is exempt: work there
            # can pre-date the first commit, so "unchanged" doesn't mean "untouched".)
            if not ex.modified and ex.status not in ("passed", "manual") and adapter.kind != "cpp":
                ex.status = "not_started"
            if outcome.detail.startswith(("numbers match", "final answer")):
                ex.findings.append(Finding("format-differs", "info",
                                           f"Correct result, but {outcome.detail.split(';', 1)[-1].strip()}."))

    for ex in exercises:
        if ex.status == "not_started" and not ex.student_files:
            ex.status = "manual"
        if not ex.modified:
            continue
        for f in ex.student_files:
            ex.findings.extend(checks.review_file(f, ex.status == "passed"))
            solution = ex.solution_dir / f.name if ex.solution_dir else None
            if solution and solution.exists():
                # Fill-in-the-blank exercises (starter ≈ solution) naturally end up identical: don't judge those.
                starter = repo.baseline_text(f)
                if starter is not None and checks.text_similarity(starter, solution.read_text(encoding="utf-8", errors="replace"), f.suffix) >= 0.85:
                    continue
                ratio = checks.similarity(f, solution)
                if ratio is not None:
                    ex.similarity = max(ratio, ex.similarity or 0)
        if ex.similarity and ex.similarity >= config.similarity_warning:
            ex.findings.append(Finding(
                "close-to-model", "warn",
                f"Your code is {ex.similarity:.0%} identical to the model answer. Fine if you wrote it yourself; "
                "if you peeked, redo this exercise from scratch in two days.",
            ))

    # Notes, knowledge and modules
    for lesson in report.lessons:
        lesson.knowledge = knowledge.parse_lesson(lesson.dir / "README.md")
        for name in NOTE_FILES:
            notes = lesson.dir / name
            if notes.exists():
                if repo.ok and repo.is_original(notes):
                    lesson.notes_score = 0.0
                else:
                    template = repo.baseline_text(notes)
                    lesson.notes_score = checks.notes_score(notes.read_text(encoding="utf-8", errors="replace"), template)
                break

    modules: dict[str, Module] = {}
    for lesson in report.lessons:
        module = modules.get(lesson.module_id)
        if module is None:
            readme = adapter.module_readme(lesson)
            questions, ticked, boxes = knowledge.parse_gate(readme) if readme else ([], 0, 0)
            module = Module(cfg.key, lesson.module_id, lesson.module_title, [], readme, questions, ticked, boxes)
            modules[lesson.module_id] = module
        module.lessons.append(lesson)
    report.modules = list(modules.values())

    # Activity: every commit, plus files with uncommitted changes
    days = {d.date() for d in repo.commit_dates}
    report.dirty_files = sorted(p for p in repo.dirty
                                if not p.startswith((".vscode", "tools/")) and "/.vscode/" not in p and p != "ATLAS-STATUS.md")
    for rel in report.dirty_files:
        path = cfg.path / rel
        if path.exists():
            days.add(datetime.fromtimestamp(path.stat().st_mtime).date())
    report.activity_days = days
    stamps = [e.last_activity for e in exercises if e.last_activity] + repo.commit_dates
    report.last_activity = max(stamps) if stamps else None

    # When did you really start? The first commit, unless you worked on files before making it.
    earliest = [report.start] if report.start else []
    for ex in exercises:
        if ex.modified or lesson_order[ex.lesson_rel] <= frontier:
            for f in ex.student_files:
                earliest.append(datetime.fromtimestamp(f.stat().st_mtime).astimezone())
    if cfg.start:
        earliest = [datetime.fromisoformat(cfg.start).astimezone()]
    report.start = min(earliest) if earliest else None
    return report
