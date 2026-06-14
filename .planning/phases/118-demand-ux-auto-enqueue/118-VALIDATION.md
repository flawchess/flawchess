---
phase: 118
slug: demand-ux-auto-enqueue
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-14
---

# Phase 118 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend, per-run-DB isolation) + vitest (frontend) |
| **Config file** | `pyproject.toml` (backend), `frontend/vitest.config.ts` (frontend) |
| **Quick run command** | `uv run pytest tests/test_<target>.py` (single file, serial) |
| **Full suite command** | `uv run pytest -n auto -x` then `( cd frontend && npm run lint && npm test -- --run )` |
| **Estimated runtime** | ~60–120 seconds (backend parallel) + ~30s (frontend) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command for the touched module
- **After every plan wave:** Run the full backend suite (`uv run pytest -n auto`)
- **Before `/gsd-verify-work`:** Full backend + frontend suites must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

> The planner fills concrete Task IDs per plan. Key behavioral seams identified by RESEARCH.md
> "Validation Architecture" that MUST have automated coverage:

| Seam | Requirement | Secure Behavior | Test Type | Automated Command | Status |
|------|-------------|-----------------|-----------|-------------------|--------|
| Auto-enqueue idempotency (no duplicate `eval_jobs` for pending/leased/completed games) | QUEUE-04 | Re-running `enqueue_tier2_window` does not create duplicate rows | unit | `uv run pytest tests/test_eval_queue_service.py` | ⬜ pending |
| Tier-2 window predicate (`full_evals_completed_at IS NULL AND lichess_evals_at IS NULL`, ~200 cap) | QUEUE-04 | Only genuinely-needs-eval games enqueued; lichess-eval games excluded | unit | `uv run pytest tests/test_eval_queue_service.py` | ⬜ pending |
| Guest exclusion (tier-1 + tier-2 enqueue no-op for guests) | EVUX-01 / QUEUE-08 | Guest enqueue calls return without creating jobs | unit | `uv run pytest tests/test_eval_queue_service.py` | ⬜ pending |
| Coverage % honesty (`count_is_analyzed_games` aligns with `is_analyzed`, lichess-eval = analyzed) | EVUX-02 | `analyzed_count` matches `is_analyzed` rows, not entry-ply drain | unit | `uv run pytest tests/test_game_repository.py` | ⬜ pending |
| In-flight count accuracy (queued/leased counts in extended `/imports/eval-coverage`) | EVUX-03 | Response in-flight counts match `eval_jobs` pending+leased for user | unit/api | `uv run pytest tests/test_imports.py` | ⬜ pending |
| Bulk button disabled-until-drained (tier-2 in-flight gate) | EVUX-01 | Endpoint returns in-flight status when user has tier-2 jobs pending/leased | api | `uv run pytest tests/test_imports.py` | ⬜ pending |
| `_claim_tier3_derived` ORDER BY refinement (active-users-first, needs-eval before PV-backfill) | QUEUE-04 | Claim order respects `users.last_activity DESC` + `lichess_evals_at` last | unit | `uv run pytest tests/test_eval_queue_service.py` | ⬜ pending |
| Tier-1 user-facing endpoint (auth-gated, guest-excluded) | EVUX-01 | Authenticated non-guest can enqueue; guest gets upsell, not job | api | `uv run pytest tests/test_imports.py` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_eval_queue_service.py` — ensure fixtures cover tier-2 window + guest + tier-3 ordering (extend if present)
- [ ] `tests/test_game_repository.py` — fixture with mixed lichess-eval + engine-analyzed + unanalyzed games for `count_is_analyzed_games`
- [ ] `tests/test_imports.py` — extend eval-coverage tests for in-flight counts + analyzed_count

*Existing pytest infrastructure (per-run-DB isolation) covers all phase requirements — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Coverage badge + CTA render with real "N of M analyzed" copy | EVUX-02 | Visual/copy assertion across Library flaw surfaces | Import games, open Library flaw panel, confirm badge shows real counts + CTA below threshold |
| In-flight "K in progress" updates without page refresh | EVUX-03 | Polling/render behavior in browser | Trigger analyze-more, watch badge climb without reload |
| Guest sees "Sign up to unlock" in place of analyze affordances | ROADMAP-118 #5 | Auth-gated UX, browser-only | As guest, confirm upsell CTA replaces both per-game + bulk buttons |
| Per-game "Analyze this game" hidden for lichess-eval games | EVUX-01 (D-118-07) | Conditional visibility rule | Open a lichess-eval analyzed game modal, confirm no analyze button |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
