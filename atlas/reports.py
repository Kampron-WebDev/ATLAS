"""Everything ATLAS writes: terminal summary, REPORT.md, KNOWLEDGE.md, dashboard.html,
ATLAS-STATUS.md (inside each course), author briefs and gate exam sheets.
"""

from __future__ import annotations

import html
import random
from datetime import datetime, timedelta
from pathlib import Path

from .brain import current_lesson, directives, sync_delta
from .engine import Result
from .model import STATUS_LABEL, CourseReport, Module


# ─────────────────────────────── helpers ───────────────────────────────
def bar(fraction: float, width: int = 20) -> str:
    fraction = max(0.0, min(1.0, fraction))
    filled = round(fraction * width)
    return "█" * filled + "░" * (width - filled)


def when(d: datetime | None) -> str:
    return d.strftime("%d %b %Y") if d else "—"


def duration(weeks: float | None) -> str:
    if weeks is None:
        return "—"
    if weeks < 8:
        return f"{weeks:.1f} weeks"
    return f"{weeks / 4.345:.1f} months"


def short(r: CourseReport) -> str:
    return {"fullstack": "Full-Stack", "jsts": "JS/TS", "python": "Python", "cpp": "C++"}.get(r.adapter, r.title)


def pace_text(r: CourseReport) -> str:
    return f"{r.pace:.2f}× plan" if r.pace is not None else "—"


def greeting(result: Result) -> str:
    hour = result.now.hour
    part = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
    return f"Good {part}, {result.config.learner}."


def verdict_paragraph(result: Result) -> str:
    active = [r for r in result.reports if r.done_weeks > 0]
    lines = []
    if not active:
        return "You haven't completed anything I can measure yet. Start with the lesson below; I'll take it from there."
    best = max(active, key=lambda r: r.pace or 0)
    lines.append(f"You're active in {len(active)} of {len(result.reports)} courses. "
                 f"Strongest momentum: **{best.title}** ({pace_text(best)}).")
    if result.holds:
        held = ", ".join(result.course(k).title for k in result.holds)
        lines.append(f"I've put **{held}** on hold: you're racing ahead there while another course falls behind.")
    behind = [r for r in active if r.verdict == "behind plan"]
    if behind:
        lines.append("Behind plan: " + ", ".join(f"**{r.title}**" for r in behind) + ". Nothing dramatic yet, but watch it.")
    warns = sum(1 for r in result.reports for e in r.exercises for f in e.findings if f.severity == "warn")
    if warns:
        lines.append(f"My code review found **{warns} warning(s)**: see *Code review* below. Small habits become big careers.")
    if result.changes and result.changes.regressions:
        lines.append(f"⚠️ **{len(result.changes.regressions)} exercise(s) that used to pass now fail.** Fix those first.")
    if result.changes and result.changes.newly_passed:
        lines.append(f"🎉 Since my last review you've passed **{len(result.changes.newly_passed)}** new exercise(s). Well done.")
    return " ".join(lines)


# ─────────────────────────────── terminal ───────────────────────────────
def terminal_summary(result: Result) -> str:
    out = ["", "═" * 72, "  🏛️  ATLAS · Chief Engineer's Review", "═" * 72, f"  {greeting(result)}", ""]
    for r in result.reports:
        if r.error and not r.lessons:
            out.append(f"  ⚠️  {r.title}: {r.error}")
            continue
        ex = r.exercises
        passed = sum(1 for e in ex if e.status == "passed")
        hold = "  ⏸ ON HOLD" if r.key in result.holds else ""
        out.append(f"  {r.title}{hold}")
        out.append(f"    {bar(r.progress)} {r.progress:6.1%}   exercises {passed}/{len(ex)}   pace {pace_text(r)}")
        eta = f"finish ≈ {when(r.finish_date)} ({r.verdict}, {r.confidence} confidence)" if r.finish_date else "ETA: not enough data yet"
        out.append(f"    📍 {r.position}")
        out.append(f"    ⏱  {eta}")
        if r.dirty_files:
            out.append(f"    💾 {len(r.dirty_files)} file(s) not committed yet")
        out.append("")
    out.append(next_text(result, compact=True))
    if result.well:
        for note in result.well.notes:
            out.append(f"  {note}")
    out.append("")
    out.append(f"  Full report : {result.config.root / 'reports' / 'REPORT.md'}")
    out.append(f"  Dashboard   : {result.config.root / 'reports' / 'dashboard.html'}")
    out.append("═" * 72)
    return "\n".join(out)


def next_text(result: Result, compact: bool = False) -> str:
    lines = ["  🎯 YOUR NEXT LESSON (decided by ATLAS)", ""]
    runnable = [a for a in result.assignments if a.action != "hold"]
    if not runnable:
        return "  🎯 Nothing assigned: every course is complete or on hold."
    first = runnable[0]
    lines += [f"    ▶ {first.course_title}", f"      {first.title}", f"      {first.detail}"]
    if first.path:
        lines.append(f"      📂 {first.path}")
    lines.append(f"      ⏱  about {first.minutes} min")
    if len(runnable) > 1 and not compact:
        lines += ["", "  Then, if you have time:"]
        for a in runnable[1:4]:
            lines.append(f"    • [{a.course_title}] {a.title}: {a.detail}")
    elif len(runnable) > 1:
        lines.append(f"      (then: {runnable[1].course_title}: {runnable[1].title})")
    for a in result.assignments:
        if a.action == "hold":
            lines.append(f"    ⏸ {a.course_title}: {a.detail}")
    return "\n".join(lines)


# ─────────────────────────────── REPORT.md ───────────────────────────────
def report_md(result: Result) -> str:
    md = [f"# 🏛️ ATLAS Review: {result.now.strftime('%A %d %B %Y, %H:%M')}", "",
          f"*{greeting(result)} Here is my assessment of all four courses.*", "",
          "## 🧭 My verdict", "", verdict_paragraph(result), "",
          "## 🎯 Your next lesson", ""]
    runnable = [a for a in result.assignments if a.action != "hold"]
    if runnable:
        a = runnable[0]
        md += [f"**{a.course_title}: {a.title}**", "", a.detail, "",
               f"📂 `{a.path}` · about {a.minutes} minutes" if a.path else f"About {a.minutes} minutes", ""]
    md += ["### Today's plan", "", "| # | Course | Task | Why | Time |", "|---|---|---|---|---:|"]
    budget, n = result.config.daily_minutes, 0
    for a in runnable:
        if budget <= 0:
            break
        n += 1
        md.append(f"| {n} | {a.course_title} | {a.title} | {a.detail} | {a.minutes} min |")
        budget -= a.minutes
    for a in result.assignments:
        if a.action == "hold":
            md.append(f"| ⏸ | {a.course_title} | On hold | {a.detail} | — |")
    md.append("")

    md += ["## 📊 Scoreboard", "", "| Course | Progress | Exercises | Pace | Projected finish | Status |",
           "|---|---|---|---|---|---|"]
    for r in result.reports:
        if r.error and not r.lessons:
            md.append(f"| {r.title} | — | — | — | — | ⚠️ {r.error} |")
            continue
        ex = r.exercises
        passed = sum(1 for e in ex if e.status == "passed")
        finish = f"{when(r.finish_date)} ({r.confidence} confidence)" if r.finish_date else "not enough data"
        status = "⏸ ON HOLD" if r.key in result.holds else (r.verdict or "—")
        md.append(f"| {r.title} | `{bar(r.progress, 12)}` {r.progress:.1%} | {passed}/{len(ex)} | {pace_text(r)} | {finish} | {status} |")
    md += ["", "*Pace = planned study weeks completed per real week (1.00× = exactly on plan). "
           "Projections sharpen as you complete more lessons.*", ""]

    md += ["## ⚖️ Sync across courses", "", "| Course | Planned weeks done | Expected by now | Difference | Last activity |",
           "|---|---:|---:|---:|---|"]
    for r in result.reports:
        delta = sync_delta(r, result.now)
        if delta is None:
            continue
        md.append(f"| {r.title} | {r.done_weeks:.2f} | {r.done_weeks - delta:.2f} | {delta:+.2f} | {when(r.last_activity)} |")
    md.append("")

    md += ["## 🚪 Gates", "", "| Course | Unit | Completion | Verdict | Missing |", "|---|---|---:|---|---|"]
    for r in result.reports:
        for m in r.modules:
            if m.verdict == "N/A" or (not m.touched and m.verdict != "PASSED"):
                continue
            missing = "; ".join(f"{c.label} ({c.detail})" for c in m.checks if c.required and not c.ok) or "—"
            md.append(f"| {r.title} | {m.title} | {m.completion:.0%} | {m.verdict} | {missing} |")
    md.append("")

    md += ["## 📚 Lesson by lesson", ""]
    for r in result.reports:
        touched = [l for l in r.lessons if l.touched]
        if not touched:
            continue
        md += [f"### {r.title}", "", "| Lesson | Done | Exercises | Notes |", "|---|---:|---|---:|"]
        for l in touched:
            ex = " · ".join(f"{e.name} {STATUS_LABEL[e.status].split()[0]}" for e in l.exercises) or "—"
            notes = f"{l.notes_score:.0%}" if l.notes_score is not None else "—"
            md.append(f"| {l.title} | {l.completion:.0%} | {ex} | {notes} |")
        md.append("")

    md += ["## 🔍 Code review", ""]
    warnings = [(r, e, f) for r in result.reports for e in r.exercises for f in e.findings if f.severity == "warn"]
    tips: dict[str, list[str]] = {}
    for r in result.reports:
        for e in r.exercises:
            for f in e.findings:
                if f.severity != "warn":
                    tips.setdefault(f.message, []).append(f"{short(r)} · {e.name}")
    for r, e, f in warnings:
        where = f"`{f.file}:{f.line}`" if f.line else (f"`{f.file}`" if f.file else "")
        md.append(f"- ⚠️ **{r.title} · {e.name}** {where}: {f.message}")
    for message, where in tips.items():
        md.append(f"- 💡 {message} *({len(where)}×: {', '.join(where[:6])}{'…' if len(where) > 6 else ''})*")
    if not warnings and not tips:
        md.append("Clean. Nothing to flag. 👏")
    md.append("")

    failing = [(r, e) for r in result.reports for e in r.exercises if e.status in ("failing", "partial", "error", "check")]
    if failing:
        md += ["## 🧪 What's failing right now", ""]
        for r, e in failing:
            md.append(f"- **{r.title} · {e.name}**: {STATUS_LABEL[e.status]} ({e.passed}/{e.total})")
            for name, message in e.failures[:3]:
                md.append(f"  - `{name}`: {message}")
            if e.detail:
                md.append(f"  - {e.detail}")
        md.append("")

    ch = result.changes
    if ch and (ch.newly_passed or ch.regressions or ch.stuck):
        md += ["## 🔁 Since my last review", ""]
        md += [f"- 🎉 Newly passing: {x}" for x in ch.newly_passed]
        md += [f"- ⚠️ Regression (was passing): {x}" for x in ch.regressions]
        md += [f"- 🧱 Stuck for {result.config.stuck_days}+ days: {x}. Ask for a hint, or re-read the lesson" for x in ch.stuck]
        md.append("")

    dirty = [(r, f) for r in result.reports for f in r.dirty_files]
    if dirty:
        md += ["## 💾 Uncommitted work", "", "Commit at the end of every session; your history is how I measure your pace.", ""]
        for r in result.reports:
            if r.dirty_files:
                md.append(f"- **{r.title}**: {len(r.dirty_files)} file(s), e.g. `{r.dirty_files[0]}`")
        md.append("")

    if result.well:
        md += ["## ❤️ Wellbeing", "", f"- Streak: **{result.well.streak} day(s)** · active {result.well.active_last_7}/7 days this week"]
        md += [f"- {n}" for n in result.well.notes]
        md.append("")

    md += ["## 🔐 New-lesson authorization", "", "| Course | Next unit | Decision | Reasons |", "|---|---|---|---|"]
    for key, auth in result.auths.items():
        title = result.course(key).title
        decision = "✅ AUTHORIZED" if auth.granted else "⛔ DENIED"
        md.append(f"| {title} | {auth.next_unit or '—'} | {decision} | {'<br>'.join(auth.reasons)} |")
    md += ["", "See also: [KNOWLEDGE.md](KNOWLEDGE.md) · [dashboard.html](dashboard.html) · briefs in `../briefs/`", ""]
    return "\n".join(md)


# ─────────────────────────────── KNOWLEDGE.md ───────────────────────────────
def knowledge_md(result: Result) -> str:
    md = ["# 🧠 What you should know by now", "",
          "Built from every lesson you've started. Cover the answers and test yourself: if you can't explain a "
          "term simply, revisit that lesson before its review date.", ""]
    if result.reviews:
        md += ["## 🔁 Reviews due now (spaced repetition)", ""]
        for r, l, interval in result.reviews:
            md.append(f"- **{r.title} · {l.title}**: {interval}-day review. Re-answer its quiz without notes.")
        md.append("")
    for r in result.reports:
        lessons = [l for l in r.lessons if l.touched and l.kind != "orientation"]
        if not lessons:
            continue
        md += [f"## {r.title}", ""]
        for l in lessons:
            state = "✅ complete" if l.complete else f"{l.completion:.0%} done"
            md += [f"### {l.title} ({state})", ""]
            k = l.knowledge
            if k.outcomes:
                md += ["**You can now:**", *[f"- {o}" for o in k.outcomes], ""]
            if k.key_terms:
                md += ["**Key terms:**", "", "| Term | Meaning |", "|---|---|", *[f"| {t} | {m} |" for t, m in k.key_terms], ""]
            if k.questions:
                md += ["**Can you answer these without notes?**", *[f"1. {q}" for q in k.questions], ""]
            if l.completed_at:
                upcoming = [l.completed_at.date() + timedelta(days=d) for d in result.config.review_intervals]
                nxt = next((d for d in upcoming if d >= result.now.date()), None)
                if nxt:
                    md += [f"*Next review: {nxt.strftime('%d %b %Y')}*", ""]
        for m in r.modules:
            if m.touched and m.explain_questions:
                md += [f"### 🎯 Gate questions for {m.title}", *[f"- {q}" for q in m.explain_questions], ""]
    return "\n".join(md)


# ─────────────────────────────── ATLAS-STATUS.md (inside each course) ───────────────────────────────
def status_md(result: Result, r: CourseReport) -> str:
    lesson = current_lesson(r)
    auth = result.auths.get(r.key)
    md = ["# 🏛️ ATLAS Status", "",
          f"*Written by ATLAS (your Chief Engineer) on {result.now.strftime('%d %b %Y %H:%M')}. Don't edit: it's regenerated every run.*", ""]
    if r.key in result.holds:
        md += [f"> ⏸ **This course is ON HOLD.** {result.holds[r.key]}", ""]
    md += [f"**Progress:** `{bar(r.progress)}` {r.progress:.1%} · **pace** {pace_text(r)} · "
           f"**projected finish** {when(r.finish_date)} ({r.confidence} confidence)", "",
           f"**📍 You are here:** {r.position}", ""]
    if lesson:
        md.append(f"**▶ Next:** {lesson.title}. Open `{lesson.dir.relative_to(r.path).as_posix()}/README.md`")
        md.append("")
    md += ["| Unit | Completion | Gate |", "|---|---:|---|"]
    for m in r.modules:
        if m.verdict != "N/A" and (m.touched or m.verdict == "PASSED"):
            md.append(f"| {m.title} | {m.completion:.0%} | {m.verdict} |")
    md.append("")
    if auth:
        md += [f"**New lessons:** {'✅ AUTHORIZED' if auth.granted else '⛔ not yet'}. {' '.join(auth.reasons)}", ""]
    md.append("Full review: `Desktop/ATLAS/reports/REPORT.md` · run `atlas` from `Desktop/ATLAS` to refresh.")
    return "\n".join(md)


# ─────────────────────────────── author briefs ───────────────────────────────
def brief_md(result: Result, r: CourseReport) -> str:
    auth = result.auths.get(r.key)
    touched = [l for l in r.lessons if l.touched and l.kind != "orientation"]
    notes = [l.notes_score for l in touched if l.notes_score is not None]
    md = [f"# 📝 ATLAS Author Brief: {r.title}", "",
          f"*For whoever writes this learner's next lessons (usually Claude). Generated {result.now.strftime('%d %b %Y %H:%M')}.*", "",
          f"**Authorization:** {'✅ AUTHORIZED' if auth and auth.granted else '⛔ DENIED'}. Next unit: {r.next_unwritten or '—'}", ""]
    if auth:
        md += [f"- {x}" for x in auth.reasons] + [""]
    md += ["## Learner profile", "",
           f"- Pace: {pace_text(r)} (recent {r.recent_pace:.2f}×)" if r.recent_pace is not None else f"- Pace: {pace_text(r)}",
           f"- Lessons completed: {sum(1 for l in r.lessons if l.complete and l.kind != 'orientation')} · touched: {len(touched)}",
           f"- Exercises passing: {sum(1 for e in r.exercises if e.status == 'passed')}/{len(r.exercises)}",
           f"- Average notes completeness: {sum(notes) / len(notes):.0%}" if notes else "- Notes: none yet",
           f"- Position: {r.position}", "",
           "## Directives (binding)", "",
           *[f"{i}. {d}" for i, d in enumerate(directives(r, result.reports, result.config, result.holds), start=1)], "",
           "## Evidence", ""]
    for l in touched:
        md.append(f"- {l.title}: {l.completion:.0%} · " + ", ".join(f"{e.name}={e.status}" for e in l.exercises))
    return "\n".join(md)


# ─────────────────────────────── gate exam sheet ───────────────────────────────
def exam_md(result: Result, r: CourseReport, m: Module) -> str:
    rng = random.Random(f"{r.key}{m.id}{result.now.date()}")
    questions = list(m.explain_questions)
    for l in m.lessons:
        qs = l.knowledge.questions
        questions += rng.sample(qs, min(2, len(qs)))
    passed = [e for l in m.lessons for e in l.exercises if e.status == "passed" and e.kind in ("exercise", "challenge", "project")]
    code_task = rng.choice(passed).name if passed else None

    md = [f"# 🎓 ATLAS Gate Exam: {m.title}", "",
          f"**Course:** {r.title} · **Unit id:** `{m.id}` · **Issued:** {result.now.strftime('%d %b %Y %H:%M')}", "",
          "## Rules", "", "- No notes, no lessons, no AI, no solutions. Answer in your own words, simply.",
          "- Write each answer directly under its question.",
          "- When finished, tell Claude: **\"ATLAS exam ready, please grade: <path to this file>\"**.",
          "- Pass mark: **70%**. Each question is worth 2 points (1 = partly right, 2 = clear and correct).", "",
          "## Evidence ATLAS has already verified", ""]
    md += [f"- {'✅' if c.ok else '❌'} {c.label}: {c.detail}" for c in m.checks] + ["", "## Questions", ""]
    for i, q in enumerate(questions, start=1):
        md += [f"### Q{i}. {q}", "", "**Answer:**", "", ""]
    if code_task:
        n = len(questions) + 1
        md += [f"### Q{n}. Explain your own solution to **{code_task}**, line by line, then describe one different way to solve it and its trade-off.",
               "", "**Answer:**", "", ""]
    md += ["---", "", "## Examiner's grading (filled in by the examiner)", "", "| Q | Score (0–2) | Comment |", "|---|---|---|", "",
           "**Total:** __ / __ · **Verdict:** PASS / FAIL", "",
           f"Record with: `atlas record {r.key} {m.id} PASS --score <n> --note \"…\"`"]
    return "\n".join(md)


# ─────────────────────────────── dashboard.html ───────────────────────────────
CSS = """
:root{--bg:#f6f7fb;--card:#fff;--ink:#1b1f2a;--muted:#667085;--line:#e4e7ec;--accent:#3b5bdb;--ok:#2f9e44;--warn:#e67700;--bad:#c92a2a}
@media (prefers-color-scheme:dark){:root{--bg:#0f1117;--card:#181b24;--ink:#e6e8ee;--muted:#98a2b3;--line:#2a2f3d;--accent:#748ffc;--ok:#51cf66;--warn:#ffa94d;--bad:#ff6b6b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px}h1{margin:0 0 4px}h2{margin:32px 0 12px;font-size:18px}
.muted{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.big{font-size:28px;font-weight:700}.bar{height:8px;background:var(--line);border-radius:6px;overflow:hidden;margin:8px 0}
.bar>span{display:block;height:100%;background:var(--accent)}.next{border-left:4px solid var(--accent)}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top;font-size:14px}th{color:var(--muted);font-weight:600}
.tag{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;border:1px solid var(--line)}
.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}
.cal{display:grid;grid-template-columns:repeat(7,18px);gap:4px}.cal i{width:18px;height:18px;border-radius:4px;background:var(--line)}
.cal i.l1{background:color-mix(in srgb,var(--accent) 45%,var(--line))}.cal i.l2{background:var(--accent)}
.wrap{overflow-x:auto}
"""


def dashboard_html(result: Result) -> str:
    e = html.escape
    runnable = [a for a in result.assignments if a.action != "hold"]
    parts = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
             f"<title>ATLAS Dashboard</title><style>{CSS}</style></head><body><main>",
             f"<h1>🏛️ ATLAS</h1><div class='muted'>Chief Engineer's dashboard · {e(result.now.strftime('%A %d %B %Y, %H:%M'))}</div>"]
    if runnable:
        a = runnable[0]
        parts.append(f"<h2>🎯 Your next lesson</h2><div class='card next'><div class='muted'>{e(a.course_title)}</div>"
                     f"<div class='big'>{e(a.title)}</div><div>{e(a.detail)}</div>"
                     f"<div class='muted'>{e(a.path)} · ~{a.minutes} min</div></div>")
    parts.append("<h2>📊 Courses</h2><div class='grid'>")
    for r in result.reports:
        if r.error and not r.lessons:
            parts.append(f"<div class='card'><b>{e(r.title)}</b><div class='bad'>{e(r.error)}</div></div>")
            continue
        passed = sum(1 for x in r.exercises if x.status == "passed")
        hold = "<span class='tag warn'>ON HOLD</span>" if r.key in result.holds else ""
        parts.append(f"<div class='card'><b>{e(r.title)}</b> {hold}<div class='big'>{r.progress:.1%}</div>"
                     f"<div class='bar'><span style='width:{min(r.progress, 1) * 100:.1f}%'></span></div>"
                     f"<div>Exercises {passed}/{len(r.exercises)} · pace {e(pace_text(r))}</div>"
                     f"<div class='muted'>Finish ≈ {e(when(r.finish_date))} ({e(r.confidence)} confidence) · {e(r.verdict)}</div>"
                     f"<div class='muted'>📍 {e(r.position)}</div></div>")
    parts.append("</div>")

    if result.well:
        cal = []
        start = result.now.date() - timedelta(days=34)
        for i in range(35):
            d = start + timedelta(days=i)
            n = result.well.calendar.get(d, 0)
            cal.append(f"<i class='l{min(n, 2)}' title='{d}: {n} course(s)'></i>")
        notes = "".join(f"<div>{e(n)}</div>" for n in result.well.notes)
        parts.append(f"<h2>❤️ Consistency</h2><div class='grid'><div class='card'><div class='big'>{result.well.streak} 🔥</div>"
                     f"<div class='muted'>day streak · {result.well.active_last_7}/7 active this week</div>{notes}</div>"
                     f"<div class='card'><div class='muted'>Last 5 weeks</div><div class='cal'>{''.join(cal)}</div></div></div>")

    rows = []
    for r in result.reports:
        for m in r.modules:
            if m.verdict != "N/A" and (m.touched or m.verdict == "PASSED"):
                cls = "ok" if m.verdict == "PASSED" else "warn" if m.verdict == "READY FOR EXAM" else ""
                missing = "; ".join(c.label for c in m.checks if c.required and not c.ok)
                rows.append(f"<tr><td>{e(r.title)}</td><td>{e(m.title)}</td><td>{m.completion:.0%}</td>"
                            f"<td class='{cls}'>{e(m.verdict)}</td><td class='muted'>{e(missing)}</td></tr>")
    if rows:
        parts.append("<h2>🚪 Gates</h2><div class='wrap'><table><tr><th>Course</th><th>Unit</th><th>Done</th><th>Verdict</th><th>Missing</th></tr>"
                     + "".join(rows) + "</table></div>")

    findings = [(r, x, f) for r in result.reports for x in r.exercises for f in x.findings]
    if findings:
        parts.append("<h2>🔍 Code review</h2><div class='wrap'><table><tr><th></th><th>Where</th><th>Note</th></tr>")
        for r, x, f in findings:
            icon = "⚠️" if f.severity == "warn" else "💡"
            parts.append(f"<tr><td>{icon}</td><td>{e(r.title)} · {e(x.name)}<br><span class='muted'>{e(f.file)}{':' + str(f.line) if f.line else ''}</span></td><td>{e(f.message)}</td></tr>")
        parts.append("</table></div>")

    auth_rows = "".join(f"<tr><td>{e(result.course(k).title)}</td><td>{e(a.next_unit or '—')}</td>"
                        f"<td class='{'ok' if a.granted else 'bad'}'>{'AUTHORIZED' if a.granted else 'DENIED'}</td>"
                        f"<td class='muted'>{e(' '.join(a.reasons))}</td></tr>" for k, a in result.auths.items())
    parts.append("<h2>🔐 New lessons</h2><div class='wrap'><table><tr><th>Course</th><th>Next unit</th><th>Decision</th><th>Reasons</th></tr>"
                 + auth_rows + "</table></div>")
    parts.append("<p class='muted'>Details: REPORT.md · KNOWLEDGE.md · briefs/</p></main></body></html>")
    return "".join(parts)


# ─────────────────────────────── write everything ───────────────────────────────
def write_all(result: Result) -> list[Path]:
    root = result.config.root
    reports_dir, briefs_dir = root / "reports", root / "briefs"
    reports_dir.mkdir(exist_ok=True)
    briefs_dir.mkdir(exist_ok=True)
    written = []
    for name, text in (("REPORT.md", report_md(result)), ("KNOWLEDGE.md", knowledge_md(result)),
                       ("dashboard.html", dashboard_html(result))):
        path = reports_dir / name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    for r in result.reports:
        if r.error and not r.lessons:
            continue
        brief = briefs_dir / f"{r.key}.md"
        brief.write_text(brief_md(result, r), encoding="utf-8")
        status = r.path / "ATLAS-STATUS.md"
        status.write_text(status_md(result, r), encoding="utf-8")
        written += [brief, status]
    return written


def write_exam(result: Result, r: CourseReport, m: Module) -> Path:
    folder = result.config.root / "exams" / r.key
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{m.id}_{result.now.strftime('%Y-%m-%d')}.md"
    if not path.exists():  # never overwrite an exam the learner may be answering
        path.write_text(exam_md(result, r, m), encoding="utf-8")
    return path
