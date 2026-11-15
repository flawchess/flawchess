"""Frozen facepalm models that tests pin explicitly (Phase 254).

`FACEPALM_MODEL` is the shipped, refitted model and moves with every refit. A test written against
an earlier model (the Phase 250 reproduction, the legacy features table, the "owner fixtures
improved" check) must pin that model here instead of reading the shipped constants.
"""

from __future__ import annotations

from typing import Final

from app.services.facepalm_score import FacepalmModel

# The Phase 250 model (fitted 2026-11-13 on facepalm-features-2026-11-13.tsv), frozen: loss
# floored at 0, no missed term, the reply spread on every row, no optional inputs. The shape
# fields keep the FacepalmModel defaults, which are exactly those pre-refit values (D-12).
PHASE_250_MODEL: Final[FacepalmModel] = FacepalmModel(
    intercept=-1.4193,
    played_coef=-0.6629,
    spread_coef=-0.3304,
    loss_coef=1.1570,
    loss_floor=0,
)
