---
phase: 164-maia-elo-lichess-blitz-normalization
reviewed: 2026-07-11T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - app/services/chesscom_to_lichess.py
  - app/schemas/library.py
  - app/services/library_service.py
  - tests/services/test_chesscom_to_lichess.py
  - tests/services/test_library_service.py
  - frontend/src/types/library.ts
  - frontend/src/hooks/useMaiaEloDefault.ts
  - frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 164: Code Review Report

**Reviewed:** 2026-07-11 (re-reviewed same day after gap-closure plan 164-04)
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Reviewed the SEED-093 Lichess-blitz rating normalization: the new
`normalize_to_lichess_blitz` / `_invert_table2_column` in
`chesscom_to_lichess.py`, the nullable `*_rating_lichess_blitz` schema fields,
their wiring in `library_service._build_card`, and the frontend
`useMaiaEloDefault` fallback logic.

The rating-conversion math and its Table-2 inversion are correct against the
current snapshot: the exact-anchor short-circuit, the leftmost-tie resolution
(classical 1935 across chess.com Blitz 1500/1550/1600), the None-gap filtering
(classical 2800/2900/3000), and the below/above-range clamps all check out and
are well tested. Correspondence gating is sound — `is_correspondence_time_control`
keys on the shared "1/{sec}" separator, so both chess.com Daily and lichess
correspondence are short-circuited before any TC dispatch, and it runs FIRST in
both `normalize_to_lichess_blitz` and `_build_card`. Null-safety of the new
fields is correct on both ends: the backend guards on
`rating is not None and time_control_bucket is not None`, and the frontend uses
`?? raw` fallback (Pitfall 5) plus optional/nullable typing.

No BLOCKER-level defects. The findings below concern a latent robustness gap
in the inversion helper (WR-02, still open) plus minor convention/coverage
notes (IN-01, IN-03, still open). **WR-01 is resolved** — see the gap-closure
re-review below.

## Gap-Closure Re-Review (Plan 164-04, commit c4b6d0b3)

Re-reviewed the targeted diff that closes WR-01:

- `app/services/chesscom_to_lichess.py` — the chess.com branch of
  `normalize_to_lichess_blitz` now maps `source_tc == "classical"` to an
  `effective_tc: ChessComSourceTC = "rapid"` before calling
  `convert_chesscom_to_lichess`, instead of returning `None`.
- `tests/services/test_chesscom_to_lichess.py` — the old
  `test_normalize_to_lichess_blitz_chesscom_classical_returns_none` is
  replaced by `..._maps_to_rapid`, asserting the result equals
  `convert_chesscom_to_lichess(1500, "rapid", "blitz")` and is not `None`.
- `tests/services/test_library_service.py` — new integration test
  `test_chesscom_classical_noncorrespondence_card_has_normalized_rating`
  exercises the fix through `get_library_game` end-to-end (real `Game` row,
  `time_control_str="1800+30"`, `time_control_bucket="classical"`), asserting
  raw ratings are untouched and `*_rating_lichess_blitz` equals the rapid-path
  conversion.

**Verification performed:**
- `uv run ty check app/ tests/` — zero errors (the `effective_tc:
  ChessComSourceTC` annotation correctly narrows the ternary's inferred
  `Literal["bullet","blitz","rapid"]` result to the wider `ChessComSourceTC`
  alias per CLAUDE.md ty-compliance rules).
- `uv run ruff format --check` / this file's slice — already formatted.
- `uv run pytest tests/services/test_chesscom_to_lichess.py
  tests/services/test_library_service.py::TestGetLibraryGame -q` — 63 passed.
- Traced the guard order in `library_service._build_card` (lines ~526-550):
  `is_correspondence_time_control` is computed once and passed in; it keys
  purely on the `"/"` separator (`app/services/normalization.py:28-41`), so a
  chess.com Daily game (`"1/86400"`) is caught by the `is_correspondence`
  early-return in `normalize_to_lichess_blitz` (line 360) *before* the
  `platform == "chess.com"` branch is reached — the classical→rapid mapping
  is unreachable for Daily games. A non-correspondence classical-bucketed
  game (e.g. `"1800+30"`, no `/`) reaches the new mapping correctly.
- Checked for out-of-domain results: the new branch reuses
  `convert_chesscom_to_lichess(rating, "rapid", "blitz")` verbatim — the same
  tested rapid-inversion path already exercised by
  `test_normalize_to_lichess_blitz_chesscom_rapid_via_table1_chain` — so no
  new math or edge case is introduced; it inherits the existing None-on-
  out-of-range and None-on-missing-column behavior of that path.
- Comment-bug-fix convention: a comment explaining the contract change is
  present at both the fix site (`chesscom_to_lichess.py:363-367`) and the
  docstring (`:335-344`), and the renamed test's comment explains the "why"
  (matches `_BUCKET_TO_SOURCE_TC`'s existing convention). Satisfies CLAUDE.md's
  "Comment bug fixes" rule.

**Result: no new defects found in the 164-04 diff.** WR-01 is resolved — the
two code paths (SQL composed grid vs. Maia normalization) now agree that a
non-correspondence chess.com `classical`-bucketed game carries a rapid-scale
rating. IN-02's chess.com-classical-bucket coverage gap is now closed by the
new `test_library_service.py` integration test (see updated IN-02 below); its
lichess-side integration-test gap remains open.

## Warnings

### WR-01: ~~chess.com "classical" bucket returns None~~ — RESOLVED (164-04, commit c4b6d0b3)

**File:** `app/services/chesscom_to_lichess.py:360-369`
**Original issue:** `normalize_to_lichess_blitz` returned `None` for
`platform == "chess.com"` when `source_tc == "classical"`, diverging from the
module's own `_BUCKET_TO_SOURCE_TC` classical→rapid convention used by the SQL
composed-grid pipeline, and causing the frontend to fall back to a raw,
wrong-scale rating for the Maia ELO default.
**Resolution:** `source_tc == "classical"` is now mapped to
`effective_tc: ChessComSourceTC = "rapid"` before calling
`convert_chesscom_to_lichess(rating, effective_tc, "blitz")`, matching the
composed-grid convention. Verified via `ty check` (zero errors), full test
suite pass, and a new end-to-end integration test through `get_library_game`.
No further action needed.

### WR-02: `_invert_table2_column` relies on unasserted column monotonicity and dict insertion order for bisect correctness

**File:** `app/services/chesscom_to_lichess.py:525-534`
**Issue:** The function builds `values` by iterating `CHESSCOM_BLITZ_TO_LICHESS.items()`
and then calls `bisect.bisect_left(values, rating)`. `bisect` silently returns
wrong indices (no exception) unless two invariants hold: (1) the dict iterates
in ascending anchor order, and (2) the target column is non-decreasing in that
order. Both hold for the current snapshot, but neither is enforced. The sibling
`_invert_intra_tc` at least (a) iterates a pre-sorted key list
(`_CHESSCOM_INTRA_KEYS`) rather than trusting dict order, and (b) asserts each
value is non-None at module load. `_invert_table2_column` has no equivalent
guard, so a future ChessGoals refit that reorders rows or introduces a
non-monotone dip in the bullet/rapid/classical columns would corrupt inversion
results without any test or assertion firing — precisely the "DO NOT edit
numerics" refit trigger the module documents.

**Fix:** Iterate a sorted key list and assert monotonicity at module load (once),
mirroring `_invert_intra_tc`:

```python
pairs = sorted(
    (
        (anchor, value)
        for anchor, row in CHESSCOM_BLITZ_TO_LICHESS.items()
        if (value := row[column]) is not None
    ),
    key=lambda p: p[0],
)
values = [v for _, v in pairs]
assert values == sorted(values), (
    f"Table 2 column {column!r} must be non-decreasing for bisect inversion"
)
```

**Status:** still open — out of scope for gap-closure plan 164-04 (untouched by
that diff); not re-evaluated in this re-review.

## Info

### IN-01: lichess-blitz identity branch skips the module's range-validation convention

**File:** `app/services/chesscom_to_lichess.py:371-372`
**Issue:** Every other branch in `normalize_to_lichess_blitz` (and the whole
module) returns `None` rather than extrapolating when a rating is outside the
published table range ("refuse rather than guess"). The lichess-blitz path
returns `rating` verbatim with no bounds check, so a provisional or malformed
lichess blitz rating (e.g. 3500 or 100) passes through unclamped. Impact is
mitigated twice downstream — `useMaiaEloDefault.clampToLadderBounds` clamps to
the ladder, and `useMaiaEngine`'s `nearestByElo` snaps to the closest rung — so
this is not a live defect, only an inconsistency in the backend contract. The
test suite explicitly excludes lichess+blitz from the out-of-range checks
(`test_chesscom_to_lichess.py:490-500`), confirming the gap is deliberate but
undocumented at the call site.

**Fix:** Add a one-line comment at line 371 noting the identity is intentionally
unbounded and relies on the frontend clamp, or clamp to the
`[_CHESSCOM_*]`-derived Maia range for consistency.

**Status:** still open — out of scope for gap-closure plan 164-04; not
re-evaluated in this re-review.

### IN-02: chess.com-classical integration coverage now closed by 164-04; lichess non-blitz integration coverage still missing

**File:** `tests/services/test_library_service.py:1003-1155`
**Issue (updated):** The original finding noted `TestGetLibraryGame` had no
integration-level test for either (a) the lichess rapid/bullet/classical path,
or (b) the chess.com classical-bucket path, at the `_build_card` integration
boundary. Gap-closure plan 164-04 added
`test_chesscom_classical_noncorrespondence_card_has_normalized_rating`, which
closes gap (b) — it seeds a real `Game` row
(`platform="chess.com"`, `time_control_bucket="classical"`,
`time_control_str="1800+30"`) and asserts `*_rating_lichess_blitz` equals the
rapid-path conversion end-to-end through `get_library_game`. Gap (a) — a
lichess rapid/bullet/classical game producing the inverted normalized rating
end-to-end through the real `Game` model and its `cast(Platform, ...)` /
`cast(TimeControlBucket, ...)` wiring — remains uncovered at the integration
level (only unit-tested directly against `normalize_to_lichess_blitz`).

**Fix:** Add a `get_library_game` case seeding a lichess rapid game (e.g.
`white_rating=1930`, `time_control_bucket="rapid"`) asserting
`white_rating_lichess_blitz == 1780`.

**Status:** partially resolved by 164-04 (chess.com-classical case added);
lichess-side integration gap still open.

### IN-03: `FlawListItem` carries raw `white_rating`/`black_rating` but no normalized fields

**File:** `app/schemas/library.py:164-165` (vs. `GameFlawCard` `106-107`)
**Issue:** Only `GameFlawCard` gained the `*_rating_lichess_blitz` fields.
`FlawListItem` (the Flaws-subtab rows) still exposes raw ratings only. This is
consistent with the current design (the Maia ELO default is driven from the
single-game `GameFlawCard`, not the flaw list), so it is not a defect today —
flagging only so that if a future surface drives the Maia slider from the Flaws
tab, the normalized rating will be silently absent there.

**Fix:** None required now; note the asymmetry so it is a conscious choice.

**Status:** still open — out of scope for gap-closure plan 164-04; not
re-evaluated in this re-review.

---

_Reviewed: 2026-07-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Re-reviewed: 2026-07-11 (gap-closure plan 164-04, commit c4b6d0b3) — WR-01 confirmed resolved, no new defects._
