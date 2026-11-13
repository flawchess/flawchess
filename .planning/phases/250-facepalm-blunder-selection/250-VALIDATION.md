---
phase: "250"
slug: "facepalm-blunder-selection"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-13"
---

# Phase 250 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: 250-RESEARCH.md
> "Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (asyncio_mode auto), pytest-xdist |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]`; per-session cloned DB (`tests/conftest.py`) |
| **Quick run command** | `uv run pytest tests/services/test_blunder_check_candidates.py tests/services/test_blunder_check_rules.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Type / schema** | `uv run ty check app/ tests/ scripts/`; `uv run alembic upgrade head && uv run alembic check` |
| **Estimated runtime** | quick ~20 seconds, full suite a few minutes |

---

## Sampling Rate

- **After every task commit:** the quick run command plus the touched test file
- **After every plan wave:** `uv run pytest -n auto -x`, `uv run ty check app/ tests/ scripts/`,
  `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`
- **Before `/gsd-verify-work`:** the full pre-merge gate in CLAUDE.md must be green; a serial full suite before release
- **Max feedback latency:** 60 seconds for the per-task run

---

## Per-Task Verification Map

Task IDs are filled in by the planner. Requirement = CONTEXT decision.

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| D-02 | Line facts match the reference on #13, #35, #153, #154, #156, #165, #170, #176, #177, #184 at depths 1 to 9 | unit | `uv run pytest tests/services/test_line_material.py -x` | ❌ W0 | ⬜ pending |
| D-02 | Mate fixtures (#34, #108, #116, #162, #168, #181, #182): mate ply is 1 | unit | same | ❌ W0 | ⬜ pending |
| D-05 | NULL rules: no line, illegal first token, malformed UCI, short quiet line give NULL; credit and mate settle | unit | same | ❌ W0 | ⬜ pending |
| D-01 / D-04 | Score formula, NULL propagation, cap, mate value; Python and SQL versions agree | unit + DB | `uv run pytest tests/services/test_facepalm_score.py -x` | ❌ W0 | ⬜ pending |
| D-01 | Window 14 (game 2099808 ply 23) scores below `FACEPALM_SCORE_MIN` | unit | same | ❌ W0 | ⬜ pending |
| D-07 | Hook: spread from the post-blunder policy, also when the reply is unusable; line facts from the ply+1 line; non-user rows NULL | DB | `uv run pytest tests/services/test_maia_flaw_scoring.py -x` | extend | ⬜ pending |
| D-07 | A line change between read and write is detected by the fingerprint | DB | same | extend | ⬜ pending |
| D-08 / D-18 | Spread mode selector and stamps; line mode with a cutoff re-runs over valued rows and runs without Maia | DB | `uv run pytest tests/scripts/test_backfill_maia_flaws.py -x` | extend | ⬜ pending |
| reclassify | Survivors keep the new values, new plies NULL, new stamps cleared | DB | `uv run pytest tests/services/test_maia_flaw_scoring.py -k reclassify -x` | extend | ⬜ pending |
| D-09 | Candidate passes at the threshold, fails just below, NULL excluded; SQL loader filters | unit + DB | `uv run pytest tests/services/test_blunder_check_candidates.py tests/repositories/test_blunder_check_repository.py -x` | rewrite | ⬜ pending |
| D-12 | Seeded draws: source shares about one third each; herring origin follows the own / foreign ratio | unit | `uv run pytest tests/services/test_blunder_check_rules.py -x` | extend | ⬜ pending |
| D-13 | Foreign games outside +-150 are never selected | DB | `uv run pytest tests/services/test_blunder_check_selection.py -x` | rewrite | ⬜ pending |
| D-14 | Level = most-played time control; bot and unrated games ignored; fallback chain | unit + DB | same file + repository test | ❌ W0 | ⬜ pending |
| D-15 / D-16 | No analysed games gives foreign blunders and foreign herrings; own slots fall back to foreign | DB | same | rewrite | ⬜ pending |
| D-17 | A false alarm before the blunder does not make the blunder eligible again | DB | same | invert | ⬜ pending |
| D-10 | Report sections render from a cache; facepalm section, own / foreign supply | unit | `uv run pytest tests/scripts/test_blunder_check_calibration.py -x` | rewrite | ⬜ pending |
| D-11 | No reader of the dropped columns left; migration up and down | grep + `uv run alembic upgrade head && uv run alembic check` | — | ⬜ pending |
| fit | The fit recovers known coefficients on synthetic data; deterministic folds | unit | `uv run pytest tests/scripts/test_fit_facepalm.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_line_material.py` with a committed fixture module (full FEN, played UCI, line) for the ten
  D-02 positions and the mate positions, copied from the `temp/` caches
- [ ] `tests/services/test_facepalm_score.py` (formula, NULLs, SQL parity, Window 14)
- [ ] `tests/scripts/test_fit_facepalm.py` (synthetic recovery, determinism)
- [ ] D-14 resolver tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Prod backfill (spread pass and line pass) completes and coverage is as expected | D-08 | Long operator run on prod | Orchestrator runs it over the tunnel and reports row counts and NULL shares |
| Calibration and spot-check on prod with the new predicate | D-10 | Needs prod data and owner judgement | Run `scripts/blunder_check/` reports; owner reviews the spot-check |
| Refit on repaired lines and line-pass recompute | D-18 | Waits for the Phase 252 prod repair | Refit, update constants, re-run the line pass, compare pass rates |
| Column drop on prod | D-11 | One-way schema change, human-gated | After the new selection is checked on prod |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
