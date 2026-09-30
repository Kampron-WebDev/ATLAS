# 🦉 Athena's memory: the learner

*Athena keeps this file up to date (ATHENA.md §10). Facts need evidence. Merge and prune; keep it under about 150 lines.*
*Seeded 30 Sep 2026 from ATLAS's first reviews and the learner's own notes and code.*

## Who they are

- Studying four courses side by side under ATLAS: **Full-Stack (the spine)**, **JS/TS**, **Python**, **C++**.
- Goal: become an excellent all-round software engineer. The four capstones form one AI tutoring platform (SYNC.md).
- Asked for a tutor because "reading alone does not cut it": they want concepts broken into steps, examples,
  diagrams, and checks before moving on. **Teach interactively, not with walls of text.**
- Types quickly and informally in chat (typos are normal: ignore them).

## Where they are (30 Sep 2026)

| Course | Position | Notes |
|---|---|---|
| Full-Stack | Orientation → M01 W1 D2 (CPU, RAM & Storage) | D1 notes and architecture answer written |
| JS/TS | Orientation → M001 L02 (Values, Expressions & Statements) | L01 notes strong |
| Python | M001 L02 (CPython: Source to Bytecode to the PVM) | L01 complete, 4/34 exercises |
| C++ | Lessons 00–02 done, ⏸ **ON HOLD** (ahead of the spine) | Moves fastest here |

## Strengths (with evidence)

- **Systems and state thinking.** In JS L01 they modelled a microwave as a state machine, and derived "heater on" from
  the state instead of storing it, so impossible combinations *can't* happen. That's senior-level instinct.
- **Data-driven design:** they saw that the traffic light's rules belong in data, not in `if`s (JS L01).
- **Architecture sketches:** clear users/needs breakdown and box diagrams (Full-Stack D1).
- **Solves by hand first:** worked out 289 cents by hand before coding CoinChange (C++ 02). Praise this habit.
- **Tidy notes** with headings, tables and code examples (Python L01: dynamic vs strong typing, duck typing).
- Initialises C++ variables with `{}`.

## Growth areas (with evidence)

- **Running max/min pattern:** C++ `02_BiggestOfThree` compares `num3 > num2` instead of `num3 > biggest`, so input
  `9 1 5` prints 5. ATLAS passed it (its one fixed input happens to work). Coach with a trace table. Don't just tell them.
- **Repeated computation instead of updating state:** CoinChange recomputes `((change % 100) % 50) % 25…` for every
  coin. Next step: a `remaining` variable, then a loop over a coin list (it links to their own "rules as data" insight).
- **Skips written reflection:** Python L01 "Still fuzzy" is empty. ATLAS directive: quiz and reflection answers are
  being skipped. Nudge them to write these *in their own words* at each wrap-up.
- Leaves `// TODO` comments in finished code (ATLAS directive: add "tidy up" to the finish).
- Pace: about 0.5–0.7× plan in Full-Stack, JS/TS and Python; about 4.8× in C++. They're drawn to C++, so use C++
  bridges as motivation for the other courses.

## Misconceptions

| Misconception | Evidence | Status |
|---|---|---|
| Running max: compare with the previous input instead of the best so far | C++ 02 BiggestOfThree | active (untested in dialogue) |

## What works for them

- Comparison tables and side-by-side language comparisons (they write these unprompted).
- Concrete scenarios (traffic light, microwave, school attendance app).
- *(Record the analogies and diagrams that land, as sessions happen.)*

## Preferences

- Step by step, with understanding checked before moving on. Examples, diagrams and graphs after each concept.
- Wants their notes updated with the concepts they personally ask about.

## Wellbeing patterns

- Often studies very early in the morning (sessions around 05:00). ATLAS tracks late nights and streaks: mention
  rest when ATLAS raises it.
