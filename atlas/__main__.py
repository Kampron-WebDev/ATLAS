"""ATLAS command line.

    atlas                          full review of all four courses (runs your code) + reports
    atlas next                     the professor's decision: your next lesson
    atlas gate <course> [unit]     gate pre-check; issues an exam sheet when you're ready
    atlas record <course> <unit> PASS|FAIL [--score N] [--note "..."] [--examiner NAME]
    atlas authorize <course>       may new lessons be written for this course? (exit code 0 = yes)
    atlas knowledge                what you should know by now + reviews due
    atlas eta                      pace and projected finish dates
    atlas history                  your progress over time
    atlas courses                  the course keys ATLAS knows
    atlas tutor [path | search]    Athena's context pack for a lesson or exercise (fast, runs no tests)

Options: --no-tests (use cached results only) · --open (open the dashboard) · --course KEY
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser

from . import brain, engine, reports, tutor
from .config import load_config
from .state import History, Ledger


def _utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def _run(config, args, save_history=True):
    only = getattr(args, "course", None)
    print("🏛️  ATLAS is reviewing your work…", flush=True)
    result = engine.run(config, run_tests=not args.no_tests, only=only, save_history=save_history)
    if not only:
        reports.write_all(result)
    return result


def _find_unit(result, course_key, unit_id):
    report = result.course(course_key)
    if report is None:
        sys.exit(f"Unknown course '{course_key}'. Try: atlas courses")
    if unit_id:
        module = next((m for m in report.modules if m.id.lower() == unit_id.lower()), None)
        if module is None:
            ids = ", ".join(m.id for m in report.modules)
            sys.exit(f"Unknown unit '{unit_id}' in {course_key}. Units: {ids}")
        return report, module
    lesson = brain.current_lesson(report)
    module = next((m for m in report.modules if lesson and m.id == lesson.module_id), None)
    if module is None:  # everything done: gate the last written unit
        module = brain.written_units(report)[-1] if brain.written_units(report) else None
    if module is None:
        sys.exit("Nothing to gate yet.")
    return report, module


def main(argv=None) -> int:
    _utf8_console()
    parser = argparse.ArgumentParser(prog="atlas", description="ATLAS: your Chief Engineer, tutor and examiner.")
    parser.add_argument("--no-tests", action="store_true", help="don't run code; reuse cached results")
    parser.add_argument("--open", action="store_true", help="open the dashboard afterwards")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("review", help="full review (default)")
    sub.add_parser("next", help="your next lesson")
    g = sub.add_parser("gate", help="gate pre-check and exam sheet")
    g.add_argument("course")
    g.add_argument("unit", nargs="?")
    rec = sub.add_parser("record", help="record a gate exam verdict")
    rec.add_argument("course")
    rec.add_argument("unit")
    rec.add_argument("verdict", choices=["PASS", "FAIL", "pass", "fail"])
    rec.add_argument("--score", default="")
    rec.add_argument("--note", default="")
    rec.add_argument("--examiner", default="Claude")
    a = sub.add_parser("authorize", help="may new lessons be generated?")
    a.add_argument("course")
    sub.add_parser("knowledge", help="what you should know + reviews due")
    sub.add_parser("eta", help="pace and projected finish")
    sub.add_parser("history", help="progress over time")
    sub.add_parser("courses", help="list course keys")
    t = sub.add_parser("tutor", help="context pack for Athena, the tutor")
    t.add_argument("target", nargs="*", help="a lesson/exercise path, or words from a lesson title")
    args = parser.parse_args(argv)

    config = load_config()
    command = args.command or "review"

    if command == "courses":
        for c in config.courses:
            print(f"  {c.key:<10} {c.title}  ({c.path})")
        return 0

    if command == "history":
        snaps = History(config.root / "history").snapshots()
        if not snaps:
            print("No history yet. Run `atlas` first.")
        for s in snaps[-20:]:
            cells = "  ".join(f"{k}:{v['progress']:.1%}" for k, v in s["courses"].items())
            print(f"  {s['date'][:16]}  {cells}")
        return 0

    if command == "tutor":
        if not args.target:
            print(tutor.overview_md(config))
            return 0
        target = " ".join(args.target)
        found = tutor.locate(config, target)
        if found is None:
            print(f"No lesson matches '{target}'. Give a folder path, or words from the lesson title.")
            return 2
        print(tutor.context_md(config, found))
        return 0

    if command == "record":
        ledger = Ledger(config.root / "ledger" / "gates.json")
        entry = ledger.record(args.course, args.unit, args.verdict, args.examiner, args.note, args.score)
        print(f"📜 Recorded: {entry['course']} {entry['unit']} → {entry['verdict']} (examiner: {entry['examiner']})")
        print("Run `atlas` to refresh the reports, status files and authorizations.")
        return 0

    result = _run(config, args, save_history=command == "review")

    if command == "review":
        print(reports.terminal_summary(result))
    elif command == "next":
        print()
        print(reports.next_text(result))
        for note in result.well.notes if result.well else []:
            print(f"  {note}")
    elif command == "eta":
        print(f"\n  {'Course':<34} {'Progress':>9} {'Pace':>11} {'Remaining':>13} {'Finish':>13}  Confidence")
        for r in result.reports:
            remaining = reports.duration(r.eta_weeks)
            print(f"  {r.title:<34} {r.progress:>8.1%} {reports.pace_text(r):>11} {remaining:>13} "
                  f"{reports.when(r.finish_date):>13}  {r.confidence}")
        print("\n  Pace 1.00× = exactly the planned speed. Estimates firm up after ~2 weeks and 5+ lessons.")
    elif command == "knowledge":
        path = config.root / "reports" / "KNOWLEDGE.md"
        print(f"\n  🧠 Written to {path}")
        for r, lesson, interval in result.reviews:
            print(f"  🔁 Review due: {r.title} · {lesson.title} ({interval}-day)")
    elif command == "gate":
        report, module = _find_unit(result, args.course, args.unit)
        print(f"\n  🚪 Gate pre-check: {report.title} · {module.title}  →  {module.verdict}\n")
        for c in module.checks:
            mark = "✅" if c.ok else ("❌" if c.required else "⚠️ ")
            print(f"    {mark} {c.label}: {c.detail}")
        if module.verdict == "READY FOR EXAM":
            path = reports.write_exam(result, report, module)
            print(f"\n  🎓 Evidence complete. Your exam sheet is ready:\n     {path}")
            print("     Answer it without notes, then tell Claude: \"ATLAS exam ready, please grade: <that path>\"")
        elif module.verdict == "PASSED":
            print("\n  📜 Already passed. It's in the ledger.")
        else:
            print("\n  Not ready yet. Finish the ❌ items above, then run the gate check again.")
    elif command == "authorize":
        auth = result.auths.get(args.course)
        if auth is None:
            print(f"Unknown course '{args.course}'.")
            return 2
        print(f"\n  🔐 {result.course(args.course).title} → {'✅ AUTHORIZED' if auth.granted else '⛔ DENIED'}")
        print(f"     Next unit: {auth.next_unit or '—'}")
        for reason in auth.reasons:
            print(f"     • {reason}")
        print(f"     Author brief: {config.root / 'briefs' / (args.course + '.md')}")
        return 0 if auth.granted else 3

    if args.open:
        dashboard = config.root / "reports" / "dashboard.html"
        webbrowser.open(dashboard.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
