# Spike Manifest

## Ideas

### server-eval-throughput

Resolve Q-008 (`.planning/research/questions.md`): pin the real throughput of
the SEED-012 server-side full-game eval drain at the Lichess-parity search
budget (1M nodes, NNUE, multiPV=1), and size the tier-2 automatic catch-up
queue from prod data. These numbers gate the milestone's automatic-window
size, UX copy, and the 15–30s tier-1 wall-clock target.

**Requirements:**

- Search budget is fixed at `nodes=1_000_000`, NNUE, multiPV=1, Threads=1 per
  worker (SEED-012 D-6 — Lichess fishnet parity; calibration requirement).
- Engine config mirrors `app/services/engine.py`: Hash=32MB (spike 001 showed
  64MB gains nothing at this budget), Threads=1, SCHED_IDLE on prod.
- Throughput projections assume ~60 evaluated plies/game (post book/forced skip).

### maia-in-browser

SEED-081: run Maia-3 client-side (ONNX in the browser) and show per-rating move probabilities.
Section added when the manifest moved to per-idea keys (2026-11-17); the findings live in the
READMEs of spikes 004 to 006.

### facepalm-puzzle-validation

SEED-261117-hfb step 1: use Lichess puzzle ratings as an independent, large label set for the
question the facepalm score asks (how visible was it?). Score puzzles with the shipped model
and measure how well the score and each of its terms rank them against the puzzle rating,
before any further shape decision is made on the owner's 261 labels.

**Requirements:**

- Fixed Maia Elo (1500) for every puzzle; two more fixed Elos as the sensitivity check. No
  player ratings fetched from the game links.
- Every fact comes from the app's own functions (`line_facts`, `best_line_facts`,
  `reply_spread`, `facepalm_score`), so the spike tests what is stored and shipped.
- Report each term against the rating, not only the composite score.
- Stratify by solution length; the primary slice is short non-mate puzzles.

## Spikes

| # | Idea | Name | Type | Validates | Verdict | Tags |
|---|------|------|------|-----------|---------|------|
| 001 | server-eval-throughput | sf-1m-node-latency-local | standard | 1M-node per-position latency on dev machine, real-game positions | VALIDATED | stockfish, throughput, seed-012, q-008 |
| 002 | server-eval-throughput | sf-1m-node-latency-prod | standard | Same benchmark on prod CPX42 under SCHED_IDLE with live traffic; API latency unaffected | VALIDATED | stockfish, throughput, prod, seed-012, q-008 |
| 003 | server-eval-throughput | catchup-queue-sizing | standard | Tier-2 catch-up queue size from prod DB (active users × recent games lacking evals) | VALIDATED | prod-db, queue-sizing, seed-012, q-008 |
| 004 | maia-in-browser | maia3-onnx-browser-feasibility | standard | Given the Maia-3 5M checkpoint, when exported to ONNX + run via onnxruntime-web, then the browser gets the full per-ELO policy over legal moves + WDL at acceptable size/latency | VALIDATED | maia, onnx, browser, seed-081 |
| 005 | maia-in-browser | agpl-client-bundle-gate | standard | Given Maia-3 is AGPL-3.0 and the frontend MIT, when Maia ships client-side, then determine whether it forces the frontend to AGPL vs the clean server-side posture | PARTIAL | maia, license, agpl, seed-081 |
| 006 | maia-in-browser | moves-by-rating-chart | standard | Given per-ELO move-prob data, when rendered with Recharts, then it matches the reference: per-move lines over ELO, you-are-here marker, top-N ∪ {blunder,best}, theme colors | VALIDATED | maia, recharts, ui, seed-081 |
| 007 | facepalm-puzzle-validation | facepalm-vs-puzzle-ratings | standard | Given a rating-stratified sample of Lichess puzzles read as blunders (loss view) and as misses (miss view), when scored with the shipped facepalm model, then the score ranks them against puzzle rating with Spearman <= -0.30 on short non-mate puzzles | PARTIAL | facepalm, maia, lichess-puzzles, seed-261117-hfb |
