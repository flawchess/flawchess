---
phase: 105
slug: mistake-detection-classification-tagging-service-on-the-fly
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-05
---

# Phase 105 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Seeded from 105-RESEARCH.md "Validation Architecture"; per-task IDs are filled in once the planner emits PLAN.md files.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (async via pytest-asyncio) |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/services/test_mistakes_service.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | ~3 s quick / ~20 s full |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/services/test_mistakes_service.py -x`
- **After every plan wave:** Run `uv run pytest -n auto -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~3 seconds (single-file quick run)

---

## Per-Task Verification Map

> Requirement-level seed from research; planner refines into per-task rows (105-NN-NN). This phase is pure backend logic — every requirement has an automated unit test; no manual-only behaviors.

| Behavior | Requirement | Threat Ref | Test Type | Automated Command | File Exists | Status |
|----------|-------------|------------|-----------|-------------------|-------------|--------|
| Severity from cp drop at halved thresholds (0.05/0.10/0.15) | LIBG-02 | — | unit | `pytest tests/services/test_mistakes_service.py::test_severity_thresholds -x` | ❌ W0 | ⬜ pending |
| Mate Option B maps ±1000 cp before sigmoid (not 1.0/0.0) | LIBG-02 | — | unit | `...::test_mate_option_b -x` | ❌ W0 | ⬜ pending |
| chess.com game → explicit "no analysis" result | LIBG-02 | — | unit | `...::test_no_analysis_chess_com -x` | ❌ W0 | ⬜ pending |
| <90% eval coverage → "no analysis" result | LIBG-02 | — | unit | `...::test_eval_coverage_gate -x` | ❌ W0 | ⬜ pending |
| ≥90% eval coverage → flaws list | LIBG-02 | — | unit | `...::test_analyzed_game -x` | ❌ W0 | ⬜ pending |
| `miss` tag when preceding opponent move was M/B | LIBG-06 | — | unit | `...::test_tag_miss -x` | ❌ W0 | ⬜ pending |
| `unpunished` tag when following opponent move didn't recover | LIBG-06 | — | unit | `...::test_tag_unpunished -x` | ❌ W0 | ⬜ pending |
| `from-winning` tag when ES_before ≥ 0.85 | LIBG-06 | — | unit | `...::test_tag_from_winning -x` | ❌ W0 | ⬜ pending |
| `result-changing` tag when flaw crossed the result boundary | LIBG-06 | — | unit | `...::test_tag_result_changing -x` | ❌ W0 | ⬜ pending |
| Exactly one tempo tag per flaw (time-pressure/hasty/knowledge-gap) | LIBG-06 | — | unit | `...::test_tempo_exclusive -x` | ❌ W0 | ⬜ pending |
| `phase` tag maps `positions[N].phase` | LIBG-06 | — | unit | `...::test_phase_tag -x` | ❌ W0 | ⬜ pending |
| Flaw object (TypedDict) has all required fields | LIBG-07 | — | unit | `...::test_flaw_record_shape -x` | ❌ W0 | ⬜ pending |
| FEN recomputed per ply via `board_fen()` | LIBG-07 | — | unit | `...::test_fen_recomputed -x` | ❌ W0 | ⬜ pending |
| Derived counts close (≤2) to Lichess oracle columns | LIBG-02/07 | — | sanity | `...::test_oracle_closeness -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_mistakes_service.py` — covers all LIBG-02 / 06 / 07 behaviors above (stubs + fixtures)
- [ ] DB-backed test for ordered per-ply position fetch (ply ordering correctness)

*No framework install needed — pytest + pytest-asyncio already in the project.*

---

## Manual-Only Verifications

*None — all phase behaviors have automated unit verification (pure backend math/derivation, no UI, no external surface).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
