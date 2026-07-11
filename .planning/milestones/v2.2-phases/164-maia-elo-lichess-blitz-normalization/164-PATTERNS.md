# Phase 164: Maia ELO Lichess-blitz normalization - Pattern Map

**Mapped:** 2026-07-11
**Files analyzed:** 7 (all modified, none newly created)
**Analogs found:** 7 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|---------------|
| `app/services/chesscom_to_lichess.py` (add `_invert_table2_column`, `normalize_to_lichess_blitz`) | utility (pure transform) | transform | same file's `_invert_intra_tc` + `convert_chesscom_to_lichess` | exact (same file, same module conventions) |
| `app/schemas/library.py` (`GameFlawCard` + 2 fields) | model (Pydantic schema) | request-response | same file's existing `white_rating`/`black_rating` fields | exact |
| `app/services/library_service.py` (`_build_card`) | service | CRUD/transform (read-serialize) | same function's existing `white_rating=game.white_rating` construction | exact |
| `tests/services/test_chesscom_to_lichess.py` (new test cases) | test | unit | same file's existing parametrized/table-inversion tests | exact |
| `frontend/src/types/library.ts` (`GameFlawCard` + 2 fields) | model (TS interface) | request-response | same file's existing `white_rating`/`black_rating` fields | exact |
| `frontend/src/hooks/useMaiaEloDefault.ts` (`MaiaEloGameData`, `deriveRawDefault`) | hook | transform | same file's existing `deriveRawDefault` raw-rating read | exact |
| `frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts` (new cases) | test | unit | same file's existing `gameData()` fixture helper + game-mode tests | exact |

Every file is a targeted extension of an existing file — no new files, no new analog search needed outside the phase's own named files (all confirmed in RESEARCH.md via direct read).

## Pattern Assignments

### `app/services/chesscom_to_lichess.py` (utility, transform)

**Analog:** same file — `_invert_intra_tc` (lines 375-425), `_interp_int_column` (231-267), `convert_chesscom_to_lichess` (275-304), `_interp_blitz_to_lichess` (367-372)

**Imports pattern** (lines 33-36, unchanged — no new imports needed):
```python
from __future__ import annotations

import bisect
from typing import Final, Literal, Mapping
```

**Core inversion pattern to copy from `_invert_intra_tc`** (lines 375-425) — copy the bisect-scan-then-interpolate structure, but do NOT copy the `assert value is not None` loop (lines 392-399) verbatim; Table 2's `classical` column has real `None` rows (Pitfall 4) so build the `(anchor, value)` pairs with a filter instead:
```python
def _invert_table2_column(
    rating: int,
    column: Literal["bullet", "rapid", "classical"],
) -> int | None:
    pairs = [
        (anchor, row[column])
        for anchor, row in CHESSCOM_BLITZ_TO_LICHESS.items()
        if row[column] is not None
    ]
    values = [v for _, v in pairs]
    anchors = [a for a, _ in pairs]
    if rating < values[0] or rating > values[-1]:
        return None
    idx = bisect.bisect_left(values, rating)
    if idx < len(values) and values[idx] == rating:
        return anchors[idx]  # leftmost tie wins — mirrors _invert_intra_tc's
                              # "fall back to the lower Blitz anchor" comment (line 421-422)
    if idx == 0:
        return None
    lo_val, hi_val = values[idx - 1], values[idx]
    lo_anchor, hi_anchor = anchors[idx - 1], anchors[idx]
    if hi_val == lo_val:
        return lo_anchor  # REACHABLE for classical (three 1935 ties) — test this, unlike
                           # _invert_intra_tc's "unreachable for current snapshot" comment (line 419)
    frac = (rating - lo_val) / (hi_val - lo_val)
    return round(lo_anchor + frac * (hi_anchor - lo_anchor))
```

**Public dispatcher pattern to copy from `convert_chesscom_to_lichess`** (lines 275-304) — same "check special case first, then branch on source, chain into Table 2" shape:
```python
def normalize_to_lichess_blitz(
    rating: int,
    platform: Platform,          # reuse app.schemas.normalization.Platform, don't redeclare
    source_tc: TimeControlBucket,  # reuse app.schemas.normalization.TimeControlBucket
    *,
    is_correspondence: bool,      # caller-supplied — keeps this module DB/IO-free (module docstring contract)
) -> int | None:
    if is_correspondence:
        return None
    if platform == "chess.com":
        if source_tc == "classical":
            return None  # chess.com has no native "classical" TC in ChessGoals tables (Pitfall 2)
        return convert_chesscom_to_lichess(rating, source_tc, "blitz")
    # platform == "lichess"
    if source_tc == "blitz":
        return rating  # identity
    blitz_equiv = _invert_table2_column(rating, source_tc)
    if blitz_equiv is None:
        return None
    return _interp_blitz_to_lichess(blitz_equiv, "blitz")
```

**Error handling / null-safety pattern:** every branch returns `None` rather than raising or extrapolating (matches the whole module's "refuse rather than guess" convention stated in `_interp_int_column`'s docstring, lines 236-244). No try/except anywhere in this module — invalid range is signaled via `None`, not an exception.

**Docstring/provenance convention:** update the module docstring (lines 1-31) to mention the new Lichess-intra-TC direction, following the existing style of dated provenance notes (e.g. line 28-30's "Phase 149-04 PRUNE-02" note).

---

### `app/schemas/library.py` (model, request-response)

**Analog:** `GameFlawCard.white_rating` / `black_rating` (lines 99-100)

**Pattern to copy** — add two new nullable `int | None` fields immediately adjacent to the existing rating fields, following the class's existing "Phase N additions" comment convention (line 108):
```python
white_rating: int | None
black_rating: int | None
white_rating_lichess_blitz: int | None = None  # NEW (Phase 164) — nullable, defaults None
black_rating_lichess_blitz: int | None = None  # NEW (Phase 164)
```
Note: existing `white_rating`/`black_rating` have NO default (required), but the new fields should default to `None` per Pitfall 5's optionality requirement and to avoid breaking any other existing `GameFlawCard(...)` construction site that doesn't pass them.

---

### `app/services/library_service.py::_build_card` (service, CRUD/transform)

**Analog:** same function, existing `white_rating=game.white_rating` / `black_rating=game.black_rating` construction (lines 533-534), and the existing `is_correspondence_time_control` call one function up (line 138, inside `_build_eval_series`'s caller scope — NOT directly reusable inside `_build_card` since it's a different function's local variable).

**Imports pattern** (already imported at line 74 — reuse, no new import needed):
```python
from app.services.normalization import is_correspondence_time_control
```
Add import for the new backend function:
```python
from app.services.chesscom_to_lichess import normalize_to_lichess_blitz
```

**Core pattern** — compute both fields right before the `GameFlawCard(...)` return, mirroring the existing `is_correspondence = is_correspondence_time_control(...)` call shape at line 138:
```python
is_correspondence = is_correspondence_time_control(game.time_control_str)
white_rating_lichess_blitz = (
    normalize_to_lichess_blitz(
        game.white_rating, game.platform, game.time_control_bucket,
        is_correspondence=is_correspondence,
    )
    if game.white_rating is not None and game.time_control_bucket is not None
    else None
)
black_rating_lichess_blitz = (
    normalize_to_lichess_blitz(
        game.black_rating, game.platform, game.time_control_bucket,
        is_correspondence=is_correspondence,
    )
    if game.black_rating is not None and game.time_control_bucket is not None
    else None
)
```
Then add to the `GameFlawCard(...)` construction (lines 524-535), directly below the existing rating fields:
```python
white_rating=game.white_rating,          # UNCHANGED — raw, still consumed by PlayerBar
black_rating=game.black_rating,          # UNCHANGED
white_rating_lichess_blitz=white_rating_lichess_blitz,   # NEW
black_rating_lichess_blitz=black_rating_lichess_blitz,   # NEW
```

**Error handling:** no try/except needed — `normalize_to_lichess_blitz` never raises, only returns `None` for invalid/out-of-range/correspondence inputs (see module pattern above). The `is not None` guards above are the only branch logic required.

---

### `tests/services/test_chesscom_to_lichess.py` (test, unit)

**Analog:** existing tests in the same file — `test_chesscom_bullet_to_lichess_bullet_via_table_inversion` (lines 81-91), `test_chesscom_daily_returns_none` (103-109), `test_below_min_returns_none`/`test_above_max_returns_none` (111-125), and the parametrized-accessor pattern at lines 147-163.

**Imports pattern** (lines 27-31) — extend the existing import block:
```python
from app.services.chesscom_to_lichess import (
    normalize_to_lichess_blitz,  # NEW
    # ...existing imports...
)
```

**Test cases to add** (per RESEARCH.md's Phase Requirements → Test Map, all new):
1. chess.com blitz → identity Table 2 lookup (mirror `test_chesscom_blitz_to_lichess_blitz_exact_anchor`, line 49).
2. chess.com bullet/rapid → Lichess-blitz via Table 1 inversion (mirror `test_chesscom_bullet_to_lichess_bullet_via_table_inversion`, line 81).
3. chess.com daily → `None` (mirror `test_chesscom_daily_returns_none`, line 103).
4. chess.com classical → `None` (Pitfall 2 — new case, no existing analog exactly, but same shape as #3).
5. Lichess blitz → identity.
6. Lichess bullet/rapid/classical → Lichess-blitz via new inversion (Pattern 2's `_invert_table2_column`).
7. Lichess classical tie: `rating=1935` → lowest of the three tied anchors (1500) — explicit new test per Pitfall 3.
8. Lichess classical None-gap: rating above the chesscom-blitz-2700-equivalent → `None` — explicit new test per Pitfall 4.
9. Correspondence (both platforms) → `None` regardless of `source_tc` — Pitfall 1.
10. Out-of-range (below/above published bounds) → `None` for all 6 `(platform, source_tc)` combos — parametrize like `test_accessors_return_none_at_edges` (lines 147-163).

**Parametrize pattern to copy** (lines 147-163):
```python
@pytest.mark.parametrize(
    ("platform", "source_tc", "rating"),
    [
        ("chess.com", "blitz", 400),
        ("chess.com", "bullet", 3200),
        ("lichess", "rapid", 200),
        # ... all 6 combos
    ],
)
def test_normalize_to_lichess_blitz_out_of_range_returns_none(platform, source_tc, rating) -> None:
    assert normalize_to_lichess_blitz(rating, platform, source_tc, is_correspondence=False) is None
```

---

### `frontend/src/types/library.ts` (model, request-response)

**Analog:** `GameFlawCard.white_rating` / `black_rating` (lines 67-68)

**Pattern to copy** — add two nullable-optional fields directly beneath the existing rating fields, following Pitfall 5's requirement (must not be required, must allow `undefined`/`null`):
```typescript
white_rating: number | null;
black_rating: number | null;
white_rating_lichess_blitz?: number | null;  // NEW (Phase 164)
black_rating_lichess_blitz?: number | null;  // NEW (Phase 164)
```
Follow the file's existing "Phase N additions" comment convention (line 215 documents Phase 112's additions — add an equivalent one-line note for Phase 164).

---

### `frontend/src/hooks/useMaiaEloDefault.ts` (hook, transform)

**Analog:** same file's `MaiaEloGameData` interface (lines 30-34) and `deriveRawDefault` (lines 69-81)

**Type pattern to copy:**
```typescript
export interface MaiaEloGameData {
  user_color: string;
  white_rating: number | null;
  black_rating: number | null;
  white_rating_lichess_blitz?: number | null;  // NEW — optional per Pitfall 5
  black_rating_lichess_blitz?: number | null;  // NEW
}
```

**Core read-with-fallback pattern** (extends lines 69-81 exactly):
```typescript
function deriveRawDefault(
  isGameMode: boolean,
  gameData: MaiaEloGameData | undefined,
  profile: MaiaEloProfile | undefined,
  sideToMove: MoverColor | undefined,
): number | null {
  if (isGameMode) {
    if (gameData == null) return null;
    const moverColor = sideToMove ?? gameData.user_color;
    if (moverColor === 'white') {
      return gameData.white_rating_lichess_blitz ?? gameData.white_rating;
    }
    return gameData.black_rating_lichess_blitz ?? gameData.black_rating;
  }
  return profile?.current_rating ?? FREE_PLAY_DEFAULT_ELO;
}
```
Everything downstream of `deriveRawDefault` (the `clampToLadderBounds` call, `userOverrodeRef`, the `useEffect` re-derivation guard, free-play path) stays untouched — this is an additive change confined to the read inside `deriveRawDefault`.

---

### `frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts` (test, unit)

**Analog:** existing `gameData()` fixture helper (lines 19-21 per RESEARCH.md) and existing game-mode default tests in the same file.

**New cases to add:**
1. normalized field present for the mover's color → used (not raw).
2. normalized field `null`/absent for the mover's color → falls back to raw `white_rating`/`black_rating`.
3. mixed: normalized present for white but not black (or vice versa) → correct fallback per color, keyed off `sideToMove`.

**Fixture pattern** — extend the existing `gameData()` helper to accept the two new optional fields (defaulting to `undefined` so existing call sites without them keep compiling, per Pitfall 5).

## Shared Patterns

### "Refuse rather than guess" null-safety convention
**Source:** `app/services/chesscom_to_lichess.py` module docstring (lines 24-26) and `_interp_int_column` (lines 236-244)
**Apply to:** `normalize_to_lichess_blitz`, `_invert_table2_column` — every edge case (out-of-range, None-gap, correspondence, chess.com-native-classical) returns `None`, never raises, never extrapolates.

### Additive nullable-field extension of an existing DTO
**Source:** `app/schemas/library.py::GameFlawCard` + `frontend/src/types/library.ts::GameFlawCard` (mirrored Pydantic/TS pair, same field names both sides)
**Apply to:** the two new `*_lichess_blitz` fields on both the backend schema and the frontend type — must default to `None`/optional on both sides so no existing construction site or test fixture breaks (Pitfall 5).

### Caller-supplied boolean over cross-module import
**Source:** `library_service.py:138`'s existing `is_correspondence_time_control(game.time_control_str)` call, reused as a parameter rather than imported into `chesscom_to_lichess.py`
**Apply to:** `normalize_to_lichess_blitz(..., *, is_correspondence: bool)` — keeps the pure-math module free of the `app.services.normalization` dependency edge, per RESEARCH.md's Open Question 2 resolution.

### Leftmost-tie-wins conservative-estimate convention
**Source:** `_invert_intra_tc`'s tie-handling comment (`chesscom_to_lichess.py:417-423`)
**Apply to:** `_invert_table2_column`'s new (and, unlike Table 1, actually reachable) tie branch for Table 2's `classical` column — return the lowest chess.com-Blitz anchor on a tie.

## No Analog Found

None — every file in this phase is a targeted extension of an existing file with a directly analogous existing pattern in the same file.

## Metadata

**Analog search scope:** `app/services/chesscom_to_lichess.py`, `app/schemas/library.py`, `app/services/library_service.py`, `tests/services/test_chesscom_to_lichess.py`, `frontend/src/types/library.ts`, `frontend/src/hooks/useMaiaEloDefault.ts`, `frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts` (all directly read; no broader codebase Glob/Grep search needed — RESEARCH.md already named and verified every touchpoint by direct read).
**Files scanned:** 7 (all read in full or targeted ranges during this pass + the prior research pass)
**Pattern extraction date:** 2026-07-11
