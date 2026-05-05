"""Phase 75 (v1.14) opening insights constants.

Single source of truth for thresholds shared between the repository
(SQL HAVING clause) and the service (Python classifier + confidence
helper). Mirrors frontend/src/lib/arrowColor.ts thresholds; CI-enforced
via tests/services/test_opening_insights_arrow_consistency.py.

Split into its own module to avoid a circular import: the repository
imports these constants, and the service imports from the repository,
so the constants cannot live in either file.
"""

# Entry-position bounds — Phase 70 used [3, 16]; lowered to [0, 16] so opening
# insights also surface findings at white's first move (entry_ply=0), black's
# first response (entry_ply=1), and white's second move (entry_ply=2). At
# entry_ply=0 the entry position is the starting position and entry_san_sequence
# is empty — _replay_san_sequence handles this by returning the starting FEN.
OPENING_INSIGHTS_MIN_ENTRY_PLY: int = 0
OPENING_INSIGHTS_MAX_ENTRY_PLY: int = 16

# Discovery floor — was 20, dropped to 10 per INSIGHT-SCORE-05 / D-04.
# Borderline-evidence findings surface with confidence="low" rather than
# being filtered out (the confidence badge replaces the prior hard floor).
OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE: int = 10

# Score classifier — replaces the Phase 70 LIGHT_THRESHOLD / DARK_THRESHOLD
# pair. Pivot is fixed at 0.50; effect-size gate is symmetric on both sides.
# See .planning/notes/opening-insights-v1.14-design.md for rationale.
OPENING_INSIGHTS_SCORE_PIVOT: float = 0.50
OPENING_INSIGHTS_MINOR_EFFECT: float = 0.05  # |score - pivot| >= 0.05 → minor
OPENING_INSIGHTS_MAJOR_EFFECT: float = 0.10  # |score - pivot| >= 0.10 → major

# Confidence buckets — two-sided Wald p-value thresholds plus N>=10 gate,
# unified across both the score-vs-50% test (score_confidence.py) and the
# eval-mean-vs-0 test (eval_confidence.py). With N < 10, confidence is forced
# to "low" regardless of p-value: small samples already carry the
# unreliable-stats opacity dim in the UI, and the bucket should match that
# signal.
#
# Threshold rationale: p < 0.01 ("high") demands strong evidence —
# < 1% chance of seeing the observed signal under H0 by chance alone.
# p < 0.05 ("medium") is the conventional weak-evidence cutoff.
# Two-sided framing matches industry convention; the one-sided framing
# previously used for the score test (halving the p) made "high confidence"
# at p_one_sided < 0.05 effectively equivalent to p_two_sided < 0.10, which
# was a weaker bar than the eval test was held to.
OPENING_INSIGHTS_CONFIDENCE_MIN_N: int = 10
OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P: float = 0.01
OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P: float = 0.05

# Two-sided 95% normal-approximation z-score (z = 1.96). Used by
# `opening_insights_service._wilson_bounds` to construct the Wilson 95% score
# interval that drives within-section ranking in `_rank_section` (quick task
# 260428-v9i, replacing the earlier Wald CI). The same z value is also the
# implicit threshold for the p < 0.05 "high" confidence bucket above;
# collocating it keeps both 95%-normal-approximation parameters in one place.
# Note: the trinomial *Wald* p-value used by
# `score_confidence.compute_confidence_bucket` is a different statistical
# procedure and is not renamed.
OPENING_INSIGHTS_CI_Z_95: float = 1.96

# --- Phase 80 MG-entry eval test (decoupled from WDL score test) ----------
# These constants are eval-specific and not shared with score_confidence.

# Engine-asymmetry MG-entry tick-mark positions (in pawns, signed
# user-perspective). Symmetric ±BASELINE around 0 cp, derived from the 2026-05-04
# Lichess benchmark v3 deduplicated per-physical-game mean of +25.18 cp
# (n=1.25M trimmed games — see reports/benchmarks-2026-05-04.md §3a).
#
# The previous per-color asymmetric values (+0.315 / -0.189) were a sampling
# artefact of the per-(user, color) slice: white-user and black-user rows
# were almost entirely *different* physical games, so the small skill edge of
# benchmark users vs typical opponents split the per-color means apart.
# Deduping at the game level cancels that artefact and yields a single
# symmetric tempo baseline of about ±25 cp (white's first-move advantage).
#
# Used only as a visual reference tick on the MG-entry bullet chart, NOT as
# the H0 reference for the z-test. The test runs against 0 cp (engine-balanced)
# regardless of color (quick task 260504-rvh).
EVAL_BASELINE_PAWNS_WHITE: float = 0.25
EVAL_BASELINE_PAWNS_BLACK: float = -0.25

# N gate for the eval z-test — unified with OPENING_INSIGHTS_CONFIDENCE_MIN_N
# at n>=10 (was 20 to bound the Edgeworth leading-error term on the normal
# approximation under ~2% for cp distributions with excess kurtosis ~2.4).
# Re-aliased rather than removed so the per-helper docstrings can keep their
# named import; the gate is now a single value across all confidence buckets.
# Calibration trade-off accepted: at p<0.01 the bucket is robust to a few-%
# error in tail probability, and the |eval_cp|>=2000 trim already clips the
# heaviest tails before the helper sees the data.
EVAL_CONFIDENCE_MIN_N: int = OPENING_INSIGHTS_CONFIDENCE_MIN_N
