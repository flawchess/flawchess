---
phase: 178
slug: lichess-compatible-accuracy-acpl-computed-columns
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-18
---

# Phase 178 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (async, per-run DB isolation) |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `uv run pytest tests/test_accuracy_acpl.py` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | ~5s quick / ~2–4 min full |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the touched module
- **After every plan wave:** Run `uv run pytest -n auto -x`
- **Before `/gsd-verify-work`:** Full suite + `uv run ty check app/ tests/` must be green
- **Max feedback latency:** ~5 seconds (quick), ~4 min (full)

---

## Per-Task Verification Map

> Filled by the planner against the final task IDs. Requirements are TBD for this phase
> (no REQ-IDs mapped); verification anchors to the locked decisions D-01..D-11 and the
> primary correctness signal (computed ACPL vs `*_acpl_imported` on lichess games).

| Task ID | Plan | Wave | Decision Ref | Threat Ref | Expected Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|--------------|------------|-------------------|-----------|-------------------|-------------|--------|
| 178-02-01 | 02 | 1 | D-08..D-11 | T-178-02-T | Pure formula module (win%/accuracy/windowed/ACPL) with named constants + correct sign/shift/parity | unit | `uv run ty check app/` + module import smoke | ❌ W0 | ⬜ pending |
| 178-02-02 | 02 | 1 | D-07..D-11 | T-178-02-T | Formula port reproduces game 296343 ACPL exactly (18/61) + accuracy within ±1 + hole/edge cases | unit | `uv run pytest tests/services/test_accuracy_acpl.py -x` | ❌ W0 | ⬜ pending |
| 178-01-01 | 01 | 1 | D-03 | T-178-01-D | Migration adds `*_imported`, copies values, NULLs canonical; reversible | migration | `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` | ✅ | ⬜ pending |
| 178-01-02 | 01 | 1 | D-01/D-04 | T-178-01-I | Model exposes `*_imported`; oracle severity columns untouched; ty clean | unit | `uv run ty check app/` | ✅ | ⬜ pending |
| 178-01-03 | 01 | 1 | D-02/D-03 | T-178-01-D | Down-migration round-trip proves copy-before-null: downgrade restores canonical=84/61 from `*_imported`, re-upgrade nulls canonical + preserves `*_imported` (copy-after-null bug must fail); `*_imported` readable; canonical NULL by default | migration/integration | `uv run pytest -k migration_178 -x` | ❌ W0 | ⬜ pending |
| 178-03-01 | 03 | 2 | D-01/D-03 | T-178-03-T | Live hook fills canonical columns atomically on full-eval completion via the single seam | integration | `uv run pytest tests/services/test_full_eval_drain.py -x` | ✅ | ⬜ pending |
| 178-03-02 | 03 | 2 | D-03 | T-178-03-I | Complete-sequence gate: holed game leaves canonical NULL while stamp is set | integration | `uv run pytest tests/services/test_full_eval_drain.py -k accuracy -x` | ✅ | ⬜ pending |
| 178-04-01 | 04 | 2 | D-06 | T-178-04-E | Backfill calls the shared compute (no duplicated formula), batched, `--db`/`--dry-run`/`--limit` | integration | `uv run python scripts/backfill_accuracy_acpl.py --db dev --dry-run --limit 5` | ❌ W0 | ⬜ pending |
| 178-04-02 | 04 | 2 | D-06 | T-178-04-E | Backfill fills canonical columns for a seeded analyzed game; holed game stays NULL | integration | `uv run pytest tests/services/test_backfill_accuracy_acpl.py -x` | ❌ W0 | ⬜ pending |
| 178-04-03 | 04 | 2 | D-07 | T-178-04-T | Validation script compares computed vs `*_imported` (primary ACPL, secondary accuracy) | manual | `uv run python scripts/validate_accuracy_acpl.py --db dev` (operator, not gated) | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/test_accuracy_acpl.py` — hand-checked fixture unit tests (win%, per-move accuracy, windowed game-level, ACPL) against a known lichess game's published values (D-07)
- [ ] Fixture: a real lichess game's per-ply eval sequence + published accuracy/ACPL (research verified game 296343 reproduces imported ACPL exactly)

*Existing pytest infrastructure (per-run DB isolation, async fixtures) covers integration/migration testing — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cross-DB validation script output (computed vs `*_imported` distribution) | D-07 | Statistical comparison over the whole DB, not a pass/fail assertion | Run `scripts/backfill_accuracy_acpl.py` on dev then the validation script; inspect ACPL delta distribution vs `*_acpl_imported` on lichess games (should track closely) |
| Prod backfill (~718k games) | D-06 | Operator step, NOT gated on phase completion | Post-deploy: `scripts/backfill_accuracy_acpl.py --db prod` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers the formula-port fixture
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s (quick)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
