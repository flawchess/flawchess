---
phase: 131
slug: tactic-precision-hardening-cook-alignment
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-22
---

# Phase 131 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-xdist (backend) |
| **Config file** | `pyproject.toml` (addopts `--ignore=tests/scripts/tagger/ --ignore=tests/scripts/benchmarks/`) |
| **Quick run command** | `uv run pytest tests/services/test_tactic_detector.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Precision harness (held-out TEST, D-11)** | `PYTHONPATH=. uv run python scripts/tactic_tagger_report.py --check-goals --eval-set test` |
| **CI precision-floor gate (dedicated step, not in -n auto)** | `uv run pytest tests/scripts/tagger/test_detector_precision.py` |
| **Estimated runtime** | quick ~15s · full suite ~2-3 min · harness ~1-2 min |

NOTE: the precision gate (`tests/scripts/tagger/`) is a DEDICATED CI step, default-excluded
from `uv run pytest -n auto` (Phase 127 D-14). Acceptance criteria that exercise it use the
explicit path.

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/services/test_tactic_detector.py -x` (~15s)
- **After every plan wave:** Run `uv run pytest -n auto -x` + `PYTHONPATH=. uv run python scripts/tactic_tagger_report.py --check-goals --eval-set test`
- **Before `/gsd-verify-work`:** Full suite green + `--check-goals --eval-set test` exits 0 (or every miss is a suppressed motif) + `tests/scripts/tagger/test_detector_precision.py` green
- **Max feedback latency:** ~15s (quick), ~2-3 min (wave)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Decision | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|----------|------------|-----------------|-----------|-------------------|-------------|--------|
| 131-01-01 | 01 | 1 | D-08 | T-131-01 | N/A (data-integrity) | unit | `uv run pytest tests/services/test_tactic_detector.py -x` | ✅ | ⬜ pending |
| 131-01-02 | 01 | 1 | D-05/D-06/D-07 | T-131-01 | N/A | unit | `uv run pytest tests/services/test_tactic_detector.py::test_depth_primary_dispatch -x` | ❌ W0 | ⬜ pending |
| 131-01-03 | 01 | 1 | D-11 | T-131-01 | N/A | harness | `PYTHONPATH=. uv run python scripts/tactic_tagger_report.py --check-goals --eval-set test` | ✅ | ⬜ pending |
| 131-02-01 | 02 | 2 | D-09 (skewer/disc-attack) | T-131-03 | N/A | harness | `PYTHONPATH=. uv run python scripts/tactic_tagger_report.py --check-goals --eval-set test` | ✅ | ⬜ pending |
| 131-02-02 | 02 | 2 | D-09 (fork/pin) | T-131-03 | N/A | harness | same | ✅ | ⬜ pending |
| 131-02-03 | 02 | 2 | D-02/D-11 | T-131-03 | N/A | floor gate | `uv run pytest tests/scripts/tagger/test_detector_precision.py` | ✅ | ⬜ pending |
| 131-03-01 | 03 | 3 | D-09 (back-rank) | T-131-04 | N/A | harness | `PYTHONPATH=. uv run python scripts/tactic_tagger_report.py --check-goals --eval-set test` | ✅ | ⬜ pending |
| 131-03-02 | 03 | 3 | D-09 (anastasia/hook) | T-131-04 | N/A | harness | same | ✅ | ⬜ pending |
| 131-03-03 | 03 | 3 | D-09 (regression lock) | T-131-04 | N/A | floor gate | `uv run pytest tests/scripts/tagger/test_detector_precision.py` | ✅ | ⬜ pending |
| 131-04-01 | 04 | 2 | D-03/D-04 | T-131-05 | guarded parse (V5) | unit (RED) | `uv run pytest tests/services/test_tactic_detector.py::test_missed_dest_sq_gate tests/services/test_tactic_detector.py::test_missed_no_suppression -x` | ❌ W0 | ⬜ pending |
| 131-04-02 | 04 | 2 | D-03 | T-131-05/06 | try/except guard | unit (GREEN) | same | ✅ (after 04-01) | ⬜ pending |
| 131-05-01 | 05 | 4 | D-11 | T-131-07 | N/A | gate + suite | `PYTHONPATH=. uv run python scripts/tactic_tagger_report.py --check-goals --eval-set test` + `uv run pytest -n auto -x` | ✅ | ⬜ pending |
| 131-05-02 | 05 | 4 | D-12 | T-131-07/08 | dev-only write | script + human | `uv run python scripts/backfill_flaws.py --db dev --dry-run` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_tactic_detector.py` — add `test_depth_primary_dispatch` (plan 01, D-05 sort-key proof)
- [ ] `tests/services/test_tactic_detector.py` — add `test_missed_dest_sq_gate` + `test_missed_no_suppression` (plan 04, Workstream B fixtures, D-04 — written RED first)
- [ ] `scripts/tactic_tagger_report.py` GOALS — raise precision to 0.90 for fork/skewer/pin/discovered-attack/back-rank-mate/anastasia-mate/hook-mate (plan 01)
- [ ] `tests/scripts/tagger/precision_floors.py` — update PRECISION_FLOOR/SUPPRESSED_MOTIFS after measurement (plans 02/03); lock discovered-check ≥0.85

All other infrastructure (the CC0 fixture, the deterministic TRAIN/TEST split, the harness,
the floor-gate test, the backfill script) already exists — no framework install needed.

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| Corrected missed-side hanging-piece/fork tags on real data | D-04 / D-12 | The CC0 puzzle fixture cannot express "the move the player played"; Workstream B is only observable on real flaw rows | After the plan-05 `--db dev` backfill, query a sample of recomputed missed-side hanging-piece/fork rows (flawchess-db MCP) and confirm previously-wrong chips are corrected/dropped; record the before/after tag-count delta |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (`test_depth_primary_dispatch`, Workstream B fixtures, GOALS raise)
- [x] No watch-mode flags
- [x] Feedback latency < ~15s (quick) / ~3 min (wave)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
