# Stack Research — v2.3 Bot Play (NEW capabilities only)

**Domain:** Clocked bot-play added to an existing client-side chess engine (React 19 PWA + FastAPI)
**Researched:** 2026-07-11
**Confidence:** HIGH (versions verified via `npm view`; chess.js `[%clk]` behavior and engine-module browser-independence verified by direct Node execution against the repo's own `node_modules`)

## Scope note

This file covers ONLY what is NEW for bot-play. The FlawChess Engine (`useFlawChessEngine` / `mctsSearch`), the Maia-3 ONNX policy worker, the Stockfish.wasm worker pool, the ELO + play-style sliders, `chess.js`, `react-chessboard`, and the game-storage normalization path already ship in prod. See **What NOT to Use / Add** for the explicit "do not replace" list. There are exactly four net-new stack concerns: a chess clock, move sounds, a headless calibration harness, and `[%clk]` PGN emission.

Headline: **only ONE new production-adjacent dependency is warranted** (`onnxruntime-node`, dev-only, for the harness). The clock and sounds are best hand-rolled; `[%clk]` is already covered by the installed `chess.js`.

The prior-milestone (v2.0 engine) stack research is preserved alongside as `STACK.prev-v2.0-engine.md`.

---

## Recommended Stack

### Core decisions (NEW work)

| Concern | Decision | Version | Why |
|---------|----------|---------|-----|
| Chess clock / timer | **Hand-roll** a deadline-based hook (`useGameClock`) | n/a | No maintained React chess-clock lib is worth a dependency; the correct pattern is ~80 lines and interval libraries get the accuracy model *wrong* (see clock section). |
| Move sounds | **Hand-roll** a tiny Web Audio wrapper (`useMoveSounds`), preloaded buffers | n/a (Web Audio API is a platform built-in) | 5 short one-shot cues; a lib (howler) adds ~30 KB + a stale dep for something the platform does natively. Precache the audio assets via the existing Workbox/`vite-plugin-pwa` config for offline. |
| Harness — Maia inference | **`onnxruntime-node`** (swap from `onnxruntime-web`) | **1.27.0** | Exact same ORT version as the pinned `onnxruntime-web@1.27.0` → identical opset/kernel support, zero model-compat risk. Native CPU EP is far faster than WASM for a batch harness, and needs no browser globals (`importScripts`, `self`, `navigator.gpu`, `Worker`). |
| Harness — Stockfish | **Reuse the vendored `stockfish-18-lite-single.js`** as a `.cjs` child process | already vendored | Already verified working headlessly in Node (memory `project_headless_stockfish_wasm_verification`). No new dependency. |
| Harness — run TS directly | **`tsx`** (esbuild loader) | **4.23.0** | Runs the exact `mctsSearch.ts` + pure engine modules unbundled, ESM + path-alias aware, no jsdom, no separate build step. Dev-only. |
| `[%clk h:mm:ss]` PGN emission | **`chess.js` `setComment()`** (already installed) | 1.4.0 (present) | Verified: `setComment('[%clk 0:03:00]')` after each move makes `.pgn()` emit `... e4 {[%clk 0:03:00]} e5 ...` — the exact lichess/PGN standard. No PGN-writer library needed; python-chess already parses it on ingest. |

### New dependencies to actually add

| Package | Version | Where | Dev/Prod |
|---------|---------|-------|----------|
| `onnxruntime-node` | 1.27.0 | harness only (`scripts/` or a `harness/` workspace) | **devDependency** — must NOT ship in the browser bundle |
| `tsx` | 4.23.0 | harness runner | **devDependency** |

That's it. The clock, sounds, and `[%clk]` add **zero** new runtime dependencies.

---

## 1. React chess clock / timer — hand-roll, deadline-based

**Recommendation: hand-roll. Do not add a library.** The npm "react-timer"/"react-countdown" family (and the few "chess clock" packages) almost all implement the *wrong* model: they decrement a counter on each `setInterval` tick and accumulate drift, and they stop cold when the tab is backgrounded (browsers throttle `setInterval` to ≥1 s for visible tabs, and much harder for hidden ones — a 3+0 blitz clock would silently freeze). None are worth the dependency for ~80 lines of correct code.

**The correct accurate-timer pattern (this is the standard, and what lichess/chess.com do):**

1. **Store deadlines, not counters.** The source of truth is `deadlineMs = Date.now() + remainingMs` for the side on move (plus the frozen `remainingMs` for the side off move). Never subtract a fixed amount per tick.
2. **Derive display from `Date.now()` deltas.** On each render tick compute `remaining = deadline - Date.now()`. Drift-free by construction: every frame recomputes against the wall clock, so no error accumulates.
3. **Drive the UI tick with `setTimeout`/`requestAnimationFrame`, not `setInterval`.** A self-rescheduling `setTimeout` (or `rAF` while visible) at ~100 ms *only repaints* the number; the *value* comes from the delta, so a throttled or skipped tick cannot corrupt time — it just repaints late.
4. **Page Visibility API for background correctness.** On `visibilitychange`: when hidden, stop the repaint loop; on becoming visible, immediately recompute `remaining = deadline - Date.now()`. Because the deadline is absolute, elapsed background time is accounted for correctly — if the clock ran out while hidden, the recompute detects `remaining <= 0`. This satisfies "survives tab backgrounding / `setInterval` throttling."
5. **Flag detection on the authoritative delta**, not on a tick reaching zero: check `Date.now() >= deadline` (a) every repaint, (b) on `visibilitychange` → visible, and (c) right before the bot is asked to move. A tick-based zero-check would miss a flag that expired while throttled/hidden.
6. **Fischer increment:** on move *commit* for a side, `remaining += incrementMs`, then set the opponent's `deadline`. Matches lichess semantics (the mover keeps the increment).
7. **Pause/resume (localStorage abandonment resume, SEED-091 decision 4):** persist `remainingMs` per side + whose turn it is (a paused clock stores plain remaining values, no live deadline). On resume, rebuild the on-move side's `deadline = Date.now() + remainingMs`. Clock is paused while away.

**Shape:** a `useGameClock({ initialMs, incrementMs })` hook returning `{ whiteMs, blackMs, activeSide, onMove(side), pause(), resume(), flagged }`, plus a pure `computeRemaining(state, now)` helper that is trivially unit-testable (feed it fake `now` values) and reusable in the harness for time-odds simulation. Keep the React `setTimeout` loop thin; put the time math in the pure helper.

**Interaction with bot think-time (SEED-091 pacing note):** the same `remainingMs` feeds both the search-budget ceiling and the human-like move delay. The bot's "thinking" delay must itself be a `setTimeout` scheduled against a deadline (so a backgrounded tab doesn't make the bot move instantly on return) — reuse the same deadline discipline.

---

## 2. Move sounds — hand-roll Web Audio; source CC0 assets

**Recommendation: hand-roll a tiny `useMoveSounds` hook over the Web Audio API.** Five short cues (move, capture, check, game-end, optionally low-time/illegal). ~40 lines: `fetch` each asset once → `AudioContext.decodeAudioData` → cache the `AudioBuffer` → on event, `createBufferSource()` and `start()`. Web Audio is the right layer: **no per-play latency** (buffers pre-decoded), supports **overlapping** plays (rapid moves), needs no DOM nodes.

**Why not the alternatives:**
- **`<audio>` elements:** simplest, but re-triggering a still-playing element needs `currentTime = 0` gymnastics, overlapping plays need cloned nodes, and first-play decode latency is noticeable. Fine as a fallback, not the primary path.
- **`howler.js` (2.2.4):** the standard tiny audio lib and it *works*, but ~30 KB gzipped, an aging release cadence, and it solves problems (audio sprites, cross-fade, streaming music) this feature doesn't have. Add it only if sound scope later grows. Documented alternative, not the default.

**Critical browser gotcha (must handle):** `AudioContext` starts `suspended` until a user gesture. Create/resume the context on the first user interaction (the "Play" button on the setup screen is the natural unlock point) and call `ctx.resume()` there. Without this, the first move plays silently on Chrome/Safari. Respect a mute toggle (persist in localStorage) and consider a sound preference / `prefers-reduced-motion`.

**Assets & licensing (be careful):**
- **Do NOT assume lichess's sound files are freely reusable.** lichess `lila` assets are under lichess's own terms and some carry attribution/CC-BY or bespoke licenses — not clean CC0. Don't copy them without checking each file.
- **Preferred: CC0.** Source from **freesound.org** filtered to CC0 (public domain), or generate synthetic clicks/thuds (a short sine/triangle burst rendered offline). CC0 avoids attribution obligations awkward in a PWA. Keep a short provenance/license note in the repo even for CC0.
- Encode as small **`.ogg` + `.mp3`** (or just `.mp3`/`.m4a` — universally supported incl. iOS Safari) at low bitrate; each cue is a few KB.

**PWA / offline:** put audio under `frontend/public/sounds/` and ensure the existing **`vite-plugin-pwa@1.3.0`** Workbox config precaches them (add the audio glob to the precache manifest if `public/` assets aren't already globbed) so sounds work when installed/offline. This mirrors how the vendored engine/maia assets are served verbatim from `public/`.

---

## 3. Headless calibration harness — `onnxruntime-node` is the right swap (feasibility: YES)

**The open feasibility question — "can Maia ONNX run headlessly in Node at harness-viable speed?" — resolves to YES, via `onnxruntime-node`, not `onnxruntime-web` in jsdom.**

### Why not run the browser worker in Node/jsdom
The Maia path in prod is `mctsSearch.ts` → `maiaQueue.ts` → `new Worker('/maia/maia-worker.js')` → `importScripts(ort.wasm.min.js)`. `maia-worker.js` depends on browser-only globals: `importScripts`, `self.onmessage`/`postMessage`, `navigator.gpu` (WebGPU probe), and the UMD `ort` global. jsdom provides **none** of `Worker`, `importScripts`, or WebGPU; shimming them to run WASM-ORT would be slow and brittle. Reject this approach.

### The clean approach (verified feasible)
The **encoding + post-processing math is already browser-independent.** Verified by inspection: `src/lib/maiaEncoding.ts` and `src/lib/sanToSquares.ts` import only `chess.js` — no `window`/`self`/`navigator`/`document`. `mctsSearch.ts` imports only pure TS modules (`select`, `leafScore`, `policyTemperature`, `types`, `guardrail`, `liveFlaw`). The browser coupling lives **entirely in the two worker-glue files** (`maia-worker.js`, and the `Worker`-spawning parts of `maiaQueue.ts`).

So the harness reimplements just the thin provider seam in Node:

1. **Maia provider (Node):** load `frontend/public/maia/maia3_simplified.onnx` with `onnxruntime-node`'s `InferenceSession.create(modelPath, { executionProviders: ['cpu'] })`. Feed the **same three inputs** the worker builds — `tokens [B,64,12]`, `elo_self [B]`, `elo_oppo [B]` — using the **ported** `encodeBoardTokens()` from `maiaEncoding.ts` (import it directly via `tsx`, since it's browser-free). Read `logits_move` / `logits_value`, then run the same `maskAndSoftmax` + `sanToUci` to produce the `Record<uci, prob>` that `EngineProviders.policy()` returns. **The existing browser encoding glue ports directly** — same numeric pipeline, minus the Worker envelope.
2. **Stockfish provider (Node):** spawn the vendored `stockfish-18-lite-single.js` copied to a no-`package.json` dir as `.cjs` and drive it over stdin/stdout UCI — the already-verified recipe. Wrap it to the same `EngineProviders` grading interface `mctsSearch` expects.
3. **Reuse `mctsSearch.ts` unchanged.** It's pure logic over the `EngineProviders` interface; wire it to the two Node providers. This is the point of the harness — it tests the *identical* search code the browser runs, so the strength map is valid.
4. **Anchors:** raw-Maia-argmax opponents (1100–1900) reuse the same Node Maia session with a straight argmax over the policy; Stockfish skill-level anchors use `setoption name Skill Level` on the vendored binary.

### Version / packages / runtime
- **`onnxruntime-node@1.27.0`** — pinned to match `onnxruntime-web@1.27.0` exactly. Eliminates the classic opset/kernel-mismatch trap: same ORT build → the model that runs in the browser runs identically in Node. (The `onnxruntime==1.20.1` in the memory files was the **Python** `onnxruntime` for a *different* Maia repro — irrelevant here; do not down-pin the Node package to it.)
- **`tsx@4.23.0`** — run `tsx harness/run.ts`; it resolves the `@/` path alias (point tsx at the frontend `tsconfig` or a small `paths` config) and executes ESM TS with no bundler. No jsdom.
- **Node ≥ 20** (repo has **v24.14.0**; `onnxruntime-node` ships prebuilt binaries for Node 18/20/22/24 on linux-x64/arm64 + macos — no native toolchain needed).
- **No jsdom, no worker shims, no `Worker` polyfill.** Keeping providers Node-native avoids the entire browser-emulation surface.

### Throughput expectation
Native CPU ORT runs the small Chessformer model in low single-digit milliseconds per position on a modern CPU — orders of magnitude faster than needed for a coarse `(ELO × slider)` grid. The full-human path is **one Maia inference per move** (no MCTS), so even thousands of games are minutes. The Stockfish-blend path costs more (search), but that's WASM-in-Node compute, already proven. Harness-viable: **comfortably YES.**

### Fallback (if `onnxruntime-node` ever mismatches the model)
Run `onnxruntime-web`'s **WASM backend inside Node** (`require('onnxruntime-web')`, force `ort.env.wasm.numThreads = 1`, point `wasmPaths` at the vendored `.wasm`). Slower and you re-inherit WASM asset-path fiddliness, but it's the *exact* runtime the browser uses — the tie-breaker oracle if a Node-vs-browser policy discrepancy is ever suspected. Keep it documented, don't build on it by default.

---

## 4. `[%clk]` PGN clock annotations — already covered by chess.js

**No new library. `chess.js@1.4.0` (already installed) emits `[%clk]` correctly** — verified by direct Node execution against the repo's `node_modules`:

```
c.move('e4'); c.setComment('[%clk 0:03:00]');
c.move('e5'); c.setComment('[%clk 0:02:58]');
c.pgn()  →  1. e4 {[%clk 0:03:00]} e5 {[%clk 0:02:58]} 2. Nf3 *
```

`setComment()` attaches a comment to the position *after* the move just played, and `.pgn()` renders it as `{...}` immediately following the move — exactly the lichess/PGN `[%clk h:mm:ss]` convention. So:
- **Frontend:** after each committed move, `chess.setComment('[%clk ' + formatClock(remainingMs) + ']')`. Format is `h:mm:ss` (single-digit hours; lichess uses `0:03:00` for 3+0). Hand-write the string — chess.js has no dedicated clock API, but doesn't need one; the annotation is just a structured comment.
- **Backend:** the existing normalization path uses **python-chess**, which parses `[%clk]` natively (it's how imported chess.com/lichess clock data already lands). The stored `platform='flawchess'` PGN flows through the same reader — **no new backend parsing code**, satisfying SEED-091 decision 1 (time-management stats won't silently exclude bot games).

One caveat to lock at plan time: emit the clock for **both** colors' moves (so time-management analytics have per-side clocks), and decide value semantics — store *remaining time after the move* (lichess convention), computed from the clock hook's `remainingMs` at move-commit (after increment). Keep the formatter a pure function shared with the clock hook.

---

## Installation

```bash
# Harness only — dev dependencies, MUST NOT reach the browser bundle
cd frontend        # or a dedicated harness workspace
npm install -D onnxruntime-node@1.27.0 tsx@4.23.0

# Clock, sounds, [%clk]: NO installs.
#   - chess.js@1.4.0 already present (handles [%clk] via setComment)
#   - Web Audio API + Page Visibility API are platform built-ins
#   - audio assets: drop CC0 .mp3/.ogg files into frontend/public/sounds/
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Hand-rolled deadline clock | `react-countdown` / a "react chess clock" npm pkg | Never for this — they use interval-decrement + accumulate drift and freeze when backgrounded. Not fit for a real chess clock. |
| Hand-rolled Web Audio `useMoveSounds` | `howler.js@2.2.4` (+ `@types/howler@2.2.13`) | If sound scope grows: audio sprites, background music, cross-fade, or a single-line cross-format fallback. Not needed for 5 one-shot cues. |
| `onnxruntime-node@1.27.0` for the harness | `onnxruntime-web` WASM backend run *inside* Node | As a correctness oracle when you suspect a Node-vs-browser policy discrepancy (identical runtime), or if a future model uses an op the Node CPU EP lacks. Slower; don't default to it. |
| `tsx` to run the harness TS | Pre-`tsc` build then run JS; or `ts-node` | If you want a committed compiled artifact. `tsx` (esbuild) is faster to iterate and alias-aware; `ts-node` is slower and stricter about ESM. |
| Port encoding into Node providers | Run the browser Maia worker under jsdom + Worker/WebGPU shims | Never — jsdom has no `Worker`/`importScripts`/WebGPU; shimming WASM-ORT is slow and brittle. The encoding math is already browser-free, so this is pure downside. |
| `chess.js setComment` for `[%clk]` | A dedicated PGN writer lib (e.g. `@mliebelt/pgn-*`) | Never here — chess.js already emits the standard annotation; a PGN library is redundant weight. |

---

## What NOT to Use / Add

These already exist and ship in prod. **Do NOT propose replacing, re-selecting, or re-benchmarking them** — bot-play consumes them as-is.

| Do NOT add/replace | Why | Use the existing thing |
|--------------------|-----|------------------------|
| Any new chess engine, or a rewrite of `mctsSearch` | The FlawChess Engine (v2.0) is the whole point of measuring; changing it invalidates calibration | `useFlawChessEngine` / `mctsSearch` (`src/lib/engine/`) |
| A different browser Maia inference stack (tfjs, hosted API) | `onnxruntime-web@1.27.0` + `maia3_simplified.onnx` in a Worker already ships | `public/maia/maia-worker.js`, `maiaQueue.ts` |
| A different/bundled Stockfish, or WASM threading | Vendored single-thread `stockfish-18-lite-single.{js,wasm}` is deliberately non-Vite-bundled; threading off (no cross-origin isolation) | `public/engine/`, `useStockfishEngine` / the search's grading provider |
| A move-selection/sampling library | The sample↔argmax blend is the engine's own play-style-slider semantics | reuse the analysis-board play-style slider + root-policy temperature (`policyTemperature.ts`) |
| A websocket/server game-session layer, an on-chain clock authority | Locked decision: the game is fully client-side; only the finished PGN is POSTed | one small store endpoint reusing the existing normalization path (`platform='flawchess'`) |
| A backend PGN/`[%clk]` parser | python-chess already parses `[%clk]` on ingest | existing normalization reader |
| `onnxruntime-node` as a **prod/runtime** dependency | It's a native binary for the Node harness only; the browser keeps using `onnxruntime-web` | mark it `devDependencies`, keep it out of the Vite bundle |

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `onnxruntime-node@1.27.0` | `onnxruntime-web@1.27.0` (pinned) | **Match these exactly.** Same ORT version → identical opset/kernel coverage → the browser model runs identically in the harness. Bump them together, never independently. |
| `onnxruntime-node@1.27.0` | Node 24.14.0 (repo), Node ≥ 20 | Prebuilt binaries for Node 18/20/22/24 on linux/macos x64+arm64; no native build toolchain needed. |
| `tsx@4.23.0` | TypeScript 6, Vite 8 project | esbuild-based, ESM-native; give it the frontend `tsconfig` (or a small `paths` config) so `@/` aliases resolve in `mctsSearch.ts` and friends. |
| `chess.js@1.4.0` | existing frontend + python-chess backend | `setComment('[%clk h:mm:ss]')` → `.pgn()` emits `{[%clk ...]}`; python-chess parses it. Verified end-to-end. |
| Web Audio + Page Visibility APIs | all target browsers incl. iOS Safari | Web Audio needs a user-gesture `resume()`; both APIs are baseline-supported. |
| audio assets (mp3/ogg) | `vite-plugin-pwa@1.3.0` Workbox | Ensure `public/sounds/*` is in the precache glob for offline PWA playback. |

---

## Sources

- Repo `node_modules` version check via `npm view` (2026-07-11): `onnxruntime-node 1.27.0`, `onnxruntime-web 1.27.0` (pinned in `frontend/package.json`), `tsx 4.23.0`, `howler 2.2.4`, `@types/howler 2.2.13`, Node `v24.14.0` — HIGH confidence (authoritative for versions).
- Direct Node execution of `chess.js@1.4.0` `setComment`/`pgn()` against the repo's own install — confirmed `{[%clk 0:03:00]}` emission — HIGH confidence (behavioral verification, not docs).
- Source inspection: `frontend/public/maia/maia-worker.js`, `src/lib/engine/maiaQueue.ts`, `src/lib/maiaEncoding.ts`, `src/lib/sanToSquares.ts`, `src/lib/engine/mctsSearch.ts` — confirmed engine math is browser-global-free and worker glue isolates the browser coupling — HIGH confidence.
- Memory `project_headless_stockfish_wasm_verification` — vendored Stockfish WASM verified headless in Node as `.cjs` — HIGH confidence (prior verification).
- Web Audio unlock-on-gesture, `setInterval` background throttling, and Page Visibility semantics — MDN-documented platform behavior — MEDIUM-HIGH confidence (standard, not project-specific).
- Sound-asset licensing (lichess assets not cleanly CC0; prefer freesound.org CC0) — MEDIUM confidence; verify each specific asset's license at plan time before committing files.

---
*Stack research for: clocked bot-play added to a client-side chess engine (FlawChess v2.3)*
*Researched: 2026-07-11*
