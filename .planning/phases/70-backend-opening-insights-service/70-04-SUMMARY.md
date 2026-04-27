---
phase: 70-backend-opening-insights-service
plan: "04"
subsystem: backend-service
tags: [opening-insights, service, classification, attribution, dedupe, ranking, sentry]
dependency_graph:
  requires: [70-01, 70-03]
  provides: [compute_insights]
  affects:
    - app/services/opening_insights_service.py
    - app/services/opening_insights_constants.py
    - tests/services/test_opening_insights_service.py
tech_stack:
  added: []
  patterns: [single-public-entry, sequential-await-same-session, two-pass-attribution, ctypes-c_int64-zobrist, sentry-set-context]
key_files:
  created:
    - app/services/opening_insights_service.py
    - app/services/opening_insights_constants.py
  modified:
    - tests/services/test_opening_insights_service.py
decisions:
  - "Constants split into a tiny opening_insights_constants.py module (16 lines) — service re-exports for backward compatibility but the constants live in their own file to avoid a circular import shape between repository and service"
  - "Two-pass attribution: pass 1 direct query_openings_by_hashes on entry_hashes, pass 2 batched query for parent prefix hashes computed via _compute_prefix_hashes() with ctypes.c_int64 signed-int64 conversion (BLOCKER-2)"
  - "Findings with no direct AND no parent match are DROPPED (D-34) — never surfaced with sentinel `<unnamed line>`. Sentry tag `openings.attribution.unmatched_dropped` set on each drop"
  - "Off-color SQL query skipped when request.color != 'all' (D-12, ~50% latency saving)"
  - "No caching layer (D-29) — partial-index-backed query keeps even Hikaru-class users <1 s"
  - "All exceptions wrapped in try/except that calls sentry_sdk.set_context with {user_id, request.model_dump()} then re-raises"
metrics:
  shipped_in_pr: "#66 (df9b689)"
  service_lines: 353
  constants_lines: 16
  service_test_lines_added: 639
  tests_passing: "all 17 service unit tests + 2 arrow-consistency tests"
ship_status: shipped
---

# Phase 70 Plan 04: Service Layer — compute_insights Pipeline (retroactive summary)

**One-liner:** Landed the orchestration brain of Phase 70 — classify, attribute (direct + parent-lineage walk + drop on miss), dedupe, rank, cap — wired through a single public `compute_insights` entry.

## Tasks Completed

| Task | Name | Files |
|------|------|-------|
| 1 | `compute_insights()` pipeline + helpers (classify, replay-SAN, prefix-hashes, attribute, dedupe, rank) | app/services/opening_insights_service.py |
| — | Constants module split out to avoid circular import between repository and service | app/services/opening_insights_constants.py |
| — | Replaced Wave 0 NotImplementedError stubs with real test bodies; added the BLOCKER-1/D-34 drop test | tests/services/test_opening_insights_service.py |

## What Was Built

- `compute_insights(session, user_id, request) -> OpeningInsightsResponse` — single public async entry. Sequential awaits on the same AsyncSession (CLAUDE.md §Critical Constraints — never asyncio.gather).
- Helpers (all private with `_` prefix):
  - `_classify_row` — strict `>` 0.55 boundary, severity tier `>= 0.60` major else minor
  - `_compute_score` — `(W + D/2)/n`, informative only (D-06)
  - `_replay_san_sequence` — chess.Board().push_san() loop for entry_fen reconstruction (D-25)
  - `_compute_prefix_hashes` — Zobrist hashes for every proper prefix, with ctypes.c_int64 signed-int64 conversion matching `app/services/zobrist.py:111-122` (BLOCKER-2)
  - `_attribute_finding` — direct → parent-lineage → drop (D-34); applies parity prefix
  - `_dedupe_within_section` — group by resulting_full_hash, keep deeper-entry (D-24)
  - `_rank_section` — sort by (severity desc, n_games desc)
- Two-pass attribution batches both direct and parent-prefix `query_openings_by_hashes` calls (no per-row roundtrips).
- Off-color optimization: when request.color != "all", only that color's SQL runs.
- Sentry: try/except wraps the entire pipeline; `set_context("opening_insights", {user_id, request.model_dump()})` + `capture_exception` + re-raise. Tag `openings.attribution.unmatched_dropped` set on drops so the drop rate is observable.

## Deviations from Plan

- Constants moved into `app/services/opening_insights_constants.py` instead of living at the top of `opening_insights_service.py` — needed because the repository imports them and a co-located definition created a circular import. The split keeps a single canonical home and the service still re-exports the names.

## Verification

- All 17 Wave 0 service unit tests pass + the new `test_attribution_drops_finding_when_no_lineage_match` (D-34) + the rescoped `test_attribution_lineage_walk_to_parent_hash`.
- Both arrow-consistency tests pass (LIGHT_THRESHOLD * 100 == arrowColor.ts LIGHT_COLOR_THRESHOLD; same for DARK).
- `grep` gates: 0 occurrences of asyncio.gather, lru_cache, functools.cache, or `from asyncio import gather`. ctypes.c_int64 present once. Sentry context capture present.

## Coupled Commit Note

Plan 70-04 and Plan 70-05 ship in the same PR (#66) so that the router-test scaffold's `pytest.importorskip("app.services.opening_insights_service")` doesn't briefly hard-error on main while the route is missing.

## Self-Check

- [x] `async def compute_insights` is the single public function
- [x] No asyncio.gather; sequential awaits on same AsyncSession
- [x] ctypes.c_int64 conversion in lineage hash computation
- [x] Sentry context capture + re-raise pattern
- [x] No caching layer (D-29)
- [x] Shipped as part of PR #66 (df9b689)
