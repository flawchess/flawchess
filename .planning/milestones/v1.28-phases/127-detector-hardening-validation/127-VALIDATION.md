---
phase: 127
slug: detector-hardening-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-19
---

# Phase 127 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (existing) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| **Quick run command** | `uv run pytest tests/services/test_tactic_detector.py -x` |
| **Full suite command** | `uv run pytest -n auto` (excludes `tests/scripts/tagger` via `addopts --ignore`) |
| **Harness (slow, explicit path)** | `uv run pytest tests/scripts/tagger -v` |
| **Estimated runtime** | quick ~5s · full suite ~2–4 min · harness ~tens of seconds (hundreds of fixture rows) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/services/test_tactic_detector.py -x` (fast, catches 4-tuple signature regressions).
- **After every plan wave:** Run `uv run pytest -n auto -x` (full default suite; excludes tagger by design per D-14).
- **Before `/gsd-verify-work`:** Full default suite green **AND** `uv run pytest tests/scripts/tagger -v` green (explicit path overrides the `--ignore`).
- **Max feedback latency:** ~5s (quick) / ~4 min (full + harness).

---

## Per-Task Verification Map

| Req | Behavior | Test Type | Automated Command | File Exists |
|-----|----------|-----------|-------------------|-------------|
| SC#1 | Every detector returns depth (4-tuple contract) | unit | `uv run pytest tests/services/test_tactic_detector.py -x` | ✅ existing (needs update) |
| SC#1 | `tactic_depth` stored on `game_flaws` (NULL on pre-existing) | integration | dev re-backfill verification (D-13) | ❌ HUMAN-UAT |
| SC#2 | Precision ≥ floor per shipped motif | harness | `uv run pytest tests/scripts/tagger -v` | ❌ W0 |
| SC#2 | Recall printed per motif (non-blocking) | harness | same | ❌ W0 |
| SC#2/D-06 | Depth-vs-puzzle-`Rating` correlation reported | harness | same | ❌ W0 |
| SC#3 | Fork/pin precision improves after relevance gate | harness delta | same | ❌ W0 |
| SC#4 | No AGPL `cook.py` code in harness | code review | `grep -rn "cook" tests/scripts/tagger scripts/` (docstring records boundary) | manual |
| SC#5 | Self-labeled fixture circularity documented/superseded | doc | read harness + `test_tactic_detector.py` docstrings | manual |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/scripts/tagger/__init__.py` — directory creation (parallel to `tests/scripts/benchmarks/`)
- [ ] `tests/scripts/tagger/conftest.py` — fixture-loading helper (loads `fixtures/tagger/detector_fixture.csv`)
- [ ] `tests/scripts/tagger/test_detector_precision.py` — precision/recall + depth-vs-Rating harness
- [ ] `fixtures/tagger/detector_fixture.csv` — committed stratified CC0 puzzle sample (produced by the selector)
- [ ] `scripts/select_tagger_fixtures.py` — one-time re-runnable selector (reads full CC0 download, stratified sample)
- [ ] `pyproject.toml` `[tool.pytest.ini_options].addopts` — add second `--ignore=tests/scripts/tagger` **together** with the dir (D-14: no dangling ignore)

*The harness directory + the `--ignore=` entry MUST land together in the same phase (D-14).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `tactic_depth` populated after dev re-backfill | SC#1 | Requires running `scripts/backfill_flaws.py --db dev` over ~32.7k tagged flaws; not a unit test | Run dev re-backfill; query `game_flaws` for non-NULL `tactic_depth` count and spot-check fork/pin tags dropped vs prior |
| Precision floor value(s) finalized | SC#2/D-09 | Floor (~0.90 core) cannot be set until the first harness run measures baseline numbers | Sequence: build harness → measure → set floors → re-measure delta (D-09 LOW-confidence by design) |
| No AGPL porting | SC#4 | Boundary judgment, not assertable | Confirm only CC0 *data* used; harness docstring records the cook.py AGPL boundary |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (tagger dir + fixture + selector)
- [ ] No watch-mode flags
- [ ] Feedback latency < ~240s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
