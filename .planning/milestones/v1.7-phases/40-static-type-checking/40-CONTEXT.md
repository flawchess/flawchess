# Phase 40: Static Type Checking - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Integrate astral `ty` into the backend and CI pipeline, and fix type safety gaps across all backend Python code. Zero type errors at completion. No frontend work in this phase.

</domain>

<decisions>
## Implementation Decisions

### Dict replacement strategy
- **D-01:** Use Pydantic models at system boundaries — external API input (chess.com/lichess JSON in `normalization.py`) and API response schemas.
- **D-02:** Use dataclasses or TypedDicts for internal data structures — accumulators (`dict[str, dict]` in `endgame_service.py`), lookup maps, intermediate computation results.
- **D-03:** Already-typed dicts like `dict[str, timedelta]` are fine as-is — only replace bare `dict` or `dict[str, dict]` where the value type is unspecified.
- **D-04:** Recursive structures like the opening trie should use TypedDict or a custom class, not Pydantic.

### ty strictness
- **D-05:** Target zero errors from day one — all type errors must be resolved before the phase is complete.
- **D-06:** For warnings and below, Claude has discretion to configure as appropriate.
- **D-07:** If any errors seem unreasonable to fix (e.g., SQLAlchemy/FastAPI patterns that ty can't handle), report to user for joint decision on suppress vs fix.

### CI integration
- **D-08:** `ty` is a blocking CI step from day one — type errors fail the build.
- **D-09:** Placement in pipeline: after ruff check, before pytest (lint → type check → tests).
- **D-10:** Runs on every PR to main (same trigger as existing ruff/pytest steps).

### Claude's Discretion
- Warning-level ty configuration (D-06)
- Exact pyproject.toml ty settings beyond error-level blocking
- Which specific dicts to convert to dataclass vs TypedDict (within the D-01/D-02 guidelines)
- Test file type annotations (follow whatever approach makes tests readable)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The user wants a clean, zero-error baseline that enforces type safety going forward.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above.

### Key files to understand
- `.github/workflows/ci.yml` — Current CI pipeline where ty step must be added
- `pyproject.toml` — Where ty configuration will live (alongside existing ruff config)
- `app/services/normalization.py` — Primary target for Pydantic models (external API dicts)
- `app/services/endgame_service.py` — Primary target for TypedDicts/dataclasses (internal accumulators)
- `app/services/import_service.py` — Uses various dict patterns that need typing
- `app/services/opening_lookup.py` — Bare dict trie that needs a typed structure

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Pydantic v2 is already used throughout `app/schemas/` — established pattern for API schemas
- `pyproject.toml` already has `[tool.ruff]` config — `[tool.ty]` goes alongside

### Established Patterns
- All backend functions already have return type annotations (`->`) — good baseline
- Repository layer uses SQLAlchemy 2.x async select() API with typed models
- Services use Pydantic schemas for API responses via `app/schemas/`
- FastAPI dependency injection and FastAPI-Users auth patterns in routers

### Integration Points
- CI pipeline (`ci.yml`): new step between ruff and pytest
- `pyproject.toml`: new `[tool.ty]` section
- `uv` dependency: `ty` needs to be added as a dev dependency
- All `app/services/*.py` files: primary targets for dict type improvements

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 40-static-type-checking*
*Context gathered: 2026-03-31*
