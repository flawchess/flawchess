---
phase: 163-gem-moves-maia-findability-move-badges-on-analysis-seed-092
verified: 2026-07-10T20:56:00Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 7/8
  gaps_closed:

    - "Board and move-list gem badges never disagree with a backend-flagged severity for the same move (WR-05 move-list side) — fixed in commit 188c4a22"
  gaps_remaining: []
  regressions: []
human_verification:

  - test: "Live-browser UAT on /analysis (163-VALIDATION.md's designated manual-only row): navigate to a known gem ply"
    expected: "Violet Gem board-corner marker, move-list GemIcon, violet MovesByRatingChart curve + 'Gem' tooltip label, and popover gem copy all render correctly and legibly"
    why_human: "jsdom performs no real layout/paint — SVG/circle geometry, icon centering, and actual color rendering cannot be validated programmatically; this was the plan's own designated manual-only UAT item from the start"
---

# Phase 163: Gem moves — Maia-findability move badges on /analysis (SEED-092) Verification Report

**Phase Goal:** Badge the rare move that is both the engine's clearly-only good move AND hard for a human at the player's rating to find, as the positive counterpart to the flaw glyphs. Detection is two-condition (C1 Maia probability ≤ GEM_MAIA_MAX_PROB=0.03, C2 expected-score gap to best alternative ≥ MISTAKE_DROP). Lazy per-visited-ply classification from the existing MultiPV=2 free run + grading run + Maia curve, cached per ply. Surfaces in Maia-violet (MAIA_ACCENT): board-corner marker + move-list glyph using the lucide Gem icon, MAIA_ACCENT curve + tooltip label in MovesByRatingChart, short popover copy. Pure frontend; no backend changes, no cross-game statistics.

**Verified:** 2026-07-10T20:56:00Z
**Status:** human_needed (all automated checks pass; one designated manual-only visual UAT item remains)
**Re-verification:** Yes — after gap closure (previous run: gaps_found, 7/8)

## Re-Verification Summary

The single gap from the initial verification — the WR-05 severity-vs-gem precedence rule was applied only to the board marker, leaving the move list able to show a GemIcon for a move the board correctly refused to badge — was fixed in commit `188c4a22` and independently re-verified:

1. **`frontend/src/pages/Analysis.tsx`** — `moveListMarkers.addGem` now returns early when the existing entry carries a severity (`if (existing?.severity != null) return;`) with a WR-05 comment; the stale "mutual exclusivity by construction" comment corrected (severity-free merges still keep tactic chips). Confirmed in the working tree, not just the diff.
2. **`frontend/src/components/analysis/VariationTree.tsx`** — `resolveMarkerIcon` precedence flipped: blunder/mistake severity wins, gem second; docstring corrected to scope the exclusivity claim to the live pipeline. Confirmed in the working tree.
3. **`frontend/src/pages/__tests__/Analysis.test.tsx`** — the WR-05 regression test now also asserts `expect(moveListGemIconPresent()).toBe(false);`. This assertion is meaningful: during the initial verification I instrumented the pre-fix code with the same check and it returned `true`, so the test demonstrably guards the fixed behavior (fail-first confirmed).

Regression check on previously-passed items: full frontend suite 1739/1739 green, `npx tsc -b` clean, `npm run lint` clean (only pre-existing `coverage/` warnings), Analysis.test.tsx 28/28 including all 9 gem tests. No regressions.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `classifyGem`/`summarizeForGem` implement C1+C2 exactly per D-01/D-02/D-04/D-07, no re-derived sigmoid/threshold | VERIFIED | `frontend/src/lib/gemMove.ts` imports `evalToExpectedScore`/`MoverColor` from `@/lib/liveFlaw` and `MISTAKE_DROP` from `@/generated/flawThresholds`; `GEM_MAIA_MAX_PROB = 0.03` single constant; unit tests (`gemMove.test.ts`) all green including both free-lunch guards, D-01 lost-position-qualifies, D-02 no-ply-guard, D-04 mover-agnostic, and the WR-02 null/null-skip cases |
| 2 | `MoveQuality` gains a 6th `'gem'` value folded into the `'good'` display bucket (never `'pending'`) | VERIFIED | `moveQuality.ts` line 36: `'best' \| 'good' \| 'inaccuracy' \| 'mistake' \| 'blunder' \| 'gem'`; `bucketKeyForQuality` `case 'gem':` present; `FlawSeverity`/`classifyMoveQuality` untouched (grep confirms) |
| 3 | Gem badge visual primitives (`GEM_GLYPH`, `GemIcon`, `SquareMarker.gem`) are a single drift-proof source, MAIA_ACCENT-colored | VERIFIED | `gemGlyph.ts` imports `MAIA_ACCENT` (no hard-coded oklch); `GemIcon.tsx` renders white lucide `Gem` in a `GEM_GLYPH.color` circle w/ `<title>Gem move</title>` (IN-02 fix present); `boardMarkers.tsx` `SquareMarker.gem?: boolean`, `severity?` now optional, gem branch reuses existing `MARKER_RADIUS`/`MARKER_CORNER_OVERLAP`; `boardMarkers.test.tsx` covers both branches, passing |
| 4 | Chart curve + SAN label render MAIA_ACCENT violet for a gem candidate; tooltip reads 'Gem'; stroke emphasis unaffected | VERIFIED | `MovesByRatingChart.tsx` `case 'gem': return MAIA_ACCENT;` (line 191-192); emphasis logic keys off SAN identity, unchanged; analysis-component tests green |
| 5 | `UnifiedMovePopover` shows a gated violet gem copy line via `isGem`; `MaiaMoveQualityBar` wires it per hovered move, segments unchanged | VERIFIED | `UnifiedMovePopover.tsx`: `isGem` prop, `Gem` icon, copy "Gem — players at this rating almost never find this." (IN-01 fix applied); `MaiaMoveQualityBar.tsx` line 529: `isGem={qualityBySan.get(m.san)?.quality === 'gem'}`; segment loop (`bucketMovesByQuality`) unchanged |
| 6 | The arrival move into any visited node (mainline + free variation, both colors) is classified against the PARENT position's cached data, stuck per node in `gemByNode` (D-04/D-05/D-06) | VERIFIED | `gemActive = currentNodeId !== null && parentFen !== null` — no `isGameMode`/`isOnPvLine` exclusion (D-05); `gemCandidate` reads `maiaCurveByFen.get(parentFen)` + `gradeSummaryByFen.get(parentFen)` (Pitfall 1); `gemByNode` one-way latch mirrors `liveFlawByNode`; 9 integration tests in `Analysis.test.tsx`'s "Gem moves" describe block cover white/black/mainline/free/sticky/ELO-re-derivation/WR-04/WR-05, all passing |
| 7 | C1 re-derives on ELO-slider movement without disturbing the ELO-free grade cache (D-03, Pitfall 6) | VERIFIED | `gradeSummaryByFen` effect deps have no `selectedElo`; `gemCandidate`/`boardSquareMarkers` read the LIVE memo at `selectedElo`; dedicated test "re-derives C1 when the ELO slider moves" passes |
| 8 | Board and move-list gem badges never disagree with a backend-flagged severity for the same move | VERIFIED (closed in re-verification) | Commit `188c4a22`: `addGem` yields to an existing severity entry; `resolveMarkerIcon` checks blunder/mistake before gem; WR-05 regression test asserts both `boardGemMarkerPresent() === false` AND `moveListGemIconPresent() === false` in the divergence scenario — passing, and confirmed fail-first against the pre-fix code |

**Score:** 8/8 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/gemMove.ts` | `GEM_MAIA_MAX_PROB`, `classifyGem`, `summarizeForGem` | VERIFIED | Present, pure, fully unit-tested, WR-02 null/null-skip fix present |
| `frontend/src/lib/__tests__/gemMove.test.ts` | Unit tests for above | VERIFIED | All green |
| `frontend/src/lib/gemGlyph.ts` | `GEM_GLYPH` single-source record | VERIFIED | Present, imports `MAIA_ACCENT` |
| `frontend/src/components/icons/GemIcon.tsx` | React gem icon component | VERIFIED | Present, `SeverityGlyphIcon`-shape-compatible, `<title>` added (IN-02) |
| `frontend/src/components/board/__tests__/boardMarkers.test.tsx` | Gem badge + regression tests | VERIFIED | Present, passing |
| `frontend/src/pages/Analysis.tsx` | Full wiring (caches, memos, sticky cache, markers) | VERIFIED | All memos/caches present and correctly gated per D-01..D-08; WR-05 guard now on BOTH board and move-list surfaces |
| `frontend/src/components/analysis/VariationTree.tsx` | `FlawMarkerEntry.gem`, `GemIcon` render at 3 sites | VERIFIED | Present at desktop/mobile/sibling-chip sites via shared `resolveMarkerIcon`; severity-wins precedence correct |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `gemMove.ts` | `@/lib/liveFlaw`, `@/generated/flawThresholds` | import | WIRED | `evalToExpectedScore`, `MoverColor`, `MISTAKE_DROP` all imported, never re-derived |
| `MoveQuality 'gem'` | `bucketKeyForQuality` → `'good'` | switch case | WIRED | Confirmed via `bucketMovesByQuality` tests |
| `gemGlyph.ts`/`boardMarkers.tsx` | `@/lib/theme` (`MAIA_ACCENT`) | import | WIRED | No hard-coded oklch literal in either file |
| `Analysis.tsx qualityBySanWithGem` | `MaiaHumanPanel` (desktop + mobile) | prop | WIRED | `grep -c "qualityBySan={qualityBySanWithGem}"` = 2; `qualityBySan={qualityBySan}` = 0 |
| `Analysis.tsx gemCandidate/gemByNode` | `boardSquareMarkers`/`moveListMarkers` | memo union | WIRED | Severity-wins guard present on both surfaces (WR-05 + 188c4a22) |
| `useMaiaEngine`/`useStockfishGradingEngine` | `Analysis.tsx` per-FEN caches | `resultFen`/`gradeMapFen` guard | WIRED | WR-03 fix confirmed present in both hooks and both cache-write guards |

### Requirements Coverage

No `.planning/REQUIREMENTS.md` exists for this milestone; traceability is via CONTEXT.md decisions D-01..D-08.

| Decision | Description | Status | Evidence |
|----------|-------------|--------|----------|
| D-01 | Lost-position best-try still qualifies (no still-losing exclusion) | SATISFIED | `classifyGem` has no such check; unit test asserts `bestEs=0.20, secondBestEs=0.05 → true`; WR-02 fix additionally protects this from phantom-0.5 suppression |
| D-02 | No opening-ply guard | SATISFIED | `classifyGem` has no ply parameter; `gemActive` has no ply-based gate |
| D-03 | C1 uses the page's selected ELO, re-derives on slider move | SATISFIED | `gemCandidate`/`boardSquareMarkers` read live `selectedElo`; dedicated integration test passes; `gradeSummaryByFen` deliberately ELO-free |
| D-04 | Both players' moves get gems (no color filter) | SATISFIED | `classifyGem` has no color parameter; white + black integration tests both pass |
| D-05 | Any visited board move classifies (mainline + free variations) | SATISFIED | `gemActive` has no `isGameMode`/`isOnPvLine` exclusion; mainline + free-node tests pass; move-list precedence gap closed by 188c4a22 |
| D-06 | Sticky per-node cache mirroring `liveFlawByNode`, mechanism-locked | SATISFIED | `gemByNode` one-way latch present, reset alongside `liveFlawByNode` at both Reset branches; sticky-navigation test passes |
| D-07 | `GEM_MAIA_MAX_PROB = 0.03` flat constant, no `P_REF_ANCHORS` reuse | SATISFIED | Constant present and asserted; grep confirms no `P_REF_ANCHORS`/`pRefForElo` reference in `gemMove.ts` |
| D-08 | No calibration tooling in-phase | SATISFIED | No such tooling added; deferred per CONTEXT.md |

### Anti-Patterns Found

None remaining. The two Warning-level findings from the initial verification (missing severity-wins guard in `moveListMarkers.addGem`; stale mutual-exclusivity docstring in `VariationTree.tsx`) were both resolved by commit `188c4a22`. No unreferenced `TBD`/`FIXME`/`XXX` markers in any phase-touched file.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Analysis integration suite (incl. 9 gem tests + extended WR-05) | `npx vitest run src/pages/__tests__/Analysis.test.tsx` | 28/28 passed | PASS |
| Full frontend suite | `npm test -- --run` | 1739/1739 passed | PASS |
| Type check | `npx tsc -b` | clean | PASS |
| Lint | `npm run lint` | clean (0 errors; 3 pre-existing warnings in generated `coverage/` files, unrelated) | PASS |
| Dead-export check | `npm run knip` | clean (run during initial verification; no export surface changed by 188c4a22) | PASS |
| WR-05 move-list fix fail-first evidence | Pre-fix instrumentation of the WR-05 test returned `MOVE_LIST_GEM_ICON_PRESENT=true`; post-fix the committed assertion `expect(moveListGemIconPresent()).toBe(false)` passes | Behavior demonstrably changed by the fix | PASS |

### Human Verification Required

| # | Test | Expected | Why Human |
|---|------|----------|-----------|
| 1 | Live-browser UAT (163-VALIDATION.md's designated manual-only row): navigate to a known gem ply on `/analysis` | Violet Gem board-corner marker, move-list `GemIcon`, violet `MovesByRatingChart` curve + 'Gem' tooltip label, popover gem copy all render correctly and legibly | jsdom cannot fully validate SVG/circle geometry, real layout, or actual color rendering — this was the plan's own designated manual-only item (163-VALIDATION.md), not newly introduced by verification |

### Gaps Summary

No gaps remain. All 8 observable truths verified against the actual codebase; all 7 code-review findings (5 warnings + 2 info) plus the verification-found WR-05 move-list extension are confirmed fixed in code with regression coverage. The only outstanding item is the pre-planned manual visual UAT row (human_verification above), which is why the status is `human_needed` rather than `passed` — the verification contract reserves `passed` for phases with an empty human-verification section.

---

_Verified: 2026-07-10T20:56:00Z_
_Verifier: Claude (gsd-verifier)_
