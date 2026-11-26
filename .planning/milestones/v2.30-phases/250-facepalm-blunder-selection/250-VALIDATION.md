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

| Task | Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|------|-------------|----------|-----------|-------------------|-------------|--------|
| 250-01-T1, T2 | D-02 | Line facts match the reference on #13, #35, #153, #154, #156, #165, #170, #176, #177, #184 at depths 1 to 9 | unit | `uv run pytest tests/services/test_line_material.py -x` | ❌ W0 (created in 250-01) | ⬜ pending |
| 250-01-T2 | D-02 | Mate fixtures (#34, #108, #116, #162, #168, #181, #182): mate ply is 1 | unit | same | ❌ W0 | ⬜ pending |
| 250-01-T2 | D-05 | NULL rules: no line, illegal first token, malformed UCI, short quiet line give NULL; credit and mate settle | unit | same | ❌ W0 | ⬜ pending |
| 250-01-T1 | D-05 | New columns exist, migration metadata-only, round trip of line facts through game_flaws | DB + schema | `uv run alembic upgrade head && uv run alembic check` | ❌ W0 | ⬜ pending |
| 250-01-T3 | D-01 / D-04 | Score formula, NULL propagation, cap, mate value; Python and SQL versions agree | unit + DB | `uv run pytest tests/services/test_facepalm_score.py -x` | ❌ W0 (created in 250-01) | ⬜ pending |
| 250-04-T1 | D-01 | Window 14 (game 2099808 ply 23) scores below `FACEPALM_SCORE_MIN` with the shipped model | unit | same | ❌ W0 | ⬜ pending |
| 250-02-T1, T2 | fit | The fit recovers known coefficients on synthetic data; deterministic folds; Form B, clip choice, separation failure | unit | `uv run pytest tests/scripts/test_fit_facepalm.py tests/scripts/test_facepalm_features.py -x` | ❌ W0 (created in 250-02) | ⬜ pending |
| 250-04-T1 | D-01 / D-04 | Shipped constants reproduce from the committed TSV | CLI | `uv run python scripts/blunder_check/fit_facepalm.py --features <TSV> --out temp/blunder-check/fit-check.md --check-constants` | ❌ W0 | ⬜ pending |
| 250-05-T1, T2 | D-07 | Hook: spread from the post-blunder policy, also when the reply is unusable; line facts from the ply+1 line; non-user rows NULL | DB | `uv run pytest tests/services/test_maia_flaw_scoring.py -x` | extend | ⬜ pending |
| 250-05-T2 | D-07 | A line change between read and write is detected by the fingerprint | DB | same | extend | ⬜ pending |
| 250-05-T2 | reclassify | Survivors keep the new values, new plies NULL, all four stamps cleared | DB | `uv run pytest tests/services/test_maia_flaw_scoring.py -k reclassify -x` | extend | ⬜ pending |
| 250-07-T1, T2 | D-08 / D-18 | Spread mode selector and stamps; line mode with a cutoff re-runs over valued rows and runs without Maia | DB | `uv run pytest tests/scripts/test_backfill_maia_flaws.py -x` | extend | ⬜ pending |
| 250-03-T1, T2 | D-09 | Candidate passes at the threshold, fails just below, NULL excluded; SQL loader filters | unit + DB | `uv run pytest tests/services/test_blunder_check_candidates.py tests/repositories/test_blunder_check_repository.py -x` | rewrite | ⬜ pending |
| 250-03-T2 | D-17 | A false alarm before the blunder does not make the blunder eligible again | DB | `uv run pytest tests/services/test_blunder_check_selection.py tests/routers/test_blunder_check_drill.py -x` | invert | ⬜ pending |
| 250-06-T1 | D-12 | Seeded draws: source shares about one third each; herring origin follows the own / foreign ratio | unit | `uv run pytest tests/services/test_blunder_check_rules.py -x` | extend | ⬜ pending |
| 250-06-T1 | D-15 / D-16 | No analysed games gives foreign blunders and foreign herrings; own slots fall back to foreign | DB | `uv run pytest tests/services/test_blunder_check_selection.py -x` | rewrite | ⬜ pending |
| 250-06-T2 | D-13 | Foreign games outside +-150 are never selected | DB | same | rewrite | ⬜ pending |
| 250-06-T2 | D-14 | Level = most-played time control; bot and unrated games ignored; fallback chain | unit + DB | same file + `tests/repositories/test_blunder_check_repository.py` | ❌ W0 | ⬜ pending |
| 250-08-T1, T2 | D-10 | Report sections render from a cache; facepalm section, own / foreign supply | unit | `uv run pytest tests/scripts/test_blunder_check_calibration.py -x` | rewrite | ⬜ pending |
| 250-08-T3 | gate | Full pre-merge gate, parallel and serial | full | `uv run pytest -n auto -x` (plus the CLAUDE.md gate list) | — | ⬜ pending |
| 250-11-T1, T2 | D-11 | No reader of the dropped columns left; migration up and down | grep + schema | `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head && uv run alembic check` | — | ⬜ pending |

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
