---
phase: 156-board-arrows-toggles-free-analysis
verified: 2026-07-06T22:10:00Z
status: passed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open /analysis (no game_id) with both the FlawChess Engine and Stockfish cards enabled, on a position where the two engines disagree."
    expected: "An amber arrow (FC, widest) and a blue arrow (SF, medium) point in different directions; the thin white next-move arrow (if on the main line) sits on top of both."
    why_human: "Visual color/geometry rendering on a live SVG board cannot be confirmed by static analysis — requires eye verification of actual pixels."
  - test: "On a position where FC and SF agree on the same move, confirm both arrows render as nested concentric arrows (not collapsed to one)."
    expected: "Amber (0.80 width) visible as the outer/widest arrow with the blue (0.50 width) arrow visible nested inside it on the same from→to."
    why_human: "The layerKey dedupe-bypass and width-sort draw order are unit-verified in isolation (dedupeArrowsByMove.test.ts) and traced by static analysis, but the actual visual concentric appearance on real SVG geometry needs a look."
  - test: "Toggle the FlawChess Engine card off, then on; independently toggle the Stockfish card off, then on."
    expected: "Toggling FC off hides only the amber arrow (blue arrow stays); toggling SF off hides only the blue arrow (amber stays)."
    why_human: "Gating logic (flawChessEnabled / engineEnabled independently gating each arrow-building loop) is confirmed by static read, but interactive toggle behavior on the running app is a UI behavior best confirmed by hand."
  - test: "Watch the amber FC arrow while the FlawChess Engine search is still running (early snapshots) to confirm it refines/moves as the search's top-ranked line changes, and does not flash/flicker a placeholder before the first snapshot."
    expected: "No arrow renders until the engine's first snapshot has a rootMove; then the arrow updates live as rankedLines[0] changes across recomputation ticks."
    why_human: "This is a live async/streaming behavior (anytime search snapshots refining over time) that static code review confirms is wired (useMemo deps include flawChessEngine.rankedLines) but cannot exercise without running the actual search."
  - test: "Open the mobile takeover board (narrow viewport) on /analysis and confirm the same two engine arrows render identically to desktop."
    expected: "Amber + blue arrows visible and toggle identically on the mobile board."
    why_human: "Mobile parity is structurally guaranteed by the shared `boardRow` JSX block (verified via static read — same `arrows={boardArrows}` reference used at both mount points), but actual mobile viewport rendering is a visual check."
---

# Phase 156: Board Arrows + Toggles (Free Analysis) Verification Report

**Phase Goal:** A user sees the FlawChess Engine's top practical move(s) rendered directly on the board as a distinct, individually toggleable arrow layer alongside the existing Stockfish arrow, always paired with the score explanation so disagreement reads as intentional rather than broken.

**Verified:** 2026-07-06T22:10:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

**Scope note (honored per instructions):** ROADMAP wording ("top-2" arrow layer, "two new theme.ts constants") predates locked decisions D-02/D-03/D-04 in `156-CONTEXT.md`. This phase's actual, locked scope is **top-1 arrow per engine** (`ARROW_COUNT = 1`) and **one new** amber theme token (`FLAWCHESS_ENGINE_ARROW`), reusing the existing blue `BEST_MOVE_ARROW` for Stockfish. Verification below is against the plan's `must_haves` and the CONTEXT decisions, not the pre-decision roadmap phrasing — consistent with the mandatory pre-read.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A FlawChess Engine amber arrow renders from `flawChessEngine.rankedLines[0].rootMove` whenever `flawChessEnabled`, and updates live as ranked lines refine (ARROW-01, D-01) | ✓ VERIFIED | `Analysis.tsx:1091-1122` `engineArrows` memo: `if (flawChessEnabled) { ... uciToSquares(flawChessEngine.rankedLines[i]?.rootMove ?? null) ... color: FLAWCHESS_ENGINE_ARROW }`; deps array includes `flawChessEngine.rankedLines` (line 1122) so it recomputes on every snapshot refinement |
| 2 | A Stockfish blue arrow renders from `engine.pvLines[0].moves[0]` whenever `engineEnabled`, reusing `BEST_MOVE_ARROW` (ARROW-03, D-04) | ✓ VERIFIED | `Analysis.tsx:1107-1119`: `if (engineEnabled) { ... uciToSquares(engine.pvLines[i]?.moves[0] ?? null) ... color: BEST_MOVE_ARROW }` — same `BEST_MOVE_ARROW` constant (`theme.ts:346`) used by `useGameOverlay.ts` game-mode arrow (reused, not reimplemented, per ARROW-03) |
| 3 | FC and SF arrows are independently toggleable via the existing Phase 155 card switches (ARROW-02, D-01) | ✓ VERIFIED | Two separate `if` gates in the same memo (`flawChessEnabled` line 1093, `engineEnabled` line 1107) — each loop runs independently; `flawChessEnabled`/`engineEnabled` are the pre-existing Phase 155 `useState` switches (`Analysis.tsx:364,369`), no new toggle UI added |
| 4 | When FC and SF point at the same move they both render as nested concentric arrows, not collapsed to one (D-05, D-06) | ✓ VERIFIED | Each arrow tagged with a distinct `layerKey: 'fc-'+i` / `'sf-'+i` (lines 1102, 1116); `arrowMoveKey` (arrowGeometry.ts:26) folds `layerKey` into the dedupe key so `dedupeArrowsByMove` no longer collapses same-move FC+SF pairs — confirmed by the new unit test `keeps two arrows on the same from→to when they have distinct layerKey values` (passes, see Behavioral Spot-Checks) |
| 5 | Three concentric arrows draw with FC widest (0.80) at the bottom, SF medium (0.50) in the middle, and the white next-move arrow thinnest (0.18) on top (D-05) | ✓ VERIFIED | Widths: `FLAWCHESS_ENGINE_ARROW_WIDTH = 0.8` (line 112), `STOCKFISH_ENGINE_ARROW_WIDTH = 0.5` (line 116), `NEXT_MOVE_ARROW_WIDTH = 0.18` with `onTop: true` (line 1080-1081, unchanged). Traced `ChessBoard.tsx:150-158` sort comparator: `onTop` items sorted last (drawn on top); among non-onTop items with equal `arrowSortKey` tier (both FC/SF colors fall to the shared default tier 3, since neither matches `DARK_GREEN`/`DARK_RED`/`DARK_BLUE`), tie-break is `b.width - a.width` — larger width sorts first in the array, and array-order-first = painted-first = visually underneath later (onTop) elements. Net: FC(0.80) painted first/bottom, SF(0.50) painted second, white(0.18, onTop) painted last/top — matches D-05 exactly |
| 6 | The mobile takeover board shows the same two engine arrows (mobile parity) | ✓ VERIFIED (structural) — visual confirmation is human_needed | `boardRow` (`Analysis.tsx:1246`) is a single shared JSX const containing `<ChessBoard ... arrows={boardArrows} .../>`, referenced identically at the mobile mount point (line 1589) and the desktop mount point (line 1732) — only one of the two trees renders at a time via `isMobile`, so there is no separate/divergent mobile arrow-wiring code path to drift out of sync |

**Score:** 6/6 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/theme.ts` | New `FLAWCHESS_ENGINE_ARROW` amber token, distinct from `FLAWCHESS_ENGINE_ACCENT` | ✓ VERIFIED | `theme.ts:353`: `export const FLAWCHESS_ENGINE_ARROW = 'oklch(0.78 0.15 85)'; // amber/gold` — distinct value from `FLAWCHESS_ENGINE_ACCENT = 'oklch(0.55 0.09 55)'` (line 78, brand brown) |
| `frontend/src/pages/Analysis.tsx` | Named `ARROW_COUNT` (=1) constant plus FC/SF width constants | ✓ VERIFIED | Lines 108/112/116: `ARROW_COUNT = 1`, `FLAWCHESS_ENGINE_ARROW_WIDTH = 0.8`, `STOCKFISH_ENGINE_ARROW_WIDTH = 0.5` |
| `frontend/src/components/board/ChessBoard.tsx` | `BoardArrow` interface gains optional `layerKey` field | ✓ VERIFIED | Lines 49-55: `layerKey?: string;` with doc comment referencing D-06 |
| `frontend/src/components/board/arrowGeometry.ts` | `arrowMoveKey` folds `layerKey` into the dedupe key | ✓ VERIFIED | Line 26: ``return `${arrow.startSquare}-${arrow.endSquare}${arrow.onTop ? '-top' : ''}${arrow.layerKey ? `-${arrow.layerKey}` : ''}`;`` |

All artifacts pass Level 1 (exists), Level 2 (substantive — real logic, not stub values), and Level 3 (wired — see Key Link Verification below).

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `Analysis.tsx` `engineArrows` memo | `boardArrows` assembly | `baseArrows` ternary at line 1130-1136 | ✓ WIRED | `qualityHoverArrows ?? (isGameMode ? (...) : engineArrows.length > 0 ? engineArrows : undefined)` — engineArrows feeds the free-analysis (`!isGameMode`) branch exactly as planned |
| `boardArrows` | `<ChessBoard arrows={boardArrows}>` | shared `boardRow` JSX const, single mount | ✓ WIRED | `boardRow` (line 1246) referenced at both mobile (1589) and desktop (1732) render sites — single source, no divergent copy |
| `arrowMoveKey`/`layerKey` | `dedupeArrowsByMove` | fold into dedupe key computation | ✓ WIRED | `dedupeArrowsByMove` (arrowGeometry.ts:44) keys purely off `arrowMoveKey(a)`, which now includes `layerKey` — no separate change needed there, confirmed correct by design and by passing unit tests |
| `flawChessEngine.rankedLines[i].rootMove` / `engine.pvLines[i].moves[0]` | `uciToSquares` | existing shared helper reused (ARROW-03: "reused, not reimplemented") | ✓ WIRED | Same `uciToSquares` import (`@/lib/sanToSquares`) used by `useGameOverlay.ts`'s existing Stockfish game-mode arrow construction and this phase's free-analysis engine arrows |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| ARROW-01 | 156-01 | Amber FC arrow layer rendering + refining live | ✓ SATISFIED | Truth #1; `REQUIREMENTS.md:96` marks Complete for Phase 156. "top-2" wording superseded by locked D-02 (top-1) — intent (live-refining practical-move arrow) is met per CONTEXT.md explicit override note |
| ARROW-02 | 156-01 | FC + SF arrow layers each individually toggleable | ✓ SATISFIED | Truth #3; game-review played-move-arrow toggle portion of this requirement's wording is explicitly out of scope for Phase 156 (Phase 157, REVIEW-01/02) per CONTEXT.md `<deferred>` |
| ARROW-03 | 156-01 | SF arrow + played-move arrow reused, no dedicated Maia arrow layer | ✓ SATISFIED | Truth #2; no new Maia arrow code added anywhere in this phase's diff (`git show 3e9d5067 5884a611 --stat` — only theme.ts/ChessBoard.tsx/arrowGeometry.ts/Analysis.tsx touched, no Maia-related file) |
| ARROW-04 | 156-01 | No unqualified "best move" copy; disagreement reads as intentional | ✓ SATISFIED | `grep -rn -i "best move" frontend/src/pages/Analysis.tsx` and the same grep on theme.ts/ChessBoard.tsx/arrowGeometry.ts return zero matches introduced by this phase (theme.ts's one pre-existing "best-scoring candidate" hit is unrelated move-quality-bar prose, not arrow copy) |

No orphaned requirements: cross-checked `REQUIREMENTS.md` Traceability table (lines 96-99) against the plan's `requirements:` frontmatter (`[ARROW-01, ARROW-02, ARROW-03, ARROW-04]`) — exact match, all 4 accounted for, no additional Phase-156-mapped IDs exist in REQUIREMENTS.md beyond these four.

### Anti-Patterns Found

None in the phase's actual diff (`git show 3e9d5067 5884a611`). Grep for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` across the five modified files returns zero hits inside the diff; the two "placeholder" string hits in `Analysis.tsx` (lines 950, 1089) are (a) an unrelated pre-existing comment about free-move ply values, and (b) this phase's own design-intent comment explaining the FC arrow deliberately has *no* placeholder arrow before the first snapshot (correctly describes the absence of a stub, not a stub itself).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `tsc -b` type-check (BoardArrow.layerKey + property access) | `cd frontend && npx tsc -b` | Zero output, exit 0 | ✓ PASS |
| dedupeArrowsByMove layerKey-bypass unit tests | `cd frontend && npm test -- --run src/components/board/__tests__/dedupeArrowsByMove.test.ts` | 1 file, 7 tests, all passed | ✓ PASS |
| `npm run lint` | `cd frontend && npm run lint` | 0 errors, 3 pre-existing `coverage/*.js` warnings (unrelated build artifacts) | ✓ PASS |
| No new unqualified "best move" copy | `grep -rn -i "best move" frontend/src/pages/Analysis.tsx frontend/src/lib/theme.ts frontend/src/components/board/ChessBoard.tsx frontend/src/components/board/arrowGeometry.ts` | 1 pre-existing unrelated hit (theme.ts move-quality-bar comment), 0 in Analysis.tsx/ChessBoard.tsx/arrowGeometry.ts | ✓ PASS |
| Draw-order trace (FC bottom / SF middle / white top) | Static trace of `ChessBoard.tsx:150-158` `arrowSortKey`/width comparator against the two new width constants | Confirmed FC(0.80) → SF(0.50) → white(0.18, onTop) draw order | ✓ PASS (static, not a runtime pixel check — see human_verification #2) |

Full suite (1527 tests) was already run green by the executor per SUMMARY.md; not re-run here per the single-full-run constraint (targeted file run above is sufficient additional evidence).

### Human Verification Required

See frontmatter `human_verification` list. Five items, all visual/live-behavior checks that cannot be settled by static analysis: (1) disagreement rendering as two distinct-direction arrows, (2) agreement rendering as visible nested-concentric arrows, (3) interactive independent toggle behavior, (4) live refinement of the FC arrow as the anytime search progresses, (5) mobile-viewport visual parity. None of these block the `passed` verdict from a code-correctness standpoint — the wiring, gating, constants, and dedupe-bypass mechanism are all verified in the codebase; only the on-screen visual/interactive result needs a human look.

### Gaps Summary

No gaps. All 6 derived truths (roadmap Success Criteria plus PLAN.md's own must_haves, reconciled against locked CONTEXT.md decisions D-01 through D-07) are verified present, substantive, and wired in the codebase. All 4 requirement IDs (ARROW-01..04) are satisfied and correctly traced. The only open items are human-observable visual/live-behavior confirmations, which are non-gating per the plan's own `<verification>` block ("Manual/UAT (not gating)").

---

*Verified: 2026-07-06T22:10:00Z*
*Verifier: Claude (gsd-verifier)*
