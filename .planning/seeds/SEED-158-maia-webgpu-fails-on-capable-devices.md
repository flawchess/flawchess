---
id: SEED-158
status: RESOLVED for iOS, SHIPPED 2026-09-07 (squash of branch seed-158-ios-maia-bisect to main; released the same evening). iOS/iPadOS runs Maia on the CPU wasm backend on the current ORT 1.27.0 build, thread count left to chooseWasmThreadCount() (1 AND 2 both measured surviving real /analysis sessions on the reference iPhone); every WebGPU shape is killed by WebKit. Bisect tooling stripped, ios-webkit gate/copy removed, page-kill sentinel kept. Reopen ONLY on an iOS `maia_failure:page-killed` Sentry event with `backend:wasm`. Desktop WebGPU per-GPU failures remain the original seed question (separate)
planted: 2026-08-29
updated: 2026-09-07 late evening (cleanup done, shipped; see "Shipped" at the top of the body)
planted_during: Sentry triage of the 2026-08-29 18:54 UTC iPad OOM cascade
  (FLAWCHESS-9V regression + new FLAWCHESS-A2/A3), same session as quick task
  260829-tku (oom terminal variant in EngineReadyGate)
re-scoped: 2026-09-06, after the FLAWCHESS-9V root cause was measured on the
  reporter's iPhone 14 Pro and fixed by quick task 260906-p54 (ORT wasm memory
  ceiling 4 GB -> 1 GB). The OOM question below is CLOSED; what remains is why
  WebGPU fails on WebGPU-capable devices and silently costs every user the fast path.
trigger_when: an iOS `maia_failure:page-killed` event appears in Sentry with `backend:wasm`, or when desktop WebGPU per-GPU failures are picked up
scope: investigation first (collect the raw webgpu-unavailable messages per device
  class via the console trace shipped in d215f8d8a), then a targeted fix in
  maia-worker.js initSession / ortRuntimeSource.ts (adapter probe, required
  features, session options, or model graph ops unsupported by the ORT WebGPU EP).
  NOT the OOM (fixed) and NOT copy/UX (shipped in 260829-tku).
supersedes: nothing
---

# SEED-158: Maia WebGPU fails on capable devices, everyone silently runs the wasm fallback

## Shipped 2026-09-07 late evening

The cleanup below was done in one pass and squash-merged to `main`: bisect runner + its test + `main.tsx`
call deleted; `devEngineSwitches.ts` deleted ENTIRELY (every switch, the inert Stockfish worker, the corner
badge) per Adrian's "remove all the things we built for debugging"; `/maia-diag.html` deleted; `maiaWorkerHost.ts`
iOS branch is `spawnOnIosWebKit()` = `fetchWasmOnlyOrtRuntime()` + `constructWorker(…, 'wasm', …)` with NO
single-thread pin (WR-01's post-timeout retry still pins); `probeOrtBackendOnce` is internal again;
`'ios-webkit'` reason, `gateOffIosWebKit()`, the `unsupported-ios` gate copy and the notice copy are gone
(`EngineUnsupportedReason` is `'no-wasm-simd'` only); the page-kill sentinel stays (minus the dev-run
`activeMaiaSessionDispatches` and `previousMaiaPageKillSummary` readers; it is the prod reopen signal, not
a debug aid); `ortVersion` stays on the `ready` message (console line + kill record context, cheap).
NOT run: the seed's standing "one more phone session from the squashed main" rule (no phone in the loop
at ship time; the exact shape — wasm, 2 threads, 1.27.0 — was measured by hand on the branch the same
evening). The reopen signal is Sentry `maia_failure:page-killed` with `backend:wasm` and `ios:true`.

## Handoff for the cleanup + ship session (written 2026-09-07 late evening, DONE — kept for the inventory)

**Result.** iOS Maia works. The lever was the BACKEND: WebKit kills the page on every WebGPU shape
(ORT 1.27.0 and 1.23.0, 1 or 2 threads, idle or stepping), while the CPU wasm backend survives full
/analysis sessions by hand on the reference iPhone 14 Pro (iOS 26.6.1) with Stockfish and the FlawChess
Engine on, in every shape tried the same evening:

| ORT | backend | wasm threads | result |
|---|---|---|---|
| 1.23.0 | webgpu | 1 | KILLED x3 (FLAWCHESS-AW 16:36-17:01 UTC, `ortVersion` in context) and x3 more 19:51-19:58 |
| 1.23.0 | wasm | 1 | survives |
| 1.27.0 | wasm | 1 | survives (`?dev-maia-ort=1.27`) |
| 1.27.0 | wasm | 2 (ORT default on 4 cores) | survives (`?dev-maia-threads=auto`) |

Neither the ORT version nor page footprint mattered (maiachess.com's page holds a 160 MB Stockfish heap
plus the 79 MB big NNUE and survives). The 1.23.0 vendoring was added and removed the same evening.
The 2026-09-06 "1.27 wasm dies at one thread" reading predates the 1 GB reservation fix and is superseded.
Bisect-runner verdicts were unreliable (it reported every cell killed while the same shape survived by hand).

**What the working tree on `seed-158-ios-maia-bisect` contains (uncommitted).** `spawn()` in
`maiaWorkerHost.ts` routes iOS/iPadOS to `spawnOnIosWebKit()`: `fetchWasmOnlyOrtRuntime()` then
`constructWorker(source, 'wasm', buffer, IOS_FORCE_SINGLE_THREAD && !isDevMaiaThreadsAuto())`. No WebGPU
probe, no asyncify download on iOS. The `ready` message carries `ortVersion` (console line, dev badge,
kill-sentinel record). CHANGELOG has the Unreleased bullet. Memory file
`project_maia_ios_two_failure_populations` is current.

**Cleanup inventory (remove unless marked keep):**

1. `frontend/src/lib/engine/devBisectRunner.ts` + `__tests__/devBisectRunner.test.ts` + its call in
   `main.tsx` (`runDevBisectRunner`) — remove.
2. `frontend/src/lib/engine/devEngineSwitches.ts` — remove the switches `ios-gate`, `maia-runtime`
   (Suspect A), `maia-ladder` (Suspect B), `maia-backend`, `maia-threads`, and their readers in
   `maiaWorkerHost.ts` (`isDevIosGateBypassed` gates `captureDevPhoneRunProgress`, the two dev-run Sentry
   markers "ready (dev phone run)" / "still alive after the probe interval" — remove both),
   `useMaiaEngine.ts` (`isDevMaiaSinglePassLadder` branch), and `ortRuntimeSource`/host
   (`isDevMaiaRuntimeWorkerFetched` branch in `spawnFromRuntime`). Decide on `stockfish=off` and the
   corner badge (`showDevEngineBadge`): both are generic phone-UAT aids; keeping the module with just those
   two is reasonable, deleting it entirely is also fine.
3. Single-thread pin — DROP it: delete `IOS_FORCE_SINGLE_THREAD` and pass `forceSingleThread = false` on
   iOS so `chooseWasmThreadCount()` applies (2 on the reference phone, measured surviving). Keep the WR-01
   post-timeout single-thread retry as is.
4. `ios-webkit` unsupported reason — now reachable only via the WebGPU dev switch's iOS terminal in
   `respawnPinnedToWasm`. With the switch gone, remove the terminal branch, `gateOffIosWebKit()`, the
   `'ios-webkit'` member of the unsupported-reason union in `engineAssetProgress.ts`, the `unsupported-ios`
   copy in `EngineReadyGate.tsx`, the `unsupported_reason` tag handling that names it, and their tests.
   `isIosWebKit()` itself STAYS (it selects the wasm spawn); trim its header to the final finding.
5. `maiaPageKillSentinel.ts` — KEEP (prod-useful: a silent kill on any platform reports on the next load).
   Remove only `previousMaiaPageKillSummary()`'s badge use if the badge goes.
6. `frontend/public/maia-diag.html` — dev tool, keep or delete at will (it produced three false "safe"
   verdicts; if kept, add that caveat to its header).
7. `frontend/public/maia/README.md` "iOS/iPadOS: wasm backend only" section — keep, adjust the thread
   sentence after step 3. `iosWebKit.ts` header — rewrite to the final finding only.
8. Tests to rewrite after 1-4: `maiaWorkerHost.test.ts` iOS block (assert: iPhone spawns `backend:'wasm'`,
   no probe, no `ensureOrtRuntime`; iPad desktop-mode UA same; real Mac spawns normally; no-SIMD iOS still
   `no-wasm-simd`), `EngineReadyGate.test.tsx` ios cases, `engineAssetProgress.test.ts` if it names the
   reason.

**Ship steps.** Full pre-merge gate (CLAUDE.md), squash-merge to `main`, then the release flow
(`/deploy`). Before the release PR: one more real /analysis session on the phone from the deployed preview
or dev build of the squashed `main` (the seed's standing rule), and check Sentry for `maia_failure:page-killed`
with `backend:wasm` afterwards — that is the only signal that would reopen this.


## Status of the original question (CLOSED 2026-09-06)

The 2026-08-29 seed asked "why was only wasm attempted on a WebGPU-capable iPad?".
Measured on Adrian's iPhone 14 Pro (iOS 26.6.1, Safari; Sentry shows "iOS 18.7" because
Apple froze the UA token) with a throwaway `WebAssembly.Memory` diag page:

- WebKit lets one page hold only **three** large wasm memory reservations; a fourth
  `new WebAssembly.Memory({initial:256, maximum:65536, shared:true})` throws
  `RangeError: Out of memory`. Six 1 GB shared memories fit at once, so it is an address-space
  cap, not RAM (the phone has 6 GB and it never mattered).
- Both vendored ORT binaries import a *shared* memory with max 65536 pages, so the glue
  reserves 4 GB even at `numThreads = 1`. Two Stockfish pool workers cost one slot each.
- On iOS 26 the device DOES have WebGPU with `shader-f16` (probe confirmed), so the host
  tries the WebGPU worker first (4 GB), it fails, and the wasm-pinned respawn asks for a
  fourth 4 GB while the first worker is still dying. That fourth reservation is the
  `no available backend found. ERR: [wasm] RangeError: Out of memory` in FLAWCHESS-9V.
  Hypothesis 3 of the original seed was the right shape: WebGPU *was* tried; only the wasm
  error survives because the respawn is a separate worker.
- Fix shipped as quick task 260906-p54: `maximum:65536` -> `maximum:16384` in both vendored
  glue files plus an `ENGINE_ASSET_CACHE_VERSION` bump. Verified on the phone: ORT at a 1 GB
  ceiling initializes the real model while one Stockfish worker and a leftover 4 GB memory
  are alive. Memory: `project_ios_wasm_reservation_budget`.

## The question that remains

The WebGPU path fails and falls back to wasm on devices that should run it:

- Adrian's iPhone 14 Pro, iOS 26.6.1 Safari (adapter present, `shader-f16: true`,
  `maxBufferSize` 1 GiB). The failure happens inside the worker's WebGPU try block
  (session create, warmup, or lazy shader compile) and surfaces only as `webgpu-unavailable`.
- Adrian's Linux dev box, both Brave and Chrome (per Adrian 2026-09-06; the claude-in-chrome
  Chrome on the same box reports no WebGPU adapter at all, see
  `project_browser_uat_techniques`, so this may be a Linux Chromium GPU-allowlist issue
  rather than an ORT one).
- A Windows 11 notebook (per Adrian 2026-09-06). This one matters most: Windows Chromium is
  the mainstream WebGPU platform, so a failure there suggests the fault is on our side.

Sentry has only 4 events in 30 days with `backend:webgpu` (FLAWCHESS-9S iOS inference errors,
FLAWCHESS-9D Android), so WebGPU rarely gets far enough to fail *after* becoming ready. The
fallback itself is not captured as an event, only as a breadcrumb plus (since d215f8d8a) a
`console.info('[maia-worker] ...')` line carrying the raw ORT message.

## Plan when triggered

1. **Collect the raw messages first.** On each of the three device classes open `/analysis`,
   copy the `[maia-worker]` fallback line from the console. Consider promoting the
   breadcrumb to a sampled Sentry event (tag `maia_failure:webgpu-fallback`, raw message in
   `contexts.maia.rawMessage`, adapter `info`/`features` in context) so the population is
   visible without asking users; keep grouping stable per the Sentry rules in CLAUDE.md.
2. **Classify.** Likely buckets: (a) `requestAdapter()` null (Linux GPU allowlist, no fix on
   our side, just make the probe skip WebGPU cheaply without loading the 24 MB asyncify
   bundle); (b) `requestDevice` refused a required feature or limit (we require `shader-f16`
   in `ortRuntimeSource.ts`; check whether the model actually needs it or whether ORT's
   WebGPU EP can run fp32 without it); (c) an op in `maia3_simplified.onnx` unsupported by
   the ORT 1.29 WebGPU EP (session create error naming the op); (d) lazy shader compile /
   warmup failure (the FLAWCHESS-9D pattern), which the warmup catch already converts to
   fallback.
3. **Fix per bucket.** (b) and (c) are ours. For (c), check the ORT release notes / op
   support matrix for the WebGPU EP at the pinned version, and consider graph-level
   adjustments in the model export or a targeted ORT bump. For (d), capture the shader
   error text.
4. **Measure the win.** With WebGPU working, re-run the Phase 219 latency measurement
   (219-MEASUREMENTS.md) on the desktop box; the wasm 4-thread ceiling is the current floor.

## iOS is worse than "no WebGPU": the wasm path kills the page (measured 2026-09-06)

With the 1 GB ceiling in place Maia *starts* on the iPhone 14 Pro (iOS 26.6.1) and then Safari
kills the WebContent process within 10 to 20 s of stepping through moves on `/analysis`
("A problem repeatedly occurred" after the automatic reload dies too). Bisect on the device,
each step served live from the dev server:

- 1 wasm thread instead of 2: still dies.
- Stockfish pool 1 instead of 2: still dies.
- Wasm heap logged after every inference: flat at 110 MB across both page lifetimes, so it is
  not heap growth and not the SEED-113 tensor leak (disposal is in place).
- `session.run` bypassed (model loaded, neutral fake outputs returned): survives indefinitely.
- No `com.apple.WebKit.WebContent-*.ips` and no `JetsamEvent-*` in Settings > Analytics Data
  for the kills, which matches WebKit's own silent per-page memory-limit termination, not a
  kernel jetsam and not a JIT crash.

So executing ORT's wasm kernels is fatal on iOS Safari while the wasm heap stays small. Prime
suspect: JavaScriptCore's optimizing wasm tier (OMG/B3) compiling ORT's very large SIMD
functions in the background with a footprint far above the heap; the ~10 s delay after
`ready` fits tier-up timing. Not proven (no Mac for Web Inspector's memory timeline), and not
controllable from the page.

Consequence for the release carrying quick task 260906-p54: before the cap, iOS users got a
graceful `oom` terminal state; after it they get a dead analysis tab.

**Hotfix shipped 2026-09-06 (`hotfix/ios-maia-gate`):** Maia is gated off ENTIRELY on
iOS/iPadOS WebKit at the D-13 choke point (`maiaWorkerHost.ts` `ensureSpawned()`, predicate in
`frontend/src/lib/engine/iosWebKit.ts`, iPadOS desktop-mode UA detected via `MacIntel` +
`maxTouchPoints > 1`). The store carries `unsupportedReason: 'ios-webkit'`, the bots gate shows
iOS-specific copy (`engine-gate-unsupported-ios`), Sentry's unsupported capture is tagged
`unsupported_reason`. Not a wasm-only ban: WebGPU also fails on the reference device, so trying
it first would only cost the 25.7 MB asyncify download before landing in the same state. When
WebGPU is made to work on iOS, NARROW the gate (allow the `'auto'` spawn when the probe picks
`webgpu`, and turn both `respawnPinnedToWasm` call sites into the `unsupported` terminal on
iOS instead of the fatal wasm respawn). Collecting the WebGPU failure reason on the phone is the
first step of the plan above.

Prior art from the ORT tracker: microsoft/onnxruntime#22776 ("Support iOS devices") and
#22086 (wasm load failures on iOS 17) are open with no maintainer guidance; WebGPU on iOS was
not an option there either at the time.

## Status 2026-09-07 evening: the gated population was invisible; now instrumented, bisect ready

Two facts found while picking the "Next steps" up (branch `seed-158-ios-maia-observability`):

1. **Prod produced ZERO Sentry events for the iOS gate on /analysis, and none on /bots for a returning
   device.** The only `unsupported` capture lived in `EngineReadyGate`'s D-17 effect. That modal is
   suppressed on /analysis whenever the status is `unsupported` (Analysis.tsx, G-213-34), and on both
   surfaces `engineGateRequired()` skips the modal entirely once the assets were seen once (a device whose
   model was already cached). So an iPhone on /analysis got an eternal pulsing Maia skeleton and an empty
   FlawChess card, with no event. Fix: the capture moved to the store choke point
   (`markEngineAssetsUnsupported` in `engineAssetProgress.ts`, once per page session, tags
   `source:engine-asset-store engine_failure:unsupported unsupported_reason:<ios-webkit|no-wasm-simd>`,
   contexts `engine_device` + `engine_page.pathname`). Same message string as before, so the dashboard
   question "how many iOS users hit the gate" is answerable from the first deploy onwards.
2. **A page kill is now visible on the next load.** `maiaPageKillSentinel.ts` writes a small localStorage
   record when the Maia worker reports `ready` (backend, threads, route, dispatch count, last batch), keeps
   it only while the page is visible, removes it on `pagehide`/hidden/worker teardown, and `main.tsx`
   reports a leftover record on startup: Sentry `Maia worker: page was killed while Maia was active`, tags
   `maia_failure:page-killed backend:<..> ios:<true|false>`, context `maia_page_kill` with the record plus
   `sessionAgeMs`/`sinceLastDispatchMs`. Unreachable in prod under the blanket gate (no `ready` on iOS), but
   it makes every phone run self-reporting and covers Android/desktop kills today.

Bisect switches (dev server only, `devEngineSwitches.ts`, all persist in localStorage until reset, badge
lists the active ones):

| Switch | Effect |
|---|---|
| `?dev-ios-gate=off` | bypass the blanket gate; spawn only when the fetch-free probe picks `webgpu`, else the `ios-webkit` terminal with no download (`spawnOnIosWebKit()` in the host, the shape a narrowing would ship) |
| `?dev-maia-runtime=worker` | Suspect A: no main-thread runtime bytes; worker resolves the `.wasm` via `wasmPaths` |
| `?dev-maia-ladder=single` | Suspect B: one 21-rung batch per position (no exact rung, no prefetch, no coarse/fill) |
| `?dev-stockfish=off` | inert Stockfish workers (unchanged) |

Note on Suspect A: the MODEL bytes never touch the main thread today (`fetchModelBuffer` in
`maia-worker.js` reads CacheStorage inside the worker), so the switch only removes the 25.7 MB runtime
transfer. If A survives, the fix is `buffer: null` on iOS, a two-line branch.

Phone protocol (reference iPhone, Safari, clear site data first, dev server via the tunnel), each cell is
one URL then stepping through a game on /analysis for ~60 s:

1. `/analysis?dev-ios-gate=off&dev-stockfish=off` (baseline, expected: killed; the reload shows the badge
   `KILLED last session: webgpu t=1 after N dispatches, last batch=B` and a Sentry event)
2. `...&dev-maia-runtime=worker` (Suspect A)
3. `...&dev-maia-runtime=main&dev-maia-ladder=single` (Suspect B)
4. `...&dev-maia-runtime=worker&dev-maia-ladder=single` (both)
5. Reset: `/analysis?dev-ios-gate=on&dev-stockfish=on&dev-maia-runtime=main&dev-maia-ladder=full`

Record the four cells here. The `dispatches`/`last batch` numbers in the kill report say how far each cell
got, which the old runs could not tell.

**Self-driving runner (2026-09-07, no data cable available so no Web Inspector from Linux):**
`frontend/src/lib/engine/devBisectRunner.ts` runs the four cells above on its own. One URL on the phone:
`/analysis?dev-bisect=start` (needs a signed-in or guest session; `?dev-bisect=stop` aborts and restores
every switch). Per cell it applies the switches, loads `/analysis?line=<Kasparov–Topalov 1999, 87 plies>`,
steps the board with synthetic ArrowLeft/ArrowRight keydowns every 1.5 s for 60 s, then reloads onto the
next cell. The outcome is decided on the NEXT load from the runner's own `running` phase (no `pagehide` =
silent death) plus the page-kill sentinel's record (`killed` vs `killed-before-ready`); `survived` means the
60 s elapsed. Each result goes to Sentry as `Maia iOS bisect: cell result` (tags `bisect_cell`,
`bisect_outcome`) and the top-left red badge shows progress and the final table. Safari's "A problem
repeatedly occurred" page needs one tap on reload per killed cell; the run resumes from localStorage. Keep
Safari in the foreground for the ~5 min (background throttling would stall the stepping). Verified on
desktop headless Chrome via CDP: all four cells run, the board walks the game, the reload chain and the
switches per cell are correct.

**Result 2026-09-07 (reference iPhone 14 Pro, iOS 26.6.1, Safari, dev server via the tunnel, runner):**

| Cell | ios-gate | stockfish | maia-runtime | maia-ladder | Outcome |
|---|---|---|---|---|---|
| baseline | off | off | main | full | **killed** (Maia was `ready`) |
| A-runtime-worker | off | off | worker | full | **killed** (Maia was `ready`) |
| B-ladder-single | off | off | main | single | **killed** (Maia was `ready`) |
| A+B | off | off | worker | single | **killed** (Maia was `ready`) |

**CONFOUNDED (found in the Sentry kill records the same evening, FLAWCHESS-AW/AV):** every kill record says
`numThreads: 2`. The iOS single-thread pin (`IOS_FORCE_SINGLE_THREAD`, a4a1f4f6d) was deleted together with
the WebGPU-only iOS branch in 28945b851, and the `?dev-ios-gate=off` bypass path (`spawnOnIosWebKit`) inherited
`spawn()`'s default `forceSingleThread = false`. So all four cells ran the 2-thread shape the diag page had
already shown to die, and the A/B verdicts above do NOT test the protocol's intended shape (WebGPU + 1 wasm
thread). Pin restored on the bypass path (constant back, with the history in its comment); re-run required.

What the four records DO say (all WebGPU, t=2, Stockfish inert, from the sentinel's `maia_page_kill` context):

| Cell | dispatches | last dispatch after `ready` | page lived after `ready` | last batch |
|---|---|---|---|---|
| baseline | 19 | 3.3 s | 9.1 s | 10 |
| A-runtime-worker | 18 | 4.8 s | 45.7 s | 10 |
| B-ladder-single | 8 | 3.5 s | 7.7 s | 1 |
| A+B | 10 | 3.5 s | 10.9 s | 21 |

Dispatching STOPS 3-5 s after `ready` in every cell (requests are serialised on `inFlight`, so a worker that
never answers freezes the queue), and the kill follows seconds to 40 s later. That is a hang-then-kill, not a
death mid-burst, and it matches ORT #26827's shape (WebKit pinned in `JSC::Wasm::parseAndCompileOMG`, 1 GB+
growth) better than "the ladder is too heavy". Two timestamps were added to tell a worker hang from a
main-thread freeze on the next run: the sentinel now records `results`/`lastResultAt` (worker's last sign of
life) and the runner writes a one-second main-thread heartbeat (`mainThreadAliveMs` in the cell result).

**Re-run 2026-09-07 13:45 UTC with the pin (`t=1` in every record): all four cells killed again.** Timeline per
cell, reconstructed from the sentinel record + the runner's main-thread heartbeat (all times after Maia `ready`):

| Cell | ready after cell start | dispatches / results | last dispatch | last result | main thread last tick | verdict |
|---|---|---|---|---|---|---|
| baseline | 11.2 s | 22 / 22 | +5.1 s | +5.3 s | +5.7 s | died at ~+5.7 s, queue EMPTY |
| A-runtime-worker | 7.5 s | 20 / 19 | +4.2 s | +4.2 s | +3.4 s (next tick due +4.4 s) | died at ~+4.3 s, 1 in flight |
| B-ladder-single | 2.1 s | 10 / 9 | +4.7 s | +3.8 s | +4.6 s | died at ~+4.7 s, 1 in flight |
| A+B | 6.9 s | 13 / 12 | +4.7 s | +3.8 s | +4.2 s | died at ~+4.7 s, 1 in flight |

The earlier "hang-then-kill" reading was wrong: the long `sessionAgeMs` values were Safari's "problem repeatedly
occurred" page waiting for a tap. The real shape is a SUDDEN kill 4.3-5.7 s after `ready` with everything
responsive up to the last second: the worker answered every request within ~1 s (22/22 in the baseline cell),
the main thread ticked to the end, no hang anywhere. Independent of wasm thread count (2 vs 1), the runtime
byte path, and the ladder shape. The diag page is cross-origin isolated exactly like the app (Vite/Caddy send
COOP/COEP on every response), so isolation is not the difference either.

What is consistent with "~5 s after ready regardless of workload": JavaScriptCore's optimising wasm tier
(OMG) compiling the 25.7 MB ORT module once inference makes it hot, on compiler threads, with a footprint far
above the heap (ORT #26827's 1 GB+ growth on WebKit 26). The diag page runs the SAME module and survives, so
the working hypothesis is "app baseline + tier-up spike > WebKit's per-page limit; diag baseline + the same
spike < limit". Not proven from the page. Discriminating next steps, cheapest first:

1. **Idle test (no code):** `/analysis?dev-ios-gate=off&dev-stockfish=off`, do NOT step, wait 60 s. Maia does one
   or two dispatches for the initial position. Dies → time/compile-driven after `ready`, workload irrelevant.
   Survives → inference-driven (per-run GPU/CPU growth), and a rate cap on iOS is worth one run.
2. **Kill reason from the device** (USB data cable + `pymobiledevice3` syslog): memory-limit vs GPU-process vs
   watchdog. Still the only way to read WebKit's own verdict.
3. **Shrink what gets tier-compiled:** a minimal onnxruntime-web build (WebGPU EP + only the CPU ops the Maia
   graph needs; `--include_ops_by_config` / `--minimal_build`) cuts the wasm from 25.7 MB to a few MB and the
   OMG footprint with it. Separate seed, sits next to the smaller-model-export idea.

**Idle test 2026-09-07 13:55-14:09 UTC (`?dev-ios-gate=off&dev-stockfish=off`, no stepping, branch
`seed-158-ios-maia-bisect` with `ready` / `alive after 60 s` Sentry markers, FLAWCHESS-B0/B1):** six sessions,
each with exactly 4 dispatches / 4 results inside the first 0.7 s after `ready` (the start-position ladder)
and NOTHING after. Four were killed while completely idle (upper bounds from the next load's `sessionAgeMs`:
≤15 s, ≤27 s, ≤6 s, ≤35 s after `ready`); two survived the 60 s probe. So the kill is **workload-independent
and intermittent**: it happens with zero inference in flight and no page activity, and it does not happen
every time. That closes the page-side bisect for good — no switch we own changes the outcome, and neither does
idleness. Everything still consistent: a transient spike after `ready` (JSC's OMG compile of the ORT module is
the named candidate) on top of the app's resting footprint, caught or missed by WebKit's periodic footprint
check. The diag page surviving is then "smaller resting footprint, same spike".

Next step that is a MEASUREMENT rather than a knob: give `/maia-diag.html` a ballast input (allocate N MB of
`ArrayBuffer`s before the WebGPU session) and find the N at which the idle diag page starts dying. That (a)
proves or kills the "resting footprint + spike" model, (b) measures the headroom the app would need to shed,
(c) is a self-contained WebKit bug repro. After that: the USB syslog for the kill reason, and the minimal ORT
build if the model holds.

### maiachess.com comparison + ORT 1.23.0 downgrade on iOS (2026-09-07, branch `seed-158-ios-maia-bisect`)

Adrian confirmed maiachess.com's analysis page runs Maia on the iPhone 14 Pro (and Android, Linux). Read from
their live bundle and the open-source `CSSLab/maia-platform-frontend`:

- Same model file (`/maia3/maia3_simplified.onnx`, 45,683,686 bytes), one batch of ALL 21 ratings per
  position on every device (the mobile page only hides the Moves-by-Rating chart; `useEngineAnalysis.ts`
  has no mobile branch). So a 21-rung ladder per position is NOT too heavy for the phone.
- onnxruntime-web **1.23.0**, plain CPU wasm backend (`ort.wasm.min.js`, no WebGPU), classic worker with
  `importScripts`, ORT's default thread count on a cross-origin-isolated page (COOP/COEP are set), STOCK
  glue with the 4 GB reservation, model cached in IndexedDB, plus one lila-stockfish-web sf17-79 worker.
- That falsifies "executing ORT wasm kernels on this graph is fatal on iOS WebKit" as a platform truth. The
  untested difference is the ORT version (1.23.0 vs our 1.27.0; their wasm module is 11.8 MB vs 13.5/24.3 MB).

Shipped on the branch (Adrian's call: keep our setup, only swap the runtime bytes on iOS): 1.23.0 vendored under
`frontend/public/maia/ort-1.23/` (same six file names, 1 GB patch applied), `runtimeDir` field on the worker
init message, `ensureOrtRuntime('ios-legacy')` + `runtimeDir: '/maia/ort-1.23'` whenever `isIosWebKit()`,
`ortVersion` on the `ready` message (console line, dev badge `maia webgpu ort=1.23.0 ...`, and the kill
sentinel record / Sentry context). Everything else on iOS is as before: WebGPU-first via the probe, one
wasm thread, blanket gate still on in prod. Phone protocol: clear site data, `/analysis?dev-ios-gate=off`,
check the badge says `ort=1.23.0`, run the idle test and then the runner (`?dev-bisect=start`). A surviving
run isolates the ORT version; a kill with `ort=1.23.0` in the record closes this lead and leaves the
page-footprint difference (their page has no MCTS, no gem grading, one small Stockfish) as the remaining one.

**2026-09-07 later: blanket gate replaced.** Adrian tested the 1.23.0 build by hand on the phone ("seems to
work") while the self-driving runner still reported every cell killed, so the runner's verdict is now suspect
(it decides "killed" from its own `running` phase on the next load; a Safari reload without `pagehide`, or
the `?dev-bisect` state surviving a manual reload, produces the same signal). Per Adrian's call the iOS
branch in `spawn()` is now `spawnOnIosWebKit()` unconditionally: probe picks `webgpu` → spawn with
`forceSingleThread` and the 1.23.0 files; probe picks `wasm` → `ios-webkit` terminal (copy now says
"needs iOS 26 or newer"). `?dev-ios-gate` only gates the dev-run Sentry markers. Stop the runner and restore
its switches with `/analysis?dev-bisect=stop` before a manual session (it may have left `dev-stockfish=off`
persisted).

**Result of the ORT 1.23.0 test (2026-09-07 evening, FLAWCHESS-AW events 16:36, 17:01:14, 17:01:44 UTC):
KILLED, three real /analysis sessions by hand.** Every record: `ortVersion: "1.23.0"`, `backend: webgpu`,
`numThreads: 1`, last batch 1 (FlawChess Engine policy calls), 39 / 101 / 131 dispatches with exactly one in
flight at the kill, 10-22 s after `ready`. Same shape as 1.27.0. **The ORT version is not the difference to
maiachess.com.** Consequences: the blanket gate is back for PRODUCTION builds (`import.meta.env.DEV` decides in
`spawn()`, no switch needed on the dev server), the changelog bullet was withdrawn, the 1.23.0 vendoring stays
(it is the base for the next step). Remaining differences to maiachess.com, one switch each:

1. **Backend: CPU wasm instead of WebGPU** — `?dev-maia-backend=wasm` (new): iOS spawns the wasm backend on the
   1.23.0 build, no probe, 1 thread. That is maiachess's exact ORT shape on our page. Our only wasm-on-iOS
   measurements were 1.27.0 (killed at 1 thread, `session.run` bypass survived); wasm on 1.23.0 has never run.
2. **Page footprint** — their analysis page has no MCTS / gem grading and a 472 KB Stockfish; run 1 with
   `?dev-stockfish=off` and the FlawChess Engine card off if 1 alone still dies.
3. **Thread count** — they use ORT's default (2-4 threads on the phone); irrelevant unless 1+2 survive.

**RESOLVED 2026-09-07 evening: the difference was the BACKEND, not the version.** Confirmed twice over: `?dev-maia-ort=1.27` (wasm backend on the current 1.27.0 build) also survived by hand, so the 1.23.0 vendoring, the `runtimeDir` init field and the `OrtRuntimeVariant` machinery were removed the same evening; the 2026-09-06 "1.27 wasm dies at one thread" reading was taken next to the 4 GB reservation and is superseded. Their Stockfish holds a
160 MB initial heap plus the 79 MB big NNUE in one instance, so page footprint was never the lever. With
`?dev-maia-backend=wasm` (CPU wasm on the 1.23.0 build, one thread) a full /analysis session by hand
survived on the reference iPhone with Stockfish and the FlawChess Engine on, while three more WebGPU
sessions the same hour were killed (FLAWCHESS-AW, 19:51-19:58 UTC). Shipped shape (`spawnOnIosWebKit()`,
every build): no WebGPU probe, `fetchWasmOnlyOrtRuntime('ios-legacy')`, `backend: 'wasm'`,
`forceSingleThread`, `runtimeDir: '/maia/ort-1.23'`. The `ios-webkit` terminal now fires only behind
`?dev-maia-backend=webgpu` (kept as the kill repro). Two dev switches decide what is dead weight:
`?dev-maia-ort=1.27` (is the version downgrade needed? the 1.27.0 wasm build died at one thread on
2026-09-06, but that predates the rest of the shape) and, later, a second wasm thread (maiachess runs
ORT's default, 2 on this phone; our 2-thread death was WebGPU next to 3 Stockfish workers). Speed on one
CPU thread is the cost: ~200 ms per rung, so a 21-rung ladder takes seconds; the ladder's coarse/fill
split already lands the chart progressively.

### Options after the idle test (2026-09-07, ranked by expected value per effort)

Facts they rest on: the kill is workload-independent and intermittent; both wasm and WebGPU paths die; every
iOS browser is WebKit, so there is no browser-side escape; assets today are `maia3_simplified.onnx` 45.7 MB
(fp32) + the 24.3 MB asyncify runtime wasm (ORT 1.27 pinned).

| # | Option | What it buys | Effort / risk |
|---|---|---|---|
| 1 | **Server-side Maia for iOS** — run the ONNX model on the backend (CPU ORT, batch of 21 ≈ tens of ms), one endpoint returning the ladder for a FEN; cache ladders by position hash (the DB is Zobrist-keyed already, common positions hit across users) | iOS gets the feature with ZERO WebKit dependency; also removes the 70 MB download on phones | Medium: endpoint + repository cache + an iOS branch in `useMaiaEngine`/the host; server CPU is a known quantity (remote-worker fleet exists); latency 100-300 ms is fine for a card that already waits on ladders |
| 2 | **Ballast measurement on `/maia-diag.html`** — allocate N MB before the WebGPU session, find the N where the idle diag page starts dying | Proves/kills "resting footprint + spike", measures headroom, is a WebKit bug repro | Small (one input on the existing page); a measurement, not a fix |
| 3 | **WebGPU without wasm** — convert the model to TF.js (onnx2tf) and run the TF.js WebGPU backend (pure JS + WGSL, no 24 MB wasm module, nothing for JSC to tier-compile) as the iOS-only worker | Keeps on-device inference on iOS if the wasm module IS the spike | Medium-large: conversion + second worker + parity tests against ORT outputs; op coverage risk; keeps two runtimes forever |
| 4 | **Minimal onnxruntime-web build** — WebGPU EP + only the ops in the Maia graph (`--minimal_build extended`, `--include_ops_by_config`) | Wasm from 24 MB to a few MB, shrinks the compile spike and the resting footprint | Large: Emscripten toolchain + ORT source build, re-vendor on every bump; unproven that WebGPU EP builds minimal |
| 5 | **Kill reason from the device** — USB data cable + `pymobiledevice3 syslog` | WebKit's own verdict (memory limit vs GPU process vs watchdog); the only way to stop guessing | Small once a cable exists; needs Developer Mode revealed by the tool |
| 6 | **Shed app resting footprint on iOS** — lazy-mount recharts/eval chart while Maia runs, trim the page tree | Might restore headroom if #2 shows the margin is small | Unknown savings, cannot be measured on the phone without a Mac; do only after #2 |
| 7 | **Smaller model export** — fp16/int8 Maia | Halves the 45.7 MB model and its GPU buffers, faster download | Does not touch the wasm-module spike; parity risk; separate seed |
| 8 | **Upstream** — WebKit bug with the #2 repro, data on ORT #26827 | Long-term fix for everyone | Slow, out of our hands |
| 9 | **Keep the gate** — Maia is desktop/Android-only on iOS, copy already shipped | Zero cost, current state | The population is now visible in Sentry (`unsupported_reason:ios-webkit`), so the cost of waiting is measurable |

Recommendation: #1 is the only option that makes iOS Maia RELIABLE rather than "survives more often", and it
reuses infrastructure the project already has; #2 and #5 are the cheap measurements to run regardless, because
they decide whether #3/#4/#6 are worth anything.

## Status 2026-09-07: three measurements that reframe the seed

All on the reference iPhone 14 Pro (iOS 26.6.1, Safari), each on a REAL build, none on the diag page.

| Build | Stockfish | Maia | Result |
|---|---|---|---|
| `origin/production` (#349: blanket iOS gate) | on | gated off | **survives** |
| `main` @ da9c9c53a, `?dev-stockfish=off` (inert Stockfish workers, no wasm fetch, no Blob) | **off** | WebGPU, badge confirms `threads=1 coi=true` | **KILLED** within seconds of stepping |
| `a7a4f6d74` (#346, last pre-219 release: ORT 1.29, no isolation, single ladder, 4 GB reservation) | on (3 workers) | tried | graceful `oom` terminal ("your device ran out of memory"), page survives |

Consequences:

- **Maia on /analysis has never run on this phone at any recent commit.** The pre-219 build lands in `oom`
  because the WebGPU worker's 4 GB reservation is the 4th large wasm memory next to 3 Stockfish workers
  (pool 2 + live eval 1), so the "it worked before Phase 219" premise is falsified for this device class.
  Phase 219 did not regress iOS; the 1 GB cap turned a graceful `oom` into a page kill by letting Maia start.
- **The kill needs only Maia.** FlawChess Engine off: dies. Stockfish off entirely (dev switch): dies. So the
  remaining suspects are what the REAL page adds to the Maia path that the diag page does not: the main-thread
  runtime/model byte copies handed to the worker (`ensureOrtRuntime()` + engine asset cache) and the 219 ladder
  workload (11-rung coarse pass + 21-rung fill + next-ply prefetch + policy calls). The diag page's
  "Maia alone survives 150 mixed shapes" is NOT evidence about the app.
- **Release path is clear:** restore the blanket iOS gate in `ensureSpawned()` (prod behaviour, measured
  surviving) and ship; iOS Maia via WebGPU is NEW work with two concrete suspects, not a regression fix.

Tooling added for this (dev server only, `import.meta.env.DEV`): `frontend/src/lib/engine/devEngineSwitches.ts`
— `/analysis?dev-stockfish=off|on` persists an inert-Stockfish switch, and the Maia `ready` message is
mirrored into a fixed corner badge (backend, numThreads, crossOriginIsolated). Serving an old commit to the
phone: `git worktree add ../flawchess-bisect <sha>`, `npm ci`, `npx vite --host --port 5174`,
`tailscale serve --bg http://127.0.0.1:5174` (restore with 5173), clear the site's data in Safari first.

### Next steps 2026-09-07 (when iOS Maia is picked up again; each is one dev switch + one phone run)

The blanket gate is back in `ensureSpawned()` (`spawn()` iOS branch, before any probe or download) and is
what ships. The work below is NEW scope, not a fix: nothing on iOS ever ran Maia on /analysis. Rules that
still hold: only REAL /analysis runs on the reference phone count (the diag page produced three false
"safe" verdicts); every step reuses the `devEngineSwitches.ts` pattern (`?dev-<switch>=…` persisted in
localStorage, dev-server only) and the corner badge; clear the site's data in Safari between builds.
Bypass the gate for these runs with a dev switch (`?dev-ios-gate=off`), never by editing the gate.

1. **Suspect A — main-thread byte copies.** `ensureOrtRuntime()` resolves the 25.7 MB asyncify binary on
   the main thread (engine asset cache, Cache API write, `ArrayBuffer`, transfer) and the model bytes go
   through the same layer; the diag page let the worker fetch via `wasmPaths` and survived. Switch:
   `?dev-maia-runtime=worker` makes the host spawn with `buffer: null` (the existing degraded path: worker
   resolves `wasmPaths` itself) and skips the model-through-cache path if there is one. If the page
   survives, the fix is to keep every engine byte off the main thread on iOS (worker-side fetch, no Cache
   API mirror), which is a small change.
2. **Suspect B — the 219 ladder workload.** Coarse 11-rung pass + 21-rung fill + next-ply prefetch +
   policy calls per step, vs. one 21-rung batch pre-219. Switch: `?dev-maia-ladder=single` disables the
   coarse pass and the prefetch in `useMaiaEngine`. If the page survives, iOS gets the single-pass ladder
   (a `isIosWebKit()` branch at the two call sites) and stays on WebGPU with one thread.
3. **If both survive only together, or neither survives:** stop. Record the two cells here, keep the gate,
   and treat iOS Maia as blocked on WebKit (ORT #26827 / #27584 are the upstream threads to watch). Do
   not add more diag knobs; the next lever would be a smaller model export, which is a separate seed.
4. **Whatever ships:** narrow the gate to the measured-safe shape only (e.g. WebGPU + single ladder), keep
   both `respawnPinnedToWasm` iOS terminals (they are unreachable under the blanket gate but guard any
   narrowing), and re-run the exact /analysis session on the phone AFTER the squash, from the deployed
   preview, before the release PR.

## Status 2026-09-06 night: iOS /analysis is STILL killed. Release blocker.

`main` (a4a1f4f6d) enables Maia on iOS 26 via WebGPU with the worker pinned to one wasm thread, and
`/analysis` on the reference iPhone 14 Pro (iOS 26.6.1, Safari AND Chrome for iOS, dev server via the
tailnet) still dies within seconds of stepping through moves. The Maia chart renders first, then WebKit
kills the page. **Do not release `main` as is.** Either the cause below is found and fixed, or the
blanket iOS gate from the 2026-09-06 hotfix (`isIosWebKit()` -> `unsupported` before any spawn) is
restored in `ensureSpawned()` before `production` moves. The Linux probe fix, the diag page, and the
terminal-instead-of-wasm-respawn logic on iOS are all still correct and can stay.

### What was measured on the phone (all via `/maia-diag.html`, same session, same device)

| Configuration | Result |
|---|---|
| Maia WebGPU alone, 30 x 21-rung ladder | survives, median 509 ms |
| Maia WebGPU alone, 150 mixed batch shapes (1/1/11/10/21/1/2/3) over 14 positions | survives |
| Stockfish x3 alone (Hash 8 MB, movetime 1500), 60 s | survives |
| Maia WebGPU (2 wasm threads) + Stockfish x3 | KILLED at run 57/60, ~10 s after the SF workers came up |
| Maia WebGPU (1 wasm thread) + Stockfish x2 | survives 150 runs |
| Maia WebGPU (1 wasm thread) + Stockfish x3 | survives 150 runs |
| **The real `/analysis` page with the 1-thread pin shipped** | **KILLED within seconds** |

So the diag mix is NOT a faithful model of `/analysis`. Every diag configuration that mirrors the shipped
code survives, and the app still dies. The kill is silent (no Sentry event, no console reachable; dev
Sentry was enabled and shows nothing from the kills), consistent with WebKit's per-page memory-limit
termination rather than a JS error.

### What `/analysis` does that the diag mix does not (the remaining suspects, unranked)

1. **FlawChess Engine (MCTS)**: `useFlawChessEngine` -> `maiaQueue` policy calls (1-3 rung batches at
   high rate, each one an ORT `run` with its own GPU readback) interleaved with grading-pool Stockfish
   searches, plus the MCTS tree in main-thread JS memory. The diag mix has no MCTS and no maiaQueue.
2. **Live Stockfish eval** at `MultiPV 2`, `go movetime 1500 nodes 2000000`, re-issued on every position
   change with the adaptive debounce; the diag loop ran a fixed movetime and single PV on 2 of 3 workers.
3. **Gem grading / `useStockfishGradingEngine`** dispatch patterns (multiple `setoption`/`position`/`go`
   per position) rather than the diag's one search per bestmove.
4. **The React page itself**: recharts, the board, per-ply Maia curves kept in state, the policy cache
   (`maiaPolicyCache`), `useMaiaEngine`'s prefetch of the NEXT ply (an extra inference per step).
5. **Main-thread copies of engine bytes**: `ensureOrtRuntime()` resolves the 25.7 MB asyncify binary on
   the main thread and transfers it; the Stockfish shared-URL path holds a Blob of the 16 MB engine.
   The diag page never fetched a runtime buffer on the main thread (the worker fetched via wasmPaths).
6. **Unverified assumption**: that the phone actually ran the pinned code. The only evidence would be
   the `[maia-worker] ready — backend=webgpu numThreads=1` console line, which is unreachable on the
   device. Chrome for iOS crashing too rules out a Safari-only quirk but not a stale module.

### Recommended next steps (in this order, each cheap)

1. Make the running configuration VISIBLE on the device: a dev-only badge (or the Maia card's existing
   backend indicator) showing `backend/numThreads` from the `ready` message, so step 6 above is settled
   in one look. Alternatively a Sentry `captureMessage` on `ready` for iOS only, tagged with both.
2. Bisect INSIDE the app with the three card switches on `/analysis` (Stockfish eval, FlawChess Engine,
   Maia). Asked for on 2026-09-06 but not yet run. The decisive cells: Maia on + both others off; Maia on
   + Stockfish on + FlawChess Engine off.
3. Extend the diag page to drive the REAL consumers instead of imitations: in dev, Vite serves
   `/src/lib/engine/maiaWorkerHost.ts`, `/src/lib/engine/maiaQueue.ts`, `/src/lib/engine/workerPool.ts`
   as modules (see `project_browser_uat_techniques`), so the page can `import()` them and run
   `acquireMaiaWorker()` + `maiaQueue` + the grading pool exactly as the app does, with the kill journal.
4. If it is total footprint after all: iOS pool of ONE grading worker (`computePoolSize()`), FlawChess
   Engine off on iOS (like `useGemSweep`'s low-power gate), lower live-eval `nodes`, smaller Hash. Test
   each on the phone via step 3 before shipping.
5. If none of that lands before the next release: restore the blanket iOS gate (one `if` in
   `ensureSpawned()` plus the old test), keep everything else.

### Bottom line on the two hypotheses so far

- "WebGPU fails on iOS" — FALSE. It works, fast (0.5 s per 21-rung ladder).
- "The second wasm thread tips the memory budget next to Stockfish" — TRUE in the diag mix, but
  NOT SUFFICIENT for `/analysis`. Something the real page adds still crosses the limit.

## Findings 2026-09-06 (Linux leg root-caused; diag page for the phone)

Tooling: `frontend/public/maia-diag.html` (committed dev tool, served at `/maia-diag.html` in dev AND
prod — excluded from the SW precache like every `.html`). It drives the REAL `/maia/maia-worker.js` with `{type:'init', backend:'webgpu'}`
and renders the raw `webgpu-unavailable` text on screen (plus a main/worker WebGPU probe with an f16
compute smoke test, a main-thread ORT run with `requestAdapter`/`requestDevice` hooks, a 30-run
ladder stress test, and a localStorage journal so a page kill is visible after reload). Built
because iOS Safari has no reachable console without a Mac.

**Linux dev box (bucket b, ours):** the box has TWO adapters. `requestAdapter()` and `low-power`
return the AMD RDNA3 iGPU WITH `shader-f16` (a real f16 compute shader returns correct results);
`high-performance` returns the NVIDIA Lovelace dGPU WITHOUT `shader-f16` (Chrome/Linux Vulkan).
ORT 1.27's native WebGPU EP creates its adapter in C++ (`webgpu_context.cc` Initialize) with
`powerPreference = HighPerformance` (the `WebGpuContextConfig` default), so it lands on the NVIDIA
adapter, requests only `[timestamp-query, subgroups]`, and the fp16 `Cast` node then fails with
`Program Cast requires f16 but the device does not support it`. Our main-thread probe in
`ortRuntimeSource.ts` calls `requestAdapter()` with NO options and so inspects the OTHER adapter,
says "webgpu", and the 25.7 MB asyncify build is downloaded for nothing before the wasm respawn.

Levers checked and rejected in ORT 1.27's web bundle:
- `ep.webgpuexecutionprovider.powerPreference` via `sessionOptions.extra`: parsed by the C++
  factory, but the JS appends the EP (and the factory reads config) BEFORE `extra` entries are added,
  so it never arrives. The JS whitelist of EP options (`device`, `preferredLayout`,
  `forceCpuNodeNames`, `validationMode`, `enableGraphCapture`) has no `powerPreference`.
- Passing our own `GPUDevice` via `executionProviders: [{ name: 'webgpu', device }]`: accepted, the
  f16 check passes, but every program then fails with `Failed to wait for the operation:3`
  (`WebGpuContext::Wait` -> `instance_.WaitAny` error; the JS-side `webgpuRegisterDevice` creates the
  WGPUInstance without ORT's `TimedWaitAny` requirement). Not usable without patching ORT.
- Same conclusion holds for 1.29's `session-options.ts` (no `powerPreference` EP option either).

Cheap fix that IS ours: make the probe request the adapter the way ORT will
(`requestAdapter({ powerPreference: 'high-performance' })`) so the decision matches and multi-GPU
boxes fall to wasm WITHOUT the wasted asyncify download. It does not make WebGPU work on such boxes.

**Windows 11 Edge (per Adrian, console pasted 2026-09-06):** WebGPU WORKS —
`[maia-worker] ready — backend=webgpu numThreads=4`. Firefox/Windows still fails (the known `Clip`
shader compile failure noted in `maia-worker.js`). So the "mainstream platform is broken" worry from
the original seed is withdrawn; the desktop failures are per-GPU/per-browser, not systemic.

**iOS (measured on the iPhone 14 Pro, iOS 26.6.1, through the tunnel-served diag page):** WebGPU
WORKS. `navigator.gpu` exists in the dedicated worker, the adapter has `shader-f16`, a real f16
compute shader returns correct values, and the REAL `maia-worker.js` reached
`ready backend=webgpu numThreads=2` in 5.8 s, then survived 30 consecutive 21-rung ladders at a flat
505-554 ms (median 509 ms) with no page kill. The "WebGPU also fails on the reference device" line in
the hotfix section was the pre-cap 4 GB reservation failure, not a WebGPU fault. Fix shipped the same
evening (uncommitted at the time of writing, see `git log` for the commit): the D-13 gate in
`maiaWorkerHost.ts` now spawns on iOS whenever the probe (`probeOrtBackendOnce()`, fetch-free) picks
`webgpu`, gates off with `unsupported`/`'ios-webkit'` when it picks `wasm` (no runtime download on the
way), and both `respawnPinnedToWasm` call sites become that same terminal on iOS (plus one Sentry
capture tagged `maia_failure:webgpu-ios-terminal` with the raw ORT text in context). Gate copy now
says "needs WebGPU, iOS 26+". The wasm path on iOS is NOT worth further work: the kill is inside
WebKit's wasm engine (flat 110 MB heap, 1 thread makes no difference, skipping `session.run` survives;
ORT #26827 samples WebKit 26 stuck in `JSC::Wasm::parseAndCompileOMG` on the same kind of workload),
which the page cannot influence, and WebGPU now covers every iOS version that has it (26+).
**Second kill, root-caused the same evening (/analysis still died with the WebGPU-only gate):** the diag
page's mix stress (varied Maia batch shapes + 3 Stockfish workers, i.e. what /analysis runs on a phone)
reproduced the kill at run 57/60, ~10 s after the Stockfish workers came up; Maia alone (150 mixed
shapes) and Stockfish x3 alone both survive. Bisect on the phone: Maia pinned to ONE wasm thread + 3
Stockfish survives; 2 threads + 3 Stockfish dies. So the WebGPU worker's default second wasm thread
(`chooseWasmThreadCount()`: 4 cores -> 2) is what tips WebKit's per-page limit next to Stockfish.
Shipped: every iOS Maia spawn sends `forceSingleThread: true` (`IOS_FORCE_SINGLE_THREAD` in
`maiaWorkerHost.ts`); Stockfish pool unchanged. Adrian's recollection that Maia ran on iPhones before
Phase 219 (single thread, no shared memory) matches.
Previously: still no raw message. Next step is to open `/maia-diag.html` through the tunnel on the
iPhone, tap 1 (probe) then 2 (ORT WebGPU via the real worker), and read the Summary / Copy log.
ORT tracker context: microsoft/onnxruntime#26827 (WebKit 26 + JSEP: CPU pinned in
`JSC::Wasm::parseAndCompileOMG` and 1 GB+ growth, i.e. the same optimizing-tier suspect as our wasm
kill) and #27584 (yolo26n WebGPU on iOS 26.3 Safari works, then crashes after ~500 inferences).

## Constraints / prior art

- `project_maia_ios_two_failure_populations`: do NOT conflate with the iOS <16.4
  no-WASM-SIMD population (permanent `unsupported`, handled by the D-13 gate).
- `project_ios_wasm_reservation_budget`: any WebGPU work must keep the asyncify glue's memory
  ceiling at 1 GB (both glue files carry the local patch; re-apply after every re-vendor).
- `project_coep_stale_runtime_cache_hangs_threaded_ort`: refresh `/maia/*?v=<n>` cache
  entries before any browser measurement, or a stale glue hides the real behavior.
- `project_engine_test_sched_idle_timeout_flake` applies to any new engine tests.
- Upfront free-memory detection on iOS WebKit is impossible and was rejected 2026-08-29;
  don't re-propose it.
- The classification/UX side is DONE (quick task 260829-tku).
