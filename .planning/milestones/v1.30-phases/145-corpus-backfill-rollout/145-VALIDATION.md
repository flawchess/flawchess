---
phase: 145
slug: corpus-backfill-rollout
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-30
---

# Phase 145 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (async, per-run cloned PostgreSQL DB) |
| **Config file** | `pyproject.toml` + `tests/conftest.py` |
| **Quick run command** | `uv run pytest -n auto <relevant test file>` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | ~60–120 seconds (full backend suite) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -n auto <relevant test file>`
- **After every plan wave:** Run `uv run pytest -n auto -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD by planner | — | — | SHIP-01 / SHIP-02 | — | — | unit/integration | `uv run pytest -n auto ...` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Testable invariants surfaced by RESEARCH.md `## Validation Architecture` (planner refines into concrete test files):

- [ ] **D-06 sentinel tolerance** — `_classify_tactic_gated` treats `allowed_pv_lines == []` as "no gate-eligible line" (no suppression); the inverted assertion at `tests/test_flaws_service.py:2521` is updated.
- [ ] **Backfill idempotency** — the tier-4 lottery predicate (`allowed_pv_lines IS NULL`) stops matching a flaw once blobs (or the `[]` sentinel) are written; double-claim is write-idempotent.
- [ ] **Submit-path isolation** — the new token-keyed blob lease/submit path does not alter live `_apply_submit` eval ingest behavior.
- [ ] **`_apply_submit` gate gap** — remote-worker-submitted games get gated tags (the missing `blob_map` argument is supplied).
- [ ] **Uniform gate denoising** — gated retag reduces per-motif noise across engine + lichess sources.

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Prod corpus backfill drains to completion on the live fleet | SHIP-01 | Requires upgraded-worker deployment + prod fleet spare capacity; cannot run in CI | `checkpoint:human-verify` — observe `backfill_multipv.py --db prod` progress query reaching ~0 remaining flaws |
| Per-motif chip counts confirm noise reduction | SHIP-02 / SC3 | Requires before/after prod snapshots around the rollout | Run the SC3 report script `--db prod` before and after; compare committed `reports/` markdown |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
