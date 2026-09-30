# 🦉 Athena: your tutor

ATLAS decides **what** you study and **whether** you've mastered it. **Athena teaches you**, one small idea at a
time, until you truly understand it. In the *Odyssey*, the goddess Athena disguised herself as a friend called
Mentor to guide young Telemachus. The word "mentor" comes from her.

## ▶ Summon her

In **Claude Code** or **Codex** chat (VS Code or terminal), from any of your course folders:

| You type | Athena… |
|---|---|
| `athena @<lesson folder>` | teaches that lesson step by step (or picks up where you stopped) |
| `athena help @<exercise folder>` | coaches you through the exercise **without giving you the answer** |
| `athena` · `athena continue` | resumes your latest session, or starts ATLAS's next lesson |
| `athena explain <anything>` | breaks one concept down, then adds it to your notes |
| `athena quiz me` | retrieval practice on reviews due and your shaky concepts |
| `athena exam prep <unit>` | gets you ready for a gate exam |
| `athena status` | shows the lesson map and your progress |

In Claude Code you can also type `/athena …`, and in Codex `$athena …`. No `@`? Words work too:
`athena python bytecode`, `athena help biggest of three`.

## 🎛 During a lesson

Just talk to her. You can also use these shortcuts:

`next` · `again` (explain it another way) · `simpler` · `deeper` · `diagram` · `example` · `quiz me` · `hint` ·
`note this` (add it to my notes) · `pause` (save and stop)

## 🧠 How she teaches

1. Reads ATLAS's view of you, her memory of you, and the whole lesson (examples, exercises, your notes).
2. Breaks the lesson into **micro-concepts** in order, and shows you the map.
3. For each one: a link to what you know, a simple analogy, a **diagram**, the precise version, a **live example**
   (you predict the output first), a real-world use, and the classic trap.
4. Asks you **one question** that proves you understand. You move on only when you've shown it. A wrong answer
   gets a *different* explanation, never the same one louder.
5. Connects every idea to your other three courses and to what's coming next.

## 📝 Your notes

When you ask her to explain something, she adds it to that lesson's `MY-NOTES.md` (or `ATHENA-NOTES.md` when a
lesson has no notes file), inside a clearly marked Athena block at the end. ATLAS **ignores** that block when it
grades your notes, so your quiz answers and reflections still have to be in your own words. That's the point.

## 💾 Her memory (`tutor/memory/`)

| File | What she remembers |
|---|---|
| `learner.md` | Your strengths, growth areas, misconceptions, what explanations work for you |
| `concepts.md` | Every concept: 🟢 solid / 🟡 shaky / 🔴 confused. **ATLAS reads this** and tells future lesson authors to revisit your shaky ones |
| `journal.md` | One entry per session |
| `sessions/` | Where you are inside each lesson, so you can stop at any point and resume |

You can read and edit all of these. Commit them with the rest of ATLAS (`git add .; git commit`).

## 🔒 Her rules (so she can't cheat you)

- She never writes your exercise code and never reveals `solution/`. She coaches with a hint ladder instead.
- She doesn't help during gate exams (she'll prep you before and debrief you after).
- She respects ATLAS: holds, gates and the order of lessons.

The full operating manual is [`ATHENA.md`](ATHENA.md). The per-course knowledge is in [`faculties/`](faculties/).
