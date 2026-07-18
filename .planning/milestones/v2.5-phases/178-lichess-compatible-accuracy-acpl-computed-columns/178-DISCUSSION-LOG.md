# Phase 178: Lichess-compatible accuracy & ACPL (computed columns) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-18
**Phase:** 178-lichess-compatible-accuracy-acpl-computed-columns
**Areas discussed:** Column strategy, Scope, Backfill operations, Validation, Column naming

---

## Column strategy (user-initiated pivot)

Original SEED-110 proposal: four NEW `*_computed` columns, leave existing platform
columns untouched. During discussion the user pivoted:

> "move the current data into new columns, NULL the existing columns and then use
> the existing columns for our computation"

| Option | Description | Selected |
|--------|-------------|----------|
| Additive `*_computed` columns (SEED-110) | Four new columns, existing untouched | |
| Repurpose canonical + preserve as `*_imported` | Canonical accuracy/acpl = our uniform values; platform data → `*_imported` | ✓ |

**User's choice:** Repurpose canonical columns; move platform data to `*_imported`.
**Notes:** Rationale — canonical column names become the uniform metric, avoiding a
future migration to swap the app onto `_computed`. Verified low blast radius:
`accuracy`/`acpl` are not surfaced to FE and not in the library API schema, so no
display change or backfill display gap.

## Which columns move/repurpose

| Option | Description | Selected |
|--------|-------------|----------|
| Only accuracy + acpl | Leave i/m/b untouched (is_analyzed sentinel + oracle counts) | ✓ |
| Also relocate i/m/b counts | Larger blast radius across library layer | |

**User's choice:** Only accuracy + acpl.
**Notes:** i/m/b are load-bearing (`white_blunders IS NOT NULL` = `is_analyzed`).

## Platform column naming

| Option | Description | Selected |
|--------|-------------|----------|
| `*_platform` | "whatever the platform reported" | |
| `*_reported` | "as reported by the source platform" | |
| `*_imported` (free-text) | Value imported from the source platform | ✓ |

**User's choice:** `*_imported` suffix — `white_accuracy_imported`, `black_accuracy_imported`, `white_acpl_imported`, `black_acpl_imported`.

## Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Columns only (backend) | Migration + compute + hook + backfill script; no API/FE | ✓ |
| Also expose in API | Surface in game/stats responses | |
| Also add frontend UI | Show in FE | |

**User's choice:** Columns only (backend).

## Backfill operations

| Option | Description | Selected |
|--------|-------------|----------|
| Ship code + script, backfill separately | Verified on dev; prod run is an operator step | ✓ |
| Include running prod backfill | Phase gated on ~718k-game prod run | |

**User's choice:** Ship code + script, run prod backfill separately.

## Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Computed vs `*_imported` report + fixture unit tests | DB-wide comparison against preserved platform values, plus hand-checked lichess fixtures | ✓ |
| Unit tests only | Fixtures only, skip DB comparison | |

**User's choice:** Computed vs `*_imported` report + hand-checked fixture unit tests.

---

## Claude's Discretion

Deferred to researcher/planner (technical, not user decisions):
- Exact live-hook seam (`full_evals_completed_at` / `lichess_evals_at`).
- Eval sign convention + post-move shift mapping for before/after plies.
- Terminal-ply / checkmate / 0–1-move game handling.
- Exact data-move migration mechanics and complete-sequence gate query.

## Deferred Ideas

- API + frontend surfacing of computed accuracy/ACPL — future phase.
- Uniform recomputation of inaccuracy/mistake/blunder counts — out of scope.
- Running prod backfill to 100% coverage — operator step post-deploy.
