"""Loads atlas.toml into typed settings."""

from __future__ import annotations

import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ATLAS_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class CourseConfig:
    key: str
    title: str
    path: Path
    adapter: str
    weekly_hours: float = 0.0
    python: Path | None = None
    gxx: Path | None = None
    weeks_per_lesson: float = 1.0
    stdin: str = ""
    start: str = ""  # optional "YYYY-MM-DD" override for when you started this course


@dataclass
class Config:
    learner: str
    courses: list[CourseConfig]
    workers: int = 6
    test_timeout: int = 40
    daily_minutes: int = 150
    similarity_warning: float = 0.93
    notes_threshold: float = 0.6
    stuck_days: int = 3
    review_intervals: list[int] = field(default_factory=lambda: [1, 3, 7, 21, 60])
    spine: str = "fullstack"
    hold_gap_weeks: float = 2.0
    root: Path = ATLAS_ROOT


def _git_user() -> str:
    try:
        out = subprocess.run(["git", "config", "--global", "user.name"], capture_output=True, text=True, timeout=10)
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def load_config(path: Path | None = None) -> Config:
    path = path or ATLAS_ROOT / "atlas.toml"
    with open(path, "rb") as f:
        data = tomllib.load(f)

    atlas = data.get("atlas", {})
    courses = []
    for key, raw in data.get("courses", {}).items():
        course_path = Path(raw["path"]).expanduser()
        courses.append(
            CourseConfig(
                key=key,
                title=raw.get("title", key),
                path=course_path,
                adapter=raw.get("adapter", key),
                weekly_hours=float(raw.get("weekly_hours", 0)),
                python=(course_path / raw["python"]) if raw.get("python") else None,
                gxx=Path(raw["gxx"]) if raw.get("gxx") else None,
                weeks_per_lesson=float(raw.get("weeks_per_lesson", 1.0)),
                stdin=raw.get("stdin", ""),
                start=str(raw.get("start", "")),
            )
        )

    return Config(
        learner=data.get("learner", {}).get("name") or _git_user() or "Engineer",
        courses=courses,
        workers=int(atlas.get("workers", 6)),
        test_timeout=int(atlas.get("test_timeout_seconds", 40)),
        daily_minutes=int(atlas.get("daily_minutes", 150)),
        similarity_warning=float(atlas.get("similarity_warning", 0.93)),
        notes_threshold=float(atlas.get("notes_filled_threshold", 0.6)),
        stuck_days=int(atlas.get("stuck_after_days", 3)),
        review_intervals=list(atlas.get("review_intervals_days", [1, 3, 7, 21, 60])),
        spine=atlas.get("spine", "fullstack"),
        hold_gap_weeks=float(atlas.get("hold_gap_weeks", 2.0)),
    )
