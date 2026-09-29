"""Runs YOUR code: node --test, pytest, or g++ + run-and-compare for C++.

All runners return an Outcome. Test runners write JUnit XML, which ATLAS parses for
per-test results and failure messages.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Outcome:
    passed: int = 0
    failed: int = 0
    total: int = 0
    failures: list[tuple[str, str]] = field(default_factory=list)
    crashed: bool = False
    detail: str = ""
    seconds: float = 0.0
    # C++ only
    compiled: bool | None = None
    output_matches: bool | None = None

    def to_dict(self) -> dict:
        return self.__dict__ | {"failures": [list(f) for f in self.failures]}

    @classmethod
    def from_dict(cls, data: dict) -> "Outcome":
        data = dict(data)
        data["failures"] = [tuple(f) for f in data.get("failures", [])]
        return cls(**data)


def _clean_env() -> dict:
    env = dict(os.environ)
    env.pop("CHECK_SOLUTION", None)  # always test the STUDENT's code
    env["PYTHONUTF8"] = "1"
    env["NO_COLOR"] = "1"
    return env


def parse_junit(xml_text: str) -> Outcome:
    outcome = Outcome()
    root = ET.fromstring(xml_text)
    for case in root.iter("testcase"):
        if case.find("skipped") is not None:
            continue
        outcome.total += 1
        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
        if problem is None:
            outcome.passed += 1
        else:
            outcome.failed += 1
            message = (problem.get("message") or problem.text or "").strip()
            outcome.failures.append((case.get("name", "?"), message.splitlines()[0][:220] if message else ""))
    return outcome


def _run_with_junit(cmd: list[str], cwd: Path, report: Path, timeout: int) -> Outcome:
    start = time.perf_counter()
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout, env=_clean_env())
    except subprocess.TimeoutExpired:
        return Outcome(crashed=True, detail=f"timed out after {timeout}s (an infinite loop?)", seconds=timeout)
    elapsed = time.perf_counter() - start
    outcome = Outcome()
    if report.exists() and report.stat().st_size:
        try:
            outcome = parse_junit(report.read_text(encoding="utf-8", errors="replace"))
        except ET.ParseError:
            pass
    if outcome.total == 0:
        tail = (proc.stderr or proc.stdout).decode("utf-8", errors="replace").strip().splitlines()
        outcome.crashed = True
        outcome.detail = " | ".join(tail[-3:])[:300] or "no tests ran"
    outcome.seconds = round(elapsed, 2)
    return outcome


def run_node(ex_dir: Path, test_files: list[Path], timeout: int) -> Outcome:
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "junit.xml"
        cmd = ["node", "--test", "--test-reporter=junit", f"--test-reporter-destination={report}",
               f"--test-timeout={timeout * 1000 // 2}", *[f.name for f in test_files]]
        return _run_with_junit(cmd, ex_dir, report, timeout)


def run_pytest(ex_dir: Path, test_files: list[Path], python: Path, timeout: int) -> Outcome:
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "junit.xml"
        cmd = [str(python), "-P", "-m", "pytest", f"--junit-xml={report}", "-o", "junit_family=xunit2",
               "-p", "no:cacheprovider", "-q", *[f.name for f in test_files]]
        return _run_with_junit(cmd, ex_dir, report, timeout)


def _normalise_output(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    return "\n".join(lines).strip()


def compile_and_run(src_dir: Path, gxx: Path, build_dir: Path, stdin: str, timeout: int) -> tuple[bool, str, str]:
    """Compile every .cpp in src_dir and run it. Returns (compiled, output, error text)."""
    sources = sorted(str(p) for p in src_dir.glob("*.cpp"))
    std = "-std=c++23" if (src_dir / ".cpp23").exists() or (src_dir.parent / ".cpp23").exists() else "-std=c++20"
    extra = ["-pthread"] if (src_dir / ".threads").exists() or (src_dir.parent / ".threads").exists() else []
    build_dir.mkdir(parents=True, exist_ok=True)
    exe = build_dir / "program.exe"
    env = _clean_env()
    env["PATH"] = str(gxx.parent) + os.pathsep + env.get("PATH", "")
    try:
        comp = subprocess.run([str(gxx), std, *sources, *extra, "-o", str(exe)], capture_output=True,
                              timeout=timeout, env=env, cwd=src_dir)
    except subprocess.TimeoutExpired:
        return False, "", "compiler timed out"
    if comp.returncode != 0:
        errors = [l for l in comp.stderr.decode("utf-8", errors="replace").splitlines() if "error" in l]
        return False, "", " | ".join(errors[:2])[:300] or "compile error"
    try:
        run = subprocess.run([str(exe)], input=stdin.encode(), capture_output=True, timeout=10, env=env, cwd=src_dir)
        output = run.stdout.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        output = "<timed out>"
    return True, _normalise_output(output), ""


def _numbers(text: str) -> list[str]:
    text = re.sub(r"0x[0-9a-fA-F]+", " ", text)  # memory addresses differ on every run
    return re.findall(r"-?\d+(?:\.\d+)?", text)


def compare_outputs(output: str, expected: str) -> tuple[bool, str]:
    """C++ programs word their prompts differently, so compare in tiers: exact → numbers → final answer."""
    def masked(text: str) -> str:
        return " ".join(re.sub(r"0x[0-9a-fA-F]+", "<addr>", text).split())

    if masked(output) == masked(expected):
        return True, ""
    got, want = _numbers(output), _numbers(expected)
    if want and got == want:
        return True, "numbers match the model answer; wording or formatting differs (compare with the README)"
    if want and got and got[-1] == want[-1] and len(want) <= 2:
        return True, "final answer matches the model answer; wording differs"
    return False, "compiles and runs, but its output differs from the model answer's. Self-check it against the README"


def run_cpp(ex_dir: Path, solution_dir: Path | None, gxx: Path, stdin: str, timeout: int) -> Outcome:
    if (ex_dir / ".modules").exists() or (ex_dir / ".skip-check").exists():
        return Outcome(detail="needs a special build (modules/CMake): check it by hand", crashed=False, compiled=None)
    start = time.perf_counter()
    build = Path(tempfile.mkdtemp(prefix="atlas-cpp-"))
    try:
        ok, output, error = compile_and_run(ex_dir, gxx, build / "student", stdin, timeout)
        outcome = Outcome(compiled=ok, total=1)
        if not ok:
            outcome.failed = 1
            outcome.detail = f"does not compile: {error}"
        elif solution_dir:
            sol_ok, expected, _ = compile_and_run(solution_dir, gxx, build / "solution", stdin, timeout)
            matches, note = compare_outputs(output, expected) if sol_ok else (False, "model answer didn't build")
            outcome.output_matches = matches
            outcome.detail = note
            if matches:
                outcome.passed = 1
            else:
                outcome.failed = 1
        else:
            outcome.passed = 1
        outcome.seconds = round(time.perf_counter() - start, 2)
        return outcome
    finally:
        shutil.rmtree(build, ignore_errors=True)
