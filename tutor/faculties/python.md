# 🐍 Athena's Python faculty: Python Engineering Mastery

**Course key:** `python` · **Folder:** `C:\Users\QweQu Antwi\Desktop\Python-Engineering-Mastery`
**Role in the four:** backend, data, AI and AI infrastructure. Levels I–XXXII, from language foundations to
production AI systems. Read `SYNC.md` there for the convergence checkpoints with the other courses.

## Layout

```text
StageN.*/LvNN.*/MNNN.<Module>/LNN.<Lesson>/
    README.md          1 Concept · 2 Why · 3 Internal mechanics · 4 Simple examples · 5 Real-world
                       6 Exercises · 7 Debugging · 8 Design question · 9 Short assessment · 10 Reflection
                       🔑 Key words · ✅ Done when
    Examples/*.py      run these live while teaching
    Exercises/NN_Name/ main.py (the learner's) · test_main.py · README.md (with hints) · solution/ (never show)
    Debugging/NN_Name/ same layout, with planted bugs
    MY-NOTES.md        the learner's notes (your block goes at the end)
MNNN.<Module>/README.md   has the unit's gate: "Explain it" questions + self-assessment boxes
LvNN.*/Level-Exam/        gate exam tasks: exam rules apply (ATHENA.md §12)
```

The README already offers 🧸 *Simple version* and 🎓 *Precise version*. Don't just repeat them: start from a
different angle (their question, a live run, a diagram), then point at the README's wording as the reference.

## Running things

Always use the course's virtual environment:

```powershell
& "C:\Users\QweQu Antwi\Desktop\Python-Engineering-Mastery\.venv\Scripts\python.exe" -m pytest -q    # in an exercise folder
& "C:\Users\QweQu Antwi\Desktop\Python-Engineering-Mastery\.venv\Scripts\python.exe" -c "print(0.1 + 0.2)"
```

## Live-demo toolkit (see it run)

| Show | How |
|---|---|
| What the PVM runs | `python -m dis file.py`, or `dis.dis(func)` |
| How Python parses | `ast.dump(ast.parse("x = 1 + 2"), indent=2)` · `python -m tokenize file.py` |
| Names vs objects | `id(x)`, `x is y`, `sys.getrefcount(x)` and a names ──► objects diagram |
| Types at runtime | `type(x)`, `isinstance`, `x.__class__.__mro__` |
| Scope and frames | `locals()`, `globals()`, and a frame-stack diagram |
| Speed | `python -m timeit "…"`, `time.perf_counter()` |
| Step through | pythontutor.com (paste a snippet), the VS Code debugger, `breakpoint()` (remove it afterwards: ATLAS flags leftovers) |

## Classic misconceptions to probe

- Variables are **boxes** holding values. ✗ In Python they're **name tags** on objects (aliasing, `is` vs `==`,
  mutable default arguments, `a = b` doesn't copy).
- "Python is interpreted line by line." ✗ The whole file is compiled to bytecode first (syntax errors come before any output).
- Dynamic typing means weak typing. ✗ `"3" + 3` is a TypeError. (The learner already has this one in their L01 notes.)
- `==` vs `is`, and `== None` (ATLAS flags that: use `is None`).
- Mutability: lists vs tuples, and modifying a list while looping over it.
- `range(len(x))` instead of `enumerate` (ATLAS tip) and `print` at import time (ATLAS warning).
- Integer division `//` vs `/`, floats (`0.1 + 0.2`), and truthiness of `0`, `""`, `[]`, `None`.
- Bare `except:` (ATLAS warning): catch what you expect.

## Bridges to the other courses

| Python idea | JS/TS | C++ | Full-Stack |
|---|---|---|---|
| CPython + bytecode + PVM | V8: Ignition bytecode + JIT | g++ → machine code | D5 Compilers, interpreters & runtimes |
| Names → objects | JS references | pointers & references (13–14) | M01 memory |
| Duck typing / Protocols | TS structural types | templates & concepts (24–25) | M11 TypeScript |
| Closures & decorators | closures (Phase 4) | lambdas (21) | M05–M06 |
| Refcounting + GC | GC (Phase 15) | RAII / smart pointers (33, 52) | M31 performance |
| asyncio | event loop (Phase 11) | threads (53) | M33–M34 distributed |

When a C++ lesson is already done (see the context pack), use it: "Remember how `g++` turned your whole file into
machine code? CPython does *half* of that…"
