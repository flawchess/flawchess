---
phase: 157-flawchess-agreement-verdict-prose-hoverable-moves
verified: 2026-07-07T06:25:48Z
status: passed
human_verification_completed: 2026-07-07 — both live UAT items (hover-arrow/popover/click-to-play on /analysis, and game-review parity on ?game_id&ply) confirmed by human
score: 8/8 must-haves verified (code + unit/component tests); 2 live-UAT items confirmed by human 2026-07-07
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open /analysis (free analysis) with Stockfish and FlawChess Engine both on. Hover the FlawChess-pick move span in the new agreement-verdict sentence below the ranked lines; confirm exactly one board arrow (amber) appears and any other engine arrows are suppressed while hovering. Hover the Stockfish-pick span; confirm the arrow switches to blue. Leave the span; confirm both persistent arrow layers are restored. Click a span while its popover is open; confirm the move is actually played on the board."
    expected: "Hovering a named move in the verdict sentence isolates that pick's board arrow in the correct tier color (amber = FlawChess, blue = Stockfish), overriding the persistent two-arrow layer; leaving restores both. Clicking a span while its popover is open plays that move on the board."
    why_human: "Component tests (FlawChessAgreementVerdict.test.tsx) verify the onHoverMovesChange/onPlayMove callbacks fire with the correct arguments in jsdom, but do not render the actual chessboard/arrow-overlay or confirm a real drag-free move executes on the live board. Both SUMMARYs explicitly state this live UAT was not performed during the automated execution."
  - test: "Open /analysis?game_id=<id>&ply=<n> for a real imported game with Stockfish on. Confirm the FlawChess card renders the same agreement-verdict sentence, hover/popover/click-to-play behavior, and arrow isolation as in free analysis (SC4, absorbs REVIEW-01)."
    expected: "The verdict, hover-arrow isolation, popover, and click-to-play behave identically on the game-review board to free analysis, with no visual or functional difference."
    why_human: "Verified structurally — FlawChessAgreementVerdict is inserted exactly once inside the single `flawChessCard` JSX variable, which is rendered at both the mobile human tab (Analysis.tsx:1548) and desktop human column (Analysis.tsx:1728), and `?game_id&ply` routes into the same Analysis.tsx component. No code path diverges. But no automated test actually loads a game-review URL and asserts on the rendered DOM, and REQUIREMENTS.md still lists REVIEW-01 as Pending pending this live confirmation."
---

# Phase 157: FlawChess Agreement Verdict (prose + hoverable moves) Verification Report

**Phase Goal:** The FlawChess Engine card gains a one-line prose verdict, analogous to the Maia position verdict, narrating whether the engine's top *practical* move agrees or diverges from Stockfish's top *objective* move — named moves hoverable (board arrow + practical/objective popover) and click-to-play. It renders on both free analysis and game review (shared Analysis.tsx), turning the side-by-side score badges into a plain-language read.

**Verified:** 2026-07-07T06:25:48Z
**Status:** passed (both live-UAT items confirmed by human 2026-07-07)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Prose verdict below FlawChess ranked lines states agreement/divergence, sourced from `engine.pvLines[0]` (not `engineTopLines[0]`), citing both evals; no bare "best move" (SC1) | ✓ VERIFIED | `frontend/src/components/analysis/FlawChessAgreementVerdict.tsx` renders `renderVerdictSentence` citing `formatScore(...)` for both picks; `Analysis.tsx:1518-1526` wires `stockfishLine={engine.pvLines[0] ?? null}` (grep confirms `engineTopLines` is never passed to the new component); `grep -in 'best move'` on the component and classifier files returns nothing |
| 2 | Two identical UCI picks classify `aligned` (D-04) | ✓ VERIFIED | `flawChessVerdict.ts:94-97` UCI-string equality check before drop math; `flawChessVerdict.test.ts` "same UCI move on both sides -> aligned, drop 0" passes |
| 3 | Divergent picks: win%-drop below `SHARP_DROP_THRESHOLD` → `safe`; at/above → `sharp`, inclusive boundary (D-05) | ✓ VERIFIED | `flawChessVerdict.ts:103` `drop < SHARP_DROP_THRESHOLD ? 'safe' : 'sharp'`; 3 tests (safe, sharp, exact-boundary inclusive-edge) pass |
| 4 | Missing objective eval on either side yields `null`, never a bogus tier (D-06) | ✓ VERIFIED | `flawChessVerdict.ts:67-75` null-gates flawChessLine/stockfishLine/objectiveEvalCp/both-evals-null; 4 dedicated tests pass |
| 5 | FlawChess side never reads/writes a mate field; eval is cp-only (Pitfall 4) | ✓ VERIFIED | `FlawChessVerdictMove.evalMate` hardcoded `null` on the FC side (`flawChessVerdict.ts:81`); mate-pick test passes |
| 6 | `SHARP_DROP_THRESHOLD` is the imported `BLUNDER_DROP` alias, no bare `0.15` literal; drop reuses `evalToExpectedScore` from `@/lib/liveFlaw` | ✓ VERIFIED | `grep -n '0.15' flawChessVerdict.ts` → empty; `export const SHARP_DROP_THRESHOLD = BLUNDER_DROP;` imported from `@/generated/flawThresholds`; `evalToExpectedScore` imported from `@/lib/liveFlaw`, no local sigmoid |
| 7 | Named moves are interactive spans: hover isolates board-arrow color (amber=FlawChess/blue=Stockfish), popover shows engine-labeled practical/objective two-line breakdown (omitting FC line for an unranked SF pick), click-while-open plays the move (D-09/D-10/D-11, SC2) | ✓ VERIFIED (component-level) / see Human Verification | `FlawChessAgreementVerdict.test.tsx` — 8 dedicated tests (hover-isolation restore-on-leave, FC-popover both-lines, SF-popover omitted-line, SF-popover included-line, click-while-open plays, click-while-closed only reveals) all pass, dispatching real DOM events (`fireEvent.focus/blur/pointerDown/click`) against the rendered component. The live on-board arrow rendering and actual free-move execution in the running app were not exercised by any automated test — routed to human verification |
| 8 | Three tiers via named constants, refining live in a fixed-height slot with no layout jump; muted prompt when Stockfish is off (D-02/D-03/D-06, SC3) | ✓ VERIFIED | Both the muted-slot and content-slot render paths use the identical `className="min-h-[1.5rem] text-sm"` wrapper (`FlawChessAgreementVerdict.tsx:250-256` and `:323-327`) — no layout-jump risk by construction; `engineEnabled=false` renders only the muted prompt without invoking the classifier (D-02/D-03 test); a null classifier result (missing `flawChessLine`) falls back to the same slot (D-06 test) |
| 9 | Verdict inserted exactly once inside the shared `flawChessCard` JSX so it renders identically on `/analysis` free analysis and game review (`?game_id&ply`) (SC4, absorbs REVIEW-01) | ✓ VERIFIED (structural) / see Human Verification | `grep -n 'FlawChessAgreementVerdict' Analysis.tsx` → exactly one import + one render call, inside the `flawChessCard` variable (line 1477); `flawChessCard` itself is referenced at both line 1548 (mobile human tab) and line 1728 (desktop human column); `?game_id`/`?ply` are parsed and gate the same `Analysis.tsx` component (no separate game-review page/component). Live confirmation on a real game-review URL was not performed — routed to human verification |

**Score:** 9/9 truths present, wired, and code-verified; 0 failed; 2 items (#7's live-app arrow/click behavior, #9's live game-review confirmation) additionally need human confirmation before REVIEW-01 can be marked Complete in REQUIREMENTS.md.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/flawChessVerdict.ts` | Pure, chess-free classifier module | ✓ VERIFIED | 107 lines, no chess.js/React/worker import, exports `FlawChessVerdictTier`, `FlawChessVerdictMove`, `FlawChessVerdictResult`, `SHARP_DROP_THRESHOLD`, `computeFlawChessVerdict` |
| `frontend/src/lib/flawChessVerdict.test.ts` | Wave-0 unit tests (D-04/D-05/D-06) | ✓ VERIFIED | 10 tests, all pass (`npx vitest run` confirmed independently) |
| `frontend/src/components/analysis/ProseSpan.tsx` | Content-agnostic hover/click-to-play span shell | ✓ VERIFIED | 102 lines; extracted verbatim button/Popover/ref wiring, parameterized via `children`; imported by both `MaiaMoveQualityBar.tsx` (thin `ProseMoveSpan` wrapper) and `FlawChessAgreementVerdict.tsx` |
| `frontend/src/components/analysis/FlawChessAgreementVerdict.tsx` | The prose verdict component | ✓ VERIFIED | 329 lines; consumes classifier, renders D-07 templates, D-09 hover isolation, D-10 popover, D-11 click-to-play |
| `frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx` | Component tests | ✓ VERIFIED | 12 tests, all pass, exercising real DOM events |
| `frontend/src/pages/Analysis.tsx` (modified) | Single wiring insertion | ✓ VERIFIED | Inserted once inside `flawChessCard`, sourced from `engine.pvLines[0]`/`flawChessEngine.rankedLines[0]`, wired to existing `setHoveredQualityMoves`/`playProseMove` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `flawChessVerdict.ts` | `@/generated/flawThresholds` | `SHARP_DROP_THRESHOLD = BLUNDER_DROP` | ✓ WIRED | No bare `0.15` literal anywhere in the module (grep-verified) |
| `flawChessVerdict.ts` | `@/lib/liveFlaw` | `evalToExpectedScore` | ✓ WIRED | Imported, used for both sides' win% computation, no re-derived sigmoid |
| `FlawChessAgreementVerdict.tsx` | `@/components/analysis/ProseSpan` | `ProseSpan` component | ✓ WIRED | Imported and rendered for both FC and SF picks |
| `FlawChessAgreementVerdict.tsx` | `@/lib/flawChessVerdict` | `computeFlawChessVerdict` | ✓ WIRED | Called inside a `useMemo` gated on `engineEnabled` |
| `Analysis.tsx` | `FlawChessAgreementVerdict` | `onHoverMovesChange={setHoveredQualityMoves}` | ✓ WIRED | Feeds the existing `qualityHoverArrows` overlay (unchanged this phase, confirmed still wins in the arrow-precedence chain) |
| `Analysis.tsx` | `FlawChessAgreementVerdict` | `onPlayMove={playProseMove}` | ✓ WIRED | Reuses the existing free-move handler verbatim, no new plumbing |
| `MaiaMoveQualityBar.tsx` | `ProseSpan` | `ProseMoveSpan` thin wrapper | ✓ WIRED | All 9 pre-existing Maia tests pass unchanged (regression-checked) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| flawChessVerdict unit tests (10) | `npx vitest run src/lib/flawChessVerdict.test.ts` | 10/10 pass | ✓ PASS |
| FlawChessAgreementVerdict component tests (12) | `npx vitest run src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx` | 12/12 pass | ✓ PASS |
| MaiaMoveQualityBar regression (9 tests, post-extraction) | `npx vitest run src/components/analysis/__tests__/MaiaMoveQualityBar.test.tsx` | 9/9 pass | ✓ PASS |
| Typecheck | `npx tsc -b` | exit 0, zero errors | ✓ PASS |
| Lint | `npm run lint` | 0 errors (3 unrelated `coverage/` artifact warnings) | ✓ PASS |
| Dead-export check | `npx knip` | no output (clean) | ✓ PASS |
| No bare "best move" string | `grep -rin 'best move' FlawChessAgreementVerdict.tsx flawChessVerdict.ts` | empty | ✓ PASS |
| No bare `0.15` threshold literal | `grep -n '0.15' flawChessVerdict.ts` | empty | ✓ PASS |

Live/visual behavioral spot-checks (arrow rendering on the real chessboard, a real drag/click-to-play move execution, and a real `?game_id&ply` page load) were intentionally NOT run — no dev server was started per this agent's "do not start servers" constraint, and per the phase's own context, these are the exact items both SUMMARYs flag as not covered by the automated run. See Human Verification below.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|--------------|------------|-------------|--------|----------|
| REVIEW-02 | 157-01, 157-02 | FlawChess card surfaces a prose agreement verdict citing both evals, named moves hoverable (arrow+popover) and click-to-play | ✓ SATISFIED | All code/test evidence above; `REQUIREMENTS.md` line 44 already marks it `[x]` Complete |
| REVIEW-01 | Not claimed in either plan's `requirements:` frontmatter, but explicitly folded into SC4 ("absorbs the old REVIEW-01 game-review-parity check") | Engine runs on the game-review board as well as free analysis | ? NEEDS HUMAN | Structurally guaranteed by the single shared `flawChessCard` insertion (evidence above), but `REQUIREMENTS.md` line 43 still lists it `[ ]` Pending, consistent with the fact that live confirmation on a real `?game_id&ply` URL was not performed. Not an orphaned requirement — ROADMAP.md's "Scope note" for Phase 157 explicitly documents this absorption; the Pending checkbox appears intentional pending the human-verification item above, not an oversight. |

No requirement IDs from the two PLAN frontmatters are unaccounted for; REVIEW-01's un-flipped checkbox is expected pending the human-verification step, not evidence of missing work.

### Anti-Patterns Found

None. Scanned all 6 phase-created/modified files (`flawChessVerdict.ts`, `flawChessVerdict.test.ts`, `ProseSpan.tsx`, `FlawChessAgreementVerdict.tsx`, `FlawChessAgreementVerdict.test.tsx`, `MaiaMoveQualityBar.tsx`) for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER`, stub returns, and hardcoded-empty props — the only match was the word "placeholder" inside a doc-comment describing D-10's *no-placeholder* rule ("otherwise it's omitted entirely, no placeholder"), which is documentation, not a stub marker.

### Human Verification Required

### 1. Live hover-arrow, popover, and click-to-play on /analysis

**Test:** Open `/analysis` (free analysis) with Stockfish and FlawChess Engine both on. Hover the FlawChess-pick move span in the new agreement-verdict sentence below the ranked lines; confirm exactly one board arrow (amber) appears and any other engine arrows are suppressed while hovering. Hover the Stockfish-pick span; confirm the arrow switches to blue. Leave the span; confirm both persistent arrow layers are restored. Click a span while its popover is open; confirm the move is actually played on the board.
**Expected:** Hovering a named move in the verdict sentence isolates that pick's board arrow in the correct tier color (amber = FlawChess, blue = Stockfish), overriding the persistent two-arrow layer; leaving restores both. Clicking a span while its popover is open plays that move on the board.
**Why human:** Component tests verify the `onHoverMovesChange`/`onPlayMove` callbacks fire with correct arguments in jsdom, but do not render the actual chessboard/arrow-overlay or confirm a real free move executes on the live board. Both plan SUMMARYs explicitly state this live UAT was not performed during the automated execution.

### 2. Live game-review parity (?game_id&ply)

**Test:** Open `/analysis?game_id=<id>&ply=<n>` for a real imported game with Stockfish on. Confirm the FlawChess card renders the same agreement-verdict sentence, hover/popover/click-to-play behavior, and arrow isolation as in free analysis (SC4, absorbs REVIEW-01).
**Expected:** The verdict, hover-arrow isolation, popover, and click-to-play behave identically on the game-review board to free analysis, with no visual or functional difference.
**Why human:** Verified structurally (single shared `flawChessCard` JSX variable rendered on both surfaces, `?game_id&ply` routes into the same `Analysis.tsx` component, no code path diverges) but no automated test loads a game-review URL and asserts on the rendered DOM. `REQUIREMENTS.md` still lists REVIEW-01 as Pending pending this confirmation.

### Gaps Summary

No gaps found. All must-haves from both plans' frontmatter (truths, artifacts, key links) are present, substantive, and wired, backed by passing unit and component tests, a clean `tsc -b`, clean lint, and clean knip. The only open items are two human-verification checks for live/visual behavior that no static analysis or jsdom test can observe — both explicitly disclosed as skipped by the executing agent in the phase SUMMARYs, and both structurally supported by the code (shared component insertion, correctly-wired callbacks) rather than left unimplemented.

---

_Verified: 2026-07-07T06:25:48Z_
_Verifier: Claude (gsd-verifier)_
