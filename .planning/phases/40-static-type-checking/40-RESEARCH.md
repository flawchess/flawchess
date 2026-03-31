# Phase 40: Static Type Checking - Research

**Researched:** 2026-03-31
**Domain:** Python static type checking with astral `ty`, TypedDict/dataclass patterns, CI integration
**Confidence:** HIGH

## Summary

Phase 40 integrates `ty` (astral's Rust-based type checker) into the FlawChess backend and CI pipeline, targeting zero type errors at completion. The research involved installing `ty` and running it against the actual codebase to produce a concrete error inventory — 51 errors in `app/` and 69 total including tests. This gives the planner an exact, prioritized list of what must be fixed rather than speculative estimates.

The errors fall into six distinct categories with different fix strategies: (1) SQLAlchemy forward-reference strings in models (suppress — these are intentional patterns), (2) `Row` vs `tuple` return types from SQLAlchemy `session.execute()` (fix by using `cast()` or adjusting return type annotations), (3) `**filter_kwargs` dict spread losing type information (fix by creating a `FilterParams` TypedDict), (4) FastAPI-Users internals in third-party code (suppress — not our code), (5) real logic bugs including `invalid-raise` in `lichess_client.py` and `no-matching-overload` in `endgame_service.py`, and (6) test-only narrowing issues from None-returning functions.

The normalization functions (`normalize_chesscom_game`, `normalize_lichess_game`) return `dict | None` with ~25 keys — these are the primary Pydantic model candidates per D-01. The opening trie uses bare `dict` — a TypedDict is the correct fix per D-04. The `**filter_kwargs` dict spread pattern in `stats_service.py` and `analysis_service.py` is the root cause of 22+ `invalid-argument-type` errors.

**Primary recommendation:** Fix errors in waves: models (suppress), repositories (Row cast), services (FilterParams TypedDict, normalization Pydantic), third-party suppress, real bugs. Add `uv run ty check app/ tests/` to CI after ruff, before pytest.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Dict replacement strategy:**
- D-01: Use Pydantic models at system boundaries — external API input (chess.com/lichess JSON in `normalization.py`) and API response schemas.
- D-02: Use dataclasses or TypedDicts for internal data structures — accumulators (`dict[str, dict]` in `endgame_service.py`), lookup maps, intermediate computation results.
- D-03: Already-typed dicts like `dict[str, timedelta]` are fine as-is — only replace bare `dict` or `dict[str, dict]` where the value type is unspecified.
- D-04: Recursive structures like the opening trie should use TypedDict or a custom class, not Pydantic.

**ty strictness:**
- D-05: Target zero errors from day one — all type errors must be resolved before the phase is complete.
- D-06: For warnings and below, Claude has discretion to configure as appropriate.
- D-07: If any errors seem unreasonable to fix (e.g., SQLAlchemy/FastAPI patterns that ty can't handle), report to user for joint decision on suppress vs fix.

**CI integration:**
- D-08: `ty` is a blocking CI step from day one — type errors fail the build.
- D-09: Placement in pipeline: after ruff check, before pytest (lint → type check → tests).
- D-10: Runs on every PR to main (same trigger as existing ruff/pytest steps).

### Claude's Discretion
- Warning-level ty configuration (D-06)
- Exact pyproject.toml ty settings beyond error-level blocking
- Which specific dicts to convert to dataclass vs TypedDict (within the D-01/D-02 guidelines)
- Test file type annotations (follow whatever approach makes tests readable)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TOOL-01 | Backend static type checking with astral `ty` integrated into CI/CD pipeline | CI YAML step added between ruff and pytest; `ty` installed as dev dependency; configuration in `[tool.ty]` |
| TOOL-02 | Backend type safety review — replace untyped dicts with TypedDicts/Pydantic models, add missing type hints | Concrete error inventory (69 diagnostics); categorized fix strategies per D-01/D-04 |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ty | 0.0.26 | Python static type checker | Decided by user; Astral (ruff/uv) ecosystem; 10-100x faster than mypy |

### Supporting (already in project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing.TypedDict | stdlib | Typed dict shapes for internal structures | Internal accumulators, lookup maps, trie nodes (D-02, D-04) |
| dataclasses.dataclass | stdlib | Typed data containers | Internal computation results where methods may be useful (D-02) |
| pydantic.BaseModel | 2.x | Validated models at API boundaries | External JSON deserialization, API response schemas (D-01) |

**Installation:**
```bash
uv add --dev ty
```

ty 0.0.26 is already installed in this project (added during research).

**Note on `[tool.uv.dev-dependencies]` deprecation:** The `uv add --dev ty` command added ty under the deprecated `tool.uv.dev-dependencies` key. The wave that installs ty should migrate to `[dependency-groups]` at the same time:
```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.4.0",
    "ty>=0.0.26",
]
```

## Architecture Patterns

### Recommended Project Structure (no changes)
The existing `routers/` → `services/` → `repositories/` layering is unchanged. Type improvements are made within existing files.

### Pattern 1: Suppressing SQLAlchemy Forward References in Models
**What:** SQLAlchemy `relationship()` strings reference other models by name — these are intentionally unresolved at import time. ty raises `unresolved-reference` for them.
**When to use:** Any `Mapped["ClassName"]` forward reference inside a `relationship()` call.
**Example:**
```python
# Source: app/models/game.py
positions: Mapped[list["GamePosition"]] = relationship(  # ty: ignore[unresolved-reference]
    back_populates="game", cascade="all, delete-orphan"
)
```
The existing `# type: ignore[name-defined]` (mypy convention) does NOT suppress ty errors. Replace with `# ty: ignore[unresolved-reference]`.

**Affected files:** `app/models/game.py`, `app/models/game_position.py`, `app/models/user.py` (3 errors)

### Pattern 2: SQLAlchemy Row vs tuple Return Types
**What:** `session.execute().fetchall()` and `.all()` return `list[Row[...]]`, not `list[tuple[...]]`. Return type annotations using `list[tuple]` cause `invalid-return-type`.
**Fix:** Use `cast()` at the return site or narrow the return type annotation to use `Sequence[Row[Any]]`. The simplest fix that preserves downstream tuple destructuring is:
```python
from sqlalchemy.engine import Row
from typing import Any

async def query_endgame_entry_rows(...) -> list[Row[Any]]:
    result = await session.execute(stmt)
    return list(result.fetchall())
```
Callers that destructure rows with `for a, b, c in rows:` continue to work because `Row` supports tuple unpacking. Callers that type-annotate their loop variables may need minor updates.

**Affected functions (10 errors across 4 files):**
- `app/repositories/analysis_repository.py`: `query_time_series`, `query_all_results`
- `app/repositories/endgame_repository.py`: `query_endgame_entry_rows`, `query_conv_recov_timeline_rows`, `query_endgame_performance_rows`, `query_endgame_timeline_rows`
- `app/repositories/stats_repository.py`: `query_rating_history`
- `app/repositories/endgame_repository.py`: `per_type_rows` dict type annotation

### Pattern 3: FilterParams TypedDict to Fix **kwargs Spread
**What:** `stats_service.py` uses `filter_kwargs = dict(time_control=..., platform=..., rated=..., opponent_type=..., recency_cutoff=...)` and spreads it with `**filter_kwargs`. ty infers `filter_kwargs` as `dict[str, list[str] | None | bool | str | datetime]` — the union is too wide for individual parameters.
**Fix:** Define a TypedDict and annotate `filter_kwargs` explicitly:
```python
from typing import TypedDict
import datetime

class FilterParams(TypedDict):
    time_control: list[str] | None
    platform: list[str] | None
    rated: bool | None
    opponent_type: str
    recency_cutoff: datetime.datetime | None
```
Then: `filter_kwargs: FilterParams = FilterParams(time_control=..., ...)`. With an explicit TypedDict annotation, `**filter_kwargs` spread is understood by ty.

**Affected:** `app/services/stats_service.py` (10 errors — the `**filter_kwargs` spread to `query_position_wdl_batch`)

### Pattern 4: Literal List Subtype Mismatch
**What:** `AnalysisRequest.time_control` is typed as `list[Literal["bullet", "blitz", "rapid", "classical"]] | None`. Repository functions accept `list[str] | None`. ty rejects the assignment: `list[Literal[...]]` is not assignable to `list[str]` due to list invariance.
**Fix:** Widen the repository parameter type to `Sequence[str] | None` (covariant), or widen Pydantic schema field type. Simpler: change repository function signatures from `list[str] | None` to `list[Literal["bullet", "blitz", "rapid", "classical"]] | None` to match the callers, OR use `list[str] | None` in the schema too. Best approach: keep schemas strict with Literal, fix repository signatures to accept `Sequence[str] | None`.

**Affected:** `app/services/analysis_service.py` → `app/repositories/analysis_repository.py` (8 errors, 4 functions: `query_all_results`, `query_matching_games`, `query_time_series`, `query_next_moves`, `query_transposition_counts`)

### Pattern 5: FastAPI-Users Third-Party Suppression
**What:** `strategy.write_token(user)` raises `unresolved-attribute` because ty can not resolve the `Strategy` return type from FastAPI-Users' type stubs. This is a beta limitation of ty with third-party libraries (D-07).
**Fix:** Per D-07, report to user. Recommendation: suppress with `# ty: ignore[unresolved-attribute]` since this is FastAPI-Users internals.

The error from `.venv/` (fastapi_users/models.py) is in a third-party package — the `allowed-unresolved-imports` config in `[tool.ty]` or the default `exclude` of `.venv/` should handle this, but the error surfaces in our code.

**Affected:** `app/routers/auth.py:170` (1 error)

### Pattern 6: Pydantic model_validator with hasattr() (Protocol issue)
**What:** In `app/schemas/position_bookmarks.py`, the `model_validator(mode="before")` uses `if hasattr(data, "moves")` to detect an ORM object, then accesses `data.id`, `data.label`, etc. ty infers `data: object` as `<Protocol with members 'moves'>` — a narrow protocol that only guarantees `.moves`, not the other attributes.
**Fix:** Use `isinstance(data, PositionBookmark)` instead of `hasattr()`, or cast the object:
```python
from app.models.position_bookmark import PositionBookmark
if isinstance(data, PositionBookmark):
    return {
        "id": data.id,
        ...
    }
```
This is the correct fix — it's also more explicit and safer than duck-typing via `hasattr`.

**Affected:** `app/schemas/position_bookmarks.py:111-118` (8 errors)

### Pattern 7: Real Logic Bugs Found by ty
These are genuine code issues that should be fixed (not suppressed):

**7a. `invalid-raise` in `lichess_client.py:124`:**
```python
raise last_attempt_error  # type: ignore[misc]
```
`last_attempt_error` is typed as `None | RemoteProtocolError | ReadError`. The initial value is `None` (before any retry loop iteration). If `raise` is reached, `last_attempt_error` could technically still be `None`. Fix: initialize as `Exception("Exhausted retries")` or narrow the type before raising.

**7b. `no-matching-overload` + `invalid-argument` in `endgame_service.py:257-261`:**
`_ENDGAME_CATEGORY_LABELS.get(endgame_class, endgame_class.replace(...))` fails because the dict is typed `dict[EndgameClass, EndgameLabel]` and the `default` uses `endgame_class.replace(...)` which returns `str`, not `EndgameLabel`. Additionally, `endgame_class` iterates from `wdl` (a `defaultdict[str, ...]`) so ty infers it as `str`, not `EndgameClass`. Fix: use `_ENDGAME_CATEGORY_LABELS[endgame_class]` directly (the dict is exhaustive) or narrow via cast.

**7c. `unresolved-attribute` on `Result.rowcount`:**
`Result[Any]` does not expose `.rowcount` in SQLAlchemy's stubs. Fix: use `CursorResult` type annotation instead of `Result[Any]`, or access via the underlying cursor.

**7d. Test-only issues (18 errors in `tests/`):**
- `game_obj.mainline()` called on `chess.pgn.read_game()` return value which is `Game | None`. Tests don't guard for `None`. Fix: add assert before use, or use `assert game_obj is not None`.
- `job` is `JobState | None` from `get_job()` in test assertions — tests don't assert non-None. Fix: assert before attribute access.
- `pov.white()` on `PovScore | None` — similar None-guard issue.
- TypeVar/generic issues from SQLAlchemy operators in test fixtures.

### Pattern 8: Normalization → Pydantic TypedDict (D-01)
**What:** `normalize_chesscom_game` and `normalize_lichess_game` return `dict | None` with 20-25 fields each. Per D-01, replace with a Pydantic model at this boundary.
**Approach:** Create a `NormalizedGame` Pydantic model in `app/schemas/` (or `app/services/normalization.py`). Functions return `NormalizedGame | None`. Downstream code (`import_service.py:_flush_batch`) that passes the dict to `bulk_insert_games` may need `model.model_dump()`.

**Affected:** `app/services/normalization.py`, `app/services/import_service.py`, `app/repositories/game_repository.py` (bulk_insert_games)

### Pattern 9: Opening Trie TypedDict (D-04)
**What:** `_TRIE: dict = {}` and `trie: dict = {}` in `opening_lookup.py`. The trie is a recursive `dict[str, ...]` where each node is either another trie node or has a `"_result"` key.
**Fix per D-04:** Use a `TypedDict`:
```python
from typing import TypedDict

class TrieNode(TypedDict, total=False):
    _result: tuple[str, str]
```
But recursive TypedDicts are not fully supported by ty (beta limitation). Alternative: use a custom class:
```python
class TrieNode:
    def __init__(self) -> None:
        self.children: dict[str, "TrieNode"] = {}
        self.result: tuple[str, str] | None = None
```
**Recommendation:** Use the custom class approach — it's cleaner, fully typed, and avoids recursive TypedDict limitations in ty's beta.

### Pattern 10: `endgame_service.py` Accumulators (D-02)
**What:** `wdl`, `conv`, `recov` are `dict[str, dict[str, int]]` accumulators (defaultdict). The value type `dict[str, int]` is already fairly specific but the key is typed as `str` when it should be `EndgameClass`.
**Fix per D-02:** Define TypedDicts:
```python
class WDLCounts(TypedDict):
    wins: int
    draws: int
    losses: int

class ConvRecovCounts(TypedDict):
    games: int
    wins: int
    draws: int
```
Then: `wdl: dict[EndgameClass, WDLCounts] = defaultdict(lambda: WDLCounts(wins=0, draws=0, losses=0))`

### Anti-Patterns to Avoid
- **Do not use `# type: ignore`** for ty suppressions — use `# ty: ignore[rule-name]`. The `type: ignore` comment is a mypy convention and ty may not respect it (though `respect-type-ignore-comments` defaults to `true`, using ty-specific syntax is clearer).
- **Do not configure `unresolved-attribute = "ignore"` globally** — this would hide real errors. Suppress per-site only.
- **Do not widen all `list[Literal[...]]` to `list[str]`** — narrowness in Pydantic schemas is valuable. Fix the repository signatures instead.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Type checking | Custom linting scripts | ty | Handles inference, generics, union narrowing correctly |
| Row type casting | Manual `tuple()` coercion | `Row[Any]` annotation | `Row` supports tuple unpacking natively |
| Recursive typed structures | Complex generic TypedDict | Custom class with typed children dict | ty beta doesn't fully support recursive TypedDicts |

**Key insight:** Most of the 69 errors are mechanical fix patterns — the hard part is knowing which to suppress (3rd-party) vs. fix (our code) vs. model as TypedDict/Pydantic.

## Common Pitfalls

### Pitfall 1: `# type: ignore` vs `# ty: ignore`
**What goes wrong:** Replacing existing `# type: ignore[name-defined]` comments in models with ty-specific syntax, or leaving both and getting "unused ignore" warnings from both tools.
**Why it happens:** The project has ruff (not mypy), so `# type: ignore` comments are mypy leftovers. ty respects them by default but its own `# ty: ignore[rule]` syntax is preferred.
**How to avoid:** Use `# ty: ignore[unresolved-reference]` for SQLAlchemy forward refs. Remove old `# type: ignore[name-defined]` if ruff lint no longer needs them. Also remove `# noqa: F821` comments if ruff's `F821` rule is already handled by the per-file-ignores in pyproject.toml.
**Warning signs:** `unused-ignore-comment` or `unused-type-ignore-comment` warnings from ty.

### Pitfall 2: `**filter_kwargs` Spread Loses TypedDict Narrowing
**What goes wrong:** Even if you annotate `filter_kwargs: FilterParams`, spreading `**filter_kwargs` may still fail if ty can't prove each key maps to the right parameter.
**Why it happens:** TypedDict `**unpacking` is only typed correctly when ty can see the full TypedDict definition matching the function signature. Python 3.12+ supports `**TypedDict` spreading better; Python 3.13 (this project) should work.
**How to avoid:** Define `FilterParams` TypedDict with exactly the keys matching the function's keyword parameters. Use `FilterParams(key=value, ...)` constructor syntax (not `dict(key=value, ...)`).
**Warning signs:** Still seeing `Expected X, found Y` for the unpacked parameters.

### Pitfall 3: SQLAlchemy `.fetchall()` Returns `Row`, Not `tuple`
**What goes wrong:** Functions typed `-> list[tuple]` or `-> list[tuple[str, str]]` fail because SQLAlchemy returns `list[Row[Any]]`.
**Why it happens:** `Row` is SQLAlchemy's cursor row type that supports tuple unpacking but is not a `tuple` subclass in the type system.
**How to avoid:** Use `-> list[Row[Any]]` from `sqlalchemy.engine`. All callers that do `for a, b, c in rows:` continue to work. Callers that explicitly annotate loop variables with tuple types may need `Row` annotations too.
**Warning signs:** `expected list[tuple[...]], found list[Row[...]]` — always a `Row` vs `tuple` issue.

### Pitfall 4: ty Beta — Third-Party Library Stubs
**What goes wrong:** ty 0.0.26 (beta) does not support plugins (unlike mypy) and may misinterpret FastAPI-Users `Strategy` generics, SQLAlchemy `Result` attributes, and other third-party APIs.
**Why it happens:** ty relies on bundled typeshed and package-provided stubs (PEP 561). For libraries with incomplete stubs or dynamic type patterns, ty may produce false positives.
**How to avoid:** Per D-07: when an error is in third-party code or clearly a ty beta limitation, use `# ty: ignore[rule-name]` at the call site and document why.
**Warning signs:** Error file path starts with `.venv/`, or error references `Unknown` type extensively.

### Pitfall 5: Pydantic model_validator `mode="before"` Type Narrowing
**What goes wrong:** When `data: object` is passed to a `model_validator(mode="before")`, ty only narrows it based on `isinstance` or `hasattr` checks. `hasattr(data, "moves")` narrows to a Protocol, not the ORM model type.
**Why it happens:** Structural subtyping via `hasattr` creates ad-hoc Protocols — ty can't know what other attributes the object has.
**How to avoid:** Replace `hasattr(data, "moves")` with `isinstance(data, PositionBookmark)` — this gives ty the full type information.

### Pitfall 6: ty `include` Scope — Checking `.venv/` by Accident
**What goes wrong:** Without explicit scope configuration, ty might check installed packages in `.venv/`, surfacing third-party errors.
**Why it happens:** ty respects `.gitignore` by default (`respect-ignore-files = true`). Since `.venv/` is typically in `.gitignore`, this is usually safe.
**How to avoid:** Always run `ty check app/ tests/` (explicit directory) rather than `ty check .` in CI. The CI step should target `app/ tests/` explicitly.

## Code Examples

Verified patterns from official documentation and local testing:

### pyproject.toml Configuration
```toml
# Source: docs.astral.sh/ty/reference/configuration/
[tool.ty.rules]
# Warnings (non-blocking):
unused-ignore-comment = "warn"
possibly-unresolved-reference = "warn"

# Explicitly disabled (unreasonable false positive rate in beta):
# (add per D-07 decisions here)
```

### ty Check Command
```bash
# Check app and tests, explicit scope, no .venv/ pollution
uv run ty check app/ tests/
```

### CI Step (after ruff, before pytest)
```yaml
- name: Type check (ty)
  run: uv run ty check app/ tests/
```

### TypedDict for FilterParams
```python
from typing import TypedDict
import datetime

class FilterParams(TypedDict):
    time_control: list[str] | None
    platform: list[str] | None
    rated: bool | None
    opponent_type: str
    recency_cutoff: datetime.datetime | None
```

### Row Return Type from SQLAlchemy
```python
from sqlalchemy.engine import Row
from typing import Any

async def query_endgame_entry_rows(...) -> list[Row[Any]]:
    result = await session.execute(stmt)
    return list(result.fetchall())
```

### ty Suppression Syntax
```python
# Suppress a specific ty rule at the call site
strategy.write_token(user)  # ty: ignore[unresolved-attribute]

# SQLAlchemy forward reference in model
positions: Mapped[list["GamePosition"]] = relationship(  # ty: ignore[unresolved-reference]
    back_populates="game", cascade="all, delete-orphan"
)
```

### TrieNode Custom Class (for opening_lookup.py)
```python
class TrieNode:
    """A node in the opening lookup trie."""
    __slots__ = ("children", "result")

    def __init__(self) -> None:
        self.children: dict[str, "TrieNode"] = {}
        self.result: tuple[str, str] | None = None
```

### NormalizedGame Pydantic Model (normalization.py)
```python
import datetime
from pydantic import BaseModel

class NormalizedGame(BaseModel):
    user_id: int
    platform: str
    platform_game_id: str
    platform_url: str | None
    pgn: str
    variant: str
    result: str
    user_color: str
    termination_raw: str
    termination: str
    time_control_str: str | None
    time_control_bucket: str | None
    time_control_seconds: int | None
    rated: bool
    is_computer_game: bool
    white_username: str
    black_username: str
    white_rating: int | None
    black_rating: int | None
    opening_name: str | None
    opening_eco: str | None
    white_accuracy: float | None
    black_accuracy: float | None
    played_at: datetime.datetime | None
    # lichess-only fields (optional)
    white_acpl: int | None = None
    black_acpl: int | None = None
    white_inaccuracies: int | None = None
    black_inaccuracies: int | None = None
    white_mistakes: int | None = None
    black_mistakes: int | None = None
    white_blunders: int | None = None
    black_blunders: int | None = None
```

## Concrete Error Inventory

**Current state:** 69 diagnostics total (`uv run ty check app/ tests/`), all `error` level (no warnings yet configured).

### app/ errors (51 total) — categorized by fix strategy

| Count | Error Type | Location | Fix Strategy |
|-------|-----------|----------|--------------|
| 3 | `unresolved-reference` | `app/models/{game,game_position,user}.py` | Suppress with `# ty: ignore[unresolved-reference]` |
| 10 | `invalid-return-type` | Repositories: `analysis_repository.py`, `endgame_repository.py`, `stats_repository.py` | Change return types from `list[tuple]` to `list[Row[Any]]` |
| 1 | `invalid-assignment` | `endgame_repository.py` per_type_rows | Use `dict[int, list[Row[Any]]]` |
| 4+2+2+2+2 | `invalid-argument-type` (query_all_results/matching_games/time_series/next_moves/transposition_counts) | `analysis_service.py` → `analysis_repository.py` | Fix `list[Literal[...]]` vs `list[str]` parameter types |
| 10 | `invalid-argument-type` (query_position_wdl_batch) | `stats_service.py` | Create `FilterParams` TypedDict, annotate `filter_kwargs` |
| 8 | `unresolved-attribute` (Protocol/moves) | `app/schemas/position_bookmarks.py` | Replace `hasattr(data, "moves")` with `isinstance(data, PositionBookmark)` |
| 1 | `unresolved-attribute` (write_token) | `app/routers/auth.py:170` | `# ty: ignore[unresolved-attribute]` (FastAPI-Users beta issue, D-07) |
| 1 | `unresolved-attribute` (rowcount) | Repository using `Result.rowcount` | Use `CursorResult` type or cast |
| 1 | `no-matching-overload` | `endgame_service.py:257` | Use `_ENDGAME_CATEGORY_LABELS[endgame_class]` directly |
| 1 | `invalid-argument` | `endgame_service.py:261` | Fix `endgame_class` type from `str` to `EndgameClass` via cast |
| 1 | `invalid-raise` | `lichess_client.py:124` | Fix `last_attempt_error` initialization to non-None |
| 1 | Third-party: `fastapi_users/models.py` | `.venv/` | Configure ty to skip `.venv/` (already default via .gitignore) |

### tests/ errors (18 total) — categorized by fix strategy

| Count | Error Type | Location | Fix Strategy |
|-------|-----------|----------|--------------|
| 5 | `unresolved-attribute` (.mainline on None) | Various test files using `chess.pgn.read_game()` | Add `assert game_obj is not None` before `.mainline()` |
| 1 | `unresolved-attribute` (.white on PovScore\|None) | Test file | Add None guard |
| 2 | `invalid-assignment` | `test_import_service.py` | Assert `job is not None` before attribute access |
| 6 | `invalid-argument-type` | Tests passing literal kwargs | Follow app fix (Row types, FilterParams) |
| 1 | `invalid-return-type` | Test helper | Follow app fix |
| 2 | `unsupported-operator` | Test with SQLAlchemy expressions | Fix expression type |
| 1 | `invalid-argument-type` (query_endgame_games) | Test | Follow Row type fix |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| mypy with plugins (SQLAlchemy, Pydantic) | ty without plugins (stubs only) | 2025 (ty beta) | Some false positives for dynamic patterns |
| `# type: ignore[name-defined]` | `# ty: ignore[unresolved-reference]` | ty adoption | Need to update suppression comment syntax |
| `list[tuple]` return annotations from SQLA | `list[Row[Any]]` | Always correct, just wasn't enforced | Callers continue to work via tuple unpacking |

**Note on ty beta status:** ty 0.0.26 is explicitly versioned as pre-stable (`0.0.x`). Breaking changes including changes to diagnostics may occur between versions. The CI step should pin: `ty>=0.0.26` (or exact pin if stability is preferred).

## Open Questions

1. **`rowcount` attribute on SQLAlchemy Result**
   - What we know: `CursorResult` (from DML statements) has `.rowcount`; `Result` (from SELECT) does not. ty correctly flags this.
   - What's unclear: Which repository function is using `.rowcount` — needs a targeted look.
   - Recommendation: Use `CursorResult` type annotation for the specific function; fix is straightforward.

2. **FastAPI-Users `write_token` (D-07 trigger)**
   - What we know: Error at `app/routers/auth.py:170`. ty cannot resolve `Strategy.write_token` due to FastAPI-Users generic typing complexity in beta.
   - What's unclear: Whether this will be fixed in a future ty release.
   - Recommendation: Suppress with `# ty: ignore[unresolved-attribute]` per D-07, document the reason.

3. **`dependency-groups` vs `tool.uv.dev-dependencies` migration**
   - What we know: uv 0.x warns that `tool.uv.dev-dependencies` is deprecated in favor of `[dependency-groups]`.
   - What's unclear: Does this require lockfile regeneration or just pyproject.toml format change?
   - Recommendation: Migrate in the same commit that adds ty. `uv add --group dev ty` writes to the correct section.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| ty | Type checking | Yes | 0.0.26 | — |
| uv | Package management | Yes | (existing) | — |
| Python 3.13 | Runtime | Yes | 3.13 | — |
| PostgreSQL 18 (Docker) | pytest integration tests | Yes (dev) | 18 | — |

No missing dependencies. ty is already installed in `.venv/`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_normalization.py tests/test_endgame_service.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOOL-01 | `ty check app/ tests/` exits 0 | smoke | `uv run ty check app/ tests/` | N/A (CI validation) |
| TOOL-02 | No untyped `dict` or bare `dict[str, dict]` in primary targets | code review + ty | `uv run ty check app/ tests/` | N/A |
| TOOL-02 | Normalization returns NormalizedGame, not dict | unit | `uv run pytest tests/test_normalization.py -x` | Yes |
| TOOL-02 | Endgame service accumulators use TypedDicts | unit | `uv run pytest tests/test_endgame_service.py -x` | Yes |
| TOOL-02 | Import service handles NormalizedGame | unit | `uv run pytest tests/test_import_service.py -x` | Yes |

### Sampling Rate
- **Per task commit:** `uv run ty check app/ tests/` (fast, ~1s)
- **Per wave merge:** `uv run pytest` (full test suite)
- **Phase gate:** `uv run ty check app/ tests/` exits 0 AND `uv run pytest` passes green

### Wave 0 Gaps
None — existing test infrastructure covers all phase requirements. No new test files needed; type errors are validated by ty itself.

## Project Constraints (from CLAUDE.md)

- **No frontend changes in this phase** — stated in phase boundary
- **Pydantic v2 throughout** — NormalizedGame must use Pydantic v2 syntax (`model_config`, validators)
- **Type safety: use `Literal["a", "b"]` for fixed value sets** — applies to NormalizedGame fields like `platform`, `result`, `user_color`, `termination`
- **uv for all dependency management** — `uv add --dev ty`, not pip
- **No SQLite** — not relevant to this phase
- **httpx async only** — not relevant to this phase
- **Backend only** — no frontend changes

## Sources

### Primary (HIGH confidence)
- [ty rules reference](https://docs.astral.sh/ty/reference/rules/) — complete rule list with default levels
- [ty configuration reference](https://docs.astral.sh/ty/reference/configuration/) — pyproject.toml options
- Local `uv run ty check app/ tests/` — actual error output (51 + 18 = 69 diagnostics, current state)

### Secondary (MEDIUM confidence)
- [ty GitHub README](https://github.com/astral-sh/ty) — maturity status (0.0.x beta), uv integration
- [ty type system feature overview issue #1889](https://github.com/astral-sh/ty/issues/1889) — TypedDict/dataclass support status, Pydantic not yet supported

### Tertiary (LOW confidence)
- [FastAPI-GeoAPI ty migration issue](https://github.com/geobeyond/fastgeoapi/issues/316) — third-party library suppression patterns (single source, community)
- [uv dependency-groups docs](https://docs.astral.sh/uv/concepts/projects/dependencies/) — `[dependency-groups]` migration guidance

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — ty installed and run locally; all error counts verified
- Architecture: HIGH — error inventory is real (not speculative); fix strategies verified against ty docs
- Pitfalls: HIGH — pitfalls derived from actual ty output, not theoretical

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (ty is in 0.0.x beta — a new release could add new errors or fix false positives)
