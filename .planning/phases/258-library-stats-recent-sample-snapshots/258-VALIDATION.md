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

Task IDs are assigned by the planner; rows are keyed by decision until then.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | D-03 (per-TC cap, `cap_reached`) | — | N/A | repo integration | `uv run pytest tests/services/test_library_window.py -k cap -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-03 (real constant, 1001 → 1000) | — | N/A | repo integration | `uv run pytest tests/services/test_library_window.py -k real_cap -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-03 (36-month bound, fixed `now_utc`) | — | N/A | repo integration | `uv run pytest tests/services/test_library_window.py -k bound -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-03 (`months_before` matches PG clamping) | — | N/A | unit | `uv run pytest tests/services/test_library_window.py -k months_before -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-04 (explicit recency replaces the bound, cap stays) | — | N/A | repo + service | `uv run pytest tests/services/test_library_window.py -k recency -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-05 (cap counts unanalyzed games) | — | N/A | service | `uv run pytest tests/services/test_library_window.py -k cap_counts_unanalyzed -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-06 (one game set for all three comparisons) | — | N/A | service | `uv run pytest tests/services/test_flaw_comparison.py -k same_game_set -x` | partly | ⬜ pending |
| TBD | TBD | TBD | D-06 (`total_n`/`analyzed_n` equal the window summary) | — | N/A | service | `uv run pytest tests/services/test_flaw_comparison.py -k window_counts -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-10 (gates apply to the windowed set) | — | N/A | service | `uv run pytest tests/services/test_flaw_comparison.py -k gate_on_window -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-11 (filter first, then cap) | — | N/A | service | `uv run pytest tests/services/test_library_window.py -k filter_first -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Tiebreak on equal `played_at` | — | N/A | repo | `uv run pytest tests/services/test_library_window.py -k tiebreak -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | NULL `played_at` / `ply_count` 0 / NULL TC never take a slot | — | N/A | repo | `uv run pytest tests/services/test_library_window.py -k excluded_rows -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-15 (quiet TC stays listed) | — | N/A | service | `uv run pytest tests/services/test_flaw_comparison.py -k quiet_tc -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-02 (timeline keeps full history) | — | N/A | service | `uv run pytest tests/services/test_library_service.py -k trend_full_history -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Clock (`dev_now_utc`) and response window fields | — | N/A | router | `uv run pytest tests/test_library_router.py -k window -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Two-user isolation of the window | T-258-01 | The window never includes another user's games | service | `uv run pytest tests/services/test_library_window.py -k two_user -x` | partly | ⬜ pending |
| TBD | TBD | TBD | D-01 (`DEFAULT_FILTERS.recency === null`) | — | N/A | frontend unit | `npm --prefix frontend test -- FilterPanel` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-12/D-13 (four wording variants, suffix) | — | N/A | frontend unit | `npm --prefix frontend test -- flawComparisonMeta` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-12 (basis line once, icon and hint kept) | — | N/A | component | `npm --prefix frontend test -- LibraryStatsSections` | update | ⬜ pending |
| TBD | TBD | TBD | D-14 (timeline caption) | — | N/A | component | `npm --prefix frontend test -- LibraryStatsSections` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-15/D-16/D-17 (quiet TC state) | — | N/A | component | `npm --prefix frontend test -- LibraryStatsSections` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Default TC when TCs are quiet | — | N/A | unit | `npm --prefix frontend test -- useLibraryStatsTc` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_library_window.py` — window repository, `months_before` and `summarize_window` tests
- [ ] Seed helpers in `tests/services/test_flaw_comparison.py`, `tests/services/test_tactic_comparison_service.py`,
      `tests/routers/test_library_tactic_comparison.py`, `tests/test_library_router.py` — default `played_at`
      relative to a fixed `_NOW`, services called with `now_utc=_NOW`, router tests pin `dev_now_utc`
- [ ] `frontend/src/components/library/stats/__tests__/flawStatsFixtures.ts` — the new window fields

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None of the three endpoints is slower than today on the largest prod account | D-18, D-19 | Needs prod data over the read-only tunnel; run by the orchestrator, not an executor | `258-RESEARCH.md` § Performance Check: largest-account query, `EXPLAIN (ANALYZE, BUFFERS)` of the window statement (default and 5-year bound), interleaved before/after timing, at least 3 rounds |
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
