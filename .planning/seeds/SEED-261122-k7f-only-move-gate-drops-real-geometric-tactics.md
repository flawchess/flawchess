---
id: SEED-261122-k7f
status: dormant
planted: 2026-11-22
planted_during: owner question about a missing "allowed fork" tag on one of their own games
trigger_when: next time tactic-tag recall is worked on, or when more owner reports of obviously missing fork/pin/skewer tags come in. Needs an investigation and measurement pass before any code change
scope: unknown until measured. Investigation first (dev and prod counts, hand spot-check), then possibly a gate rule change plus a retag
---

# SEED-261122-k7f: The only-move gate drops real geometric tactics when a second move also wins

## The case

http://localhost:5175/analysis?game_id=3252412&ply=32

Dev DB, game 3252412, user 28, flaw at ply 32 (0-based, White's move). White plays `Qg4`, which allows
`Nxf2`, a knight fork of the queen on g4 and both rooks (d1, h1). The flaw is stored as a blunder with
`allowed_tactic_motif = NULL`.

Position after `Qg4` (Black to move): `2r2rk1/pb4pp/1p2pq2/2npN3/3NnPQ1/3B4/PPP2P1P/2KR3R b - - 0 17`

Refutation PV (`game_positions.pv` at ply 33):
`e4f2 d3h7 g8h7 g4h5 f6h6 h5h6 g7h6 b2b4 c5e4 d4e6 f2h1 d1h1`

## What was established (2026-11-22)

Replayed both steps on this position with the current code:

- `tactic_detector.detect_tactic_motif` fires `FORK`, piece knight, confidence 100, depth 0.
- `forcing_line_gate.apply_forcing_line_filter` returns False. The reject comes from the only-move test on
  the firing node (`is_solver_node_forced`, `app/services/forcing_line_gate.py`).

Node 0 of `game_flaws.allowed_pv_lines` (white-perspective cp): `b = -419`, `s = -368`, `su = c5d3`.
From Black's view the best move `Nxf2` is +419 and the second-best `Nxd3+` is +368. The gap is 51 cp, below
`ONLY_MOVE_CP_GAP_THRESHOLD` (100), and the win-prob gap is far below `ONLY_MOVE_WIN_PROB_MARGIN` (0.35).
The other gate rules were not the cause: pre-flaw eval is -240 (not already winning), and the firing node
clears the 0 cp geometric floor.

## Hypothesis

The only-move rule is a puzzle-validity criterion (one correct solution). For "you allowed a fork" the
statement is true whether or not the opponent has a second winning move. The same reasoning already relaxed
the rule for mate motifs (`_resolve_mate_priority`, the `mate_motif` branch).

In this case the second-best move is probably the same fork one move later (`Nxd3+`, recapture, then `Nxf2`
still hits the queen and the h1 rook). **Not verified**: no engine was run on that line, and the blob stores
only the second move's UCI and eval, not its continuation.

## Open questions, to answer before changing anything

1. **How big is this?** Count flaws where the raw detector fires a geometric motif (tier 2, plus
   hanging-piece) and the gate rejects it on the only-move test alone. Split by motif, firing depth,
   orientation (allowed vs missed), and by the second-best move's solver eval. Dev user 28 first, then prod.
2. **How many of those are real?** Hand spot-check a sample. Earlier sweeps did this for the 100 to 150 cp
   band (`reports/retag/ab-validation-2026-06-30.md`); the band below 100 cp has not been looked at.
3. **Is the second-best move usually the same tactic?** This needs the second move's PV, which the blob does
   not store. Measure on a sample by running Stockfish on the second move and re-running the detector.
4. **Does the same problem hit the missed orientation,** and does a relaxation there re-credit incidental
   tactics in positions where everything wins?
5. **Eval mismatch to explain:** `game_positions.eval_cp` after `Qg4` is -660, while the blob's node 0 best
   is -419. Different depth or source is likely, but it was not checked. If the blob evals are systematically
   shallower, the 100 cp gap is measured on noisier numbers than assumed.
6. **Precision and recall impact** on the CC0 fixture (`tactic-tagger-report` skill). Note the gate is not
   exercised by that fixture the same way, so prod-data counts matter more here.

## Candidate fixes (not decided)

1. **Relax the only-move test for geometric motifs firing at depth 0** when the second-best move is also
   clearly winning for the solver. Uses only the existing blob. Risk: re-credits incidental forks in
   positions where everything wins. The threshold for "clearly winning" would need a sweep.
2. **Same-motif check on the second-best move.** Credit the tag when the second-best move leads to the same
   motif. More precise, but needs the second move's PV: an engine change, a blob schema change, and a
   backfill.
3. **Leave the gate as is** if the measured count is small or the spot-check shows mostly incidental tactics.

Any rule change needs a retag (prod run facts: 4.76M rows in 3h17m) and an A/B validation like the earlier
threshold sweeps.

## Constraints

- Do not judge candidate rules by engine eval alone; hand spot-checks decided the earlier sweeps and caught
  defects the numbers missed.
- The mate-motif relaxation is the precedent for dropping uniqueness when the tag is true either way. Keep
  the strict rule for tier-3 motifs unless the measurements say otherwise.
- The app hides some tags downstream (decided-lost positions, `MIN_TACTIC_CHIP_CONFIDENCE`); measure at the
  stored-column level, then check what the UI would actually show.

## Breadcrumbs

- `app/services/forcing_line_gate.py` (`is_solver_node_forced`, `apply_forcing_line_filter`, constants and
  their provenance comments)
- `app/services/tactic_detector.py` (`detect_fork`, `_GEOMETRIC_REGISTRY`, `floor_cp_for_motif`)
- `app/services/flaws_service.py` (`_classify_tactic_gated`, `_detect_tactic_for_flaw`)
- `reports/retag/ab-validation-2026-06-30.md`, `scripts/ab_validate_gate.py`
- `tests/services/test_forcing_line_gate.py`
