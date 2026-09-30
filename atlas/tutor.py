"""Athena's link to ATLAS: finds the lesson behind a path and packs everything the tutor needs.

`atlas tutor <path>` is fast on purpose. It reads the course layout, ATLAS's last results and the
tutor's memory, but runs no tests (the tutor runs the one exercise it's helping with, itself).

Two-way link:
  * ATLAS → Athena: position, holds, exercise status, reviews due, wellbeing (the context pack).
  * Athena → ATLAS: concepts the tutor still sees as shaky (memory/concepts.md) become author-brief
    directives, and tutor-written notes (checks.strip_tutor_blocks) never count as the learner's notes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .adapters import Adapter, Plan, adapter_for
from .assess import _status
from .config import Config, CourseConfig
from .gitinfo import Repo
from .model import STATUS_LABEL, Exercise, Lesson
from .runners import Outcome
from .state import Cache, fingerprint

TUTOR_NAME = "Athena"
TUTOR_NOTES = "ATHENA-NOTES.md"  # used only when a lesson has no MY-NOTES.md of its own
COURSE_ALIASES = {"fullstack": "fullstack", "fs": "fullstack", "full-stack": "fullstack", "jsts": "jsts",
                  "js": "jsts", "ts": "jsts", "javascript": "jsts", "typescript": "jsts", "python": "python",
                  "py": "python", "cpp": "cpp", "c++": "cpp"}
SHAKY = ("🟡", "🔴", "shaky", "confused")


def tutor_dir(config: Config) -> Path:
    return config.root / "tutor"


def memory_dir(config: Config) -> Path:
    return tutor_dir(config) / "memory"


# ─────────────────────────────── the concept ledger ───────────────────────────────
@dataclass
class ConceptRow:
    concept: str
    course: str
    lesson: str
    status: str
    checked: str = ""
    links: str = ""

    @property
    def shaky(self) -> bool:
        return any(s in self.status.lower() for s in SHAKY)


def concept_rows(config: Config) -> list[ConceptRow]:
    """Rows of the table in memory/concepts.md: | Concept | Course | Lesson | Status | Last checked | Links |"""
    path = memory_dir(config) / "concepts.md"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.lstrip().startswith("|") else []
        if len(cells) < 4 or cells[0].lower() == "concept" or set(cells[0]) <= set("-: "):
            continue
        rows.append(ConceptRow(*cells[:4], *(cells[4:6] + ["", ""])[:2]))
    return rows


def flagged_concepts(config: Config) -> dict[str, list[str]]:
    """Course key → concepts the tutor still sees as shaky or confused."""
    out: dict[str, list[str]] = {}
    for row in concept_rows(config):
        key = COURSE_ALIASES.get(row.course.lower(), row.course.lower())
        if row.shaky and row.concept not in out.get(key, []):
            out.setdefault(key, []).append(row.concept)
    return out


# ─────────────────────────────── finding the lesson ───────────────────────────────
@dataclass
class Located:
    cfg: CourseConfig
    adapter: Adapter
    lessons: list[Lesson]
    lesson: Lesson | None = None
    exercise: Exercise | None = None
    in_solution: bool = False
    candidates: list[Lesson] = field(default_factory=list)


def _inside(path: Path, folder: Path) -> bool:
    try:
        path.resolve().relative_to(folder.resolve())
        return True
    except ValueError:
        return False


def _load(cfg: CourseConfig) -> tuple[Adapter, list[Lesson]]:
    adapter = adapter_for(cfg)
    try:
        plan = adapter.plan()
    except Exception:  # the layout is still usable without the plan's weights
        plan = Plan(total_weeks=0.0)
    return adapter, adapter.discover(plan)


def _locate_path(cfg: CourseConfig, path: Path) -> Located:
    adapter, lessons = _load(cfg)
    found = Located(cfg, adapter, lessons)
    owners = [l for l in lessons if _inside(path, l.dir)]
    if owners:
        found.lesson = max(owners, key=lambda l: len(l.dir.parts))
        exercises = [e for e in found.lesson.exercises if _inside(path, e.dir)]
        if exercises:
            found.exercise = max(exercises, key=lambda e: len(e.dir.parts))
            found.in_solution = "solution" in path.resolve().relative_to(found.exercise.dir.resolve()).parts
        return found
    found.candidates = [l for l in lessons if _inside(l.dir, path)]
    if not found.candidates or path.resolve() == cfg.path.resolve():
        current = current_rel(cfg)
        found.lesson = next((l for l in lessons if l.rel == current), None)
        found.candidates = [] if found.lesson else found.candidates
    return found


def locate(config: Config, target: str) -> Located | None:
    """A path (absolute, relative to here, or relative to a course) or a search like 'python bytecode'."""
    raw = Path(target.strip().lstrip("@").strip('"')).expanduser()
    tries = [raw] if raw.is_absolute() else [Path.cwd() / raw] + [c.path / raw for c in config.courses]
    for path in tries:
        if path.exists():
            for cfg in config.courses:
                if cfg.path.exists() and _inside(path, cfg.path):
                    return _locate_path(cfg, path)
    return search(config, target)


def search(config: Config, query: str) -> Located | None:
    words = [w for w in re.split(r"[\s/\\]+", query.lower().lstrip("@")) if w]
    only = COURSE_ALIASES.get(words[0]) if words else None
    if only:
        words = words[1:]
    if not words:
        return None
    matches: list[Located] = []
    exercise_matches: list[Located] = []
    for cfg in config.courses:
        if (only and cfg.key != only) or not cfg.path.exists():
            continue
        adapter, lessons = _load(cfg)
        for lesson in lessons:
            haystack = f"{lesson.title} {lesson.rel} {lesson.module_title}".lower()
            if all(w in haystack for w in words):
                matches.append(Located(cfg, adapter, lessons, lesson))
            for ex in lesson.exercises:  # "biggest of three" finds Exercises/02_BiggestOfThree
                name = ex.name.lower()
                if all(w in name or w in haystack for w in words) and any(w in name for w in words):
                    exercise_matches.append(Located(cfg, adapter, lessons, lesson, ex))
    if len(matches) == 1:
        return matches[0]
    if not matches and len(exercise_matches) == 1:
        return exercise_matches[0]
    pool = matches or exercise_matches
    if not pool:
        return None
    first = pool[0]
    return Located(first.cfg, first.adapter, first.lessons, candidates=[m.lesson for m in pool])


# ─────────────────────────────── what ATLAS last said ───────────────────────────────
def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def status_line(cfg: CourseConfig, label: str) -> str:
    match = re.search(rf"\*\*{re.escape(label)}\*\*\s*(.+)", _read(cfg.path / "ATLAS-STATUS.md"))
    return match.group(1).strip() if match else ""


def current_rel(cfg: CourseConfig) -> str:
    match = re.search(r"\*\*▶ Next:\*\*.*?Open `(.+?)/README\.md`", _read(cfg.path / "ATLAS-STATUS.md"))
    return match.group(1) if match else ""


def hold_text(cfg: CourseConfig) -> str:
    match = re.search(r"ON HOLD\.\*\*\s*(.+)", _read(cfg.path / "ATLAS-STATUS.md"))
    return match.group(1).strip() if match else ""


def report_section(config: Config, file: str, heading: str, limit: int = 12) -> list[str]:
    lines, keep = [], False
    for line in _read(config.root / "reports" / file).splitlines():
        if line.startswith("## "):
            keep = heading in line
            continue
        if keep and line.strip():
            lines.append(line.rstrip())
    return lines[:limit]


# ─────────────────────────────── the tutor's memory ───────────────────────────────
def session_file(config: Config, lesson: Lesson) -> Path:
    module = re.sub(r"[^\w.-]+", "-", lesson.module_id)
    return memory_dir(config) / "sessions" / lesson.course / f"{module}__{lesson.dir.name}.md"


def session_status(path: Path) -> str:
    match = re.search(r"\*\*Status:\*\*\s*(.+)", _read(path))
    return match.group(1).strip() if match else ("started" if path.exists() else "")


def notes_file(lesson: Lesson) -> Path:
    mine = lesson.dir / "MY-NOTES.md"
    return mine if mine.exists() else lesson.dir / TUTOR_NOTES


def last_journal_entry(config: Config, max_lines: int = 10) -> list[str]:
    entry: list[str] = []
    for line in _read(memory_dir(config) / "journal.md").splitlines():
        if line.startswith("### "):
            if entry:
                break
            entry.append(line)
        elif entry and line.strip():
            entry.append(line)
    return entry[:max_lines]


def open_sessions(config: Config) -> list[tuple[Path, str, str]]:
    """(file, title, status) of every session that isn't complete, newest first."""
    folder = memory_dir(config) / "sessions"
    files = sorted(folder.glob("*/*.md"), key=lambda p: p.stat().st_mtime, reverse=True) if folder.exists() else []
    out = []
    for f in files:
        status = session_status(f)
        if "complete" in status.lower() and "incomplete" not in status.lower():
            continue
        title = next((l[2:].strip() for l in _read(f).splitlines() if l.startswith("# ")), f.stem)
        out.append((f, title, status))
    return out


# ─────────────────────────────── exercises ───────────────────────────────
def run_command(cfg: CourseConfig, adapter: Adapter, ex: Exercise) -> str:
    if adapter.kind == "pytest":
        return f'& "{cfg.python}" -m pytest -q' if cfg.python else "python -m pytest -q"
    if adapter.kind == "node":
        return "node --test"
    sources = " ".join(f'"{f.name}"' for f in ex.student_files if f.suffix == ".cpp") or "*.cpp"
    gxx = f'& "{cfg.gxx}"' if cfg.gxx else "g++"
    return f"{gxx} -std=c++20 -Wall -Wextra {sources} -o program.exe; if ($?) {{ .\\program.exe }}"


def exercise_state(cfg: CourseConfig, adapter: Adapter, repo: Repo, cache: Cache, ex: Exercise) -> tuple[str, list]:
    files = ex.student_files + ex.test_files
    if adapter.kind == "cpp" and ex.solution_dir:
        files += list(ex.solution_dir.glob("*.cpp"))
    cached = cache.get(ex.key, fingerprint(files, extra=adapter.kind + cfg.stdin))
    modified = (not repo.ok) or any(not repo.is_original(f) for f in ex.student_files)
    if cached is None:
        return ("⬜ not started" if not modified else "✏️ changed since ATLAS last ran it"), []
    outcome = Outcome.from_dict(cached)
    status = _status(outcome, adapter.kind)
    if not modified and status not in ("passed", "manual") and adapter.kind != "cpp":
        status = "not_started"
    return STATUS_LABEL.get(status, status), outcome.failures if status != "not_started" else []


# ─────────────────────────────── the context pack ───────────────────────────────
def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def context_md(config: Config, found: Located, now: datetime | None = None) -> str:
    now = now or datetime.now()
    cfg, lessons, lesson = found.cfg, found.lessons, found.lesson
    root = tutor_dir(config)
    md = [f"# 🦉 {TUTOR_NAME} context pack", "",
          f"*Built by ATLAS {now.strftime('%d %b %Y %H:%M')} from its last review + the tutor's memory. No tests were run.*", ""]

    if lesson is None:
        md += ["Several lessons match. Pick one:", ""]
        for l in found.candidates[:15]:
            md.append(f"- [{l.course}] {l.title} · `{l.dir}` · {session_status(session_file(config, l)) or 'no session yet'}")
        return "\n".join(md)

    index = lessons.index(lesson)
    current = current_rel(cfg)
    current_index = next((i for i, l in enumerate(lessons) if l.rel == current), None)
    if current_index is None:
        relation = "ATLAS has no current lesson on record for this course (run `atlas`)."
    elif index == current_index:
        relation = "✅ CURRENT: this is exactly the lesson ATLAS assigned in this course."
    elif index < current_index:
        relation = f"🔁 REVIEW: an earlier lesson (ATLAS's current one is '{lessons[current_index].title}')."
    else:
        relation = (f"⏩ AHEAD by {index - current_index} lesson(s) of ATLAS's current one "
                    f"('{lessons[current_index].title}').")
    hold = hold_text(cfg)

    md += ["## 📍 Where this is", "",
           f"- **Course:** {cfg.title} (`{cfg.key}`) · faculty: `{root / 'faculties' / (cfg.key + '.md')}`",
           f"- **Unit:** {lesson.module_title} (`{lesson.module_id}`)",
           f"- **Lesson:** {lesson.title} · {lesson.kind} · #{index + 1} of {len(lessons)} written",
           f"- **Folder:** `{lesson.dir}`",
           f"- **Read:** `{lesson.dir / 'README.md'}`",
           f"- **Notes file:** `{notes_file(lesson)}`" + ("" if notes_file(lesson).exists() else " (doesn't exist yet: create it)"),
           f"- **ATLAS:** {relation}",
           f"- **Hold:** {'⏸ ON HOLD. ' + hold if hold else 'none'}", ""]

    if found.exercise:
        md += ["## 🎯 Focus: one exercise", "",
               f"- **{found.exercise.name}** ({found.exercise.kind}) · `{found.exercise.dir}`",
               f"- Student files: {', '.join(f.name for f in found.exercise.student_files) or '—'}"]
        if found.in_solution:
            md.append("- ⚠️ The path points INTO the model answer (`solution/`). Never show or paraphrase it to the learner.")
        md.append("")

    repo, cache = Repo(cfg.path), Cache(config.root / ".cache" / "results.json")
    if lesson.exercises:
        md += ["## 🧪 Exercises in this lesson (status from ATLAS's cache)", ""]
        for ex in lesson.exercises:
            state, failures = exercise_state(cfg, found.adapter, repo, cache, ex)
            md.append(f"- {state} · **{ex.name}** ({ex.kind}) · `{_rel(ex.dir, lesson.dir)}` · run: `{run_command(cfg, found.adapter, ex)}`")
            for name, message in failures[:2]:
                md.append(f"    - ✗ {name}: {message[:160]}")
        md.append("")

    md += ["## 🔗 Neighbours (for bridging)", ""]
    for label, other in (("Previous", lessons[index - 1] if index > 0 else None),
                         ("Next", lessons[index + 1] if index + 1 < len(lessons) else None)):
        if other:
            status = session_status(session_file(config, other))
            md.append(f"- **{label}:** {other.title} · `{other.dir}`" + (f" · tutored: {status}" if status else ""))
    md.append("")

    md += ["## 🧭 The other courses right now", ""]
    for other in config.courses:
        if other.key != cfg.key and other.path.exists():
            held = " ⏸ on hold" if hold_text(other) else ""
            md.append(f"- **{other.title}:** {status_line(other, '📍 You are here:') or 'unknown'}{held}")
    md.append("")

    session = session_file(config, lesson)
    rows = concept_rows(config)
    shaky = [r for r in rows if r.shaky and COURSE_ALIASES.get(r.course.lower(), r.course.lower()) == cfg.key]
    md += ["## 🧠 Memory", "",
           f"- **Session file:** `{session}` → " + (f"RESUME ({session_status(session)})" if session.exists()
                                                    else f"NEW: create it from `{root / 'templates' / 'session.md'}`"),
           f"- **Learner profile:** `{memory_dir(config) / 'learner.md'}`",
           f"- **Concept ledger:** `{memory_dir(config) / 'concepts.md'}` ({len(rows)} concept(s) recorded)",
           f"- **Journal:** `{memory_dir(config) / 'journal.md'}`"]
    if shaky:
        md.append("- **Still shaky in this course:** " + "; ".join(f"{r.concept} ({r.lesson})" for r in shaky[:8]))
    last = last_journal_entry(config)
    if last:
        md += ["- **Last session:**", *[f"    {line}" for line in last]]
    md.append("")

    reviews = report_section(config, "KNOWLEDGE.md", "Reviews due", 6)
    wellbeing = report_section(config, "REPORT.md", "Wellbeing", 5)
    late = 0 <= now.hour < 5
    if reviews or wellbeing or late:
        md += ["## ❤️ Warm-up & wellbeing", "", *reviews, *wellbeing]
        if late:
            md.append(f"- 🌙 It's {now.strftime('%H:%M')}. Keep this session short and protect your sleep.")
        md.append("")
    return "\n".join(md)


def overview_md(config: Config, now: datetime | None = None) -> str:
    """`atlas tutor` with no path: open sessions + what ATLAS assigned last time."""
    now = now or datetime.now()
    md = [f"# 🦉 {TUTOR_NAME}: where were we?", ""]
    sessions = open_sessions(config)
    if sessions:
        md += ["## ⏯ Unfinished sessions (newest first)", ""]
        md += [f"- {title} · {status} · `{path}`" for path, title, status in sessions[:6]]
        md.append("")
    nxt = report_section(config, "REPORT.md", "Your next lesson", 8)
    if nxt:
        md += ["## 🎯 ATLAS's next lesson (from its last review)", "", *nxt, ""]
    last = last_journal_entry(config)
    if last:
        md += ["## 📓 Last session", "", *last, ""]
    if 0 <= now.hour < 5:
        md += [f"🌙 It's {now.strftime('%H:%M')}. A short session, then sleep: that's when learning sticks.", ""]
    md.append("Start with: `athena @<lesson or exercise folder>` · or `atlas tutor <course> <words from the title>`")
    return "\n".join(md)
