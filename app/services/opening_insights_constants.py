"""Phase 75 (v1.14) opening insights constants.

Single source of truth for thresholds shared between the repository
(SQL HAVING clause) and the service (Python classifier + confidence
helper). Mirrors frontend/src/lib/arrowColor.ts thresholds; CI-enforced
via tests/services/test_opening_insights_arrow_consistency.py.

Split into its own module to avoid a circular import: the repository
imports these constants, and the service imports from the repository,
so the constants cannot live in either file.
"""

# Entry-position bounds — unchanged from Phase 70
OPENING_INSIGHTS_MIN_ENTRY_PLY: int = 3
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

# Confidence buckets — two-sided Wald p-value thresholds plus N>=10 gate.
# Replaces the prior CI half-width bucketing (which answered "is the point
# estimate precise?" rather than "is this score different from 50% by chance?").
# With N < 10, confidence is forced to "low" regardless of p-value: small
# samples already carry the unreliable-stats opacity dim in the UI, and the
# bucket should match that signal.
OPENING_INSIGHTS_CONFIDENCE_MIN_N: int = 10
OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P: float = 0.01
OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P: float = 0.05
