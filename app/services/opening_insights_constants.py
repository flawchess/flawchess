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

# Confidence buckets — one-sided Wald p-value thresholds plus N>=10 gate.
# One-sided framing matches the directional question a finding card asks
# ("is this score worse/better than 50%?"); equivalent to halving the
# two-sided p. With N < 10, confidence is forced to "low" regardless of
# p-value: small samples already carry the unreliable-stats opacity dim in
# the UI, and the bucket should match that signal.
OPENING_INSIGHTS_CONFIDENCE_MIN_N: int = 10
OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P: float = 0.05
OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P: float = 0.10

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
# user-perspective). Per-game mean from the 2026-05-04 Lichess benchmark
# (n=1.25M trimmed games — see reports/benchmarks-2026-05-04.md §3a).
#
# Used only as a visual reference tick on the MG-entry bullet chart, NOT as
# the H0 reference for the z-test. The test runs against 0 cp (engine-balanced)
# regardless of color. Quick task 260504-rvh decoupled the visual baseline
# from the test H0 so that a user whose MG-entry mean equals the engine
# asymmetry (+0.32 pawns for white, -0.19 for black) is no longer
# automatically classified as "no signal" — the chart shows the asymmetry
# as a tick the user can read against.
EVAL_BASELINE_PAWNS_WHITE: float = 0.315
EVAL_BASELINE_PAWNS_BLACK: float = -0.189

# N gate for the eval z-test, raised from 10 to 20 to keep the Edgeworth
# leading-error term on the normal approximation under ~2% (the population
# excess kurtosis of ~2.4 cp at MG entry slows CLT convergence relative to a
# normal-data baseline). Decoupled from OPENING_INSIGHTS_CONFIDENCE_MIN_N
# (which gates the WDL score-confidence test, where the binomial-style
# variance is bounded and N=10 stays defensible).
EVAL_CONFIDENCE_MIN_N: int = 20
