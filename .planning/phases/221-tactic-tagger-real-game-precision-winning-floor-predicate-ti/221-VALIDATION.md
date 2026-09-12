---
phase: "221"
slug: "tactic-tagger-real-game-precision-winning-floor-predicate-ti"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-12"
---

# Phase 221 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `221-RESEARCH.md` § Validation Architecture (measured 2026-09-12).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`asyncio_mode = "auto"`), `pyproject.toml` `[tool.pytest.ini_options]` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/services/test_forcing_line_gate.py tests/services/test_tactic_detector.py -q` |
| **Fixture gate command** | `uv run pytest tests/scripts/tagger -q` (~10 s; NOT in the default run — `pyproject.toml` `--ignore=tests/scripts/tagger`) |
| **Full suite command** | `uv run pytest -n auto -x && uv run pytest tests/scripts/tagger -q` |
| **Static gates** | `uv run ruff check . --fix && uv run ruff format app/ tests/ scripts/ analysis/ && uv run ty check app/ tests/ scripts/ && uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200` |
| **Frontend (clearance-suppression leg only)** | `cd frontend && npm run lint && npm test -- --run && npm run build` |
| **Estimated runtime** | quick ~5 s · fixture gate ~10 s · full suite ~3–4 min |

---

## Sampling Rate

- **After every task commit:** Run the unit file(s) the task touched (`test_forcing_line_gate.py` / `test_tactic_detector.py` / `test_flaws_service.py` / `test_retag_flaws.py`).
- **After every detector-touching task:** Run `uv run pytest tests/scripts/tagger -q` — non-negotiable, the default suite excludes it.
- **After every plan wave:** Run `uv run pytest -n auto -x && uv run pytest tests/scripts/tagger -q` plus the static gates.
- **Before `/gsd-verify-work`:** Full CLAUDE.md pre-merge gate plus the tagger gate, plus the frontend leg if clearance was suppressed.
- **Max feedback latency:** 15 seconds (unit + fixture gate)

---

## Per-Task Verification Map

Task IDs are filled in by the planner; the requirement → test binding below is the contract each task must honour.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | TAGFIX-01 | — | N/A | unit | `uv run pytest tests/services/test_forcing_line_gate.py -q` (new `TestWinningFloorAtFiring`: reject <+200 tier-3, accept ≥+200, accept solver mate, 0-floor tier-2 at +50/−50, odd depth rounds up, `bm` before `b`, `None` motif skips floor) | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | TAGFIX-01 (D-03) | — | N/A | unit | `uv run pytest tests/services/test_flaws_service.py -q` (extend `TestClassifyTacticGated`: blob `None` + `positions[n]`/`positions[n-1]` fallback; nothing suppressed merely for lacking a blob) | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | TAGFIX-02 | — | N/A | unit | `uv run pytest tests/services/test_flaws_service.py -q` (`pre_flaw_eval_cp=None` + solver mate → reject non-mate motif; mate motif credited; no mate → blob gate still runs; 4 existing `blobs_pending` tests unmodified and green) | ⚠ extend | ⬜ pending |
| TBD | TBD | TBD | TAGFIX-03 | — | N/A | unit + harness | `uv run pytest tests/services/test_tactic_detector.py -q && uv run pytest tests/scripts/tagger -q` (persistence on `boards[k+3]`, line-ends fires, k=6 no fire, both orientations; sacrifice floor still met) | ⚠ extend | ⬜ pending |
| TBD | TBD | TBD | TAGFIX-04 | — | N/A | unit + harness | `uv run pytest tests/services/test_tactic_detector.py -q && uv run pytest tests/scripts/tagger -q && uv run pytest tests/services/test_tactic_comparison_service.py -q` (CONTEXT worked examples as fixtures; real-share ≥ 0.8 or 4 suppression assertions) | ⚠ extend / ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | TAGFIX-05 | — | N/A | harness + unit | `uv run pytest tests/scripts/tagger -q && uv run pytest tests/services/test_tactic_detector.py -q` (7 fixes; flipped WR-02 fixture re-labelled; `14 not in _TIER3_REGISTRY` assertion) | ✅ / ❌ one-liner | ⬜ pending |
| TBD | TBD | TBD | TAGFIX-05 (SC1) | — | N/A | analysis script | `uv run python scripts/research/oracle_compare.py` (manual; needs the local lichess-puzzler clone) | ✅ (to move) | ⬜ pending |
| TBD | TBD | TBD | TAGFIX-06 | — | N/A | unit | `uv run pytest tests/services/test_flaws_service.py -q` (new `TestMissedOrientationParity`: one-move stack, intermezzo k=2 on missed, D-10 recapture → NULL, ply-0 / malformed-SAN fallback) | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | TAGFIX-07 | — | N/A | harness | `uv run pytest tests/scripts/tagger -q` (new `test_realgame_real_share_floor`; CSV loader in `conftest.py`; `REALGAME_REAL_SHARE_FLOOR` in `precision_floors.py`) | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | TAGFIX-08 | — | N/A | static + smoke | `uv run ruff check . && uv run ruff format --check scripts/ && uv run ty check scripts/`; each `scripts/research/*.py` exits 0 with the clone absent | ❌ new | ⬜ pending |
| TBD | TBD | TBD | TAGFIX-09 | — | N/A | unit | `uv run pytest tests/scripts/test_retag_flaws.py -q` (report has removed/survived/shifted; written on a non-dry run; `--db prod` docstring corrected) | ⚠ extend | ⬜ pending |
| TBD | TBD | TBD | TAGFIX-09 (acceptance) | — | N/A | operator SQL | §2.1 acceptance query through `bin/prod_db_tunnel.sh`; pasted into SUMMARY | ❌ manual | ⬜ pending |
| TBD | TBD | TBD | TAGFIX-09 (changelog) | — | N/A | doc | `grep -n "tactic" CHANGELOG.md` under `[Unreleased]` | ❌ new | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `fixtures/tagger/realgame_tags.csv` — sampled from prod **before** any detector edit (TAGFIX-07, D-13)
- [ ] `tests/scripts/tagger/conftest.py` — `realgame_fixture` session fixture + `RealGameRow` TypedDict loader (TAGFIX-07)
- [ ] `tests/scripts/tagger/precision_floors.py` — `REALGAME_REAL_SHARE_FLOOR` dict (TAGFIX-07)
- [ ] `tests/services/test_forcing_line_gate.py::TestWinningFloorAtFiring` — stubs for TAGFIX-01
- [ ] `tests/services/test_flaws_service.py::TestMissedOrientationParity` — stubs for TAGFIX-06
- [ ] No framework install needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ~20-row spot-check of Claude's real-game labels | TAGFIX-07 (D-13) | Human judgement on tactic reality | Operator reviews 20 stratified rows of `realgame_tags.csv`; disagreements recorded in SUMMARY |
| Oracle parity (0 cook-only for deflection/fork/trapped-piece, 0 ours-only for discovered-attack) | TAGFIX-05 (SC1) | Needs the local AGPL lichess-puzzler clone, not in CI | `uv run python scripts/research/oracle_compare.py`; paste the divergence table |
| Prod retag + acceptance queries (losing-share <5 %/motif, <2 % overall; sacrifice −1 OOM; missed intermezzo ≤3× allowed; zero motif 14) | TAGFIX-09 | Prod write via tunnel after deploy; dev has zero motif-14 rows | `bin/prod_db_tunnel.sh` then `uv run python scripts/retag_flaws.py --db prod`; run §2.1 SQL; paste into SUMMARY |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
