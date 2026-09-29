# 🏛️ ATLAS: your Chief Engineer, Professor & Examiner

**A**ssessment, **T**racking & **L**earning **A**nalytics **S**ystem.

In the myth, Atlas holds up the sky. This ATLAS holds up your four courses:

| Course | Folder |
|---|---|
| Full-Stack Engineering Mastery (the **spine**) | `Desktop\Full-Stack-Engineering-Mastery` |
| JavaScript & TypeScript Mastery | `Desktop\JavaScript-TypeScript-Mastery` |
| Python Engineering Mastery | `Desktop\Python-Engineering-Mastery` |
| The C++ 20 Masterclass | `Desktop\The-C-20-Masterclass-Source-Code-main` |

ATLAS is the **command centre**. It inspects your real work, runs your code, reviews it like a senior engineer, measures your pace, decides **which lesson you take next**, keeps the four courses **in sync**, sets and pre-checks your **gate exams**, and decides whether new lessons may be written. It's strict because it cares: the goal is to make you an excellent engineer, not to make you feel busy.

---

## ▶ Everyday use

From this folder, in PowerShell:

```powershell
.\atlas.ps1                  # full review of everything (run it at the end of every study session)
.\atlas.ps1 next             # "Professor, what do I study now?"
.\atlas.ps1 --open           # review, then open the visual dashboard
```

| Command | What ATLAS does |
|---|---|
| `atlas` | Full review: runs every exercise you've touched, reviews your code, updates every report |
| `atlas next` | Names **the** next lesson (across all four courses) and why |
| `atlas gate <course> [unit]` | Gate pre-check. When the evidence is complete, it issues a **gate exam sheet** |
| `atlas record <course> <unit> PASS\|FAIL --score N --note "…"` | Records an examiner's verdict in the official ledger |
| `atlas authorize <course>` | May new lessons be written for this course? (AUTHORIZED / DENIED + reasons) |
| `atlas knowledge` | Writes what you should know by now, plus reviews due today |
| `atlas eta` | Pace and projected finish date for every course |
| `atlas history` | Your progress over time |
| `atlas courses` | Course keys: `fullstack`, `jsts`, `python`, `cpp` |

Add `--no-tests` to reuse cached results (instant), or `--course python` to look at one course.

**Tip:** add this folder to your PATH and you can type `atlas next` from anywhere.

## 📂 What ATLAS writes

| File | For |
|---|---|
| `reports/REPORT.md` | The full review: verdict, next lesson, today's plan, scoreboard, sync, gates, code review, failures, changes, wellbeing, authorizations |
| `reports/dashboard.html` | The same, visual. Open it in a browser |
| `reports/KNOWLEDGE.md` | Per lesson: what you can now do, key terms, self-test questions, next review date |
| `ATLAS-STATUS.md` *(inside each course)* | Where you are in that course, holds, gate status. Regenerated every run; git-ignored |
| `briefs/<course>.md` | **Author brief**: the binding instructions for whoever writes your next lessons |
| `exams/<course>/<unit>_<date>.md` | Gate exam sheets for you to answer |
| `ledger/gates.json` | The **official record** of gate verdicts. Only a recorded PASS unlocks new lessons |
| `history/*.json` | One snapshot per review: trends, regressions, "stuck" detection |

---

## 🧠 How ATLAS judges you (fully transparent)

### Exercises

| Course type | How your work is checked |
|---|---|
| JS/TS & Full-Stack | Runs **your** `main.js` against the exercise's tests (`node --test`) |
| Python | Runs **your** `main.py` against its tests with pytest, in the course's own `.venv` |
| C++ | Compiles your program with g++, runs it **and** the model answer on the same input, and compares them in tiers: exact → same numbers → same final answer. "Runs but differs" is half credit, and you self-check it against the README |

An exercise that still matches the original starter in the course's **first Git commit** counts as *not started*, not *failing*.

| Status | Counts as |
|---|---|
| ✅ passed | 100% |
| 🟡 partial | the share of tests passing |
| 🔎 runs, output differs (C++) | 50% |
| ❌ failing / 💥 crashes / ⬜ not started | 0% |

### Code review (the Chief Engineer's eye)

Warnings: top-level `console.log`/`print` that runs on import · leftover `debugger`/`breakpoint()` · bare `except:` · code that's more than 93% identical to the model answer (you might have peeked).
Tips: loose `==` in JS · `== None` in Python · `range(len(…))` · `using namespace std;` · leftover TODOs in finished work · correct output with different formatting.

### Pace and ETA

Every lesson is worth its **planned study weeks** (from each course's own plan). **Pace = planned weeks completed ÷ real weeks since you started.** 1.00× means exactly on plan. The ETA blends your overall pace with the last 14 days. Confidence stays *low* until you've studied for about 2 weeks and completed 5 or more lessons, so early numbers are rough.

### Sync and holds

The four courses are designed to run side by side at about 1.00× each (see `Python-Engineering-Mastery\SYNC.md`). If one course gets **more than `hold_gap_weeks`** (default 2) planned weeks ahead of your slowest active course, ATLAS puts it **ON HOLD**. It won't assign it, and won't authorize new lessons for it, until the others catch up. That stops you doing lots of Python while quietly forgetting JS/TS.

### How ATLAS picks your next lesson

In order: a **gate exam** you're ready for → **finish** a lesson you've already started → the next lesson in the course that's **furthest behind** in sync (the spine gets a small preference, and a course you haven't touched in 4+ days gets priority). Held courses are skipped.

### Gates (you can't skip them)

1. **Evidence pre-check** (automatic, `atlas gate`): every exercise and debugging challenge passes, the review challenge is done, notes and quiz answers are written, and the self-assessment gate is ticked in the module README.
2. **Exam** (examiner): ATLAS issues an exam sheet built from the unit's "Explain it" questions, lesson quizzes and one of your own solutions. You answer it without notes, then ask Claude to grade it. Claude records the verdict with `atlas record`.
3. **Authorization:** new lessons for a course are generated **only** when every written unit is gate-PASSED **and** the course isn't on hold. The author must follow the directives in `briefs/<course>.md`.

### Wellbeing

ATLAS tracks your streak and active days. It will tell you to take a **rest day** after 7 days straight, and it notices late-night sessions. Sleep is when learning sticks.

---

## ⚙️ Configuration: `atlas.toml`

Change course paths, your time split (`weekly_hours`), the hold threshold, the daily plan length, review intervals, and the similarity threshold. If you worked on a course before its first commit, set `start = "YYYY-MM-DD"` under that course so your pace is fair.

## 🧪 ATLAS's own tests

```powershell
..\Python-Engineering-Mastery\.venv\Scripts\python -m pytest
```

A Chief Engineer holds itself to its own standard.

## 🔒 Keep ATLAS's records safe

The ledger and history are your academic record. Make this folder a Git repository and commit after each review:

```powershell
git init; git add .; git commit -m "ATLAS: first review"
```
