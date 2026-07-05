---
phase: 151-maia-in-the-browser-all-position-surfaces
verified: 2026-07-05T06:04:00Z
status: passed_with_override
score: 13/14 requirements fully verified (1 partially verified — MAIA-06 latency clause, accepted)
behavior_unverified: 0
overrides_applied: 1
override_note: "MAIA-06 latency-measurement gap accepted by user at phase close (2026-07-05). Op-support + static sizes verified; numeric per-device latency deferred as a non-blocking follow-up. REQUIREMENTS.md MAIA-06 corrected to [~] partial. Phase goal (Maia live + surfaces + VALID-01 calibration) achieved."
gaps:
  - truth: "MAIA-06: 'Download size and per-position latency are measured on desktop and mobile (WASM vs WebGPU; single call vs ELO sweep), a model size is chosen against a board-response target, and the model is confirmed to load with no unsupported-op errors.'"
    status: partial
    reason: "Op-support (no unsupported-op errors) is confirmed twice (scripts/inspect_maia_onnx.mjs in Plan 01 + the live human pass in Plan 06). Static on-disk artifact sizes are real and recorded. But per-device (desktop/mobile) cold-load and per-position latency numbers were NOT recorded — 151-MAIA-MEASUREMENTS.md §2 marks every cell of the latency table 'NOT YET MEASURED' and states outright 'These require an actual browser session per device/backend ... the human ran the live calibration pass but did not record numeric timings.' The model-size decision (D-10: keep the smallest maia3_simplified.onnx) was therefore made against qualitative ('felt responsive') evidence only, not against the numeric board-response target the requirement text calls for ('a model size is chosen against a board-response target') — no such target was ever defined. REQUIREMENTS.md nonetheless marks MAIA-06 unconditionally '[x] Complete', which overstates what was actually delivered."
    artifacts:
      - path: ".planning/phases/151-maia-in-the-browser-all-position-surfaces/151-MAIA-MEASUREMENTS.md"
        issue: "§2 latency table is entirely 'NOT YET MEASURED'; no board-response numeric target was ever set, so the D-10 model-size decision rests on the qualitative VALID-01 pass, not a measured latency budget"
    missing:
      - "Real desktop + mobile cold-load and per-position latency numbers (WASM and WebGPU, single-call and ELO-sweep) captured via devtools Performance / performance.now() around the worker init→ready and analyze→result round-trips"
      - "A stated numeric board-response target the measured latency is judged against (or an explicit decision that no target is needed, recorded as such rather than silently absent)"
      - "REQUIREMENTS.md's MAIA-06 row corrected to reflect partial completion (or an accepted override) instead of an unqualified 'Complete'"
---

# Phase 151: Maia-in-the-Browser (All Position Surfaces) Verification Report

**Phase Goal:** Maia-3 runs live in-browser on the analysis board and, for every position, surfaces
a "Moves by Rating" chart plus a Maia WDL eval bar on the LEFT of the board — standalone user value,
and the live calibration gate that proves Maia is trustworthy enough to build on.
**Verified:** 2026-07-05
**Status:** gaps_found (one non-functional gap — MAIA-06 latency-measurement clause; everything else verified)
**Overall verdict:** **CONDITIONAL PASS** — see "Verdict" section at the end.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Unmodified, version-pinned `maia3_simplified.onnx` loads via onnxruntime-web WASM with no unsupported-op errors (MAIA-01) | ✓ VERIFIED | `sha256sum frontend/public/maia/maia3_simplified.onnx` = `405bf76c...` matches `151-MAIA-CONTRACT.md` and `public/maia/README.md` exactly; `scripts/inspect_maia_onnx.mjs` ran a real inference (Plan 01); confirmed again in the Plan 06 human live pass |
| 2 | onnxruntime-web runs the model in a lazy Web Worker, never in the initial bundle (MAIA-02) | ✓ VERIFIED | `frontend/public/maia/maia-worker.js` is a classic Worker; `useMaiaEngine` creates `new Worker(...)` only on mount of the Analysis page (route-level `React.lazy`); model/.wasm excluded from PWA precache (`vite.config.ts` `globIgnores` incl. `**/*.onnx`) |
| 3 | Original MIT glue produces a normalized, deterministic per-legal-move probability distribution from FEN + policy tensor, no AGPL code copied (MAIA-03) | ✓ VERIFIED | `frontend/src/lib/maiaEncoding.ts` (282 lines, explicit "NOT derived from CSSLab" header); 15 unit tests in `maiaEncoding.test.ts` all pass (softmax sums to 1, illegal moves absent, single-legal-move → 1.0) |
| 4 | Full per-ELO probability curve + Maia WDL computed per position; ELO sourced from rating-at-game-time / current_rating (MAIA-04) | ✓ VERIFIED | `useMaiaEngine` batches the whole `MAIA_ELO_LADDER` in one `session.run`; `get_current_rating_by_platform()` (backend, index-backed, 8 passing tests) + `useMaiaEloDefault` (6 passing tests incl. user-override-then-late-load ordering) wire the two ELO sources end-to-end |
| 5 | Inference cache is ephemeral, board-session-scoped, no persistence (MAIA-05) | ✓ VERIFIED | `useMaiaEngine.test.ts` "cache hit... skips a second worker round-trip"; `grep -rn "localStorage\|indexedDB" frontend/src/hooks/useMaiaEngine.ts` → no matches |
| 6 | MAIA-06 op-support + size measured; per-device latency measured; model size chosen against a board-response target | ⚠️ **PARTIAL — see gap below** | Op-support ✓ (twice); static sizes ✓ (real, on-disk); per-device cold-load/latency numbers explicitly **NOT YET MEASURED** (`151-MAIA-MEASUREMENTS.md` §2); no numeric board-response target was ever defined, so the model-size decision rests on qualitative evidence only |
| 7 | "Moves by Rating" chart renders one line per candidate move over the ELO ladder for every position (SURF-01) | ✓ VERIFIED | `MovesByRatingChart.tsx` pivots `perElo` into one `<Line>` per shown SAN; 7 passing tests |
| 8 | Chart marks "you are here" ELO + emphasizes played/best move (SURF-02) | ✓ VERIFIED | `<ReferenceLine x={selectedElo}>`; test asserts the you-are-here label text; played/best get distinct `theme.ts` accents + thicker stroke |
| 9 | Chart line set capped at top-N-by-peak, always unioned with {played, best} (SURF-03) | ✓ VERIFIED | `capMovesByPeak` exported + unit-tested for membership/count/dedup with a played move outside top-N |
| 10 | Maia WDL eval bar on LEFT, Stockfish eval bar on RIGHT, both shown for every position in game mode AND free play (SURF-04) | ✓ VERIFIED | `Analysis.tsx` `boardRow` (shared by desktop+mobile, mounted once): Maia `<EvalBar testId="analysis-maia-eval-bar" whiteFraction={...}>` immediately followed by the board then the Stockfish `<EvalBar>` (default `testId="analysis-eval-bar"`) — read directly at lines 901-951; `Analysis.test.tsx` asserts both testids render |
| 11 | Chart + Maia bar recompute live on every board navigation, no server round-trip (SURF-05) | ✓ VERIFIED | `useMaiaEngine({fen: position, ...})` — `position` drives re-analysis; no `fetch`/`axios` in the hook or worker; human-confirmed responsive live recompute in `151-MAIA-MEASUREMENTS.md` §2 |
| 12 | Repo LICENSE is full AGPL-3.0 text; README consistent (LIC-01) | ✓ VERIFIED | `LICENSE` (661 lines) begins "GNU AFFERO GENERAL PUBLIC LICENSE"; `grep -n "license-MIT\|MIT licensed" README.md` → 0 matches; badge/bullet/License-section all say AGPL-3.0 |
| 13 | Visible MaiaAttribution notice citing CSSLab repo, AGPL text, model path, Chessformer paper (LIC-02) | ✓ VERIFIED | `MaiaAttribution.tsx` renders always-visible (non-hover-gated) with 3 real anchors; mounted via `MaiaHumanPanel` (`showAttribution`) on both the desktop human column and every mobile Human tab; 5+3 passing tests |
| 14 | Live calibration eyeball + move-label sanity check performed and passed before shipping (VALID-01) | ✓ VERIFIED | `151-MAIA-MEASUREMENTS.md` §3: human APPROVED verdict, bar-direction/WDL-sign check, per-ELO calibration check, AND an explicit move-label sanity check confirming the best-effort 4352-vocab reconstruction produces correct SANs for the checked positions |

**Score:** 13/14 requirement IDs fully verified; 1 (MAIA-06) partially verified — see gap.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/public/maia/maia3_simplified.onnx` | Pinned, unmodified model | ✓ VERIFIED | SHA-256 `405bf76c...` matches contract + README; 45,683,686 bytes |
| `frontend/public/maia/maia-worker.js` | Classic Worker, EP selection | ✓ VERIFIED | `numThreads=1` forced on both WASM and WebGPU paths (grep confirms, never >1); WebGPU feature-detected + try/catch fallback |
| `scripts/inspect_maia_onnx.mjs` | Contract inspection script | ✓ VERIFIED | Present, referenced in 151-01-SUMMARY as run to completion |
| `151-MAIA-CONTRACT.md` | Confirmed tensor contract | ✓ VERIFIED | All 6 items (a)-(f) answered concretely, no unresolved CONFIRM-AT-RUNTIME on load-bearing facts |
| `frontend/src/lib/maiaEncoding.ts` | Board→tensor, mask, softmax, expectedScore | ✓ VERIFIED | 282 lines, exported functions match plan's named API; 15 tests |
| `frontend/src/hooks/useMaiaEngine.ts` | Hook producing perElo/wdl/expectedScoreAtSelectedElo | ✓ VERIFIED | 278 lines; 10 tests incl. debounce, stale-discard, cache-hit, tab-hide pause, unmount cleanup |
| `frontend/src/components/analysis/MovesByRatingChart.tsx` | Recharts chart | ✓ VERIFIED | 289 lines; 7 tests |
| `frontend/src/components/analysis/EloSelector.tsx` | Interactive ELO control | ✓ VERIFIED | 66 lines; 7 tests; ladder-derived bounds (not hard-coded) |
| `frontend/src/components/analysis/EvalBar.tsx` (extended) | `whiteFraction`/`testId` override | ✓ VERIFIED | 14 tests (8 pre-existing + 6 new) all pass |
| `frontend/src/components/analysis/MaiaAttribution.tsx` | Visible attribution notice | ✓ VERIFIED | 3 real anchors, `data-testid="maia-attribution"` |
| `frontend/src/hooks/useMaiaEloDefault.ts` | D-06/D-07 ELO default hook | ✓ VERIFIED | 100 lines; 6 tests incl. user-override-then-late-load ordering |
| `frontend/src/pages/Analysis.tsx` (integration) | 3-column desktop + mobile Human tab | ✓ VERIFIED | Read directly: `analysis-human-column` (left) + board column (center, both bars) + engine panel (right, unchanged); mobile 4-tab `Moves\|Eval\|Human\|Tags` + free-play `Moves\|Human` pair |
| `LICENSE` | Full AGPL-3.0 text | ✓ VERIFIED | 661 lines, canonical FSF text, filled-in appendix |
| `app/repositories/game_repository.py::get_current_rating_by_platform` | Index-backed rating query | ✓ VERIFIED | Rides `ix_games_user_played_at`; no migration; 6 repository + 2 router tests pass |
| `.planning/phases/151-.../151-MAIA-MEASUREMENTS.md` | MAIA-06 measurements + VALID-01 sign-off | ⚠️ PARTIAL | Sizes + calibration verdict recorded; latency table entirely unmeasured (see gap) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `maia-worker.js` | `maia3_simplified.onnx` | `session.create(MODEL_PATH)` | WIRED | `MODEL_PATH` constant resolves to `/maia/maia3_simplified.onnx`; confirmed loadable |
| `useMaiaEngine` | `maia-worker.js` | `new Worker('/maia/maia-worker.js')` + postMessage protocol | WIRED | Mock-worker tests exercise init/analyze/result/error/terminate round-trip |
| `useMaiaEngine.perElo` | `MovesByRatingChart` | prop pass-through in `Analysis.tsx`/`MaiaHumanPanel` | WIRED | `perElo={maia.perElo}` read directly at Analysis.tsx:1068/1208 |
| `useMaiaEngine.expectedScoreAtSelectedElo` | Maia `EvalBar` | `whiteFraction={maia.expectedScoreAtSelectedElo ?? 0.5}` | WIRED | Read directly at Analysis.tsx:910 |
| `useMaiaEloDefault.selectedElo` | `EloSelector` + `useMaiaEngine` | prop pass-through | WIRED | `selectedElo`/`onEloChange={setSelectedElo}` threaded through `MaiaHumanPanel` |
| `GET /users/me/profile` | `current_rating` | `get_current_rating_by_platform` → `_primary_current_rating` → response field | WIRED | Confirmed in both `get_profile` and `update_profile` assembly sites |
| `useUserProfile().data.current_rating` | `useMaiaEloDefault` free-play default | `profile?.current_rating ?? FREE_PLAY_DEFAULT_ELO` | WIRED | Read directly in `useMaiaEloDefault.ts:69` |
| `MaiaAttribution` | Analysis surface | `MaiaHumanPanel` (`showAttribution`) mounted in desktop human column + every mobile Human tab | WIRED | Confirmed via grep + code read (2 mount sites) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All Maia-related frontend unit/behavior test files pass | `npx vitest run --run <9 test files>` | 9 files / 72 tests passed | ✓ PASS |
| Full frontend suite unaffected | `npx vitest run` | 114 files / 1316 tests passed | ✓ PASS |
| `tsc -b` clean across the whole project | `npx tsc -b` | no output (clean) | ✓ PASS |
| `npm run lint` clean (Maia files) | `npm run lint` | 0 errors (3 unrelated pre-existing warnings in `coverage/` artifacts) | ✓ PASS |
| `npm run knip` clean (no dead Maia exports) | `npm run knip` | clean | ✓ PASS |
| `npm run build` succeeds; PWA precache excludes `.onnx`/ort-wasm | `npm run build` + plan's exact regex gate | `.onnx`/`ort-wasm*.wasm` absent from `dist/sw.js` | ✓ PASS |
| Worker forces `numThreads=1`, feature-detects WebGPU | `grep numThreads\|webgpu\|requestAdapter public/maia/maia-worker.js` | forced on both paths, never >1; `navigator.gpu?.requestAdapter()` present with try/catch fallback | ✓ PASS |
| No COOP/COEP headers introduced | `grep -rn "Cross-Origin-Opener\|Cross-Origin-Embedder" vite.config.ts deploy/ .github/` | none found; CI guard (`ci.yml` "No COOP/COEP header guard") present and unmodified | ✓ PASS |
| Backend `current_rating` behavior | `uv run pytest tests/test_game_repository.py::TestGetCurrentRatingByPlatform tests/test_users_router.py::TestProfileCurrentRating` | 8 passed | ✓ PASS |
| Full backend suite unaffected | `uv run pytest -n auto` | 3171 passed, 18 skipped | ✓ PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` conventions apply to this phase (frontend ML-inference + license phase, not a migration/CLI-tooling phase); none declared in the plans. Skipped — no runnable probe entry points for this phase's domain.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| LIC-01 | 151-02 | Relicense MIT→AGPL-3.0 | ✓ SATISFIED | LICENSE + README confirmed |
| LIC-02 | 151-02, 151-06 | Visible attribution notice | ✓ SATISFIED | `MaiaAttribution` built + mounted on both layouts |
| MAIA-01 | 151-01 | Pinned unmodified model + confirmed I/O contract | ✓ SATISFIED | SHA-256 verified, contract doc complete |
| MAIA-02 | 151-04 | Lazy Web Worker inference | ✓ SATISFIED | Classic Worker, route-level lazy mount |
| MAIA-03 | 151-04 | Original MIT encoding/masking/softmax glue | ✓ SATISFIED | `maiaEncoding.ts`, no AGPL code copied |
| MAIA-04 | 151-03, 151-04, 151-06 | Full per-ELO curve + WDL, ELO from rating-at-game-time | ✓ SATISFIED | All three plans' slices confirmed present and wired |
| MAIA-05 | 151-04 | Ephemeral, non-persisted cache | ✓ SATISFIED | Ref-held Map, no localStorage/IndexedDB |
| MAIA-06 | 151-01, 151-04, 151-06 | Size + latency measured, no unsupported-op, size chosen vs target | ⚠️ **PARTIAL** | Op-support + size ✓; per-device latency + numeric target ✗ (see gap) |
| SURF-01 | 151-05 | Moves-by-Rating chart, one line/move | ✓ SATISFIED | `MovesByRatingChart` |
| SURF-02 | 151-05 | You-are-here line + played/best emphasis | ✓ SATISFIED | `ReferenceLine` + accent styling |
| SURF-03 | 151-05 | Top-N ∪ {played, best} cap | ✓ SATISFIED | `capMovesByPeak` |
| SURF-04 | 151-05, 151-06 | Maia bar LEFT, Stockfish bar RIGHT, all positions | ✓ SATISFIED | Both bars confirmed mounted and ordered correctly in `boardRow` |
| SURF-05 | 151-04, 151-06 | Live recompute, no server round-trip | ✓ SATISFIED | `position`-keyed hook, no network calls |
| VALID-01 | 151-06 | Live calibration + trust gate | ✓ SATISFIED | Human sign-off recorded, including move-label sanity check |

No orphaned requirements found — all 14 IDs declared across the 6 plans' frontmatter (LIC-01, LIC-02, MAIA-01..06, SURF-01..05, VALID-01) are the exact set assigned to Phase 151 in REQUIREMENTS.md's traceability table; none are missing from a plan's `requirements:` field.

### Anti-Patterns Found

No debt markers (`TBD`/`FIXME`/`XXX`), no unresolved `TODO`/`HACK`, no empty stub implementations (`return null`, `=> {}`, hardcoded empty arrays flowing to render) found across all Maia-related source files (`maiaEncoding.ts`, `useMaiaEngine.ts`, `maia-worker.js`, `useMaiaEloDefault.ts`, `MovesByRatingChart.tsx`, `EloSelector.tsx`, `MaiaHumanPanel.tsx`, `EvalBar.tsx`, `MaiaAttribution.tsx`, backend `game_repository.py`/`users.py`). The one "placeholder" grep hit in `MovesByRatingChart.tsx` is a doc-comment describing the legitimate loading-state UI (chart renders a placeholder while `perElo` is empty pre-inference) — not a stub.

The only quality finding is the MAIA-06 gap documented above, which is **honestly self-disclosed** in `151-06-SUMMARY.md` ("Open follow-up (non-blocking): numeric MAIA-06 per-device latency/cold-load timings remain unrecorded") and in `151-MAIA-MEASUREMENTS.md` itself — this is a transparency strength, not a concealment pattern, but REQUIREMENTS.md's unqualified "Complete" checkbox for MAIA-06 does not reflect that disclosed partiality.

### Human Verification Required

None beyond what the phase's own blocking-human checkpoint (Task 4 of Plan 06, VALID-01) already captured and recorded with an APPROVED verdict. No additional human verification items were identified by this automated pass.

### Gaps Summary

**One gap, non-blocking to the phase's core stated goal, but a real shortfall against the literal MAIA-06 requirement text and against REQUIREMENTS.md's claim of full completion:**

`151-MAIA-MEASUREMENTS.md` §2 explicitly and honestly records that per-device (desktop/phone), per-backend (WASM/WebGPU) cold-load and per-position latency numbers were **never captured** — every cell reads "NOT YET MEASURED." The requirement (MAIA-06) asks for exactly these numbers plus "a model size... chosen against a board-response target." Op-support and static artifact sizes ARE measured and real. But no numeric latency budget was ever defined, so the D-10 "keep the smallest model" decision rests entirely on the qualitative VALID-01 calibration pass ("felt responsive," no stall observed) rather than a measured number against a target, as the requirement literally specifies.

This does **not** undermine the phase's central deliverables: Maia-3 genuinely runs client-side, both position surfaces (chart + LEFT eval bar) are live and wired for every position in both game mode and free play, the AGPL relicense + attribution are real, and the VALID-01 trust gate (calibration + move-label correctness) passed with actual human judgment recorded — this is the load-bearing gate the phase goal calls "the live calibration gate that proves Maia is trustworthy enough to build on," and it is genuinely satisfied.

**Recommendation:** either (a) accept this as an intentional, disclosed deferral via a VERIFICATION.md override (the SUMMARY already flagged it as a non-blocking follow-up, not a hidden gap) and open a quick follow-up task to capture real device numbers before a latency budget is needed downstream, or (b) run a short device-timing pass now if Phase 152 (which builds directly on this surface) needs a concrete latency ceiling. Either way, REQUIREMENTS.md's MAIA-06 row should be corrected to note the partial scope rather than reading as unconditionally "Complete."

---

## Verdict

**CONDITIONAL PASS.**

13 of 14 phase requirements are fully verified against the actual codebase (not just SUMMARY claims): real files with matching SHA-256 hashes, real passing tests exercising the behavior-dependent invariants (stale-result discard, cache-hit, tab-hide pause, user-override precedence), real code-read confirmation of the 3-column desktop layout and mobile tab wiring, a real AGPL relicense, and a real human-recorded VALID-01 calibration + move-label sanity check. The full backend (3171 passed) and frontend (1316 passed) test suites are green with these changes in place; `tsc -b`, `lint`, `knip`, and `build` are all clean; the PWA precache correctly excludes the model/wasm; no COOP/COEP regression.

The one shortfall is MAIA-06's latency-measurement clause, honestly disclosed by the executor rather than hidden, and not load-bearing for the phase's stated user-value and calibration-gate goals. This phase can reasonably proceed to Phase 152 (which depends on the calibration trust gate, not on a latency budget), but the gap should be explicitly acknowledged/overridden or closed with a short follow-up rather than left silently marked "Complete" in REQUIREMENTS.md.

---
_Verified: 2026-07-05_
_Verifier: Claude (gsd-verifier)_
