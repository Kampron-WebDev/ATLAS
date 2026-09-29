"""What ATLAS remembers between runs: the result cache, run history and the gate ledger."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from . import __version__


def fingerprint(files: list[Path], extra: str = "") -> str:
    h = hashlib.sha256((__version__ + extra).encode())
    for f in sorted(files):
        try:
            h.update(f.name.encode() + f.read_bytes())
        except OSError:
            h.update(b"<missing>")
    return h.hexdigest()


class Cache:
    """Test results keyed by exercise, reused while the code is unchanged."""

    def __init__(self, path: Path):
        self.path = path
        try:
            self.data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}

    def get(self, key: str, fp: str) -> dict | None:
        entry = self.data.get(key)
        return entry["outcome"] if entry and entry.get("fp") == fp else None

    def put(self, key: str, fp: str, outcome: dict) -> None:
        self.data[key] = {"fp": fp, "outcome": outcome}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=1), encoding="utf-8")


class History:
    """One JSON snapshot per assessment run, for trends, regressions and 'stuck' detection."""

    def __init__(self, folder: Path):
        self.folder = folder
        folder.mkdir(parents=True, exist_ok=True)

    def snapshots(self) -> list[dict]:
        result = []
        for file in sorted(self.folder.glob("*.json")):
            try:
                result.append(json.loads(file.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        return result

    def latest(self) -> dict | None:
        snaps = self.snapshots()
        return snaps[-1] if snaps else None

    def save(self, snapshot: dict) -> Path:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = self.folder / f"{stamp}.json"
        path.write_text(json.dumps(snapshot, indent=1, default=str), encoding="utf-8")
        return path


class Ledger:
    """The official record of gate exams. Only a recorded PASS unlocks new lessons."""

    def __init__(self, path: Path):
        self.path = path
        try:
            self.entries: list[dict] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.entries = []

    def record(self, course: str, unit: str, verdict: str, examiner: str, note: str = "", score: str = "") -> dict:
        entry = {
            "course": course,
            "unit": unit,
            "verdict": verdict.upper(),
            "examiner": examiner,
            "score": score,
            "note": note,
            "date": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        self.entries.append(entry)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.entries, indent=1), encoding="utf-8")
        return entry

    def latest(self, course: str, unit: str) -> dict | None:
        matches = [e for e in self.entries if e["course"] == course and e["unit"] == unit]
        return matches[-1] if matches else None

    def passed(self, course: str, unit: str) -> bool:
        entry = self.latest(course, unit)
        return bool(entry and entry["verdict"] == "PASS")
