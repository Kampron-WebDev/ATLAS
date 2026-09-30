# ⚙️ Athena's C++ faculty: The C++ 20 Masterclass

**Course key:** `cpp` · **Folder:** `C:\Users\QweQu Antwi\Desktop\The-C-20-Masterclass-Source-Code-main`
**Role in the four:** memory, performance and systems thinking: the "what the machine really does" course. Lessons
00–60, from programming thinking to concurrency, performance and capstones. Each lesson folder is its own gate unit.

⏸ This course is often **ON HOLD** because the learner moves fast here. Check the context pack and follow
ATHENA.md §13: review and unfinished exercises are fine, new material waits.

## Layout

```text
NN.<LessonName>/
    README.md                 🎯 By the end… · 🧸 Big idea · sections · ⚠️ Common traps · ✅ Check yourself
    N.M<Topic>/main.cpp       the original masterclass source demos (+ CMakeLists.txt): use as live examples
    Examples/NN_Name/
    Exercises/README.md       exercise list
    Exercises/NN_Name/main.cpp  the learner's work · solution/ (never show)
```

No `MY-NOTES.md` here, so your notes go in `ATHENA-NOTES.md` inside the lesson folder (the context pack names it).

## Running things

```powershell
& "C:\mingw64\bin\g++.exe" -std=c++20 -Wall -Wextra "main.cpp" -o program.exe; if ($?) { .\program.exe }
```

- **How ATLAS checks C++:** it compiles the learner's program and the model answer, feeds both the **same stdin**
  (`5 7 3 3725 87 2 4 6 8 10`), and compares the outputs. "Runs, output differs" is half credit.
- That means **passing ≠ correct.** One fixed input can't find every bug. Always invent edge cases: equal numbers,
  negatives, zero, the largest value, and inputs in a different order.
- `*.exe` is git-ignored in this course, so building inside an exercise folder is safe.

## Live-demo toolkit

| Show | How |
|---|---|
| Compilation stages | `g++ -E` (preprocess) · `g++ -S` (assembly) · `g++ -c` (object) · link. Compare with `python -m dis` |
| Sizes and memory | `sizeof(x)`, `&x` (addresses), `std::numeric_limits<int>::max()` |
| Warnings as teachers | `-Wall -Wextra`: read every warning together |
| Overflow and conversions | tiny programs printing before/after values |
| Step through | gdb (`C:\mingw64\bin\gdb.exe`) or the VS Code debugger; trace tables on paper first |
| See the machine code | godbolt.org (Compiler Explorer): paste a function, watch `-O0` vs `-O2` |

## Diagrams this course lives on

- **Memory maps:** stack frames (growing down), the heap, addresses as boxes (`0x7ff…`), and pointers as arrows.
- **Trace tables** (the course's own tool from lesson 02): a row per line, a column per variable.
- **Compilation pipeline:** `.cpp ─► preprocessor ─► compiler ─► assembler ─► linker ─► .exe`.
- **Object lifetime:** a timeline of construction → use → destruction (scope, RAII).

## Classic misconceptions to probe

- **Running max/min:** compare each new value with the *best so far*, not with the previous input. (Evidence:
  `02_BiggestOfThree` compares `num3 > num2`, which prints 5 for input `9 1 5`. It passes ATLAS's single stdin test
  anyway, so coach it with rung 4: "trace it with 9 1 5".)
- Uninitialised variables hold garbage (prefer `int x{};`, which the learner already does, which is good).
- Integer division truncates, `%` with negatives, and overflow is undefined for signed types.
- `=` vs `==` inside `if`. `std::endl` vs `'\n'`. `using namespace std;` (ATLAS tip).
- Arrays decay to pointers. Pointer vs reference. Dangling pointers/references.
- Copy vs move, and who owns what (smart pointers, RAII, rule of five).

## Bridges

C++ shows the machine that the other languages hide. Use it that way: "Python's name tags are, underneath,
pointers to heap objects with a reference count", and "JS's garbage collector does automatically what `delete`
did here." C++ lessons 01–02 pair with Full-Stack W1 and Python M001 (see SYNC.md).
