"""Opening insights constants.

Single source of truth for thresholds shared between the repository
(SQL HAVING clause) and the service (Python classifier + confidence
helper). Mirrors frontend/src/lib/arrowColor.ts thresholds; CI-enforced
via tests/services/test_opening_insights_arrow_consistency.py.

Split into its own module to avoid a circular import: the repository
imports these constants, and the service imports from the repository,
so the constants cannot live in either file.
"""

# Entry-position bounds [0, 16]: opening insights also surface findings at
# white's first move (entry_ply=0), black's first response (entry_ply=1), and
# white's second move (entry_ply=2). At
# entry_ply=0 the entry position is the starting position and entry_san_sequence
# is empty — _replay_san_sequence handles this by returning the starting FEN.
OPENING_INSIGHTS_MIN_ENTRY_PLY: int = 0
OPENING_INSIGHTS_MAX_ENTRY_PLY: int = 16

# Discovery floor. Small-N findings (n in 10..19) are dominated by
# post-selection noise: the SQL pre-filter on score <= 0.45 OR score >= 0.55
# selects the very statistic the score-vs-50% test then uses. The Wilson score
# test (null SE = 0.5/sqrt(n)) is less sensitive to that selection (null SE
# doesn't depend on observed score), but the floor stays at 20; lowering it is a
# separate decision.
# Decoupled from the explorer's MIN_GAMES_FOR_COLOR (frontend, still 10) —
# the explorer arrow palette can tolerate weaker evidence than a surfaced
# "weakness" card on the Insights tab.
OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE: int = 20

# Score classifier. Pivot is fixed at 0.50; effect-size gate is symmetric on
# both sides.
OPENING_INSIGHTS_SCORE_PIVOT: float = 0.50
OPENING_INSIGHTS_MINOR_EFFECT: float = 0.05  # |score - pivot| >= 0.05 → minor
OPENING_INSIGHTS_MAJOR_EFFECT: float = 0.10  # |score - pivot| >= 0.10 → major

# Confidence buckets — two-sided p-value thresholds plus N>=10 gate, unified
# across both the score-vs-50% test (score_confidence.py — Wilson score test)
# and the eval-mean-vs-0 test (eval_confidence.py —
# Wald-z, Wilson does not apply to continuous one-sample mean tests). With
# N < 10, confidence is forced to "low" regardless of p-value: small samples
# already carry the unreliable-stats opacity dim in the UI, and the bucket
# should match that signal.
#
# Threshold rationale: p < 0.01 ("high") demands strong evidence —
# < 1% chance of seeing the observed signal under H0 by chance alone.
# p < 0.05 ("medium") is the conventional weak-evidence cutoff.
# Two-sided framing matches industry convention and holds the score test to the
# same bar as the eval test (a one-sided p < 0.05 would be equivalent to a
# two-sided p < 0.10).
OPENING_INSIGHTS_CONFIDENCE_MIN_N: int = 10
OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P: float = 0.01
OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P: float = 0.05

# Two-sided 95% normal-approximation z-score (z = 1.96). Used by
# `score_confidence.wilson_bounds` (default z) to construct the Wilson 95% score
# interval that drives within-section ranking in `_rank_section`. The same z
# value is also the implicit threshold for the p < 0.05 "medium" confidence
# bucket above; collocating it keeps both 95%-normal-approximation parameters in
# one place. Note: the Wilson score-test p-value used by
# `score_confidence.compute_confidence_bucket` and the Wilson CI bound are
# inversions of one another — they share this z but are still two separate
# computations.
OPENING_INSIGHTS_CI_Z_95: float = 1.96

# --- MG-entry eval test (decoupled from WDL score test) ----------
# These constants are eval-specific and not shared with score_confidence.

# Engine-asymmetry MG-entry tick-mark positions (in pawns, signed
# user-perspective). Symmetric ±BASELINE around 0 cp, derived from the 2026-05-04
# Lichess benchmark v3 deduplicated per-physical-game mean of +25.18 cp
# (n=1.25M trimmed games, 2026-05-04 Lichess benchmark).
#
# The previous per-color asymmetric values (+0.315 / -0.189) were a sampling
# artefact of the per-(user, color) slice: white-user and black-user rows
# were almost entirely *different* physical games, so the small skill edge of
# benchmark users vs typical opponents split the per-color means apart.
# Deduping at the game level cancels that artefact and yields a single
# symmetric tempo baseline of about ±25 cp (white's first-move advantage).
#
# On Openings surfaces these are the eval bar's centre AND the H0 reference of the
# MG-entry eval z-test (Phase 242, D-13; applied by opening_eval.finalize_opening_eval),
# so "typical for the colour" reads as neutral. The endgame-entry eval is unchanged:
# endgame_service still tests against 0 cp.
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
