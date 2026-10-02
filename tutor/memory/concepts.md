# 🧠 Athena's concept ledger

*One row per concept Athena has taught or checked. Status: 🟢 solid · 🟡 shaky · 🔴 confused.*
*ATLAS reads the 🟡/🔴 rows (by course key) and tells future lesson authors to revisit them, so keep the columns intact.*
*Course column: `fullstack` · `jsts` · `python` · `cpp`.*

| Concept | Course | Lesson | Status | Last checked | Links |
|---|---|---|---|---|---|
| Dynamic vs strong typing | python | M001 L01 | 🟢 solid | 2026-09-29 | ↔ JS coercion (`"3" + 3`) · ➡ M004 data types |
| Duck typing | python | M001 L01 | 🟢 solid | 2026-09-29 | ↔ TS structural types · ➡ Protocols (Level VIII) |
| State and state machines | jsts | M001 L01 | 🟢 solid | 2026-09-29 | ↔ Full-Stack UI state · ➡ reducers, protocols |
| Rules as data (table-driven logic) | jsts | M001 L01 | 🟢 solid | 2026-09-29 | ➡ C++ CoinChange as a loop over a coin list |
| Running maximum (compare with best so far) | cpp | 02 ProgrammingThinking | 🟡 shaky | 2026-09-30 | from code evidence only: confirm in dialogue · ➡ loops (11), arrays (12) |
| Storage vs RAM vs cache (who keeps, who works) | fullstack | M01-W1 D2 | 🟢 solid | 2026-09-30 | thought saved file lives in "cache" (everyday meaning); fixed same session · ➡ Redis, browser cache |
| Fetch–decode–execute, Program Counter, jumps | fullstack | M01-W1 D2 | 🟢 solid | 2026-09-30 | first counted "steps" as lines; fixed via trace · ↔ Python PVM loop, C++ 01 · ➡ D5 |
| Latency ladder and ratios (units cancel) | fullstack | M01-W1 D2 | 🟢 solid | 2026-10-02 | ratios right, labelled counts as "ns" once; later 1000x slower with correct unit, twice (concept 5, cold start) · ➡ HumanLatency, FormatBytes |
| I/O-bound vs CPU-bound | fullstack | M01-W1 D2 | 🟢 solid | 2026-09-30 | ➡ Month 31 performance, async I/O in Node |
| Locality and cache lines | fullstack | M01-W1 D2 | 🟡 shaky | 2026-09-30 | asked for breakdown; library/photocopier analogy landed · ↔ C++ vectors are contiguous · ➡ Month 31 |
| Off-by-one and NaN propagation (debugging) | fullstack | M01-W1 D2 | 🟢 solid | 2026-10-01 | traced by hand, found both bugs, guard clause; overclaimed "green = correct" once, fixed · ➡ edge cases in FormatBytes |
| Search loop needs a "no match" plan (undefined past the end) | fullstack | M01-W1 D2 | 🟢 solid | 2026-10-02 | AverageMemory, FormatBytes, HumanLatency all same family · ➡ array bounds in C++ |
| Rounding/boundary: choose unit before rounding (1024.0 KB) | fullstack | M01-W1 D2 | 🟡 shaky | 2026-10-02 | understands mechanism after prompt; judged a trade-off · ➡ D3 binary/hex |
| Why the hierarchy exists (cost/size trade-off) | fullstack | M01-W1 D2 | 🟢 solid | 2026-10-02 | recap blank said "operation speed", but his own pupil/desk/library analogy later said "quick access holds less… because fast memory is expensive" · re-ask once in a later session to lock in |
