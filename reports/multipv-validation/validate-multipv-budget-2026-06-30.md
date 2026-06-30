# FlawChess MultiPV Budget Validation Report

**Generated:** 2026-06-30 01:41:22Z (UTC)
**DB target:** `dev`
**Query limit:** 1000
**Script:** `scripts/validate_multipv_budget.py`
**Constant:** `ONLY_MOVE_WIN_PROB_MARGIN = 0.35`
**Margin band:** +/-0.05 around 0.35
**SC4 gate:** fraction-in-band <= 0.1 AND positions >= 200

Reads `game_flaws.allowed_pv_lines` JSONB blobs (Phase 142 eval drain) and computes the win-prob margin (p(best) - p(second)) at each solver node (even index in the blob). The fraction of solver nodes within +/-0.05 of `ONLY_MOVE_WIN_PROB_MARGIN` (0.35) must be <= 0.1 for the node budget to be considered reliable (SC4). If more than 10% fall in the band, raise the node budget to 1.5-2M nodes (D-06) before merging Phase 142.

## Summary

| Metric | Value |
|--------|-------|
| Flaw positions examined | 219 |
| Solver nodes with second move | 1202 |
| Solver nodes trivially forced (no second move) | 56 |
| Malformed nodes skipped (T-142-04-02) | 0 |
| Nodes in-band (+/-0.05 of margin) | 19 |
| **Fraction in-band** | **0.0158** (gate threshold: <= 0.1) |
| **SC4 gate verdict** | **PASS** (positions >= 200: YES) |

## Margin Distribution Histogram

Win-prob margin = p(best) - p(second) at each solver node. Bins of width 0.05. Bins overlapping the gate band [0.30, 0.40] are marked `** IN BAND **`.

| Bin | Margin range | Count | Fraction | Band? |
|----:|:-------------|------:|---------:|:------|
|  0 | [0.00, 0.05) |    918 | 0.7637 | |
|  1 | [0.05, 0.10) |     96 | 0.0799 | |
|  2 | [0.10, 0.15) |     56 | 0.0466 | |
|  3 | [0.15, 0.20) |     22 | 0.0183 | |
|  4 | [0.20, 0.25) |     23 | 0.0191 | |
|  5 | [0.25, 0.30) |     14 | 0.0116 | |
|  6 | [0.30, 0.35) |      7 | 0.0058 | `** IN BAND **` |
|  7 | [0.35, 0.40) |     12 | 0.0100 | `** IN BAND **` |
|  8 | [0.40, 0.45) |     10 | 0.0083 | |
|  9 | [0.45, 0.50) |      3 | 0.0025 | |
| 10 | [0.50, 0.55) |      2 | 0.0017 | |
| 11 | [0.55, 0.60) |      2 | 0.0017 | |
| 12 | [0.60, 0.65) |      4 | 0.0033 | |
| 13 | [0.65, 0.70) |      4 | 0.0033 | |
| 14 | [0.70, 0.75) |      2 | 0.0017 | |
| 15 | [0.75, 0.80) |      1 | 0.0008 | |
| 16 | [0.80, 0.85) |      0 | 0.0000 | |
| 17 | [0.85, 0.90) |      1 | 0.0008 | |
| 18 | [0.90, 0.95) |      0 | 0.0000 | |
| 19 | [0.95, 1.00) |      0 | 0.0000 | |
| —  | [< 0.00)      |     25 | 0.0208 | (negative margin) |

**Mean margin:** 0.0509 | **Median:** 0.0138 | **Stdev:** 0.1057

## PV1 Drift Spot-Check (Advisory)

> **Note:** This section is advisory only. It does not affect the `--check-goals` exit code. The authoritative PV1-drift guard is the test-suite flaw-count invariant verified in Plan 142-02 Task 3 (`uv run pytest tests/services/test_full_eval_drain.py -x`). That test confirms tactic tag counts are unchanged after switching to multipv=2, which is the practical safety net for PV1-eval boundary drift.

The concern (RESEARCH FLAG): switching the whole-game pass to multipv=2 uses less aggressive Stockfish pruning, which can cause PV1 eval_cp to drift slightly vs multipv=1 at the same node budget (~5-15 cp typical). A *systematic* shift that moves flaw classification boundaries (severity: 0 cp = equalized, blunder/mistake separation near ±150 cp proxy) would be the concern. Small per-position drift (<15-20 cp) falls within the accepted non-determinism window (memory: project_eval_nondeterminism).

**Sample size:** 100 game_positions rows with non-NULL eval_cp
(sampled from up to 100 positions in Phase-142-analyzed games)

| Metric | Value |
|--------|-------|
| Mean absolute eval_cp | 264.7 cp |
| Stdev eval_cp | 378.4 cp |
| Fraction within ±150 cp (contested zone) | 0.530 (53/100) |
| Fraction > ±300 cp (already-winning zone) | 0.330 (33/100) |

**Interpretation:** Compare these values across Phase 142 boundary. A systematic multipv=2 PV1 shift of >15-20 cp would increase the contested-zone fraction significantly (more positions would be pushed into or out of the ±150 cp band). The values above represent the post-Phase-142 distribution; if a pre-Phase-142 snapshot is available, subtract means to estimate drift magnitude.

## Methodology Notes

- **Explicit column projection:** `select(GameFlaw.game_id, GameFlaw.ply, GameFlaw.allowed_pv_lines)` — never select the whole ORM entity (Pitfall 4: deferred columns raise `MissingGreenlet`).
- **Solver color:** `allowed_pv_lines` blob starts at `flaw_ply+1`. The solver is the opponent of the flaw-maker: black if `flaw_ply % 2 == 0` (white made the flaw), white if odd. Even indices in the blob are solver nodes.
- **Margin constant:** `ONLY_MOVE_WIN_PROB_MARGIN = 0.35` from `app/services/forcing_line_gate.py` (D-07 provisional; final value committed in Phase 144).
- **Sigmoid:** `eval_cp_to_expected_score(cp, solver_color)` from `app/services/eval_utils.py` with `LICHESS_K = 0.00368208`. No hand-rolled sigmoid.
- **Mate nodes:** `eval_mate_to_expected_score` returns 0.0 or 1.0; mate nodes produce margins near 1.0 and never cluster near the gate band.
