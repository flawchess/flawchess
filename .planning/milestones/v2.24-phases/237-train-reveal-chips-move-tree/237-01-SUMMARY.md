---
phase: 237-train-reveal-chips-move-tree
plan: 01
subsystem: api
tags: [pydantic, telemetry, train, jsonb, schema-versioning]
status: complete

requires: []
provides:
  - "REVIEW_TELEMETRY_SCHEMA_VERSION = 2 (app/schemas/train.py)"
  - "ReviewTelemetry v: Literal[1, 2] with review_chips_selected, review_chips_total, review_strip_expanded"
  - "ReviewTelemetry._keys_match_version cross-version model validator"
affects: [237-09]

tech-stack:
  added: []
  patterns:
    - "Per-patch schema version constants (solve stays 1, review is 2) instead of one shared constant"
    - "model_validator(mode='after') keeps a JSONB column to exactly two clean shapes"

key-files:
  created: []
  modified:
    - app/schemas/train.py
    - tests/schemas/test_train_telemetry_schema.py
    - tests/routers/test_train.py

key-decisions:
  - "Separate REVIEW_TELEMETRY_SCHEMA_VERSION = 2; TELEMETRY_SCHEMA_VERSION stays 1 so SolveTelemetry (Literal[1]) keeps accepting every solve patch (RESEARCH Pitfall 4)"
  - "Mixed-version bodies (v2 keys on v1, v1 card keys on v2) are a plain 422 via ValueError, no Sentry capture (expected client drift)"
  - "Stored top-level v reflects the LAST patch merged (jsonb last-write-wins); analysis branches on v for review keys only, documented in the ReviewTelemetry docstring"

requirements-completed: [D-12, D-13]

duration: 12 min
completed: 2026-10-08
actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: 4e05ef4b5c7b69401c2ce9d1a82e2a9340117129
plan_head_after: a2332d7d25e567c9de7f204a1b9043ad7b1b3645
commits: 2

coverage:
  - deliverable: "Review route accepts and stores a v2 body (chips selected/total, strip expanded) through the jsonb merge"
    verification:
      - kind: test
        ref: "tests/routers/test_train.py#test_review_flush_v2_body_is_stored"
        status: pass
    human_judgment: false
  - deliverable: "v1 review bodies and v1 card keys keep validating and storing unchanged"
    verification:
      - kind: test
        ref: "tests/schemas/test_train_telemetry_schema.py#test_review_telemetry_v1_card_keys_still_valid"
        status: pass
      - kind: test
        ref: "tests/routers/test_train.py#test_review_flush_merges_into_solved_row"
        status: pass
    human_judgment: false
  - deliverable: "Mixed-version bodies are a plain 422"
    verification:
      - kind: test
        ref: "tests/schemas/test_train_telemetry_schema.py#test_review_telemetry_rejects_mixed_versions"
        status: pass
      - kind: test
        ref: "tests/routers/test_train.py#test_review_flush_rejects_bad_body"
        status: pass
    human_judgment: false
  - deliverable: "Solve patch unaffected (SolveTelemetry still v: 1 only, constants split per patch)"
    verification:
      - kind: test
        ref: "tests/schemas/test_train_telemetry_schema.py#test_versions_are_split_per_patch"
        status: pass
      - kind: test
        ref: "tests/schemas/test_train_telemetry_parity.py"
        status: pass
    human_judgment: false
  - deliverable: "ReviewTelemetry docstring documents the v2 meaning of review_explored and the phone-only strip flag (D-13)"
    verification: []
    human_judgment: true
    rationale: "Documentation prose; no test asserts wording"
---

# Phase 237 Plan 01: Review Telemetry v2 Boundary Summary

**ReviewTelemetry accepts a v2 body (review_chips_selected, review_chips_total, review_strip_expanded) behind a separate REVIEW_TELEMETRY_SCHEMA_VERSION = 2, with a model validator that rejects v1/v2 key mixes and leaves the solve patch on v1.**

## Performance

- **Duration:** 12 min
- **Tasks:** 2 (1 tracer, 1 TDD-flagged auto)
- **Files modified:** 3

## Accomplishments

- `ReviewTelemetry.v` is now `Literal[1, 2]`; v1 stays valid forever for old bundles and open tabs.
- Three optional v2 fields added; both counts reuse the clamped `TelemetryCardCount` (cap 10), the strip flag is a `StrictBool`.
- `_keys_match_version` (flat guard clauses) raises a plain `ValueError` for v2 keys on a v1 body or v1 card keys on a v2 body, so the JSONB only ever holds two shapes. It runs on `ReviewRequest` too (inherited).
- `REVIEW_TELEMETRY_SCHEMA_VERSION: Final = 2` added next to the unchanged `TELEMETRY_SCHEMA_VERSION: Final = 1`; the block comment no longer claims the version is stamped on both patches.
- Docstring documents D-13: under v2 `review_explored` means "forked at least one sideline", `review_explore_moves` / `review_board_moves` keep their v1 meaning, `review_line_steps` counts move-tree steps, `review_strip_expanded` is phone-only, and the stored row-level `v` is the last patch merged.
- Tests: router round trip for a stored v2 body (solve keys preserved, top-level v from the last patch), mixed-version rows in the bad-body list; schema tests for v2 accept/clamp, StrictBool, mixed rejects, v1 unchanged, v3 rejected, split constants, v2 `exclude_none` dump.

## Task Commits

1. **Task 1 (tracer): v2 review body end to end** - `28e672d36` (feat)
2. **Task 2: schema unit tests** - `a2332d7d2` (test)

## Mutation proof (Task 2)

Temporarily deleted the `if self.v == 2 and any(...)` guard in `_keys_match_version`: `test_review_telemetry_rejects_mixed_versions[payload2]` (`{"v": 2, "exit": "pagehide", "review_cards_total": 2}`) went red (1 failed, 32 passed). Guard restored byte-identically from a backup copy; the suite and the parity test were re-run green (38 passed).

## TDD Gate Compliance

Task 2 was flagged `tdd="true"` but tests it pins an implementation that Task 1 (the tracer) had already landed, per the plan's task order. There is therefore no separate RED commit preceding a GREEN commit for this behavior; the plan is `type: execute`, not `type: tdd`. RED-equivalent evidence is the mutation run above (the guard removed, the target test fails on the planned assertion).

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. The only boundary touched is the existing review route; mitigations T-237-01/02/03 are implemented and pinned by tests (existing `test_review_flush_rejects_other_users_row` stayed green).

## Verification

- `uv run pytest tests/routers/test_train.py -x -k review`: 21 passed
- `uv run pytest tests/schemas`: 165 passed (includes `test_train_telemetry_parity.py`, untouched)
- `ruff format --check`, `ruff check .`, `ty check app/ tests/ scripts/`: clean
- `scripts/check_function_size.py app/ --fail-over-depth 4`: no breaches
- Tracer gate: `<verify>` re-run end to end after the commit, passed; expansion (Task 2) proceeded.

## Next Phase Readiness

Plan 09 can switch the client to `v: 2`, add the TS constant and the parity-test row for `REVIEW_TELEMETRY_SCHEMA_VERSION`. No coordination needed server-side.

## Self-Check: PASSED

- FOUND: app/schemas/train.py, tests/schemas/test_train_telemetry_schema.py, tests/routers/test_train.py
- FOUND commits: 28e672d36, a2332d7d2
