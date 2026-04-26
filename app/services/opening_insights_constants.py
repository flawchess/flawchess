"""Phase 70 (v1.13) opening insights constants.

Single source of truth for thresholds shared between the repository
(SQL HAVING clause) and the service (Python classifier). Mirrors
frontend/src/lib/arrowColor.ts thresholds; CI-enforced via
tests/services/test_opening_insights_arrow_consistency.py.

Split into its own module to avoid a circular import: the repository
imports these constants, and the service imports from the repository,
so the constants cannot live in either file.
"""

OPENING_INSIGHTS_MIN_ENTRY_PLY: int = 3
OPENING_INSIGHTS_MAX_ENTRY_PLY: int = 16
OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE: int = 20
OPENING_INSIGHTS_LIGHT_THRESHOLD: float = 0.55
