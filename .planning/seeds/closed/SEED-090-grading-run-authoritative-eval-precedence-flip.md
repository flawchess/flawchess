---
title: Grading-run-authoritative eval reconciliation (precedence flip) — preferred alternative to SEED-089's unified pass
trigger_condition: When next doing analysis-page engine/eval work, or when a user reports cross-card eval inconsistency (a move labeled "Best" showing a lower eval than a move labeled "Good")
planted_date: 2026-07-10
source: Critical-evaluation session 2026-07-10 (review of SEED-089); Adrian prefers this design
---

# SEED-090: Grading-run-authoritative eval reconciliation (precedence flip)

## Relationship to SEED-089

Same user-visible problem, same root cause — see SEED-089 for the full diagnosis (three
independent Stockfish searches; free-run-first reconciliation mixes per-move evals from two
differently-configured searches, so a move labeled "Good" can display a higher number than the
move labeled "Best").

SEED-089's chosen fix (option 2: one high-MultiPV full-width pass + gap-only `searchmoves`
fallback) was critically reviewed and **two of its load-bearing claims failed**:

1. **"Uncovered moves can never be labeled Good" is false in exactly the regime of the
   triggering screenshot.** Coverage is cut by *eval rank* (Stockfish's top-K); labels are cut
   by *expected-score drop* through the Lichess sigmoid (`LICHESS_K ≈ 0.00368`,
   `frontend/src/lib/liveFlaw.ts`). The sigmoid flattens at large evals: at +4.2, a move a full
   **~85cp worse** still classifies "good" (drop ≈ 0.04 < `INACCURACY_DROP` 0.05). Winning
   positions routinely have >8 moves within 85cp of best, so an uncovered move gets a
   fallback grade from a *different search*, lands in the Good band, and can print a number
   above the unified best — the original bug, reproduced through the new architecture. The
   clamp SEED-089 defers ("leave out until observed") would in fact be mandatory day one.
2. **"Common case: zero extra Stockfish calls" is optimistic.** `selectCandidatesByMass`
   always unions in `playedSan` (D-07), and on an analysis page the interesting positions are
   the ones where the user blundered — a played blunder is very often outside Stockfish's
   top-8, so the fallback fires routinely, not rarely.

Plus two softer costs: the gap fallback rebuilds a slimmer Source B (same `searchmoves`
machinery, pv[0]-keying, stale guards — the "kill the grading run" simplification is half
illusory), and MultiPV≈8 risks a visible depth regression on the flagship Stockfish card
("Depth 19" is a trust signal).

**This seed is the preferred design.** SEED-089 stays open as the fallback architecture: it
wins one thing this design cannot (one worker instead of two → CPU/battery saving on the
mobile PWA). If a future measurement shows the dual-worker cost is unacceptable, revisit 089
*with the day-one clamp amendment*.

## The design: flip precedence, extend the union, delete nothing

Keep both existing searches exactly as configured today. Make the **grading run** (Source B:
`searchmoves`-restricted, `movetime 4000`, one coherent MultiPV ranking over every displayed
candidate) the **authoritative source for every displayed per-move eval**, with the free run
(Source A: MultiPV=2, `movetime 1500 nodes 2000000`) serving only as the fast first paint and
the pre-grading placeholder.

Why this closes the bug **by construction**:

- **Coverage by construction, no fallback path.** The grading union *is* the displayed set:
  Maia mass set (≤5) ∪ `playedSan` ∪ `bestSan` ∪ FC card's top-2 — extended (see below) with
  the free run's top-2 root moves. There is no "uncovered displayed move", hence no
  cross-search gap grade, hence no invariant hole. Typical union stays 6-9, inside the
  depth-parity window Phase 158 measured.
- **One search feeds every compared number.** All ranked/labeled evals come from a single
  `searchmoves` MultiPV search, so "nothing labeled Good outranks Best" holds for **all**
  displayed moves, not just top-K-covered ones.
- **No depth regression.** The free run is untouched (MultiPV stays 2, "Depth 19" intact).
  And the precedence flip is *quality-justified*: `useStockfishGradingEngine.ts:39-52`
  documents the Phase 158 headless measurement — at movetime 4000 and union size 6-8 the
  grading run reaches depth parity with or exceeds the free run at its 1500ms/MultiPV=2
  budget. The deeper number wins.
- **No serialization regression.** The grading run is already serialized behind Maia today;
  nothing new waits. The Stockfish card still paints from the free run in <100ms.

### Changes (all frontend, no backend)

1. **Extend `unionSans`** (`Analysis.tsx:796-800`) with the free run's top-2 root-move SANs
   (`engine.pvLines[].moves[0]` via `bestSanFromPv`). In practice this adds ≤1 move:
   `bestSan` is already unioned in via `selectCandidatesByMass`; only the 2nd PV line is new.
   Keep the existing sort+dedup so re-emission of the same set doesn't re-trigger a search.
2. **Flip `buildEvalLookup` precedence** (`engineEvalLookup.ts:40-60`): grading-first. A move
   present in both sources resolves to the grading value; free-run values fill only
   not-yet-graded moves (the pre-arrival placeholder role). Progressive refinement inverts:
   a move's number upgrades once (free → grading) and then only sharpens within the grading
   stream.
3. **Best/Good labels MUST derive from the reconciled map's own ranking, not free-run
   `bestSan`.** This is the critical correctness detail: under grading-first numbers, keeping
   the free-run `designatedBestSan` pin (`Analysis.tsx:871`, `classifyMoveQuality`) would
   *re-create* the bug in mirror image (label Best on Rad1 per free run while grading numbers
   say exd6 +4.3 > Rad1 +4.2). Rule: **Best = argmax over reconciled displayed evals,
   tie-break toward free-run `bestSan`**. `classifyMoveQuality`'s existing own-top-scorer
   path already does the argmax; the change is to stop passing the free-run pin once grading
   values are in (or pass a grading-derived pin). Numbers and label then move together
   atomically per committed snapshot, so a contradiction can never display. Near-tie label
   flips mid-stream are acceptable (same visual behavior as the card's own depth-climb
   reordering); if UAT flags flicker, pin at the grading run's `bestmove` commit.
4. **Stockfish card reads the lookup too.** Its two PV lines' displayed evals resolve through
   the reconciled lookup (falling back to their own free-run value until graded — which is a
   noop pre-grading since free-run values fill the map). Re-sort the card's 2 lines by
   reconciled eval so the card's line 1 always agrees with the chart's Best crown on
   near-ties. PV move-sequence text stays from the free run (the eval is for the same root
   move; grading's PV may differ — display-only, acceptable).
5. **Eval bar / headline eval: decide in plan.** Option (a) leave it free-run — it's a coarse
   graphic where ±20cp is invisible, and it keeps first-paint snappy; option (b) let the
   best move's reconciled eval refine it once grading lands (consistent with the card).
   Lean (a) unless UAT shows a visible headline-vs-card mismatch.
6. **Depth label:** the card headline keeps the free run's depth (it describes the displayed
   PV lines). Per-move eval asides elsewhere don't display depth today — no change.
7. **Source C stays display-excluded** (carried over from SEED-089, already agreed): the FC
   card's per-ply hover previews read the reconciled lookup, never the MCTS pool grade.
   The pool grade remains internal to the engine's move choice.

Net diff: union extension + precedence flip + label rule + card reads the lookup. No worker
deleted, no MultiPV retune, no new fallback code path, no headless re-measurement required as
a gate (the Phase 158 measurement already covers the grading config this design relies on).

## Timing profile (traced 2026-07-10, current code)

Question answered during the session: *when does the 4000ms grading run actually start?*

- **Trigger chain:** `useMaiaEngine`'s worker returns the **whole ELO ladder in one message**
  (`rawPolicyByElo`, all rungs atomically) → `perElo` set → `shownSans`/`unionSans` recompute
  → `candidatesKey` changes → the grading hook's adaptive debounce fires **immediately**
  when the change is "settled" (>150ms since the previous change, which Maia inference time
  guarantees) → `setoption MultiPV` + `position` + `go movetime 4000 searchmoves …`. The
  grading worker is booted at card-enable, not per position, so there is no init cost on the
  hot path. **Effective start delay ≈ Maia inference time + one React effect flush.**
- **Union churn restarts the clock.** `bestSan` comes from the free run and can flip as depth
  climbs during its ~1500ms window; the FC card's displayed SANs stream from the MCTS. Each
  union change stops and re-goes the grading search (stop → stale-bestmove discard → re-go),
  restarting the 4000ms cap. Mitigations already built in: the per-(FEN, SAN) grade cache
  persists across restarts, each re-go searches the union of already-graded + newly-needed
  SANs, and grades stream progressively on every `info` line — so first grading numbers paint
  within a few hundred ms of the first `go`; 4000ms is time-to-final-depth, not first paint.
- **Worst-case settled timeline on a fresh position:** Maia inference (~hundreds of ms) →
  go → possible restarts during the free run's 1.5s + FC streaming → final deep numbers ≈
  4s after the *last* union change (~5-6s total). Revisited positions are instant (Maia
  cache + grade cache both hit).
- Extending the union with the free run's top-2 (change 1) slightly increases churn risk
  (the 2nd PV line reorders during the free run). If restarts prove visible in UAT, the
  cheap fix is to add the free-run contribution to the union only once the free run's
  `bestmove` commits (a ≤1.5s delay on grading ≤1 extra move, invisible given the cache).

## Known trade-offs (accepted)

- **Two workers stay alive** — no CPU/battery saving vs SEED-089's option 2. This is the
  price of airtight coverage + zero depth regression. Revisit via 089 if mobile battery
  becomes a complaint.
- **One-time number shift at ~4s:** cards show free-run values until grading lands, then
  upgrade once (±0.1-0.3 typical). Same visual class as depth-climb sharpening; the
  progressive-refinement direction is now deeper-wins, which is defensible.
- **When Maia AND FC cards are both off**, `gradingEnabled` is false and the Stockfish card
  stands alone on the free run — no cross-card issue exists in that state by definition.

## Verification sketch (for the plan phase)

- Unit: `buildEvalLookup` precedence flip (grading wins on overlap; free-run fills gaps).
- Unit: Best-label rule — construct a grading map where a non-`bestSan` move has the top
  reconciled eval; assert it gets `best` and `bestSan` gets `good` (the mirror-image bug).
- UAT on the SEED-089 screenshot position: Stockfish card, FC card prose, and Maia tooltip
  must all show identical numbers for Rad1/exd6/Bc1, ordering consistent with labels.
- UAT: navigate rapidly through a game — no orphaned grades, restarts converge, card first
  paint still <100ms.
