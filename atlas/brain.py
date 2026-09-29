"""The professor's judgement: pace, ETA, gates, sync & holds, the next lesson,
authorization for new lessons, wellbeing, reviews and the author briefs.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .config import Config
from .model import CourseReport, GateCheck, Lesson, Module
from .state import Ledger

WEEK = timedelta(days=7)
HOLD_GAP_WEEKS = 2.0  # a course this many planned weeks ahead of the slowest active course is put on hold
NEGLECT_DAYS = 4


# ─────────────────────────────── pace & ETA ───────────────────────────────
def compute_pace(report: CourseReport, now: datetime) -> None:
    report.done_weeks = sum(l.weight * l.completion for l in report.lessons)
    if not report.start or report.done_weeks <= 0:
        report.confidence = "none"
        report.verdict = "not started" if report.done_weeks <= 0 else ""
        return
    elapsed = max((now - report.start) / WEEK, 1 / 7)
    report.pace = report.done_weeks / elapsed

    window_start = now - timedelta(days=14)
    recent_done = sum(l.weight * l.completion for l in report.lessons
                      if l.touched and any(e.last_activity and e.last_activity >= window_start for e in l.exercises))
    report.recent_pace = recent_done / min(elapsed, 2.0)
    used = report.pace if elapsed < 2 else 0.5 * report.pace + 0.5 * report.recent_pace

    remaining = max(report.total_weeks - report.done_weeks, 0)
    if used > 0 and report.total_weeks:
        report.eta_weeks = remaining / used
        report.finish_date = now + report.eta_weeks * WEEK
        report.target_date = report.start + report.total_weeks * WEEK
        slack = report.total_weeks * 0.08 * WEEK
        if report.finish_date < report.target_date - slack:
            report.verdict = "ahead of plan"
        elif report.finish_date > report.target_date + slack:
            report.verdict = "behind plan"
        else:
            report.verdict = "on track"

    completed = sum(1 for l in report.lessons if l.complete and l.kind != "orientation")
    if elapsed < 2 or completed < 5:
        report.confidence = "low"
        if report.verdict:
            report.verdict = "early estimate"  # a few days of data can't say "behind" or "ahead" yet
    elif elapsed < 8:
        report.confidence = "medium"
    else:
        report.confidence = "high"


def sync_delta(report: CourseReport, now: datetime) -> float | None:
    """Planned weeks done minus planned weeks expected by now (target pace = 1.0)."""
    if not report.start:
        return None
    elapsed = max((now - report.start) / WEEK, 1 / 7)
    return report.done_weeks - min(elapsed, report.total_weeks or elapsed)


# ─────────────────────────────── gates ───────────────────────────────
def evaluate_gate(module: Module, ledger: Ledger, config: Config) -> None:
    if module.id == "00":  # orientation is setup, not a gated unit
        module.verdict, module.checks = "N/A", []
        return
    lessons = [l for l in module.lessons if l.kind != "orientation"]
    exercises = [e for l in lessons for e in l.exercises if e.status != "manual"]
    passed = [e for e in exercises if e.status == "passed"]
    checks = [GateCheck("All exercises & debugging challenges pass", bool(exercises) and len(passed) == len(exercises),
                        f"{len(passed)}/{len(exercises)} passing")]

    reviews = [l for l in lessons if l.kind == "review"]
    if reviews:
        ok = all(l.complete for l in reviews)
        checks.append(GateCheck("Module review challenge done", ok, "done" if ok else "not done yet"))

    with_notes = [l for l in lessons if l.notes_score is not None]
    if with_notes:
        written = [l for l in with_notes if l.notes_score >= config.notes_threshold]
        checks.append(GateCheck("Notes, quiz answers & reflections written", len(written) == len(with_notes),
                                f"{len(written)}/{len(with_notes)} lessons"))

    if module.gate_boxes:
        checks.append(GateCheck("Self-assessment gate ticked in the README", module.gate_ticked == module.gate_boxes,
                                f"{module.gate_ticked}/{module.gate_boxes} boxes"))

    close = [e.name for e in exercises if any(f.rule == "close-to-model" for f in e.findings)]
    checks.append(GateCheck("Work is clearly your own", not close, ", ".join(close) or "no concerns", required=False))
    warns = sum(1 for e in exercises for f in e.findings if f.severity == "warn" and f.rule != "close-to-model")
    checks.append(GateCheck("Code review clean", warns == 0, f"{warns} warning(s)", required=False))

    module.checks = checks
    if ledger.passed(module.course, module.id):
        module.verdict = "PASSED"
    elif all(c.ok for c in checks if c.required):
        module.verdict = "READY FOR EXAM"
    elif module.touched:
        module.verdict = "IN PROGRESS"
    else:
        module.verdict = "NOT STARTED"


# ─────────────────────────────── position & authorization ───────────────────────────────
def current_lesson(report: CourseReport) -> Lesson | None:
    for lesson in report.lessons:
        if lesson.kind == "orientation" and (lesson.complete or not lesson.exercises):
            continue
        if not lesson.complete:
            return lesson
    return None


def written_units(report: CourseReport) -> list[Module]:
    return [m for m in report.modules if m.id != "00"]


def next_unwritten(report: CourseReport) -> str:
    plan = getattr(report, "plan", None)
    if not plan or not plan.module_order:
        return ""
    written = {m.id for m in report.modules}
    for unit in plan.module_order:
        if unit not in written:
            return plan.module_titles.get(unit, unit)
    return ""


@dataclass
class Authorization:
    course: str
    granted: bool
    reasons: list[str] = field(default_factory=list)
    next_unit: str = ""


def authorize(report: CourseReport, ledger: Ledger, holds: dict[str, str]) -> Authorization:
    auth = Authorization(report.key, False, next_unit=report.next_unwritten)
    if not report.next_unwritten:
        auth.reasons.append("Every lesson in this course already exists. ATLAS controls pacing and gates only.")
        return auth
    missing = [m for m in written_units(report) if not ledger.passed(report.key, m.id)]
    for module in missing:
        state = module.verdict or "IN PROGRESS"
        auth.reasons.append(f"Gate not passed: {module.title} ({state}, {module.completion:.0%} complete)")
    if report.key in holds:
        auth.reasons.append(f"Course is ON HOLD for sync: {holds[report.key]}")
    auth.granted = not auth.reasons
    if auth.granted:
        auth.reasons.append("All written units are gate-passed and the course is in sync.")
    return auth


# ─────────────────────────────── sync, holds and the next lesson ───────────────────────────────
def compute_holds(reports: list[CourseReport], now: datetime, gap_weeks: float = HOLD_GAP_WEEKS) -> dict[str, str]:
    deltas = {r.key: sync_delta(r, now) for r in reports if not r.error and r.start}
    active = {k: v for k, v in deltas.items() if v is not None}
    if len(active) < 2 or gap_weeks <= 0:
        return {}
    slowest_key = min(active, key=active.get)
    holds = {}
    for key, delta in active.items():
        gap = delta - active[slowest_key]
        if key != slowest_key and gap >= gap_weeks and delta > 0.5:
            title = next(r.title for r in reports if r.key == slowest_key)
            holds[key] = f"{gap:.1f} planned weeks ahead of {title}. Bring that course up first."
    return holds


@dataclass
class Assignment:
    course: str
    course_title: str
    action: str  # "lesson" | "finish" | "exam" | "request-lessons" | "hold"
    title: str
    detail: str
    minutes: int
    path: str = ""
    score: float = 0.0


def plan_assignments(reports: list[CourseReport], holds: dict[str, str], auths: dict[str, Authorization],
                     config: Config, now: datetime) -> list[Assignment]:
    """Rank what to study, across all courses. The first item is THE next lesson."""
    result = []
    for report in reports:
        if report.error and not report.lessons:
            continue
        delta = sync_delta(report, now) or 0.0
        idle_days = (now - report.last_activity).days if report.last_activity else 99
        base = -delta + (0.4 if report.key == config.spine else 0) + (1.0 if idle_days >= NEGLECT_DAYS else 0)

        if report.key in holds:
            result.append(Assignment(report.key, report.title, "hold", "⏸ On hold for sync", holds[report.key], 0, score=-99))
            continue

        exam_ready = [m for m in report.modules if m.verdict == "READY FOR EXAM"]
        if exam_ready:
            m = exam_ready[0]
            result.append(Assignment(report.key, report.title, "exam", f"Gate exam: {m.title}",
                                     f"Run `atlas gate {report.key} {m.id}`, answer the exam sheet, then ask Claude to grade it.",
                                     45, score=base + 1.5))
            continue

        lesson = current_lesson(report)
        if lesson:
            todo = [e for e in lesson.exercises if e.status != "passed" and e.status != "manual"]
            started = [e for e in todo if e.modified]
            if started:
                names = ", ".join(e.name for e in started[:3])
                result.append(Assignment(report.key, report.title, "finish", f"Finish: {lesson.title}",
                                         f"In progress: {names}. {len(todo)} item(s) left in this lesson.",
                                         30 * len(todo), str(lesson.dir), score=base + 0.8))
            else:
                result.append(Assignment(report.key, report.title, "lesson", lesson.title,
                                         f"{lesson.module_title} · {len(todo)} exercise(s) and challenge(s)",
                                         120, str(lesson.dir / "README.md"), score=base))
            continue

        auth = auths.get(report.key)
        if report.next_unwritten:
            if auth and auth.granted:
                detail = f"Ask Claude: \"ATLAS authorized {report.key}: write {report.next_unwritten}\"."
            else:
                detail = "; ".join(auth.reasons) if auth else "Gate the current unit first."
            result.append(Assignment(report.key, report.title, "request-lessons", f"Next: {report.next_unwritten}",
                                     detail, 10, score=base - 0.5))
    result.sort(key=lambda a: -a.score)
    return result


# ─────────────────────────────── wellbeing & streaks ───────────────────────────────
@dataclass
class Wellbeing:
    streak: int = 0
    active_last_7: int = 0
    late_nights: int = 0
    notes: list[str] = field(default_factory=list)
    calendar: dict = field(default_factory=dict)  # date → number of courses active


def wellbeing(reports: list[CourseReport], now: datetime) -> Wellbeing:
    w = Wellbeing()
    days = Counter()
    for r in reports:
        for d in r.activity_days:
            days[d] += 1
    w.calendar = dict(days)
    today = now.date()
    day = today if today in days else today - timedelta(days=1)
    while day in days:
        w.streak += 1
        day -= timedelta(days=1)
    w.active_last_7 = sum(1 for i in range(7) if today - timedelta(days=i) in days)
    late = {t for r in reports for t in getattr(r, "commit_times", []) if t >= now - timedelta(days=7) and 0 <= t.hour < 5}
    w.late_nights = len({t.date() for t in late})

    if w.streak >= 3:
        w.notes.append(f"🔥 {w.streak}-day streak. Consistency beats intensity, keep it going.")
    if w.active_last_7 >= 7:
        w.notes.append("🛌 You've studied every day this week. Take a proper rest day: memory consolidates during rest.")
    if w.late_nights >= 2:
        w.notes.append(f"🌙 {w.late_nights} late-night sessions this week. Sleep is when learning sticks; aim to finish before midnight.")
    if w.streak == 0 and days:
        w.notes.append("👋 No activity since yesterday. Even 25 focused minutes today keeps the chain alive.")
    return w


# ─────────────────────────────── spaced reviews ───────────────────────────────
def reviews_due(reports: list[CourseReport], config: Config, today: date) -> list[tuple[CourseReport, Lesson, int]]:
    due = []
    for r in reports:
        for lesson in r.lessons:
            if lesson.kind == "orientation" or not lesson.completed_at:
                continue
            age = (today - lesson.completed_at.date()).days
            for interval in config.review_intervals:
                if interval <= age <= interval + 2:
                    due.append((r, lesson, interval))
                    break
    return due


# ─────────────────────────────── changes since last run ───────────────────────────────
def snapshot(reports: list[CourseReport], now: datetime) -> dict:
    return {
        "date": now.isoformat(timespec="seconds"),
        "courses": {
            r.key: {
                "done_weeks": round(r.done_weeks, 3),
                "progress": round(r.progress, 4),
                "pace": r.pace,
                "eta_weeks": r.eta_weeks,
                "lessons_complete": sum(1 for l in r.lessons if l.complete),
                "units": {m.id: m.verdict for m in r.modules},
                "exercises": {e.rel: e.status for e in r.exercises},
            }
            for r in reports if not (r.error and not r.lessons)
        },
    }


@dataclass
class Changes:
    newly_passed: list[str] = field(default_factory=list)
    regressions: list[str] = field(default_factory=list)
    stuck: list[str] = field(default_factory=list)


def changes_since(previous: list[dict], current: dict, config: Config, now: datetime) -> Changes:
    ch = Changes()
    if previous:
        last = previous[-1]["courses"]
        for course, data in current["courses"].items():
            before = last.get(course, {}).get("exercises", {})
            for ex, status in data["exercises"].items():
                old = before.get(ex)
                if status == "passed" and old and old != "passed":
                    ch.newly_passed.append(f"{course}: {ex.split('/')[-1]}")
                if old == "passed" and status != "passed":
                    ch.regressions.append(f"{course}: {ex}")
    horizon = now - timedelta(days=config.stuck_days)
    for course, data in current["courses"].items():
        for ex, status in data["exercises"].items():
            if status not in ("failing", "partial", "error"):
                continue
            first_bad = None
            for snap in previous:
                if snap["courses"].get(course, {}).get("exercises", {}).get(ex) in ("failing", "partial", "error"):
                    first_bad = datetime.fromisoformat(snap["date"])
                    break
            if first_bad and first_bad <= horizon:
                ch.stuck.append(f"{course}: {ex}")
    return ch


# ─────────────────────────────── author briefs ───────────────────────────────
def directives(report: CourseReport, reports: list[CourseReport], config: Config, holds: dict[str, str]) -> list[str]:
    """Binding instructions for whoever writes this learner's NEXT lessons."""
    out = []
    exercises = report.exercises
    touched = [l for l in report.lessons if l.touched and l.kind != "orientation"]

    if report.pace is not None:
        if report.pace > 1.6:
            out.append(f"Pace is {report.pace:.1f}× the plan. Raise the difficulty: add ⭐ stretch goals, fewer hints, "
                       "one extra no-hints exercise per lesson.")
        elif report.pace < 0.6:
            out.append(f"Pace is {report.pace:.1f}× the plan. Reduce the load: smaller steps, more worked examples, "
                       "hints on every exercise, and split long lessons in two.")

    notes = [l.notes_score for l in touched if l.notes_score is not None]
    if notes and sum(notes) / len(notes) < config.notes_threshold:
        out.append("Reflection and quiz answers are being skipped. Make them part of the exercises "
                   "(e.g. a test that reads an ANSWERS.md), and keep lesson reading shorter.")

    rules = Counter(f.rule for e in exercises for f in e.findings)
    if rules["print-on-import"] >= 2:
        out.append("The learner leaves top-level print/console.log calls in modules. Include a short "
                   "'side effects on import' reminder and one debugging challenge built around it.")
    if rules["close-to-model"]:
        out.append("Several solutions match the model answers closely. Use variation exercises whose answers "
                   "can't be pattern-matched, and add 'explain your solution' prompts.")
    if rules["loose-equality"] or rules["none-equality"]:
        out.append("Equality/identity habits need reinforcing (== vs === / is None). Revisit this briefly in the next module.")
    if rules["todo-left"] >= 3:
        out.append("Finished code keeps its TODO comments. Add 'tidy up' to the Done-when checklist.")

    skipped_debug = [e for l in touched if l.complete or l.completion > 0.5 for e in l.exercises
                     if e.kind == "debugging" and e.status == "not_started"]
    if skipped_debug:
        out.append(f"{len(skipped_debug)} debugging challenge(s) skipped. Open the next lesson with a debugging warm-up.")

    weak = [l for l in touched if 0 < l.completion < 1]
    for l in weak[:3]:
        missing = [e.name for e in l.exercises if e.status != "passed"]
        out.append(f"Revisit '{l.title}': unfinished {', '.join(missing[:3])}. Add a warm-up on this in the next module.")

    if report.key in holds:
        out.append(f"HOLD: {holds[report.key]} Do not generate new lessons for this course until ATLAS lifts the hold.")

    cpp = next((r for r in reports if r.adapter == "cpp" and r.key != report.key), None)
    if cpp:
        done = [l for l in cpp.lessons if l.complete]
        if done:
            out.append(f"The learner has completed C++ up to '{done[-1].title}'. Cross-reference those concepts where they help.")
    if not out:
        out.append("No adjustments needed. The learner is on track, so continue as planned.")
    return out
