# Phase 40: Static Type Checking - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 40-static-type-checking
**Areas discussed:** Dict replacement, ty strictness, CI integration

---

## Dict Replacement

### External API dicts

| Option | Description | Selected |
|--------|-------------|----------|
| TypedDicts | Lightweight type hints without runtime validation | |
| Pydantic models | Runtime validation + type hints, catches unexpected API changes | ✓ |
| You decide | Claude picks based on context | |

**User's choice:** Pydantic models, initially wanted Pydantic everywhere including internal dicts.

### Internal dicts strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, pragmatic mix | Pydantic at boundaries, dataclasses/TypedDicts for internal data | ✓ |
| Pydantic everywhere | Consistency over performance | |

**User's choice:** Pragmatic mix — after Claude explained performance overhead of Pydantic for internal accumulators in hot loops (game import).
**Notes:** User was open to Pydantic everywhere but accepted the tradeoff reasoning.

---

## ty Strictness

| Option | Description | Selected |
|--------|-------------|----------|
| Fix-all strict | Zero errors from day one, suppress false positives with inline comments | |
| Incremental | Start basic, tighten as ty matures | |
| You decide | Claude evaluates ty capabilities | |

**User's choice:** Zero errors for error level. For warnings and below, Claude decides. If errors seem unreasonable, report to user for joint decision.
**Notes:** User provided a nuanced answer beyond the options — wants collaborative handling of edge cases.

---

## CI Integration

### Blocking behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Blocking from day one | ty errors fail the build immediately | ✓ |
| Non-blocking initially | Run as informational, switch later | |

**User's choice:** Blocking from day one.

### Pipeline placement

| Option | Description | Selected |
|--------|-------------|----------|
| After ruff, before pytest | lint → type check → tests | ✓ |
| Parallel with ruff | Both run simultaneously | |
| You decide | Claude picks optimal placement | |

**User's choice:** After ruff, before pytest.
**Notes:** User asked about CI trigger scope — confirmed it runs on every PR (not just deploy).

---

## Claude's Discretion

- Warning-level ty configuration
- Exact pyproject.toml settings beyond error blocking
- Dataclass vs TypedDict choice per internal dict
- Test file type annotation approach

## Deferred Ideas

None — discussion stayed within phase scope.
