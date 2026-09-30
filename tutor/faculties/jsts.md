# 🟨 Athena's JS/TS faculty: JavaScript & TypeScript Mastery

**Course key:** `jsts` · **Folder:** `C:\Users\QweQu Antwi\Desktop\JavaScript-TypeScript-Mastery`
**Role in the four:** the web platform's language, in depth. Part 1 is JavaScript (Phases 1–19, including internals,
async, DSA, patterns, testing and Node). Part 2 is TypeScript (Phases 20–30, up to type-level programming and large
systems). See `ROADMAP.md` there.

## Layout

```text
PartN.*/PNN.<Phase>/MNNN.<Module>/LNN.<Lesson>/
    README.md          1 Concept · 2 Why · 3 Internal mechanics · 4 Simple examples · 5 Real-world
                       6 Exercises · 7 Debugging · 8 Design question · 9 Short assessment · 10 Reflection
    Examples/*.js      run live
    Exercises/NN_Name/ main.js (the learner's) · main.test.js · README.md · solution/ (never show)
    Debugging/NN_Name/ planted bugs
    MY-NOTES.md
MNNN.<Module>/README.md  the unit gate · LNN.ModuleReview = review challenge
PNN.<Phase>/Phase-Exam/  gate exam (ANSWER-KEY.md inside: never open it)
```

## Running things

```powershell
node --test                  # in an exercise folder
node Examples\file.js
node -e "console.log(0.1 + 0.2)"
node                         # the REPL, for quick experiments
```

Exercises are ES modules that export functions. A top-level `console.log` runs on every import, including by the
tests (ATLAS warns about it). Demos belong in `Examples/`.

## Live-demo toolkit

| Show | How |
|---|---|
| Types and coercion | `typeof`, `Object.is`, `[] + {}`, `"5" * 2` vs `"5" + 2` |
| Tables of data | `console.table(arr)` |
| Engine internals | `node --print-bytecode --print-bytecode-filter=fnName file.js` (convergence with `python -m dis`) |
| Event loop | a timeline diagram: call stack │ microtasks │ macrotasks; or a `setTimeout`/`Promise` ordering puzzle |
| Scope and closures | a diagram of environment records as boxes chained by `outer` arrows |
| Step through | `node --inspect-brk` + Chrome DevTools, or the VS Code debugger (remove `debugger;` afterwards: ATLAS flags it) |
| Types (Part 2) | `npx tsc --noEmit`, hovering types, and the TS Playground for `type` experiments |

## Classic misconceptions to probe

- `==` vs `===` (ATLAS flags loose equality) and truthy/falsy (`0`, `""`, `null`, `undefined`, `NaN`).
- `let`/`const`/`var` and hoisting. `const` doesn't make an object immutable.
- Primitives are copied, while objects are shared by reference. Arrays as function arguments.
- Expression vs statement (Lesson 02!): "does it produce a value?"
- `this` depends on *how* a function is called, not where it's written.
- Async: `await` pauses the *function*, not the program. A Promise isn't a thread. Microtasks run before timers.
- TS: types are erased at runtime. Structural typing, not nominal. `any` vs `unknown`.

## Bridges

| JS/TS idea | Python | C++ | Full-Stack |
|---|---|---|---|
| Engine, host, runtime | CPython / PVM | compiler + OS | D5 Compilers & runtimes |
| Closures | closures & decorators | lambda captures (21) | M05–M06 |
| Prototypes & classes | the object model (Level IV) | classes & inheritance (26, 36) | M06 |
| Event loop | asyncio (Level XV) | threads (53) | M06 async |
| TS generics / structural types | Protocols + generics | templates + concepts | M11 |

The Full-Stack course *uses* JS every week. Point out when a JS/TS lesson is exactly what the spine needs next.
