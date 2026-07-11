---
phase: 165-gem-move-elo-calibration-harness-restore-fen-analysis-deep-l
verified: 2026-07-11T15:55:00Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 165: Gem-move ELO calibration harness + restore `?fen=` analysis deep-link Verification Report

**Phase Goal:** Build the empirical basis for an ELO-scaled iso-rarity gem-move ceiling (Phase 163 D-08): a headless Node harness that measures, over ~3000 stratified Kaggle "brilliant" moves, the raw Maia probability at each ELO rung {600,1000,1400,1800,2200,2600} plus a single Stockfish C2 grade per position, emitting a TSV + drop-off summary. Sub-deliverable: restore an additive `?fen=<fen>` analysis deep-link (alongside `?line=`) so the TSV's arbitrary mid-game positions are clickable. Reuse the real engines and import the actual classifyGem/evalToExpectedScore/MISTAKE_DROP — zero reimplementation drift.
**Verified:** 2026-07-11T15:55:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | (165-01) `--n 5` emits a well-formed TSV in `reports/data/` with every D-05 column + sibling summary TSV, no crash | ✓ VERIFIED | Independently re-ran `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/gem-elo-calibration.mjs --n 5 --seed 1 --movetime 800`; exit 0; produced `gem-elo-calibration-2026-07-11T13-49-08-546Z.tsv` + `-summary.tsv`; identical numeric output to the executor's original run (deterministic seed) |
| 2 | (165-01) Harness imports the REAL classifyGem/summarizeForGem/evalToExpectedScore/MISTAKE_DROP from frontend source, never re-derives them | ✓ VERIFIED | `gem-elo-calibration.mjs` lines 41-57 import from `@/lib/maiaEncoding`, `@/lib/gemMove`, `@/lib/liveFlaw`, `@/generated/flawThresholds`, `@/hooks/uciParser`; grep confirms zero local re-declaration of these symbols under `scripts/` |
| 3 | (165-01) Per position: exactly 1 Stockfish grade + 6 Maia forward passes; c2_pass/best_es/second_best_es computed ONCE, only maia_p_<rung> varies per rung | ✓ VERIFIED | Code read: `gradePosition()` called once per position (main loop line 637); `maiaProbsForPosition()` does one batched `session.run` across all 6 rungs (line 645, `maiaProbsForPosition` batches `rungs.length` into one feed) |
| 4 | (165-01) gem-parity check asserts imported gem pipeline reproduces hand-derived classifyGem booleans for a fixed fixture | ✓ VERIFIED | Independently ran `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/gem-parity.check.mjs`; exit 0, printed PASS line |
| 5 | (165-01) Sampling is stratified via two-pass streaming reservoir sampling, deterministic for (--n, --seed), never loads the 2.2GB CSV into memory | ✓ VERIFIED | Code read: `streamCsvLines` uses `fs.createReadStream` + `readline` (never `readFileSync`); two independent `--n 5 --seed 1` runs produced byte-identical sampled rows/output |
| 6 | (165-02) `/analysis?fen=<url-encoded FEN>` loads that position as a free-play root; board shows it, moves playable | ✓ VERIFIED | Code: `Analysis.tsx` line 700-704 fen-seeding effect calls existing `loadMainLine([], rootFenSeed)`; Human-verify Task 3 checkpoint executed during plan execution and approved ("approved" per 165-02-SUMMARY.md) |
| 7 | (165-02) `?line=` still works unchanged; precedence game_id > fen > line (fen wins) | ✓ VERIFIED | Code: line-effect guard (line 688) includes `rootFenSeed !== null` → early-returns when a FEN is present; fen-effect guard (line 700) requires `rootFenSeed !== null`. Both guards check `rootFenSeed` directly (not "did the other effect already run"), so the outcome is deterministic by static analysis regardless of effect execution order — game_id already wins via the separate `isGameMode` guard on the game-mode effect (line 674) |
| 8 | (165-02) `buildAnalysisFenUrl` encodeURIComponent-encodes; `parseAnalysisFenParam` decodes+validates via chess.js, round-trips, returns null for null/empty/garbage (incl. malformed percent-escape, CR-01) | ✓ VERIFIED | `npm test -- --run src/lib/analysisUrl`: 24/24 tests passed, including the CR-01 regression test (`'50%'` / `'%'` → null); `npx tsc -b` exits 0 |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/lib/frontend-alias-hook.mjs` | `@/` resolve hook → live frontend TS | ✓ VERIFIED | Exists, substantive (uses `registerHooks`), wired — successfully resolves imports in both `gem-parity.check.mjs` and `gem-elo-calibration.mjs` runs |
| `scripts/lib/gem-parity.check.mjs` | Wave-0 gem-logic parity tripwire | ✓ VERIFIED | Exists, substantive, runs and passes independently |
| `scripts/gem-elo-calibration.mjs` | Full calibration harness | ✓ VERIFIED | Exists (683 lines), substantive, runs end-to-end producing schema-correct output |
| `reports/data/gem-elo-calibration-<ts>.tsv` (generated) | D-05 schema TSV | ✓ VERIFIED | Generated on independent re-run; header matches exact D-05 column order; 6 `maia_p_*` + 6 `gem_*` columns; `analysis_url` contains `encodeURIComponent`'d FEN with `%20` |
| `reports/data/gem-elo-calibration-<ts>-summary.tsv` (generated) | drop-off summary | ✓ VERIFIED | Generated; gem-detection rate per rung (20%→0%) + percentiles + skip counts present |
| `frontend/src/lib/analysisUrl.ts` (new exports) | `buildAnalysisFenUrl`, `parseAnalysisFenParam` | ✓ VERIFIED | Both exported; CR-01 fix confirmed present (decode inside try/catch, line 121) |
| `frontend/src/lib/analysisUrl.test.ts` (extended) | build/parse/round-trip/garbage cases | ✓ VERIFIED | 24 tests total, incl. CR-01 malformed-percent-escape regression test |
| `frontend/src/pages/Analysis.tsx` | reads `?fen=`, seeds free-play root, enforces precedence | ✓ VERIFIED | `fenParam`/`rootFenSeed` read (line 446-447), new seeding effect (700-704), precedence guard on line-effect (688) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `frontend-alias-hook.mjs` | `frontend/src/*.ts` | `registerHooks` resolve rewrite | ✓ WIRED | Confirmed by successful live-source import in both harness and parity check runs |
| CSV `san` | canonical SAN | `new Chess(fen).move(csvSan).san` | ✓ WIRED | `sampleStratified` line 303 canonicalizes lazily on reservoir-slot win; `gem-elo-calibration.mjs` main loop uses `canonSan` throughout |
| Stockfish grades | `summarizeForGem` | keyed by `pv[0]`, white-POV normalized | ✓ WIRED | `gradePosition` (lines 482-508): keys `gradeBySan` by decoded `pv[0]` SAN, applies `whitePovSign` to cp/mate before storing |
| `parseAnalysisFenParam` | chess.js validation | try/catch around decode+construct | ✓ WIRED | Lines 114-127 of `analysisUrl.ts`; decode now inside try (CR-01 fix, commit `2cbde3ef`) |
| fen-seeding effect | `loadMainLine([], rootFenSeed)` | existing hook method, no new API | ✓ WIRED | `Analysis.tsx` line 702; `?line=` effect guarded by `rootFenSeed !== null` (see truth 7) for deterministic precedence |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SEED-094 | 165-01, 165-02 | Gem-move ELO calibration brilliant-moves harness (SEED-094-gem-move-elo-calibration-brilliant-moves-harness.md) | ✓ SATISFIED | Both plans declare `requirements: [SEED-094]`; harness + deep-link both implemented and verified above; no orphaned sub-requirements found in ROADMAP.md phase 165 entry (single requirement ID, fully covered) |

No orphaned requirements — SEED-094 is the sole requirement mapped to Phase 165 in ROADMAP.md, and both plans claim it.

### Anti-Patterns Found

None. Grepped all 6 phase-modified files for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER|placeholder|not yet implemented|coming soon` — zero hits in phase-authored code. (Pre-existing unrelated "placeholder" comments in `Analysis.tsx` at lines 1017/1540/1709 predate this phase and are outside its diff.)

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Gem-parity tripwire passes | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/gem-parity.check.mjs` | exit 0, PASS printed | ✓ PASS |
| Harness smoke run (independent re-run) | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/gem-elo-calibration.mjs --n 5 --seed 1 --movetime 800` | exit 0; TSV+summary written; identical to prior run | ✓ PASS |
| Frontend unit tests (analysisUrl) | `cd frontend && npm test -- --run src/lib/analysisUrl` | 24/24 passed | ✓ PASS |
| Frontend type-check | `cd frontend && npx tsc -b` | exit 0, no output | ✓ PASS |
| Frontend lint | `cd frontend && npm run lint` | 0 errors (3 unrelated warnings in `coverage/` build artifacts) | ✓ PASS |
| Knip (dead-export check) | `cd frontend && npx knip` | no hits for analysisUrl/Analysis.tsx new symbols | ✓ PASS |

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` convention; the phase's own verification commands (gem-parity check, harness smoke run) were run directly above and serve the same function.

### Human Verification Required

None outstanding. The phase's one `checkpoint:human-verify` gate (165-02 Task 3 — exercising `?fen=` in a live browser: mid-game FEN loads a playable free-play root, `?line=` unaffected, garbage FEN degrades gracefully) was executed during plan execution and approved by the user ("approved", per `165-02-SUMMARY.md` Task Commits section and `human_judgment: true` / `status: pass` in its coverage frontmatter). No new human-verification items were identified during this retroactive check.

### Gaps Summary

No gaps. Both plans' must-haves (5 truths + 3 artifacts + 3 key links for 165-01; 3 truths + 3 artifacts + 2 key links for 165-02) are verified against the actual codebase, not just SUMMARY.md claims:

- Independently re-ran the gem-parity check and the `--n 5` harness smoke test (not just trusting the executor's prior run) — both reproduced identical, schema-correct output.
- Read the full 683-line harness source and confirmed the 1-Stockfish-grade + 6-Maia-forward-pass invariant, SAN canonicalization, and white-POV normalization are implemented as specified, not stubbed.
- Confirmed the post-review CR-01 fix (`decodeURIComponent` moved inside the try/catch in `parseAnalysisFenParam`) is present in the current `analysisUrl.ts` and covered by a dedicated regression test, both of which pass.
- Confirmed `gemMove.ts`/`GEM_MAIA_MAX_PROB` were untouched by this phase (git log shows no phase-165 commits touching that file), respecting the plan's explicit "do not modify" boundary.
- Confirmed the deferred full `--n 3000` (~2.5h) soak is explicitly out of scope per the plan's own `success_criteria` — not treated as a gap.

Phase goal achieved. Ready to proceed.

---

*Verified: 2026-07-11T15:55:00Z*
*Verifier: Claude (gsd-verifier)*
