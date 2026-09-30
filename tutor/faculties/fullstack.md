# 🌐 Athena's Full-Stack faculty: Full-Stack Engineering Mastery (the spine)

**Course key:** `fullstack` · **Folder:** `C:\Users\QweQu Antwi\Desktop\Full-Stack-Engineering-Mastery`
**Role in the four:** **the spine.** How real systems are engineered, over 36 months: computing fundamentals, the
internet, HTML, CSS, JS, Git, accessibility (Year 1); then backend, databases, auth and testing (Year 2); then
production, cloud, DevOps, architecture and AI (Year 3). The language courses feed it (see
`Python-Engineering-Mastery\SYNC.md`). ATLAS gives the spine a small priority.

## Layout

```text
YearN.*/MNN.<Month>/WN.<Week>/DN.<Day>/
    README.md          1 Concept · 2 Why it exists · 3 Internal mechanics · 4 Simple examples · 5 Real-world
                       6 Coding exercises · 7 Debugging · 8 Architecture question · 9 Short assessment · 10 Reflection
    Examples/*.js      run live (e.g. cache-demo.js, my-machine.js)
    Exercises/NN_Name/ main.js · main.test.js · README.md · solution/ (never show)
    Debugging/NN_Name/
    MY-NOTES.md        sections: Architecture question · Quiz · Reflection (theirs to write)
WN.<Week>/README.md    each WEEK is a gate unit (a review + gate at the end of the week)
DN.Project-*           project days: coach the design first, then the code
```

A "lesson" here is a **day**. Keep the day's micro-concepts tight (6–10), because the week is the real unit. Tie each
day to the week's story ("Day 2 is *where* data lives; Day 4 is *who* runs the programs").

## Running things

```powershell
node --test                  # in an exercise folder
node Examples\my-machine.js
```

Later months add browsers, servers and databases: use `curl`, the browser DevTools (Network, Elements,
Performance, Lighthouse), `git log --graph`, and `docker` as the months introduce them.

## Diagrams this course lives on

- **Layers:** app ▸ runtime ▸ OS ▸ hardware · HTML ▸ CSS ▸ JS · OSI/TCP-IP.
- **Request journey:** `browser ──DNS──► IP ──TCP/TLS──► server ──► DB ──► response ──► render`.
- **Latency ladder** (D2): an ASCII log-scale bar chart, from L1 cache to the network. Scale it to human time ("if L1 = 1 s…").
- **Architecture boxes:** clients, API, services, DB, cache and queue. The learner already draws these well (see the D1 notes).
- **Sequence diagrams** for protocols (HTTP, auth flows) and **state machines** for UI.

## Classic misconceptions to probe

- RAM vs storage vs cache: "more RAM makes everything faster".
- Binary/hex (D3): place value, why 0xFF = 255, bytes vs bits (formatBytes: 1000 vs 1024).
- Process vs thread vs program (D4).
- Compiled vs interpreted as a *spectrum* (D5 converges with C++ 01, JS Phase 1 and Python M001).
- HTTP is stateless, cookies/sessions add state. Frontend vs backend responsibilities (security lives on the server).
- CSS: the cascade, specificity, the box model, and normal flow before flex/grid.
- Git: commits are snapshots, not diffs, and a branch is just a pointer.

## Bridges

This course is where the other three *meet*. Its convergence exercises (the SYNC.md table) are big "aha" moments:
when a day matches a checkpoint (M01: "compiled vs JIT vs bytecode interpreter" with `node --print-bytecode`,
`python -m dis` and `g++ -S` side by side), mention it and offer the side-by-side live.
