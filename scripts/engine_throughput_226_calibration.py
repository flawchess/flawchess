"""engine_throughput_226_calibration.py — Phase 226 calibration statistics.

Turns an in-session A0a-vs-A0b null comparison into per-family powered
thresholds (D-09, D-10), turns an arm-vs-A0a `ParityVerdictResult` into a
powered verdict with a z-based shape guard (D-10, replacing the Phase 199
CI-overlap shape guard per RESEARCH Pattern 6), turns the set of shipped
items' powered verdicts into one refit decision (D-11), and implements the
report-only Maia-anchor reproducibility cross-check (RESEARCH F-7).

This module takes every threshold as a function PARAMETER and holds NO frozen
constants itself — those live in `engine_throughput_226_verdict.py` (Plan
226-05), the accept-rule twin that transcribes `reports/engine-throughput-226/
step0-protocol.md`'s numbers verbatim, mirroring how `calibration_parity_verdict.py`
carries Phase 199's frozen constants while `calibration_anchor_fit.py` stays
parametric.

stdlib-only (`json`/`math`/`pathlib`/`typing`) — no numpy/scipy, matching
`calibration_parity_verdict.py`'s and `calibration_anchor_fit.py`'s
convention. Standalone research tool (`scripts/`, not `app/`) — exempt from
CLAUDE.md's Sentry-capture rules, which apply only to `app/services` and
`app/routers`.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, TypedDict, cast

from calibration_parity_verdict import (
    ExposedCellResult,
    Family,
    FamilyResult,
    ParityVerdictResult,
)

Item = Literal["underfill", "guard", "root_split", "candidate_cap"]

#: (bot_elo, bot_blend) — a calibration cell key, same shape as
#: `calibration_parity_verdict.CellKey`.
ZGuardCell = tuple[int, float]

#: One row from a calibration harness ledger TSV (`calibration-harness-*.tsv`),
#: as read by `csv.DictReader` — every field is a string, including numeric
#: ones (`game_index`, `cp_loss_sum`); callers pass the raw dict rows.
LedgerRow = Mapping[str, str]


class FamilyNullCheck(TypedDict):
    """One family's (A0b-vs-A0a) null-derived powered threshold (D-10)."""

    null_shift: float
    null_se: float
    base_threshold: float
    se_floor: float
    threshold: float
    model_check_fired: bool
    escalate: bool


class FamilyPowered(TypedDict):
    """One family's pooled-shift reading against a powered threshold."""

    pooled_shift: float
    pooled_se: float
    threshold: float
    beyond_threshold: bool


class PoweredVerdict(TypedDict):
    """An arm-vs-A0a `ParityVerdictResult` rendered as a powered verdict."""

    label: str
    validity: Literal["valid", "void"]
    maia: FamilyPowered
    sf: FamilyPowered
    z_guard_cells: list[ZGuardCell]
    real_shift: bool | None


class RefitDecision(TypedDict):
    decision: Literal["refit", "no-refit", "escalate"]
    reasons: list[str]


class IdentityResult(TypedDict):
    """Maia-anchor reproducibility cross-check result (RESEARCH F-7,
    report-only — never a gate criterion)."""

    matched: int
    identical: int
    differing: list[tuple[str, str, int]]


def load_parity_verdict(path: str | Path) -> ParityVerdictResult:
    """Reads a `ParityVerdictResult`-shaped JSON file written by
    `calibration_parity_verdict.py`'s `_write_verdict`. Raises `ValueError` on
    a missing top-level family key rather than returning a partial result."""
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    for family in ("maia", "sf"):
        if family not in payload:
            raise ValueError(
                f"load_parity_verdict: {path!r} is missing required family key {family!r}"
            )
    return cast(ParityVerdictResult, payload)


def null_check(
    null_parity: ParityVerdictResult,
    base_thresholds: Mapping[Family, float],
    se_multiplier: float,
    escalation_factor: float,
) -> dict[Family, FamilyNullCheck]:
    """Derives a powered per-family threshold from an in-session A0b-vs-A0a
    null comparison (D-09, D-10).

    Per family: `se_floor = se_multiplier * pooled_se`; `threshold =
    max(base_threshold, se_floor)`. If the null's own `|pooled_shift|`
    exceeds that threshold, the threshold inflates to the observed
    `|pooled_shift|` and `model_check_fired` is set (the null moved by more
    than the model predicted). `escalate` fires independently, against the
    unmodified `base_threshold`, when `|pooled_shift| > escalation_factor *
    base_threshold` — a null drift too large to absorb by inflating the
    threshold at all.

    A NaN pooled SE (every cell's SE degenerate) raises `ValueError` rather
    than silently producing a threshold from a non-value.
    """
    result: dict[Family, FamilyNullCheck] = {}
    family: Family
    for family in ("maia", "sf"):
        pooled = null_parity[family]["pooled"]
        null_shift = pooled["shift"]
        null_se = pooled["se"]
        if math.isnan(null_se):
            raise ValueError(
                f"null_check: {family} pooled se is NaN (every cell SE degenerate) — "
                "cannot derive a threshold from a non-value"
            )
        base_threshold = base_thresholds[family]
        se_floor = se_multiplier * null_se
        threshold = max(base_threshold, se_floor)
        model_check_fired = abs(null_shift) > threshold
        if model_check_fired:
            threshold = abs(null_shift)
        escalate = abs(null_shift) > escalation_factor * base_threshold
        result[family] = {
            "null_shift": null_shift,
            "null_se": null_se,
            "base_threshold": base_threshold,
            "se_floor": se_floor,
            "threshold": threshold,
            "model_check_fired": model_check_fired,
            "escalate": escalate,
        }
    return result


def _family_powered(family_result: FamilyResult, threshold: float) -> FamilyPowered:
    pooled = family_result["pooled"]
    shift = pooled["shift"]
    return {
        "pooled_shift": shift,
        "pooled_se": pooled["se"],
        "threshold": threshold,
        "beyond_threshold": abs(shift) > threshold,
    }


def _z_guard_cells(
    maia_cells: Sequence[ExposedCellResult],
    sf_cells: Sequence[ExposedCellResult],
    z_guard: float,
) -> list[ZGuardCell]:
    """Cells (paired by index across families, strict zip — both families'
    `exposed_cells` come from the same `parity_verdict` call over the same
    sorted cell-key list) where `abs(shift) / se_shift > z_guard` in BOTH
    families. A zero `se_shift` raises `ValueError` (cannot compute a
    z-score) rather than silently dividing."""
    cells: list[ZGuardCell] = []
    for maia_cell, sf_cell in zip(maia_cells, sf_cells, strict=True):
        for cell in (maia_cell, sf_cell):
            if cell["se_shift"] == 0:
                raise ValueError(
                    "_z_guard_cells: se_shift is 0 for cell "
                    f"({cell['bot_elo']}, {cell['bot_blend']}) — cannot compute a z-score"
                )
        z_maia = abs(maia_cell["shift"]) / maia_cell["se_shift"]
        z_sf = abs(sf_cell["shift"]) / sf_cell["se_shift"]
        if z_maia > z_guard and z_sf > z_guard:
            cells.append((maia_cell["bot_elo"], maia_cell["bot_blend"]))
    return cells


def powered_verdict(
    label: str,
    parity: ParityVerdictResult,
    thresholds: Mapping[Family, float],
    z_guard: float,
) -> PoweredVerdict:
    """Renders one arm-vs-A0a `ParityVerdictResult` as a powered verdict
    (D-10, D-11).

    Validity comes from BOTH families' `null_control.within_threshold` — the
    Phase 199 validity gate is kept unchanged. When void, `real_shift` is
    `None` (a void comparison answers nothing about whether a real shift
    occurred). When valid, `real_shift` is true iff either family's pooled
    shift exceeds its powered `threshold`, or the z-based shape guard fires
    (a cell whose `|shift| / se_shift` exceeds `z_guard` in BOTH families —
    the Phase 199 CI-overlap shape guard is not used, per D-10).
    """
    maia_powered = _family_powered(parity["maia"], thresholds["maia"])
    sf_powered = _family_powered(parity["sf"], thresholds["sf"])
    valid = (
        parity["maia"]["null_control"]["within_threshold"]
        and parity["sf"]["null_control"]["within_threshold"]
    )
    if not valid:
        return {
            "label": label,
            "validity": "void",
            "maia": maia_powered,
            "sf": sf_powered,
            "z_guard_cells": [],
            "real_shift": None,
        }
    z_guard_cells = _z_guard_cells(
        parity["maia"]["exposed_cells"], parity["sf"]["exposed_cells"], z_guard
    )
    real_shift = (
        maia_powered["beyond_threshold"] or sf_powered["beyond_threshold"] or bool(z_guard_cells)
    )
    return {
        "label": label,
        "validity": "valid",
        "maia": maia_powered,
        "sf": sf_powered,
        "z_guard_cells": z_guard_cells,
        "real_shift": real_shift,
    }


def refit_decision(
    verdicts: Mapping[Item, PoweredVerdict], shipped: Mapping[Item, bool]
) -> RefitDecision:
    """Reduces the set of shipped items' powered verdicts to one refit
    decision (D-11: one refit after all shipped items are attributed, never
    per item). Escalate wins over refit, refit wins over no-refit. A held
    item (`shipped[item]` false) never contributes, regardless of its own
    verdict — D-11's refit covers shipped tree-shape changes only.

    Escalate fires whenever a SHIPPED item's verdict is void, or entirely
    absent from `verdicts` — a void comparison on a shipped item is never a
    silent no-refit (D-11).
    """
    reasons: list[str] = []
    escalate = False
    refit = False
    for item, is_shipped in shipped.items():
        if not is_shipped:
            continue
        verdict = verdicts.get(item)
        if verdict is None:
            escalate = True
            reasons.append(f"{item}: shipped item has no powered verdict recorded")
            continue
        if verdict["validity"] == "void":
            escalate = True
            reasons.append(f"{item}: shipped item's comparison is void (null control failed)")
            continue
        if verdict["real_shift"]:
            refit = True
            reasons.append(f"{item}: shipped item shows a real (powered) shift")
    if escalate:
        return {"decision": "escalate", "reasons": reasons}
    if refit:
        return {"decision": "refit", "reasons": reasons}
    return {
        "decision": "no-refit",
        "reasons": reasons if reasons else ["no shipped item shows a real (powered) shift"],
    }


def _ledger_key(row: LedgerRow) -> tuple[str, str, int]:
    return (row["pass"], row["anchor"], int(row["game_index"]))


#: Fields compared for identity between a matched pair of Maia-anchor rows —
#: the same fields RESEARCH F-7 checked by hand against the committed
#: ledgers (result, plies, reason, cp_loss_sum).
_IDENTITY_COMPARE_FIELDS = ("result", "plies", "reason", "cp_loss_sum")


def maia_anchor_identity(
    ledger_a_rows: Sequence[LedgerRow], ledger_b_rows: Sequence[LedgerRow]
) -> IdentityResult:
    """Report-only Maia-anchor reproducibility cross-check (RESEARCH F-7):
    rows from both ledgers, restricted to anchors starting with `"maia"`, are
    keyed by `(pass, anchor, game_index)`. For every key present in both
    ledgers, `result`/`plies`/`reason`/`cp_loss_sum` are compared for exact
    (string) equality — the same fields a byte-identical replay reproduces.
    Never a gate criterion; A0a-vs-sweep-225-a0 and July-21-era drift checks
    both read this as a report-only cross-check (D-09, RESEARCH F-7)."""
    rows_a = {_ledger_key(row): row for row in ledger_a_rows if row["anchor"].startswith("maia")}
    rows_b = {_ledger_key(row): row for row in ledger_b_rows if row["anchor"].startswith("maia")}
    shared_keys = sorted(set(rows_a) & set(rows_b))

    identical = 0
    differing: list[tuple[str, str, int]] = []
    for key in shared_keys:
        row_a, row_b = rows_a[key], rows_b[key]
        if all(row_a[field] == row_b[field] for field in _IDENTITY_COMPARE_FIELDS):
            identical += 1
        else:
            differing.append(key)

    return {"matched": len(shared_keys), "identical": identical, "differing": differing}
