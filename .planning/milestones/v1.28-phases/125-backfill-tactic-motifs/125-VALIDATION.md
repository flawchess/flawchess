---
phase: 125
slug: backfill-tactic-motifs
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-18
---

# Phase 125 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-xdist (per-run DB isolation, see `tests/conftest.py`) |
| **Config file** | `pyproject.toml` (addopts + markers) |
| **Quick run command** | `uv run pytest tests/test_backfill_flaws.py -q` |
| **Full suite command** | `uv run pytest -n auto` |
| **Estimated runtime** | quick ~10–20s · full suite ~minutes |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_backfill_flaws.py -q`
- **After every plan wave:** Run `uv run pytest -n auto`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~20 seconds (quick run)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 125-W0-01 | 01 | 0 | TACSCH-03 | — / — | N/A | integration | `uv run pytest tests/test_backfill_flaws.py -q` | ✅ (extend existing) | ⬜ pending |
| 125-cov-01 | 01 | 1 | TACSCH-03 | — / — | N/A | integration/SQL | `uv run python scripts/coverage_report_tactic_motifs.py --db dev` | ❌ W0 | ⬜ pending |
| 125-idem-01 | 01 | 1 | TACSCH-03 | — / — | N/A | integration | `uv run pytest tests/test_backfill_flaws.py::test_idempotent -q` (existing, confirm) | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_backfill_flaws.py` — **extend** the existing Phase 108 suite with one test that seeds a `GamePosition` with a real `pv` at `flaw_ply + 1`, runs `run_backfill` (inject `session_maker`, line ~119), and asserts the resulting `GameFlaw` row has `tactic_motif IS NOT NULL` when the PV fires a detector, and `tactic_motif IS NULL` when no PV is present (no-PV bucket). One test covers both paths. The existing dry-run / real-run / idempotency tests stay green.

*The framework and DB-isolation harness already exist; Wave 0 is a single test extension, not a framework install.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dev backfill run produces honest coverage (D-04) | TACSCH-03 / SC#1 | Operates on the live dev DB (~11.2k full-eval'd games), not a test fixture | Run `backfill_flaws.py --db dev --full-evald-only` (smoke with `--dry-run`/`--limit` first), then `coverage_report_tactic_motifs.py --db dev`; confirm overall %, by-motif counts, and the NULL split (no-PV vs PV-but-no-fire), and spot-check a sample per NULL bucket |
| Prod backfill execution | TACSCH-03 / SC#1 | Deferred (D-01) — outside this phase's completion gate; runbook only | Documented runbook delivered this phase; prod run is a later operational step |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
