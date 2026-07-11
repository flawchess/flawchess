# Phase 164: Maia ELO Lichess-blitz normalization - Research

**Researched:** 2026-07-11
**Domain:** Pure-Python rating-conversion math (existing module) + FastAPI serialization + React hook consumption
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| SEED-093 | Normalize player ratings to their Lichess-blitz equivalent (Maia-3's training scale) before setting the analysis-board Maia ELO slider default and per-player Maia ELO, so chess.com and Lichess-non-blitz ratings no longer mis-condition Maia's move prediction. | Full converged design in `.planning/seeds/SEED-093-maia-elo-lichess-blitz-normalization.md`. This research confirms the conversion machinery's exact seams (Pattern 1-3), resolves the seed's open on-read-vs-stored sub-decision (on-read, see Architecture Patterns + serialization touchpoint), and surfaces two gaps the seed's routing table didn't cover: the `time_control_bucket="classical"` daily/correspondence ambiguity (Pitfall 1/2) and Table 2's tie/None-gap edge cases in the new inversion direction (Pitfall 3/4). |
</phase_requirements>

## Summary

This phase generalizes an already-shipped conversion module (`app/services/chesscom_to_lichess.py`,
Phase 94.4) rather than building new machinery. The two lookup tables (`CHESSCOM_INTRA_TC`,
`CHESSCOM_BLITZ_TO_LICHESS`) and the `_interp_int_column` primitive are locked-value snapshots that
must not be touched. The only new code is: (1) a Lichess-column inversion sibling to the existing
`_invert_intra_tc`, (2) one public dispatcher `normalize_to_lichess_blitz`, (3) two computed fields
added at the exact point `GameFlawCard` is constructed in `library_service.py` (on-read, no
migration), and (4) a small `useMaiaEloDefault.ts` read-with-fallback change.

The seed's design is sound and its line-131 claim is verified exactly against the real table
(chesscom-blitz 1000 -> Lichess-blitz 1420, Lichess-rapid 1615, gap +195). But the seed's routing
table has one real gap the planner must close: **the persisted `games.time_control_bucket` column
cannot distinguish "daily/correspondence" from "genuine classical"** for either platform — both
collapse to the string `"classical"` at import time (`parse_time_control` in
`app/services/normalization.py`). The existing codebase already solves this ambiguity with
`is_correspondence_time_control(game.time_control_str)`, used identically in
`library_repository.py`/`library_service.py` today. The plan must route through that check FIRST,
before dispatching on `time_control_bucket`, or daily/correspondence games will silently get a bogus
"classical" conversion instead of the documented `None` fallback.

A second real gap: inverting Table 2's Lichess `classical` column hits **three tied anchor rows**
(chess.com-Blitz 1500/1550/1600 all map to Lichess-Classical 1935) — unlike Table 1's Bullet/Rapid
columns, which the current code's tie-handling branch documents as "unreachable" for the current
snapshot. Generalizing to Table 2's `classical` column makes that branch reachable for real, so it
needs an explicit test, not just defensive code.

**Primary recommendation:** Add one small helper in the composed inversion path that special-cases
correspondence detection before any table lookup, generalize `_invert_intra_tc`'s pattern (not the
function itself — the domain differs) into a new `_invert_table2_column` operating on Table 2's four
Lichess columns (with None-gap filtering for `classical`'s trailing None rows and leftmost-anchor tie
resolution), and compute the two new fields on-read inside `_build_card()` in `library_service.py`
where `game.platform` / `game.time_control_bucket` / `game.time_control_str` / `game.white_rating` /
`game.black_rating` are all already in scope.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Rating conversion math (table lookup + inversion) | API / Backend | — | Pure function, no I/O, belongs in `app/services/chesscom_to_lichess.py` alongside the existing converter (single source of truth, already unit-tested there) |
| Correspondence/daily detection | API / Backend | — | `is_correspondence_time_control()` already lives in `app/services/normalization.py` and is read at the same `game.time_control_str` the serializer already has in scope |
| Computed-field serialization | API / Backend | — | `_build_card()` in `library_service.py` already assembles `GameFlawCard` from `game.*` fields at request time — no new query, no migration |
| Maia ELO slider default derivation | Frontend / Client | — | `useMaiaEloDefault.ts` already owns "which color's rating do we default to" logic; reading a second nullable field with fallback is additive, not a new responsibility |
| Raw rating display (player bar) | Frontend / Client | — | `Analysis.tsx` `PlayerBar` reads `white_rating`/`black_rating` directly; explicitly untouched by this phase |

## Standard Stack

### Core
No new libraries. This phase extends `app/services/chesscom_to_lichess.py` (pure Python, stdlib
`bisect` only) and touches existing Pydantic schemas / TypeScript interfaces / one React hook.

### Supporting
N/A — no new dependencies.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| On-read compute (recommended) | Stored columns computed at import time + Alembic migration + backfill script | Only worth it if a future query needs to filter/sort by normalized rating (not needed today — SEED-093 explicitly leaves this open, this research resolves it to on-read) |
| Generalizing `_invert_intra_tc` in place | A wholly new inversion function, `_invert_table2_column` | The domains differ enough (Table 1 has no None gaps and no ties in Bullet/Rapid; Table 2's `classical` column has both) that a separate function with its own docstring is clearer than parameterizing one function to handle two different edge-case profiles — recommend a sibling function, not an in-place generalization |

**Installation:** None — no new packages for either backend or frontend.

**Version verification:** N/A — no new package installs in this phase.

## Package Legitimacy Audit

**Not applicable.** This phase installs zero new packages (backend: pure Python stdlib addition to
an existing module; frontend: a type/hook change only). No `npm install` / `uv add` / registry check
required.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────┐
                    │  games row (already loaded, no new query) │
                    │  platform, time_control_bucket,           │
                    │  time_control_str, white_rating,           │
                    │  black_rating                              │
                    └───────────────────┬─────────────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────┐
                    │ library_service.py::_build_card()         │
                    │  for each color:                          │
                    │   1. is_correspondence_time_control(      │
                    │        game.time_control_str)             │
                    │      → True: normalized = None             │
                    │   2. else: source_tc = derive from         │
                    │        (platform, time_control_bucket)     │
                    │   3. normalize_to_lichess_blitz(            │
                    │        rating, platform, source_tc)        │
                    └───────────────────┬─────────────────────┘
                                        │  white_rating_lichess_blitz
                                        │  black_rating_lichess_blitz
                                        ▼
                    ┌─────────────────────────────────────────┐
                    │ chesscom_to_lichess.py                    │
                    │  normalize_to_lichess_blitz(rating,        │
                    │    platform, source_tc) -> int | None      │
                    │   - chess.com blitz  → Table 2 blitz col   │
                    │   - chess.com bullet/rapid → invert Table 1│
                    │       → Table 2 blitz col                  │
                    │   - lichess blitz    → identity             │
                    │   - lichess bullet/rapid/classical →        │
                    │       invert Table 2 (that column)          │
                    │       → chesscom-blitz anchor →             │
                    │       Table 2 blitz col                     │
                    │   - daily/correspondence/out-of-range →None │
                    └───────────────────┬─────────────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────┐
                    │ GameFlawCard (Pydantic) → JSON             │
                    │  white_rating, black_rating (unchanged,    │
                    │    raw, still consumed by PlayerBar)       │
                    │  white_rating_lichess_blitz,                │
                    │  black_rating_lichess_blitz (new, nullable) │
                    └───────────────────┬─────────────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────┐
                    │ useLibraryGame() → GameFlawCard             │
                    │ Analysis.tsx: gameData                       │
                    │  - PlayerBar reads raw white_rating/          │
                    │    black_rating (Analysis.tsx:2056, UNCHANGED)│
                    │  - useMaiaEloDefault reads the *_lichess_blitz│
                    │    field for the mover's color, falls back    │
                    │    to raw when null                          │
                    └─────────────────────────────────────────┘
```

### Recommended Project Structure

No new files or directories. All changes land in existing files:
```
app/services/chesscom_to_lichess.py   # + _invert_table2_column, + normalize_to_lichess_blitz
app/schemas/library.py                # GameFlawCard + 2 nullable fields
app/services/library_service.py       # _build_card() computes the 2 fields
tests/services/test_chesscom_to_lichess.py  # + new test coverage (existing file)
frontend/src/types/library.ts         # GameFlawCard + 2 nullable fields
frontend/src/hooks/useMaiaEloDefault.ts     # MaiaEloGameData + 2 fields, deriveRawDefault reads them
frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts  # + new test coverage (existing file)
```

### Pattern 1: Correspondence detection BEFORE bucket dispatch

**What:** Any caller deriving a "source TC" for conversion purposes must check
`is_correspondence_time_control(game.time_control_str)` first, and only fall through to
`time_control_bucket`-based dispatch when it's False.

**When to use:** Any place that needs to distinguish "daily/correspondence" from "genuine classical"
— which the `time_control_bucket` column alone cannot do, because `parse_time_control()` buckets
both into `"classical"`.

**Example:**
```python
# Source: app/services/normalization.py (existing helper, already imported in
# library_repository.py and library_service.py for an unrelated purpose — reuse it)
from app.services.normalization import is_correspondence_time_control

is_correspondence = is_correspondence_time_control(game.time_control_str)
```

### Pattern 2: Table 2 column inversion (new sibling to `_invert_intra_tc`)

**What:** Given a rating on any of Table 2's four Lichess columns (`bullet`/`blitz`/`rapid`/
`classical`), find the chess.com-Blitz anchor whose column value is closest, honoring None-gaps
(classical is None above 2700) and ties (classical has three anchors mapping to 1935).

**When to use:** `normalize_to_lichess_blitz` for `platform="lichess"`, `source_tc` in
`("bullet", "rapid", "classical")`.

**Example (illustrative shape, following the existing `_invert_intra_tc` structure at
`app/services/chesscom_to_lichess.py:375-425`):**
```python
def _invert_table2_column(
    rating: int,
    column: Literal["bullet", "rapid", "classical"],  # blitz excluded — identity case, no inversion needed
) -> int | None:
    """Find chess.com-Blitz anchor whose Table 2 `column` value ~= `rating`.

    Unlike Table 1's Bullet/Rapid columns (asserted fully-populated + strictly
    monotone), Table 2's `classical` column has trailing None rows (chess.com
    Blitz 2800/2900/3000) and THREE TIED anchors (1500/1550/1600 all -> 1935).
    Filter out None entries before building the scan domain; on a tie, return
    the LOWEST chess.com-Blitz anchor (conservative-estimate convention,
    matching the existing Table 1 tied-row fallback comment).
    """
    pairs = [
        (anchor, row[column])
        for anchor, row in CHESSCOM_BLITZ_TO_LICHESS.items()
        if row[column] is not None
    ]
    # pairs is already anchor-ascending (dict insertion order == _CHESSCOM_BLITZ_KEYS order)
    values = [v for _, v in pairs]
    anchors = [a for a, _ in pairs]
    if rating < values[0] or rating > values[-1]:
        return None
    idx = bisect.bisect_left(values, rating)
    if idx < len(values) and values[idx] == rating:
        return anchors[idx]  # leftmost tie wins
    if idx == 0:
        return None
    lo_val, hi_val = values[idx - 1], values[idx]
    lo_anchor, hi_anchor = anchors[idx - 1], anchors[idx]
    if hi_val == lo_val:
        return lo_anchor  # reachable for `classical` — must be tested, not just defensive
    frac = (rating - lo_val) / (hi_val - lo_val)
    return round(lo_anchor + frac * (hi_anchor - lo_anchor))
```

### Pattern 3: Public dispatcher shape

```python
# Source: app/services/chesscom_to_lichess.py (extends the existing module)
def normalize_to_lichess_blitz(
    rating: int,
    platform: Platform,  # reuse app.schemas.normalization.Platform, don't redeclare
    source_tc: TimeControlBucket,  # reuse app.schemas.normalization.TimeControlBucket
    *,
    is_correspondence: bool,  # caller passes is_correspondence_time_control() result
) -> int | None:
    if is_correspondence:
        return None  # chess.com daily + lichess correspondence, both fold here
    if platform == "chess.com":
        if source_tc == "classical":
            return None  # chess.com has no native "classical" TC in the ChessGoals tables
        return convert_chesscom_to_lichess(rating, source_tc, "blitz")  # source_tc is bullet/blitz/rapid
    # platform == "lichess"
    if source_tc == "blitz":
        return rating  # identity — already the target scale
    blitz_equiv = _invert_table2_column(rating, source_tc)  # bullet/rapid/classical
    if blitz_equiv is None:
        return None
    return _interp_blitz_to_lichess(blitz_equiv, "blitz")
```

**Note on the `is_correspondence` parameter:** making it an explicit caller-supplied boolean (rather
than re-deriving it from a `time_control_str` argument inside the module) keeps
`chesscom_to_lichess.py` free of any dependency on `app/services/normalization.py`, preserving its
"pure Python — no DB, no I/O" module docstring contract. The caller (`library_service.py`) already
imports `is_correspondence_time_control` for the clock-suppression use one screen away
(`library_service.py:138`) — reuse that same call result.

### Anti-Patterns to Avoid
- **Dispatching on `time_control_bucket` alone without the correspondence check:** silently produces
  a wrong-scale "classical" conversion for daily/correspondence games instead of the documented
  `None` fallback (Pitfall 1 below).
- **Treating Table 2 column inversion as a copy-paste of `_invert_intra_tc`:** the `assert value is
  not None` in the current function is correct for Table 1 (Bullet/Rapid are fully populated) but
  would raise `AssertionError` in production if copy-pasted verbatim against Table 2's `classical`
  column (which has real None rows above chess.com-Blitz 2700).
- **Snapping the normalized value to a ladder rung inside the conversion function:** `useMaiaEngine`
  already does nearest-rung selection at read time (per the seed's edge-case note) — keep
  `normalize_to_lichess_blitz` returning the unsnapped interpolated int.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Detecting daily/correspondence games | A new regex/string check on `time_control_str` | `is_correspondence_time_control()` (`app/services/normalization.py:28`) | Already exists, already tested, already imported by the two files this phase touches |
| Chess.com rating conversion tables | A new lookup table | `CHESSCOM_INTRA_TC` / `CHESSCOM_BLITZ_TO_LICHESS` (existing, value-locked) | These are the ChessGoals empirical snapshot; re-deriving them would silently diverge from the locked values other code (SQL anchor pipeline, benchmark percentiles) already depends on |
| Linear interpolation between anchors | A new interp helper | `_interp_int_column()` (existing, module-private) | Already handles None-gaps + clamp-to-range + exact-anchor short-circuit; the new Table 2 inversion needs equivalent (not identical) logic but should follow its exact contract |

**Key insight:** Every primitive this phase needs already exists in the codebase in a directly
analogous form. The work is composition (a new inversion direction + one dispatcher) and one
serialization touchpoint, not new math.

## Common Pitfalls

### Pitfall 1: `time_control_bucket="classical"` is ambiguous (daily/correspondence vs genuine classical)
**What goes wrong:** A chess.com daily game or a lichess correspondence game both get
`time_control_bucket="classical"` at import time (`parse_time_control()` in
`app/services/normalization.py:83-85` explicitly buckets any `"/"`-format TC string as
`"classical"`). If the plan dispatches `normalize_to_lichess_blitz` purely off `time_control_bucket`,
these games get a bogus conversion through the classical-column path instead of the seed's intended
`None` (raw-fallback) behavior.
**Why it happens:** `time_control_bucket` is a duration-estimate bucket for both platforms; the
platform's own daily/correspondence category is a separate signal only recoverable from the raw
`time_control_str` (the `"/"` separator).
**How to avoid:** Check `is_correspondence_time_control(game.time_control_str)` before any bucket
dispatch, for BOTH platforms (this function is already platform-agnostic and already used this way
elsewhere in the codebase).
**Warning signs:** A test asserting a daily/correspondence game gets `None` will fail if this check
is skipped — make this an explicit test case, not an incidental one.

### Pitfall 2: chess.com has no native "classical" TC in the ChessGoals tables
**What goes wrong:** `ChessComSourceTC` in `chesscom_to_lichess.py` is
`Literal["bullet", "blitz", "rapid", "daily"]` — there is no `"classical"` entry, because chess.com
itself has no live time control that long (its longest live category is rapid; anything longer is
daily). But FlawChess's own `time_control_bucket` enum DOES include `"classical"`, and a chess.com
game with an unusually long live TC (a custom time control, rare but possible) could theoretically
bucket to `"classical"` without being a `"/"`-format daily game.
**Why it happens:** `time_control_bucket` is a FlawChess-internal duration bucket independent of what
each platform natively calls its TCs.
**How to avoid:** For `platform == "chess.com"` and `source_tc == "classical"` (non-correspondence),
return `None` — there is no ChessGoals mapping for this combination. Document this as an accepted
edge case (likely near-zero occurrence in practice) rather than guessing which chess.com column it
should chain through.
**Warning signs:** None of the existing tests exercise this combination — add one explicitly so the
behavior is locked, not accidental.

### Pitfall 3: Table 2's `classical` column has tied anchors — the "unreachable" defensive branch becomes reachable
**What goes wrong:** `_invert_intra_tc`'s tie-handling branch (`if hi_col == lo_col: return
lo_blitz`) is commented as unreachable for Table 1's current snapshot. Table 2's `classical` column
has THREE tied rows (chess.com-Blitz 1500, 1550, 1600 all map to Lichess-Classical 1935) — verified
directly against the table in this research. A copy-pasted inversion function that assumes strict
monotonicity (no defensive tie handling, or an untested one) will silently pick an arbitrary or
incorrect anchor for `rating == 1935`.
**Why it happens:** Table 2 was fit independently per column; unlike Table 1's Bullet/Rapid columns
(re-fetched 2026-05-27 specifically to fix monotonicity bugs), Table 2 was never audited for
monotonicity per-column because until this phase nothing inverted it.
**How to avoid:** Write an explicit test for `rating=1935` inverting through `classical` — assert it
returns the LOWEST tied anchor (1500), matching the project's existing conservative-estimate
convention (see the Table 1 comment at `chesscom_to_lichess.py:417-423`).
**Warning signs:** A round-trip test (invert then forward-convert) landing on a different anchor than
expected for a mid-1900s classical rating.

### Pitfall 4: Table 2's `classical` column has trailing None rows
**What goes wrong:** Chess.com-Blitz anchors 2800/2900/3000 have `classical: None` in
`CHESSCOM_BLITZ_TO_LICHESS`. A naive port of `_invert_intra_tc`'s `assert value is not None` loop
(which is correct for Table 1's fully-populated Bullet/Rapid columns) will raise `AssertionError` in
production the first time a high Lichess-classical rating is normalized.
**Why it happens:** Table 1 and Table 2 have different None-population profiles; the existing
assertion is specific to Table 1's guarantee, not a general property of the module's tables.
**How to avoid:** Filter `None` entries out of the (anchor, value) pairs before building the sorted
scan domain (see Pattern 2's example) — do not assert non-None.
**Warning signs:** A test with a high (>2500) Lichess-classical input rating raising instead of
returning a value or `None` gracefully.

### Pitfall 5: `MaiaEloGameData`'s two new fields must be OPTIONAL, not required
**What goes wrong:** If `white_rating_lichess_blitz` / `black_rating_lichess_blitz` are added as
required (non-optional) fields to the `MaiaEloGameData` TypeScript interface, every existing test
constructing a `MaiaEloGameData` literal (see `useMaiaEloDefault.test.ts`'s `gameData()` helper,
lines 19-21) breaks, and any real API response missing the field (defensive coding, or an older
cached client bundle mid-deploy) throws instead of falling back.
**Why it happens:** The fields are additive per the seed (`Additive, never replacing`), and the
"fall back to raw when null" behavior in `deriveRawDefault` (per seed line 79) requires the type to
allow `undefined`/`null`, not just `number`.
**How to avoid:** Declare as `white_rating_lichess_blitz?: number | null` (or `number | null` with an
explicit `?? null` default at every existing test-fixture call site) on both the Pydantic
`GameFlawCard` (`= None` default) and the TS interface.
**Warning signs:** Existing `useMaiaEloDefault.test.ts` fixtures failing to compile after the type
change — that's the tell the fields weren't made optional.

## Code Examples

### Frontend: `deriveRawDefault` read-with-fallback (extends existing function)
```typescript
// Source: frontend/src/hooks/useMaiaEloDefault.ts:69-81 (existing function, minimal diff shown)
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

### Backend: computed-field call site (extends existing `_build_card`)
```python
# Source: app/services/library_service.py:524-534 (existing GameFlawCard() construction)
# `is_correspondence` is ALREADY computed one screen up in _build_eval_series
# (library_service.py:138) for the clock-suppression use — but that's scoped inside
# _build_eval_series, not _build_card. _build_card must compute its OWN
# is_correspondence_time_control(game.time_control_str) call (cheap, pure function,
# no reason to thread it through as a parameter for a single extra call).
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
return GameFlawCard(
    ...,
    white_rating=game.white_rating,          # UNCHANGED — raw, still consumed by PlayerBar
    black_rating=game.black_rating,          # UNCHANGED
    white_rating_lichess_blitz=white_rating_lichess_blitz,   # NEW
    black_rating_lichess_blitz=black_rating_lichess_blitz,   # NEW
    ...,
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Maia ELO slider/prior defaults to the raw platform/TC rating | Defaults to a Lichess-blitz-normalized equivalent (this phase) | Phase 164 | Maia-3's move-prediction conditioning matches its training distribution (Lichess-blitz) instead of being systematically off by ~150-250 (chess.com) or up to ~200 (Lichess non-blitz) |
| Per-user blended anchor for benchmark percentiles already converts chess.com→lichess SQL-side (`per_user_cte_median_anchor`, `user_benchmark_percentiles_service.py`) | This phase adds the missing Lichess-intra-TC direction (non-blitz Lichess → Lichess-blitz), which no existing caller needed until now | Phase 164 | SEED-091 (bot play, deferred) can now reuse `normalize_to_lichess_blitz` for its own save-time conversion, per the seed's "Related" section |

**Deprecated/outdated:** None — this is a pure addition, no removed code paths.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Chess.com games with `time_control_bucket="classical"` that are NOT correspondence-format are rare/near-zero in the actual dataset | Pitfall 2 | Low — even if more common than expected, the recommended behavior (`None` → raw fallback) is safe, just less useful; worth a quick DB count check at plan time if the planner wants to size the impact |
| A2 | The leftmost-tied-anchor convention (lowest chess.com-Blitz anchor on a `classical`-column tie) is the right choice, mirroring the existing Table 1 comment's stated principle | Pattern 2 / Pitfall 3 | Low — this only affects the exact Lichess-classical rating 1935 (and its immediate interpolated neighborhood); a planner/reviewer could reasonably choose "highest anchor" instead with no functional difference in practice given the tie only spans 100 chesscom-blitz-equivalent points |

**If this table is empty:** N/A — two low-risk assumptions logged above; both are implementation
conventions, not compliance/security/performance claims, and don't need explicit user sign-off before
planning proceeds (recommend the planner state the convention explicitly in the plan so it's
reviewable, not silently baked in).

## Open Questions

1. **Should `normalize_to_lichess_blitz` live in `chesscom_to_lichess.py` or get its own module?**
   - What we know: every primitive it needs (both tables, `_interp_int_column`,
     `convert_chesscom_to_lichess`) already lives in `chesscom_to_lichess.py`, and the module's own
     docstring already anticipates this exact extension ("Table 2 ... `convert_chesscom_to_lichess`").
   - What's unclear: whether the module name (`chesscom_to_lichess`) still reads accurately once it
     also does Lichess-intra-TC inversion (a "lichess to lichess" operation with no chess.com
     involved for the `source_tc="blitz"` and Lichess bullet/rapid/classical cases).
   - Recommendation: keep it in the same module — renaming risks breaking the 4 existing import
     sites (`canonical_slice_sql.py`, `user_benchmark_percentiles_service.py`,
     `test_chesscom_to_lichess.py`) for a cosmetic gain. Update the module docstring to mention the
     new Lichess-intra-TC direction.

2. **Does `is_correspondence_time_control` need to be re-exported or imported fresh in
   `chesscom_to_lichess.py`?**
   - What we know: `chesscom_to_lichess.py`'s docstring states "Pure Python — no DB, no I/O" as a
     design property; importing from `app.services.normalization` wouldn't break that (still pure),
     but would add a new intra-`app.services` dependency edge.
   - What's unclear: whether the plan should thread `is_correspondence: bool` in as an explicit
     caller-supplied parameter (Pattern 3, recommended above) or have the module import and call
     `is_correspondence_time_control` itself given a raw `time_control_str`.
   - Recommendation: caller-supplied boolean (as shown in Pattern 3) — keeps the conversion module
     dependency-free and mirrors how `library_service.py` already computes this flag independently
     for its own clock-suppression use.

## Environment Availability

Skipped — this phase has no external tool/service/runtime dependencies. It extends existing Python
(stdlib `bisect`, already used) and TypeScript code with no new packages, no new endpoints requiring
external calls, and no infra changes.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (backend); Vitest 4.1.7 (frontend) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (backend); `frontend/vite.config.ts` / `vitest` config (frontend) |
| Quick run command | `uv run pytest tests/services/test_chesscom_to_lichess.py -x` (backend conversion logic); `cd frontend && npx vitest run src/hooks/__tests__/useMaiaEloDefault.test.ts` (frontend hook) |
| Full suite command | `uv run pytest -n auto` (backend); `( cd frontend && npm test -- --run )` (frontend) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEED-093 | chess.com blitz -> Lichess-blitz (identity Table 2 lookup, existing path) | unit | `uv run pytest tests/services/test_chesscom_to_lichess.py -k blitz_to_lichess_blitz -x` | Yes (existing tests already cover this exact path) |
| SEED-093 | chess.com bullet/rapid -> Lichess-blitz (via Table 1 inversion, existing path reused with new target) | unit | `uv run pytest tests/services/test_chesscom_to_lichess.py -k normalize_to_lichess_blitz -x` | New — add to existing file |
| SEED-093 | chess.com daily -> None (raw fallback) | unit | `uv run pytest tests/services/test_chesscom_to_lichess.py -k daily -x` | Existing test covers `convert_chesscom_to_lichess`'s daily=None; add one for `normalize_to_lichess_blitz` |
| SEED-093 | Lichess blitz -> identity | unit | `uv run pytest tests/services/test_chesscom_to_lichess.py -k lichess_blitz_identity -x` | New |
| SEED-093 | Lichess bullet/rapid/classical -> Lichess-blitz (NEW inversion direction) | unit | `uv run pytest tests/services/test_chesscom_to_lichess.py -k invert_table2 -x` | New — Wave 0 gap |
| SEED-093 | Lichess classical tie (rating=1935 -> lowest of 3 tied anchors) | unit | `uv run pytest tests/services/test_chesscom_to_lichess.py -k classical_tie -x` | New — Wave 0 gap (Pitfall 3) |
| SEED-093 | Lichess classical None-gap (rating above chesscom-blitz-2700-equivalent) | unit | `uv run pytest tests/services/test_chesscom_to_lichess.py -k classical_none_gap -x` | New — Wave 0 gap (Pitfall 4) |
| SEED-093 | Lichess correspondence -> None (raw fallback) | unit | `uv run pytest tests/services/test_chesscom_to_lichess.py -k correspondence -x` | New — Wave 0 gap (Pitfall 1) |
| SEED-093 | Out-of-published-range (below 500 / above 3000 chesscom-blitz equivalent) -> None for every source path | unit | `uv run pytest tests/services/test_chesscom_to_lichess.py -k out_of_range -x` | New — parametrize across all 6 (platform, source_tc) combos |
| SEED-093 | `_build_card` populates the two new fields correctly for a real Game row | unit/integration | `uv run pytest tests/services/test_library_service.py -k lichess_blitz -x` (or equivalent existing test file for `library_service.py`) | New — locate the actual test file for `_build_card`/`get_library_game` first |
| SEED-093 | `deriveRawDefault` reads normalized field with raw fallback | unit | `cd frontend && npx vitest run src/hooks/__tests__/useMaiaEloDefault.test.ts` | New cases added to existing file |
| SEED-093 | `Analysis.tsx:2056` raw rating display unaffected | manual / existing test | `cd frontend && npx vitest run src/pages/__tests__/Analysis.test.tsx` | Existing — verify no regression, no new test needed unless the plan wants an explicit assertion |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/services/test_chesscom_to_lichess.py -x` (backend);
  `cd frontend && npx vitest run src/hooks/__tests__/useMaiaEloDefault.test.ts` (frontend hook task)
- **Per wave merge:** `uv run pytest -n auto -x` (backend full suite); `( cd frontend && npm run lint
  && npm test -- --run )` (frontend)
- **Phase gate:** Full suite green before `/gsd-verify-work`, per the CLAUDE.md pre-merge gate.

### Wave 0 Gaps
- [ ] Locate (or confirm absence of) an existing test file exercising `library_service.py::_build_card`
  / `get_library_game` directly — grep found no dedicated `test_library_service.py` in the earlier
  file search; the planner should verify which existing test file (if any) is the right home for a
  `_build_card`-level integration test of the two new fields, or add one.
- [ ] New parametrized test block in `tests/services/test_chesscom_to_lichess.py` covering: identity
  (Lichess blitz), Table-2-column inversion (bullet/rapid/classical), the classical tie (1935), the
  classical None-gap (above ~chesscom-blitz-2700-equivalent), correspondence/daily → None (both
  platforms), and out-of-range → None (all 6 source paths).
- [ ] New test cases in the existing `useMaiaEloDefault.test.ts` covering: normalized field present →
  used; normalized field null → raw fallback used; normalized field present for one color but not the
  other (mixed).

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Unrelated — existing FastAPI-Users auth on the games endpoints is untouched |
| V3 Session Management | No | Unrelated |
| V4 Access Control | No | The two new fields ride the existing `GameFlawCard` response, already IDOR-guarded by `get_library_game`'s ownership check (`game.user_id != user_id` → None → 404) — no new access-control surface |
| V5 Input Validation | Yes | `normalize_to_lichess_blitz`'s `rating`/`platform`/`source_tc` are all sourced from the trusted `games` row (already validated/typed at import time via `Platform`/`TimeControlBucket` Pydantic Literals), not raw user input — no new validation surface, but keep the `Literal` typing (no bare `str`) per CLAUDE.md |
| V6 Cryptography | No | Unrelated |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Information disclosure via computed fields | Information Disclosure | Both new fields are derived from ratings already exposed on `GameFlawCard` (raw `white_rating`/`black_rating`) — no new information is disclosed, only a derived transformation of already-visible data. No `*_hash` fields are touched (CLAUDE.md V5 rule stays satisfied) |

No new attack surface — this phase adds a pure computed transformation of already-authorized,
already-exposed data. No auth/session/access-control changes.

## Sources

### Primary (HIGH confidence)
- `app/services/chesscom_to_lichess.py` (full read) — table structures, `_invert_intra_tc`,
  `_interp_int_column`, `convert_chesscom_to_lichess`, `composed_chesscom_to_lichess_grid`, published
  bounds, monotonicity/None-gap/clamp discipline, module docstring provenance notes
- `tests/services/test_chesscom_to_lichess.py` (full read) — existing test style, coverage pattern,
  equivalence-testing convention (`composed_grid` tests) to mirror for new inversion tests
- `app/services/normalization.py` (read) — `parse_time_control`, `is_correspondence_time_control`,
  confirms `"classical"` bucket collapses daily/correspondence with genuine classical for BOTH platforms
- `app/models/game.py` (read) — `Game` ORM fields available at `_build_card` call time
- `app/schemas/library.py` (full read) — `GameFlawCard` schema, existing field set
- `app/services/library_service.py` (targeted read, lines 120-160, 362-613) — `_build_card()`
  construction site, existing `is_correspondence_time_control` usage pattern one screen away
- `app/schemas/normalization.py` (grep) — existing `Platform`/`TimeControlBucket` Literal types to reuse
- `frontend/src/hooks/useMaiaEloDefault.ts` (full read) — `MaiaEloGameData`, `deriveRawDefault`,
  `clampToLadderBounds`, `userOverrodeRef`, free-play path
- `frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts` (full read) — existing fixture/test shape
- `frontend/src/types/library.ts` (targeted read) — `GameFlawCard` TS mirror, exact field list
- `frontend/src/pages/Analysis.tsx` (targeted read, lines 555-600, 2030-2070) — confirmed
  `useMaiaEloDefault` call site and `PlayerBar` line 2056 raw-rating read (line reference verified
  accurate)
- `.planning/seeds/SEED-093-maia-elo-lichess-blitz-normalization.md` (full read) — converged design,
  routing table, edge cases

### Secondary (MEDIUM confidence)
- `app/services/user_benchmark_percentiles_service.py` (targeted read) — confirms a related but
  distinct existing chess.com→lichess conversion usage (SQL-side blended anchor), useful prior-art
  context, not directly reused by this phase

### Tertiary (LOW confidence)
None — every claim in this research was verified directly against the codebase in this session.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; every primitive verified by direct file read
- Architecture: HIGH — serialization touchpoint, ORM fields, and schema/type locations all confirmed
  by direct read, not inferred
- Pitfalls: HIGH — the two real gaps (correspondence-vs-classical ambiguity, Table 2 tie/None-gap)
  were discovered by directly inspecting the table data and the bucketing logic, not assumed

**Research date:** 2026-07-11
**Valid until:** Stable — the underlying tables are value-locked (per module docstring, any refit
requires a new module-level constant), and the serialization/hook code paths are not on an active
refactor trajectory. 60-day validity is reasonable; re-verify only if `chesscom_to_lichess.py`,
`library_service.py`, or `useMaiaEloDefault.ts` are touched by an intervening phase.
