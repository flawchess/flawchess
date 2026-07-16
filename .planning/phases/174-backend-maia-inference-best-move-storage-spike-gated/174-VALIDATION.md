---
phase: 174
slug: backend-maia-inference-best-move-storage-spike-gated
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-16
---

# Phase 174 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (per-run DB clone, `-n auto` local) |
| **Config file** | `pyproject.toml` / `tests/conftest.py` |
| **Quick run command** | `uv run pytest tests/test_maia_parity.py tests/test_game_best_moves.py` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | ~90 seconds (quick), ~4 min (full parallel) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command for the touched area
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green + parity gate green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

*Requirement column matches each PLAN.md `requirements` frontmatter.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 174-01-* | 01 | 1 | GEMS-04 | — | Python port tier-matches client within epsilon (THE GATE) | parity/unit | `uv run pytest tests/services/test_maia_encoding.py` + `scripts/maia_parity_spike.py` | ❌ W0 | ⬜ pending |
| 174-02-* | 02 | 2 | GEMS-06 | — | worker image dep-set lacks onnxruntime/numpy | integration | `uv run pytest tests/test_dependency_isolation.py` | ❌ W0 | ⬜ pending |
| 174-03-* | 03 | 2 | GEMS-01 | T-174-05 | table + migration round-trips, composite PK (game_id, ply), FK CASCADE | unit/migration | `uv run pytest tests/models/test_game_best_move.py` | ❌ W0 | ⬜ pending |
| 174-04-* | 04 | 2 | GEMS-02, GEMS-03, GEMS-05, GEMS-07 | — | candidate gate + ELO clamp + query-time reclassification (constants-only) | unit | `uv run pytest tests/services/test_maia_engine.py tests/services/test_best_move_candidates.py` | ❌ W0 | ⬜ pending |
| 174-05-* | 05 | 3 | GEMS-03 | — | eval-apply integration + Pitfall-1 MultiPV-2 fallback; RSS-vs-OOM measurement | integration | `uv run pytest tests/services/test_eval_apply_best_moves.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_maia_parity.py` — parity spike fixtures + tier-stability assertions (GEMS-04, the gate)
- [ ] `tests/fixtures/maia_parity/` — FEN + pinned ELO + expected client `maia_prob` per ply
- [ ] `tests/test_game_best_moves_model.py` — model + migration stubs (GEMS-01)
- [ ] `tests/test_dependency_isolation.py` — worker-image dep-set assertion (GEMS-06)
- [ ] `onnxruntime==1.20.1` + `numpy` in the new isolated uv group (pinned per Pitfall 2)

*The parity fixtures (Wave 0) are the literal spike gate — no downstream work proceeds until they pass (D-02).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Steady-state backend RSS vs OOM history | GEMS-03 (D-03b) | Requires running backend + measuring container RSS against prod OOM budget | Boot backend with maia session eager-loaded; `docker stats` backend RSS; compare to 4GB container budget + Stockfish pool residency |
| Live-board gem vs stored-DB gem agreement | GEMS-05 (D-04) | Cross-stack (frontend board render vs backend row) visual check for the same position/rating | Analyze a game with a known gem; confirm board marker matches stored `maia_prob` tier |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
