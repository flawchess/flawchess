---
phase: 147
slug: persist-only-forcing-line-gated-tactic-tags-suppress-ungated
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-01
---

# Phase 147 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend, async) |
| **Config file** | pyproject.toml / tests/conftest.py (per-run cloned DB from migrated template) |
| **Quick run command** | `uv run pytest tests/<targeted_test>.py` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | ~120s (full suite, parallel) |

---

## Sampling Rate

- **After every task commit:** Run the targeted test file(s) for that task
- **After every plan wave:** Run `uv run pytest -n auto -x`
- **Before `/gsd-verify-work`:** Full suite + `uv run ty check app/ tests/` must be green
- **Max feedback latency:** ~120 seconds

---

## Per-Task Verification Map

*Populated by the planner from PLAN.md tasks. See RESEARCH.md `## Validation Architecture` for the coverage design. Migration must be verified against seeded dev rows covering every carve-out case (cp-based suppress, mate-adjacent keep, `[]`-sentinel keep) plus an idempotency re-run assertion.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | — | — | SEED-074 | — | N/A | unit/integration/migration | `uv run pytest ...` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Migration test file — asserts the guarded UPDATE suppresses exactly the cp-based candidate rows, preserves mate-adjacent (`pre_flaw_eval_cp IS NULL`) and D-06 `[]`-sentinel rows, and is idempotent on re-run
- [ ] Part A threading tests — assert `_classify_tactic_gated` returns NULL under `blobs_pending` for cp-based motifs with no blob, and raw motif is kept for mate-adjacent / `[]`-sentinel cases
- [ ] Part B endpoint + atomic-write integration test — new lease/submit pair, server re-classify with worker blobs, single-transaction write of flaws + gated tags + both completion markers

*Existing per-run-DB isolation infrastructure (tests/conftest.py) covers DB setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Upgraded fleet worker end-to-end against a live dev backend | SEED-074 (Part B) | Requires running `scripts/remote_eval_worker.py` against a dev server + Stockfish | Dev-first e2e gate: run worker against dev backend, confirm atomic write of gated tags + completion markers before any prod change |
| Prod candidate row-count sizing for migration batch size | SEED-074 (Part A migration) | Needs `bin/prod_db_tunnel.sh` + prod-db read-only MCP | Run the RESEARCH.md candidate-count query against prod before finalizing chunk size |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
