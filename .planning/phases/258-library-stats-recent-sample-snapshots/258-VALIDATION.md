---
phase: "258"
slug: "library-stats-recent-sample-snapshots"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-21"
---

# Phase 258 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `258-RESEARCH.md` § Validation Architecture. The phase has no REQ-IDs; the CONTEXT.md decisions
> (D-01 to D-19) are the requirement set.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend, per-worker cloned Postgres DB); Vitest + Testing Library (frontend) |
| **Config file** | `pyproject.toml` (`addopts` ignores `tests/scripts/benchmarks` and `tests/scripts/tagger`); `frontend` vitest config |
| **Quick run command** | `uv run pytest tests/services/test_flaw_comparison.py tests/services/test_tactic_comparison_service.py tests/services/test_library_window.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` and `( cd frontend && npm test -- --run )` |
| **Estimated runtime** | quick ~60 seconds; full ~5 minutes |

---

## Sampling Rate

- **After every task commit:** Run the quick run command, plus the affected frontend test file
- **After every plan wave:** Run `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run )`
- **Before `/gsd-verify-work`:** The full pre-merge gate from the root `CLAUDE.md` must be green, plus the prod
  performance item (D-18/D-19)
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

Task IDs follow `{plan}-T{n}` (plan 258-NN, task n). Test files are created inside the task that
needs them (tdd tasks), so no separate Wave 0 plan exists; the "File Exists" column says which task
creates or extends the file.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-T1 | 258-01 | 1 | Clock (`dev_now_utc`), response window fields, D-04 flag, D-13 at-cap / under-cap line | — | N/A | router + component | `uv run pytest tests/test_library_router.py -k "FlawComparison" -x` and `npm --prefix frontend test -- src/components/library/stats/__tests__/LibraryStatsSections.test.tsx` | extended in 01-T1 | ⬜ pending |
| 01-T2 | 258-01 | 1 | Seed migration (every comparison seed has `played_at`, flaw calls pass `now_utc`) | — | N/A | service | `uv run pytest tests/services/test_flaw_comparison.py tests/services/test_tactic_comparison_service.py tests/routers/test_library_tactic_comparison.py -x` | existing | ⬜ pending |
| 01-T3 | 258-01 | 1 | D-03 (per-TC cap, `cap_reached`) | — | N/A | repo integration | `uv run pytest tests/services/test_library_window.py -k cap -x` | created in 01-T3 | ⬜ pending |
| 01-T3 | 258-01 | 1 | D-03 (real constant, 1001 → 1000) | — | N/A | repo integration | `uv run pytest tests/services/test_library_window.py -k real_cap -x` | created in 01-T3 | ⬜ pending |
| 01-T3 | 258-01 | 1 | D-03 (36-month bound, fixed `now_utc`) | — | N/A | repo integration | `uv run pytest tests/services/test_library_window.py -k bound -x` | created in 01-T3 | ⬜ pending |
| 01-T3 | 258-01 | 1 | D-03 (`months_before` matches PG clamping) | — | N/A | unit | `uv run pytest tests/services/test_library_window.py -k months_before -x` | created in 01-T3 | ⬜ pending |
| 01-T3 | 258-01 | 1 | D-04 (explicit recency replaces the bound, cap stays) | — | N/A | repo + service | `uv run pytest tests/services/test_library_window.py -k recency -x` | created in 01-T3 | ⬜ pending |
| 01-T3 | 258-01 | 1 | D-05 (cap counts unanalyzed games) | — | N/A | repo + summary | `uv run pytest tests/services/test_library_window.py -k cap_counts_unanalyzed -x` | created in 01-T3 | ⬜ pending |
| 01-T3 | 258-01 | 1 | D-06 (`total_n`/`analyzed_n` equal the window summary) | — | N/A | service | `uv run pytest tests/services/test_library_window.py -k window_counts -x` | created in 01-T3 | ⬜ pending |
| 01-T3 | 258-01 | 1 | D-10 (flaw gate applies to the windowed set) | — | N/A | service | `uv run pytest tests/services/test_library_window.py -k gate_on_window -x` | created in 01-T3 | ⬜ pending |
| 01-T3 | 258-01 | 1 | D-11 (filter first, then cap) | — | N/A | repo | `uv run pytest tests/services/test_library_window.py -k filter_first -x` | created in 01-T3 | ⬜ pending |
| 01-T3 | 258-01 | 1 | Tiebreak on equal `played_at` | — | N/A | repo | `uv run pytest tests/services/test_library_window.py -k tiebreak -x` | created in 01-T3 | ⬜ pending |
| 01-T3 | 258-01 | 1 | NULL `played_at` / `ply_count` 0 / NULL TC never take a slot | — | N/A | repo | `uv run pytest tests/services/test_library_window.py -k excluded_rows -x` | created in 01-T3 | ⬜ pending |
| 01-T3 | 258-01 | 1 | D-15 (quiet TC stays listed on the flaw payload) | — | N/A | service | `uv run pytest tests/services/test_library_window.py -k quiet_tc -x` | created in 01-T3 | ⬜ pending |
| 01-T3 | 258-01 | 1 | D-02 (timeline keeps full history) | — | N/A | service | `uv run pytest tests/services/test_library_service.py -k trend_full_history -x` | extended in 01-T3 | ⬜ pending |
| 01-T3 | 258-01 | 1 | Two-user isolation of the window | T-258-01 | The window never includes another user's games | repo + service | `uv run pytest tests/services/test_library_window.py -k two_user -x` | created in 01-T3 | ⬜ pending |
| 02-T1 | 258-02 | 2 | D-06 (facepalm rows = analyzed window ids = flaw rows), D-10 (facepalm low coverage on the window), D-15 (facepalm list rule) | T-258-05 | Facepalm rows read only the user's own window | service | `uv run pytest tests/services/test_flaw_comparison.py -k "same_game_set or window" -x` | extended in 02-T1 | ⬜ pending |
| 02-T2 | 258-02 | 2 | D-06 (tactic rows = tactic-ready window ids), D-10 (tactic gate on the window), D-15 (quiet TC absent) | T-258-05 | Tactic rows read only the user's own window | service | `uv run pytest tests/services/test_tactic_comparison_service.py -k "tactic_window or gate_on_window or quiet_tc" -x` | extended in 02-T2 | ⬜ pending |
| 03-T1 | 258-03 | 2 | D-15/D-16/D-17 (quiet TC state), default TC when TCs are quiet | — | N/A | component + unit | `npm --prefix frontend test -- src/lib/__tests__/flawComparisonMeta.test.ts src/components/library/stats/__tests__/LibraryStatsSections.test.tsx src/hooks/__tests__/useLibraryStatsTc.test.ts` | meta test created in 03-T1 | ⬜ pending |
| 03-T2 | 258-03 | 2 | D-12/D-13 (eight wording variants, suffix, shown once), popover "in the recent sample" | — | N/A | frontend unit + component | `npm --prefix frontend test -- src/lib/__tests__/flawComparisonMeta.test.ts src/components/library/stats/__tests__/LibraryStatsSections.test.tsx` | extended in 03-T2 | ⬜ pending |
| 03-T3 | 258-03 | 2 | D-14 (timeline caption) | — | N/A | component | `npm --prefix frontend test -- src/components/library/__tests__/FlawTrendChart.test.tsx` | extended in 03-T3 | ⬜ pending |
| 03-T3 | 258-03 | 2 | D-01 / D-08 (`DEFAULT_FILTERS.recency === null`, `opponentStrength` = ANY_RANGE) | — | N/A | frontend unit | `npm --prefix frontend test -- src/components/filters/__tests__/FilterPanel.defaults.test.ts` | created in 03-T3 | ⬜ pending |
| 04-T1 | 258-04 | 3 | D-18 / D-19 tool (timing script, window EXPLAIN SQL), dev dry run | T-258-09 | Read-only, one connection, outputs gitignored | operator script | `uv run python temp/library-258/time_snapshot_endpoints.py --db dev --rounds 1 --warmup 0` | created in 04-T1 (gitignored) | ⬜ pending |
| 04-T2 | 258-04 | 3 | Full pre-merge gate, changelog | — | N/A | gate | CLAUDE.md pre-merge gate commands | existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_library_window.py` — window repository, `months_before` and `summarize_window` tests (258-01 Task 3)
- [ ] Seed helpers in `tests/services/test_flaw_comparison.py`, `tests/services/test_tactic_comparison_service.py`,
      `tests/routers/test_library_tactic_comparison.py` — default `played_at` relative to a fixed `_NOW`, flaw
      calls with `now_utc=_NOW` (258-01 Task 2); facepalm and tactic calls with `now_utc=_NOW` and the
      router clock pins (258-02 Tasks 1 and 2); `tests/test_library_router.py` `pin_library_now` (258-01 Task 1)
- [ ] `frontend/src/components/library/stats/__tests__/flawStatsFixtures.ts` — the new window fields (258-01 Task 1)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None of the three endpoints is slower than today on the largest prod account | D-18, D-19 | Needs prod data over the read-only tunnel; run by the orchestrator, not an executor | `temp/library-258/window_explain.sql` through the `flawchess-prod-db` MCP (account query, window `EXPLAIN (ANALYZE, BUFFERS)` with the 36-month and the 5-year bound), then `uv run python temp/library-258/time_snapshot_endpoints.py --db prod --user <id> --rounds 3` (258-04 Task 2 human-check; every row PASS, exit 0) |
| Basis-line and quiet-state wording read well in the app | D-13, D-17 | Copy judgement | Open Library → Stats, check each wording variant and a time control with no recent games |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
