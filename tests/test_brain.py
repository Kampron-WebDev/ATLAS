"""Tests for the professor's judgement: pace, holds, gates, authorization, next lesson, wellbeing, history."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from atlas import brain
from atlas.adapters import Plan
from atlas.config import Config
from atlas.model import CourseReport, Exercise, Lesson, Module
from atlas.state import Ledger

NOW = datetime(2026, 10, 10, 12, 0).astimezone()


def make_exercise(name, status="passed", kind="exercise", modified=True, when=NOW):
    ex = Exercise("c", f"L/{name}", Path("."), name, kind, "L", [Path("main.js")], [], None)
    ex.status, ex.modified, ex.last_activity, ex.first_activity = status, modified, when, when
    if status == "partial":
        ex.passed, ex.total = 1, 2
    return ex


def make_lesson(title, statuses, weight=0.5, kind="lesson", notes=1.0, module="M001"):
    lesson = Lesson("c", title, Path(title), title, module, f"Module {module}", kind, weight)
    lesson.exercises = [make_exercise(f"{title}-{i}", s) for i, s in enumerate(statuses)]
    lesson.notes_score = notes
    return lesson


def make_report(key="c", lessons=(), start_days_ago=14, total=10.0, adapter="jsts"):
    r = CourseReport(key, f"Course {key}", Path("."), adapter)
    r.lessons = list(lessons)
    r.total_weeks = total
    r.start = NOW - timedelta(days=start_days_ago)
    r.plan = Plan(total_weeks=total, module_order=["M001", "M002"], module_titles={"M001": "Module 001", "M002": "Module 002"})
    return r


@pytest.fixture
def config(tmp_path):
    return Config(learner="Test", courses=[], root=tmp_path)


def test_pace_and_eta_on_plan():
    r = make_report(lessons=[make_lesson("A", ["passed"], weight=2.0)], start_days_ago=14)
    brain.compute_pace(r, NOW)
    assert r.done_weeks == 2.0
    assert r.pace == pytest.approx(1.0)
    assert r.eta_weeks == pytest.approx(8.0)
    assert r.confidence == "low" and r.verdict == "early estimate"  # only 1 lesson done


def test_partial_credit():
    r = make_report(lessons=[make_lesson("A", ["passed", "partial", "not_started", "failing"], weight=1.0)])
    brain.compute_pace(r, NOW)
    assert r.done_weeks == pytest.approx((1 + 0.5) / 4)


def test_sync_hold_for_a_course_racing_ahead():
    fast = make_report("fast", [make_lesson("A", ["passed"], weight=5.0)], start_days_ago=14)
    slow = make_report("slow", [make_lesson("B", ["passed"], weight=0.5)], start_days_ago=14)
    for r in (fast, slow):
        brain.compute_pace(r, NOW)
    holds = brain.compute_holds([fast, slow], NOW, gap_weeks=2.0)
    assert list(holds) == ["fast"]
    assert brain.compute_holds([fast, slow], NOW, gap_weeks=0) == {}


def test_gate_verdicts(config, tmp_path):
    ledger = Ledger(tmp_path / "gates.json")
    ready = Module("c", "M001", "Module 001", [make_lesson("A", ["passed", "passed"]), make_lesson("R", ["passed"], kind="review")])
    brain.evaluate_gate(ready, ledger, config)
    assert ready.verdict == "READY FOR EXAM"

    unfinished = Module("c", "M002", "Module 002", [make_lesson("B", ["passed", "failing"])])
    brain.evaluate_gate(unfinished, ledger, config)
    assert unfinished.verdict == "IN PROGRESS"
    assert not unfinished.checks[0].ok

    no_notes = Module("c", "M003", "Module 003", [make_lesson("C", ["passed"], notes=0.0)])
    brain.evaluate_gate(no_notes, ledger, config)
    assert no_notes.verdict == "IN PROGRESS"

    ledger.record("c", "M001", "PASS", "Claude")
    brain.evaluate_gate(ready, ledger, config)
    assert ready.verdict == "PASSED"


def test_authorization_requires_passed_gates_and_no_hold(config, tmp_path):
    ledger = Ledger(tmp_path / "gates.json")
    r = make_report(lessons=[make_lesson("A", ["passed"])])
    r.modules = [Module("c", "M001", "Module 001", r.lessons)]
    r.next_unwritten = brain.next_unwritten(r)
    assert r.next_unwritten == "Module 002"

    assert not brain.authorize(r, ledger, {}).granted
    ledger.record("c", "M001", "PASS", "Claude")
    assert brain.authorize(r, ledger, {}).granted
    assert not brain.authorize(r, ledger, {"c": "ahead"}).granted


def test_next_lesson_prefers_the_course_behind_and_respects_holds(config):
    config.spine = "none"
    ahead = make_report("ahead", [make_lesson("A1", ["passed"], weight=3.0), make_lesson("A2", ["not_started"])])
    behind = make_report("behind", [make_lesson("B1", ["passed"], weight=0.2), make_lesson("B2", ["not_started"])])
    for r in (ahead, behind):
        brain.compute_pace(r, NOW)
        r.modules = [Module(r.key, "M001", "Module 001", r.lessons)]
        r.last_activity = NOW
    plan = brain.plan_assignments([ahead, behind], {}, {}, config, NOW)
    assert plan[0].course == "behind" and plan[0].title.endswith("B2")  # "Finish: B2", since its exercises are started

    plan = brain.plan_assignments([ahead, behind], {"behind": "test hold"}, {}, config, NOW)
    runnable = [a for a in plan if a.action != "hold"]
    assert runnable[0].course == "ahead"


def test_wellbeing_streak_and_rest_advice():
    r = make_report()
    r.activity_days = {(NOW - timedelta(days=i)).date() for i in range(7)}
    w = brain.wellbeing([r], NOW)
    assert w.streak == 7 and w.active_last_7 == 7
    assert any("rest day" in n for n in w.notes)


def test_changes_regressions_and_stuck(config):
    old = {"date": (NOW - timedelta(days=5)).isoformat(), "courses": {"c": {"exercises": {"a": "passed", "b": "failing", "c": "failing"}}}}
    now = {"date": NOW.isoformat(), "courses": {"c": {"exercises": {"a": "failing", "b": "failing", "c": "passed"}}}}
    ch = brain.changes_since([old], now, config, NOW)
    assert ch.regressions == ["c: a"]
    assert ch.newly_passed == ["c: c"]
    assert "c: b" in ch.stuck
