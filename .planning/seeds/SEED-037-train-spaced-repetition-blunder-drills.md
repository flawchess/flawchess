---
id: SEED-037
status: dormant
planted: 2026-06-04
planted_during: 2026-06-04 split of SEED-010 into Library (SEED-036) + Train (this seed)
refined: 2026-07-23 (gsd-explore session — full design settled, stale premises removed)
lineage: split from SEED-010 (planted 2026-05-01, reworked 2026-06-03); SEED-010 closed
trigger_when: user invokes `/gsd-new-milestone` for Train (all data dependencies already shipped as of v2.5)
scope: milestone (multi-phase)
depends_on: none open — the original SEED-036 dependencies are satisfied or obsolete (see Data Dependencies)
---

# SEED-037: Train — spaced-repetition blunder drills

> **Lineage.** Split out of SEED-010 (closed) on 2026-06-04. Refined 2026-07-23 in a
> gsd-explore session: the design below is *settled*, not provisional. The old seed's
> premises (best-move endpoint dependency, FSRS adoption, GM-coach prototype loop) are
> superseded — see Rejected Alternatives.

## Why This Matters

The **retention play** — the feature that turns FlawChess from an analysis tool into a
habit. Analysis tells a user *where* they went wrong; training makes them *stop* going
wrong by re-presenting their own blunders on a spaced schedule until the pattern sticks.
Aimchess monetizes essentially this at $7.99/mo; FlawChess differentiates on price
(free/open) and on training from the user's *own* games rather than generic puzzles.

## Settled Design (2026-07-23)

### Training model: true spaced repetition, session-gated

Per-item due dates, but sessions happen on a **user-configured weekly schedule**
(weekday picker + N puzzles per session). Due dates snap to the first scheduled session
on/after the ideal date. The schedule is a commitment device, not a lock — an ad-hoc
"train now" session on an off day is allowed and draws the same queue.

### Scheduler: rolled our own (FSRS rejected)

A pure-function **interval ladder keyed by mastery streak**:

- streak 0 → due next scheduled session
- streak 1 → due ~3 days out
- streak 2 → due ~10 days out
- each due date snapped forward to the next scheduled session day

Wrong answer → streak resets to 0, item returns next session. State per item: `streak`,
`due_date` (plus a solve log). Fully testable, no dependency.

### Session composition: exactly N, cap + backfill, ~25% red herrings

Every session is exactly N while material lasts:

- **~75% of N — SR items**: due items **most-overdue first**; if due < slots, pad by
  **introducing new flaws** from the pool (recent games preferred). Backlogs drain
  gradually; being caught up never yields an empty session (Anki's model).
- **~25% of N — red herrings**: one-off fillers drawn fresh from the herring source
  (below), recency-weighted, no repeats until the source is exhausted. No streak/due
  bookkeeping — they vaccinate against "there's always a killer move here"
  pattern-gaming, they're not material to master. Failing one just shows the reveal.

### Puzzle taxonomy: three types, one grading rule

All puzzles look identical to the solver ("play the best move you can find") and share
one grading rule; they differ only in sourcing and reveal messaging:

1. **Sharp find-the-move** — own blunder where the blob's best-vs-second expected-score
   gap is large: effectively only the best move grades correct.
2. **Avoid-the-blunder** — own blunder where best-vs-second is close: several moves
   grade correct; the point is not repeating the mistake.
3. **Red herring** — a position the user handled *well* with several roughly-equal
   options, sourced from **non-gem `game_best_moves` candidate rows** (user played the
   stored best move out-of-book, best ≈ second — the exact complement of gem
   detection). Winnability-floor applies. No new analysis needed.

The best-vs-second gap is a **classifier, not an entry gate** — soft-answer blunders
become type 2 instead of being excluded, so the pool grows.

### Pool entry (which flaws qualify)

- **Blunders only** (v1). Mistakes are a later pool-expansion lever if active users run dry.
- **User's own flaws only** — `game_flaws` stores both players; filter by ply parity vs
  `user_color`.
- **Winnability floor** — exclude positions already lost before the blunder (expected
  score below ~20–25%, via `eval_cp_to_expected_score`). Drilling hopeless positions
  teaches nothing.
- **Answer key present** — require stored `best_move` + `pv` AND a non-empty
  `game_flaws.missed_pv_lines` blob (node 0 carries best `b`/`bm` vs second-best
  `s`/`sm`/`su` — MultiPV-2 at the decision position, Phase 141). The blob classifies
  the puzzle as sharp vs avoid-the-blunder (see taxonomy above). Blobs are tier-4
  opportunistic (new games ~100% inline, backlog still filling), so this is a
  present-data filter, not a blocker.
- **Recency-weighted introduction** — prefer flaws from recent games when padding
  sessions with new items. No Zobrist dedup (repeat blunders may coexist).

### Pool exit (retirement)

Retire after **3 consecutive spaced correct solves** (correct solves in 3 separate
sessions; a miss resets to 0). Simple to explain in UI ("2/3 mastered"). The ladder
decides *when* reps happen; this counter decides *retirement*.

### Solve loop

- **Single move, one attempt.** Play the move that avoids your blunder; done. No
  multi-move lines (pv-line quality from eval data isn't curated like lichess puzzles).
- **Lichess-minimal solve screen**: board oriented to user's color, opponent's last move
  animated + highlighted, "White/Black to move" prompt. No eval bar, no game metadata —
  nothing that leaks the answer or severity.
- **Grading is fully client-side and uniform across all three puzzle types**: exact
  match to stored `best_move` → instant correct; any other move → the vendored client
  Stockfish WASM (shipped for Bot Play, v2.3) evals it ~1s. **Correct = the played
  move's expected-score drop vs best stays below the project's existing MISTAKE
  threshold** (reuse the flaw-taxonomy constants; inaccuracies pass). Sharp puzzles
  still effectively require the best move because second-best is a mistake there by
  construction. No grading endpoint, no backend engine load. Backend only **records
  results** (streak, due date, solve log).
- **Reveal (after the attempt)**: original blunder vs best line (pv shown passively as a
  playable/steppable line), plus the game card and a deep link into the analysis board
  ("see what actually happened"). Full game context lives here, not on the solve screen.

### Schedule & reminders (v1: in-app only)

Settings: weekday picker + N per session. Surfacing: nav badge / dashboard card on
session days ("12 puzzles waiting") + a session-streak counter (consecutive scheduled
sessions completed). **No push, no email in v1** — PWA push (service worker, VAPID,
subscription storage, scheduled sender) is its own project; defer to v2.

### Empty/cold states

- No analyzed games yet → point to import/analysis (reuse Library readiness patterns).
- Pool exhausted (everything mastered, nothing due) → celebrate + offer mistakes-tier
  expansion later; never a dead screen.

## Rejected Alternatives (decision log 2026-07-23)

- **FSRS** — rejected. Item lifetime is ~3–6 reps, grading is binary, and due dates get
  quantized to scheduled session days anyway; FSRS's per-user memory-model fitting has
  nothing to bite on. The interval ladder is honest and testable.
- **`POST /api/analysis/best-move` grading endpoint** (the original SEED-036 dependency,
  never built) — obsolete. The full-game eval pipeline (v1.26+) already stores
  `best_move`+`pv` per ply, and client Stockfish WASM grades arbitrary moves locally.
- **Session-mastery / Leitner-lite model** (no due dates) — considered; user chose true
  SR with per-item due dates.
- **Retry on wrong move** — rejected; one attempt, matching "in the real game you got
  one chance". Reveal follows immediately.
- **Eval bar / game metadata during solving** — rejected (leaks answer/severity);
  context moves to the reveal screen.
- **GM-coach collaboration loop** — dropped from this seed. The `/train-sketch`
  prototype built for it was deleted on 2026-07-23 (route + `frontend/src/pages/TrainSketch/`).
- **Zobrist dedup of repeat blunders** — not necessary.
- **Sharp answer key as an entry GATE** (round-1 decision) — superseded in round 2: the
  best-vs-second gap classifies puzzle type instead of excluding soft-answer blunders.
- **Per-type grading thresholds** — rejected; one uniform not-a-mistake rule keeps the
  solver-facing contract honest and the grading code type-blind.
- **SR-tracking red herrings** (streaks/due dates, or fail-promotes-to-pool) — rejected;
  herrings are one-off fillers.

## Data Dependencies (all shipped)

- `game_flaws` — materialized blunders/mistakes for both players (v1.24/v1.27); ply
  parity gives ownership.
- `game_positions.best_move` / `.pv` — full-game eval pipeline (v1.26+); the answer key.
- `game_flaws.missed_pv_lines` — write-once JSONB blob (Phase 141); node 0 has best
  (`b`/`bm`) + second-best (`s`/`sm`/`su`) — the sharp-vs-soft puzzle classifier.
  Deferred column: load via `undefer()`. Tier-4 opportunistic coverage.
- `game_best_moves` — MultiPV-2 best/second eval for plies where the user played the
  stored best move out-of-book (v2.4); **non-gem rows (best ≈ second) are the red
  herring source**. Same opportunistic-backfill caveat (two populations).
- Client Stockfish WASM — vendored for Bot Play (v2.3); the grading engine.
- `eval_cp_to_expected_score` (`app/services/eval_utils.py`) — expected-score mapping
  for the winnability floor and grading verdicts.
- Analysis board — the reveal's deep-link target.

## Name — TBD

Pick before the build. On-brand candidates lean into "flaws/fixing": *Fix / FlawFix*,
*Rematch / Comebacks*, or plain *Train / Drills / Practice*. Working name for the
top-level page is **Train** (nav `Import · Openings · Endgames · Library · Train`).

## Phase Decomposition (rough sketch — planner refines)

1. **Pool + scheduler backend.** Drill-item data model (per-user per-flaw: streak,
   due_date, solve log), pool-entry query (blunders, ownership, winnability, blob
   present, recency), sharp-vs-soft blob classifier, red-herring source query
   (non-gem `game_best_moves`), interval ladder, session-composition endpoint
   (75/25 mix), result-recording endpoint.
2. **Train page + solve loop (frontend).** Route + nav, session flow
   (queue → solve → reveal → done), client-side grading via Stockfish WASM, reveal with
   pv + game card + analysis-board link.
3. **Schedule + progress surface.** Weekday/N settings, nav badge + dashboard card,
   session streak, mastered-count/retention stats, cold/empty states.

## Deferred / v2

- **Mistakes tier** — expand pool entry beyond blunders.
- **Push/email reminders** — PWA push subsystem or an email pipeline.
- **Half-credit / retry variants** — if one-attempt proves too harsh in practice.

## Breadcrumbs

- `app/services/eval_utils.py` — `eval_cp_to_expected_score` (Lichess sigmoid).
- `frontend/src/pages/Bots/` + vendored `stockfish-18-lite-single.js` — client engine
  integration to reuse for grading.
- `.planning/seeds/closed/SEED-036-library-page-milestone.md` — origin of the (now
  obsolete) best-move-endpoint plan.
- lichess-puzzler — https://github.com/ornicar/lichess-puzzler — reference for turning
  eval swings into training positions (sharpness filtering ideas).

## Source / decision log

**2026-07-23 round 2 (user + Claude):** red herrings promoted from v2 into v1 at ~25%
of each session (one-off fillers, sourced from non-gem `game_best_moves` rows);
avoid-the-blunder puzzle type added; sharp-answer-key gate demoted to a classifier fed
by `missed_pv_lines` blob MultiPV-2 data (resolves the round-1 open question); grading
unified to one not-a-mistake threshold across all types.

**2026-07-23 refinement (user + Claude, gsd-explore):** all Settled Design decisions
above; `/train-sketch` prototype deleted; GM-coach loop dropped; FSRS rejected in favor
of the streak-keyed interval ladder; grading moved fully client-side.

**2026-06-04 split (user + Claude):** SEED-010 split into SEED-036 (Library) +
SEED-037 (this seed); SEED-010 closed.

**2026-06-03 origin (SEED-010 "Deferred extensions"):** SR blunder-training as the
milestone after Library; red herrings deferred; name TBD.
