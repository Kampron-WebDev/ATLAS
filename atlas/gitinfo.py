"""Everything ATLAS learns from a course's Git history.

* The FIRST commit holds the original starters, so a file that still matches it is untouched.
* Commit dates show when you worked, which drives pace, streaks and ETAs.
* `git status` shows work you haven't committed yet.
"""

from __future__ import annotations

import hashlib
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def blob_sha(data: bytes) -> str:
    """Git's object id for file contents: sha1("blob <len>\\0" + data)."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def content_variants(data: bytes) -> set[str]:
    """Hashes of the file as-is and with line endings normalised (Git may store LF for CRLF files)."""
    lf = data.replace(b"\r\n", b"\n")
    return {blob_sha(data), blob_sha(lf), blob_sha(lf.replace(b"\n", b"\r\n"))}


class Repo:
    def __init__(self, root: Path):
        self.root = root
        self.ok = (root / ".git").exists()
        self.root_commit = ""
        self.baseline: dict[str, str] = {}
        self.touches: dict[str, list[datetime]] = defaultdict(list)  # path → commit dates (after root)
        self.commit_dates: list[datetime] = []
        self.dirty: set[str] = set()
        if self.ok:
            self._load()

    def _git(self, *args: str) -> str:
        out = subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=self.root,
                             capture_output=True, timeout=120)
        if out.returncode != 0:
            return ""
        return out.stdout.decode("utf-8", errors="replace")

    def _load(self) -> None:
        roots = self._git("rev-list", "--max-parents=0", "HEAD").split()
        if not roots:
            self.ok = False
            return
        self.root_commit = roots[-1]

        for entry in self._git("ls-tree", "-r", "-z", self.root_commit).split("\0"):
            if "\t" in entry:
                meta, path = entry.split("\t", 1)
                self.baseline[path] = meta.split()[2]

        current_date = None
        is_root = False
        for line in self._git("log", "--format=@@@%H %cI", "--name-only").splitlines():
            if line.startswith("@@@"):
                sha, iso = line[3:].split(" ", 1)
                current_date = datetime.fromisoformat(iso).astimezone()
                is_root = sha == self.root_commit
                self.commit_dates.append(current_date)
            elif line.strip() and current_date and not is_root:
                self.touches[line.strip()].append(current_date)

        status = self._git("status", "--porcelain=v1", "-z", "--untracked-files=all")
        for entry in status.split("\0"):
            if len(entry) > 3:
                self.dirty.add(entry[3:])

    def rel(self, path: Path) -> str:
        return path.resolve().relative_to(self.root.resolve()).as_posix()

    def is_original(self, path: Path) -> bool:
        """True if the file is byte-for-byte the version in the first commit."""
        if not self.ok:
            return False
        sha = self.baseline.get(self.rel(path))
        if sha is None:
            return False  # a new file the student created
        try:
            return sha in content_variants(path.read_bytes())
        except OSError:
            return False

    def baseline_text(self, path: Path) -> str | None:
        if not self.ok or self.rel(path) not in self.baseline:
            return None
        return self._git("show", f"{self.root_commit}:{self.rel(path)}")

    def activity(self, path: Path) -> list[datetime]:
        """Dates of commits that touched the file, plus its modification time if it has uncommitted changes."""
        rel = self.rel(path)
        dates = list(self.touches.get(rel, []))
        if rel in self.dirty and path.exists():
            dates.append(datetime.fromtimestamp(path.stat().st_mtime).astimezone())
        return dates

    def is_dirty(self, path: Path) -> bool:
        return self.ok and self.rel(path) in self.dirty

    def start_date(self) -> datetime | None:
        return min(self.commit_dates) if self.commit_dates else None
