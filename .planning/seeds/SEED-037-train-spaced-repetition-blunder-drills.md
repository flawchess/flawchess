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

- **Assess first (binary guess)**: before moving, the user commits to *"one critical
  move"* vs *"several fine moves"* — pure position judgment, worth a point. Ground
  truth comes from the same blob classifier (sharp → critical; avoid-the-blunder and
  herrings → several). Deliberately NOT a 3-way type guess: blunder-history vs herring
  is episodic memory, not chess skill, and would add noise to the score.
- **Then always play a move — single move, one attempt.** Even on a "several fine
  moves" claim: choosing a concrete move in a quiet position is real training. No
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
- **Reveal (after the attempt)**: guess verdict + move verdict, original blunder vs best
  line (pv shown passively as a playable/steppable line), plus the game card and a deep
  link into the analysis board ("see what actually happened"). Full game context lives
  here, not on the solve screen. Herring reveal: "you handled this well in the game —
  several moves are fine"; blunder reveal names the original mistake.

### Motif layer (tactic-tagged flaws only — the schema-abstraction lever)

Learning-theory rationale: repeating an identical position risks learning *the card,
not the concept*. Two features force semantic processing, both conditional on tactic
tags (many sharp puzzles have a single best move but no tag — those skip this layer):

- **Motif multiple-choice quiz** — on **missed-tactic** flaws only (there the tactic IS
  the solution; on allowed-tactic flaws the tactic lives in the refutation, handled
  below). Shown after correct moves ("what did you just play?") AND after failed ones
  post-reveal ("what tactic did you miss?") — failers need the schema most. True motif
  + 2–3 plausible distractors from the motif enum (e.g. fork vs discovered attack),
  never the full taxonomy. Naming the pattern is itself retrieval practice.
- **Escalated active walkthrough on repeat-blunder** — trigger: the user plays their
  *exact original blunder move* AND the flaw is tactic-tagged (the strongest signal the
  pattern hasn't encoded; ration the user's time to that moment). Missed-tactic → step
  through the tactic they missed again (`missed_pv_lines`); allowed-tactic → step
  through the opponent's punishment (`allowed_pv_lines`, "this allowed a [fork] —
  again"). **Click-through stepping, reusing the analysis board's existing
  missed/allowed tactic line-stepping UI.** Any other wrong move, or untagged flaw →
  normal passive reveal.

### Scoring & gamification (solid learning, light game layer)

- **Per puzzle: 0–2 points, independent** — +1 correct guess, +1 correct move. Correct
  guess with a failed move still earns 1 (right judgment, failed execution).
- **Session result**: total score / 2N as a percentage, mapped to a green/yellow/red
  rating (theme.ts colors; band thresholds are named constants, planner tunes — e.g.
  ≥80% green, ≥50% yellow).
- **Scoring never touches the SR mechanics**: mastery streak and due dates are driven by
  move correctness alone. The guess layer is metacognition + score only, so pool
  behavior stays predictable.
- **Motif quiz is a separate tally, not main-score points**: session end shows
  "Patterns named: 4/5" as its own stat. Keeps 0–2 comparable across sessions
  regardless of how many tactic-tagged puzzles appeared.
- **v1 gamification inventory**: per-puzzle points, session score + color rating,
  patterns-named tally, scheduled-session streak, mastered count. No XP, leagues, or
  badges — the learning is the product.

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
- **3-way type guess** (sharp / avoid-blunder / herring) — rejected; types 2 and 3 are
  indistinguishable from the board (they differ by user history, not position
  character), so the third option would test memory, not judgment.
- **"Declare herring = done, no move"** — rejected; a move is always required, the loop
  stays uniform and quiet-position move choice is itself training.
- **Move-gated scoring** (wrong move = 0 regardless of guess) — rejected in favor of
  independent guess/move points.

## Data Dependencies (all shipped)

- `game_flaws` — materialized blunders/mistakes for both players (v1.24/v1.27); ply
  parity gives ownership.
- `game_positions.best_move` / `.pv` — full-game eval pipeline (v1.26+); the answer key.
- `game_flaws.missed_pv_lines` / `.allowed_pv_lines` — write-once JSONB blobs
  (Phase 141); `missed_pv_lines` node 0 has best (`b`/`bm`) + second-best
  (`s`/`sm`/`su`) — the sharp-vs-soft puzzle classifier; both lines feed the escalated
  walkthrough. Deferred columns: load via `undefer()`. Tier-4 opportunistic coverage.
- `game_flaws.missed_tactic_motif` / `.allowed_tactic_motif` (+ confidence/depth/piece)
  — gate and content of the motif layer; motif enum supplies quiz distractors.
- Analysis board tactic line-stepping UI — reuse for the escalated click-through
  walkthrough (already handles both missed and allowed orientations).
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
   (queue → guess → solve → reveal → done), client-side grading via Stockfish WASM,
   reveal with verdicts + pv + game card + analysis-board link, session-end score +
   color rating screen.
3. **Schedule + progress surface.** Weekday/N settings, nav badge + dashboard card,
   session streak, mastered-count/retention stats, cold/empty states.

## Deferred / v2

- **Mistakes tier** — expand pool entry beyond blunders.
- **Motif-aggregated progress** (candidate, not yet decided) — progress surface groups
  mastery by motif ("forks: 1/4, two failed twice"), turning stats into a diagnosis of
  conceptual weaknesses rather than an item counter.
- **Motif-variation injection** — when a user keeps failing a motif, prefer introducing
  *different* positions sharing that motif (variability of practice; the real cure for
  card-memorization — motif mastery should be demonstrated on unseen positions).
- **LLM one-line "why"** — pydantic-ai generated explanation sentence on the reveal
  ("the knight was overloaded defending e5 and the back rank"). Capability exists
  (endgame insights stack); cost/caching is the open question.
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

**2026-07-23 round 4 (user + Claude, learning-theory review):** motif layer added to
counter card-memorization — multiple-choice motif quiz on missed-tactic flaws (correct
AND failed attempts, separate "patterns named" tally, plausible distractors), escalated
active walkthrough (click-through, reusing analysis-board line stepping) triggered only
by replaying the exact original blunder on a tactic-tagged flaw. Motif-aggregated
progress, motif-variation injection, and LLM explanations recorded as v2 candidates.

**2026-07-23 round 3 (user + Claude):** pre-move metacognition layer added — binary
"one critical move vs several fine moves" guess (3-way type guess rejected as
memory-testing), move always required, independent 0–2 scoring per puzzle, session
score → green/yellow/red rating, guess layer isolated from SR mechanics; gamification
capped at points/rating/streak/mastered-count.

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
