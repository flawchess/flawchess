---
phase: 221-tactic-tagger-real-game-precision-winning-floor-predicate-ti
plan: 01
subsystem: testing
tags: [tactic-tagger, precision-harness, real-game-gate, prod-sampling, agpl-boundary]

requires: []
provides:
  - fixtures/tagger/realgame_tags.csv — 164-row hand-labelled real-game tactic-tag
    sample, frozen before any TAGFIX-01..06 detector/gate change lands (D-13)
  - scripts/research/sample_realgame_tags.py — the reproducible (md5-hash) sampler
  - REALGAME_REAL_SHARE_FLOOR / REALGAME_MIN_ROWS_FOR_FLOOR in precision_floors.py
  - _compute_realgame_metrics / RealGameMotifStats scorer shared by the CI gate and
    scripts/tactic_tagger_report.py
  - scripts/research/{oracle_compare,dev_probe}.py under the project lint/type gates
affects: [221-04, 221-05, 221-06]

tech-stack:
  added: []
  patterns:
    - "read-only sampler with a stratified md5(game_id||ply) rank window (never
      random()) for reproducible before/after sampling"
    - "real-game scorer with surviving/real_surviving/suppressed buckets (no
      false-negative column — a suppressed incidental/wrong row is a win)"

key-files:
  created:
    - scripts/research/sample_realgame_tags.py
    - fixtures/tagger/realgame_tags.csv
  modified:
    - scripts/research/oracle_compare.py (relocated from reports/tactic-tagger/review-2026-09-12-scripts/)
    - scripts/research/dev_probe.py (relocated from reports/tactic-tagger/review-2026-09-12-scripts/)
    - tests/scripts/tagger/conftest.py
    - tests/scripts/tagger/test_detector_precision.py
    - tests/scripts/tagger/precision_floors.py
    - scripts/tactic_tagger_report.py

key-decisions:
  - "Stratification rates: PER_STRATUM_OVERSAMPLED=8, PER_STRATUM_CONTROL=2 (58 strata,
    landed at 164 rows — inside the plan's 120-200 acceptance bar and close to the
    ~150 target)."
  - "REALGAME_MIN_ROWS_FOR_FLOOR=8 exactly matches PER_STRATUM_OVERSAMPLED, so only
    the four oversampled motifs (16 surviving rows each, both orientations combined)
    clear the gating bar; every other motif (4 surviving rows) is reported but not
    gated."
  - "Real-game floors seeded ~0.05 below the wave-1 (pre-fix) measurement: sacrifice
    0.32, clearance 0.38, intermezzo 0.70, x-ray 0.82."

requirements-completed: [TAGFIX-07, TAGFIX-08]

coverage:
  - id: D1
    description: "fixtures/tagger/realgame_tags.csv committed, ~150 prod rows stratified by motif x orientation, sampled before any detector/gate edit, every row labelled real/incidental/wrong with a rationale"
    requirement: TAGFIX-07
    verification:
      - kind: unit
        ref: "tests/scripts/tagger/test_detector_precision.py#test_realgame_fixture_schema"
        status: pass
      - kind: unit
        ref: "tests/scripts/tagger/test_detector_precision.py#test_realgame_real_share_floor"
        status: pass
    human_judgment: true
    rationale: "Every label was determined by this executor (not the operator) from the position/SAN-line/eval alone; the plan requires an independent operator spot-check of ~20 rows (the <human-check> harvested to 221-UAT.md at end-of-phase) before the labels can be trusted for the prod retag gate."
  - id: D2
    description: "Real-game scorer (surviving/real_surviving/suppressed, no FN column) shared identically by the CI gate and scripts/tactic_tagger_report.py"
    requirement: TAGFIX-07
    verification:
      - kind: unit
        ref: "tests/scripts/tagger/test_detector_precision.py#test_realgame_real_share_floor"
        status: pass
      - kind: other
        ref: "PYTHONPATH=. uv run python scripts/tactic_tagger_report.py (byte-identical two-run diff)"
        status: pass
    human_judgment: false
  - id: D3
    description: "scripts/research/{oracle_compare,dev_probe,sample_realgame_tags}.py pass ruff check/format/ty and exit 0 with one line when the AGPL clone is absent"
    requirement: TAGFIX-08
    verification:
      - kind: other
        ref: "uv run ruff check . && uv run ruff format --check scripts/ && uv run ty check app/ tests/ scripts/"
        status: pass
      - kind: other
        ref: "oracle_compare.py run with the lichess-puzzler clone directory renamed away"
        status: pass
    human_judgment: false
  - id: D4
    description: "precision_floors.py documents the discoveredCheck/cook label caveat and the oracle-comparison + two disproved deviations"
    requirement: TAGFIX-08
    verification:
      - kind: other
        ref: "python -c check for 'oracle_compare'/'discoveredCheck'/'cook' in precision_floors.__doc__"
        status: pass
    human_judgment: false

actuals:
  tokens: 36423
  tasks: 3
  commits: 5
  plan_head_before: ae291404ec1e2b53629412f69e68ff7c6d7d0fcf

duration: 4h 10min
completed: 2026-09-12
status: complete
---

# Phase 221 Plan 01: Real-Game Tactic-Tag Gate — Sample, Label, Score, Floor Summary

**Froze a 164-row hand-labelled real-game tactic-tag sample from prod (before any detector edit), scored it with a shared surviving/real_surviving/suppressed harness next to the puzzle-fixture gate, and seeded never-regress floors — pre-fix real-share measured at sacrifice 0.375, clearance 0.4375, intermezzo 0.750, x-ray 0.875.**

## Performance

- **Duration:** ~4h 10min
- **Started:** 2026-09-12T14:35Z (execute-phase dispatch)
- **Completed:** 2026-09-12T18:48Z
- **Tasks:** 3 completed
- **Files modified:** 11 (2 new, 9 modified/relocated)

## Accomplishments

- Relocated `oracle_compare.py` / `dev_probe.py` from a `reports/` scratch directory into `scripts/research/` (git-mv, history preserved) and brought both under the project's `ruff check`/`ruff format`/`ty check` gates — the measured pre-fix baseline was 39 ruff findings + 2 ty diagnostics (RESEARCH.md), now 0.
- New `scripts/research/sample_realgame_tags.py`: read-only, one connection, stratified by `(motif, orientation)` via `md5(game_id::text || ply::text)` rank windows (never `random()`), oversampling sacrifice/clearance/intermezzo/x-ray at 8 rows/stratum and every other tagged motif at 2 rows/stratum. Achieved 164 rows across all 58 strata (29 motifs × 2 orientations) — see the per-stratum table below.
- `fixtures/tagger/realgame_tags.csv` committed and frozen (D-13) before this plan touched any detector/gate code; every row hand-labelled `real`/`incidental`/`wrong` with a one-clause rationale written from the position, SAN line and frozen `eval_at_firing` alone (no `wrong` labels used; 133 real, 31 incidental).
- `tests/scripts/tagger/conftest.py` gained `RealGameRow`/`RealGameLabel`, `_load_realgame()`, `build_realgame_board()` (post-D-09 production board build — both orientations push a move) and the `realgame_fixture` pytest fixture.
- `tests/scripts/tagger/test_detector_precision.py` gained `RealGameMotifStats` / `_compute_realgame_metrics` (surviving/real_surviving/suppressed — no false-negative column, since a suppressed incidental/wrong row is a win, not a miss), `test_realgame_fixture_schema`, and `test_realgame_real_share_floor` (prints the per-motif table, proves the no-double-count invariant, and now gates on `REALGAME_REAL_SHARE_FLOOR`).
- `scripts/tactic_tagger_report.py` imports the SAME scorer (never duplicates it) and splices a "Real-Game Gate" section into the report, byte-identical across two runs.
- `tests/scripts/tagger/precision_floors.py` seeded `REALGAME_REAL_SHARE_FLOOR` (sacrifice 0.32, clearance 0.38, intermezzo 0.70, x-ray 0.82) + `REALGAME_MIN_ROWS_FOR_FLOOR = 8`, and gained two new module-docstring paragraphs (real-game floors are orthogonal to `PRECISION_FLOOR`; `discoveredCheck` labels are not cook output, plus the oracle-comparison record and the two disproved "precision-first" deviations it must prevent from recurring).
- No file under `app/` was touched at any point in this plan (`git diff --name-only app/` is empty across all three commits).

## Achieved sample: 164 rows across 58 strata

```
allowed anastasia-mate 2   allowed arabian-mate 2   allowed attraction 2
allowed back-rank-mate 2   allowed boden-mate 2     allowed capturing-defender 2
allowed clearance 8        allowed deflection 2     allowed discovered-attack 2
allowed discovered-check 2 allowed double-bishop-mate 2  allowed double-check 2
allowed dovetail-mate 2    allowed en-passant 2     allowed fork 2
allowed hanging-piece 2    allowed hook-mate 2      allowed interference 2
allowed intermezzo 8       allowed mate 2           allowed pin 2
allowed promotion 2        allowed sacrifice 8      allowed self-interference 2
allowed skewer 2           allowed smothered-mate 2 allowed trapped-piece 2
allowed under-promotion 2  allowed x-ray 8
missed  <same 29 motifs, same per-stratum counts>
```

(Every one of the 29 motifs is present in both orientations on prod, including `self-interference` (int 14) — 2+2=4 rows sampled, confirming persisted rows still exist ahead of D-12's registry removal.)

## BEFORE table (pre-fix; `before_share == real_share` since nothing is suppressed yet)

| Motif | before_n | before_share (= real_share, pre-fix) |
|---|---:|---:|
| sacrifice | 16 | **0.375** (6/16 real) |
| clearance | 16 | **0.4375** (7/16 real) |
| intermezzo | 16 | **0.750** (12/16 real) |
| x-ray | 16 | **0.875** (14/16 real) |
| discovered-check | 4 | 0.750 |
| interference | 4 | 0.750 |
| promotion | 4 | 0.750 |
| self-interference | 4 | 0.750 |
| trapped-piece | 4 | 0.750 |
| under-promotion | 4 | 0.750 |
| all other motifs (18) | 4 each | 1.000 |

Full table (with floor/status columns added by task 3) reproducible via `uv run pytest tests/scripts/tagger -q -k realgame_real_share_floor -s`. Also embedded (task-2 shape, no floor column) in `reports/tactic-tagger/tactic-tagger-2026-09-12.md`.

## Seeded `REALGAME_REAL_SHARE_FLOOR` (pre-fix; a later plan raises these post-fix)

```python
REALGAME_MIN_ROWS_FOR_FLOOR: int = 8
REALGAME_REAL_SHARE_FLOOR: dict[str, float] = {
    "sacrifice": 0.32,   # measured 0.375
    "clearance": 0.38,   # measured 0.4375
    "intermezzo": 0.70,  # measured 0.750
    "x-ray": 0.82,       # measured 0.875
}
```

Every other motif has only 4 surviving rows (below the 8-row bar) and is reported but never gated.

## Ruff/ty findings fixed on the relocated scripts

RESEARCH.md measured 39 ruff findings (E401 multi-import, E702 semicolons, E731 lambda assignment, F401 unused imports, E741 ambiguous names) + 2 ty `unresolved-import` diagnostics on the two scripts as-is. After the relocation + cleanup (one import per line, `def` instead of lambda assignment, `_PROJECT_ROOT` sys.path bootstrap, `# ty: ignore[unresolved-import]` on the two AGPL-clone imports with a reason), both files are clean: `uv run ruff check .`, `uv run ruff format --check scripts/`, and `uv run ty check app/ tests/ scripts/` all exit 0. `oracle_compare.py` additionally required a `C901`/`PLR0912` refactor in the ungated `main()` (extracted `_fires`/`_cook_safe` helpers) that RESEARCH's static count did not itself measure but the live gate caught.

## Task Commits

Each task was committed atomically:

1. **T-221-01-01: relocate scripts, sample real-game tags, load like production** — `e6c96641c` (feat)
2. **T-221-01-02: label every real-game row and score it beside the fixture gate** — `db01c7af5` (feat)
3. **T-221-01-03: seed the never-regress real-share floors and document TAGFIX-08** — `b4b4cfdec` (feat)

**Plan metadata:** committed separately per `git_commit_metadata` (see `docs(221-01)` commit below).

## Files Created/Modified

- `scripts/research/sample_realgame_tags.py` — new: the read-only, reproducible sampler
- `fixtures/tagger/realgame_tags.csv` — new: the frozen, fully-labelled real-game fixture
- `scripts/research/oracle_compare.py` — relocated + lint/type-cleaned + AGPL-clone-absent guard
- `scripts/research/dev_probe.py` — relocated + lint/type-cleaned + required `--db` flag
- `tests/scripts/tagger/conftest.py` — `RealGameRow`/`RealGameLabel`/`_load_realgame`/`build_realgame_board`/`realgame_fixture`
- `tests/scripts/tagger/test_detector_precision.py` — `RealGameMotifStats`/`_compute_realgame_metrics`/`_print_realgame_table`/`test_realgame_fixture_schema`/`test_realgame_real_share_floor`
- `tests/scripts/tagger/precision_floors.py` — `REALGAME_REAL_SHARE_FLOOR`/`REALGAME_MIN_ROWS_FOR_FLOOR` + two new docstring paragraphs
- `scripts/tactic_tagger_report.py` — `_score_realgame`/`_realgame_table` spliced into `_build_report`
- `reports/tactic-tagger/tactic-tagger-2026-09-12.md` — generated report with the new Real-Game Gate section

## Decisions Made

- Stratification rates chosen to land near the ~150 target while keeping the four oversampled motifs' floors gate-able: `PER_STRATUM_OVERSAMPLED=8`, `PER_STRATUM_CONTROL=2` → 164 rows.
- `REALGAME_MIN_ROWS_FOR_FLOOR=8` was set to exactly match `PER_STRATUM_OVERSAMPLED`, so precisely the four target motifs (16 surviving rows each) clear the bar and every other motif (4 rows) is reported-only.
- Floor values rounded DOWN from the literal "measured − 0.05" value (e.g. clearance 0.4375 − 0.05 = 0.3875, seeded at 0.38 not 0.39) to stay safely conservative rather than accidentally stricter than the "~0.05 below" instruction.
- Labelling rubric applied mechanically where the rubric text itself is mechanical ("the tagging side is not losing where it fires" — any row with a losing `eval_at_firing` is not `real`), and by hand-reading the SAN line for the four oversampled motifs plus `self-interference` and any row with an unreadable eval, per the CONTEXT worked examples (clearance `Na6+ Ka8 [Qc7]` = real; `Kh1→g2 … [Rh1]` = incidental).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Extracted helper functions in `dev_probe.py` to clear the `C901`/`PLR0912` complexity gate**
- **Found during:** Task 1 (relocating `dev_probe.py`)
- **Issue:** The relocated `main()` function (with the fixed lint-clean structure) tripped `C901` (complexity 16 > 15) and `PLR0912` (16 branches > 12) — a gate this repo enforces project-wide (`pyproject.toml` `extend-select = ["C901", "PLR0912", "PLR0915"]`).
- **Fix:** Extracted `_build_record()` and `_missed_recapture()` as named helpers (mirroring the file's own established per-row-scoring shape), reducing `main()`'s branching without changing behavior.
- **Files modified:** `scripts/research/dev_probe.py`
- **Verification:** `uv run ruff check .` exits 0; re-ran the script against dev, output unchanged in shape.
- **Committed in:** `e6c96641c` (Task 1 commit)

**2. [Rule 3 - Blocking] `_INT_TO_MOTIF: Mapping[int, str]` type annotation to satisfy ty's invariant-generics rule**
- **Found during:** Task 1 (`sample_realgame_tags.py` / `dev_probe.py`)
- **Issue:** Annotating the module alias as `dict[int, str]` while assigning `td._INT_TO_MOTIF` (typed `dict[int, Literal[...]]`) fails ty's `invalid-assignment` check — `dict` is invariant in its value type.
- **Fix:** Used `collections.abc.Mapping[int, str]` (covariant) for the alias annotation instead.
- **Files modified:** `scripts/research/dev_probe.py`
- **Verification:** `uv run ty check app/ tests/ scripts/` exits 0.
- **Committed in:** `e6c96641c` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking lint/type gate fixes required to land the relocated scripts inside the project's static gates, exactly as TAGFIX-08 requires). No scope creep; no `app/` file was touched.

## Issues Encountered

- **Self-caught working-tree incident (no lasting impact):** while regenerating `reports/tactic-tagger/tactic-tagger-2026-09-12.md` I ran `rm -f reports/tactic-tagger/tactic-tagger-*.md` to clear a stale copy before re-running the report script — the glob also matched six PRE-EXISTING, already-committed historical report files (`tactic-tagger-2026-06-19.md` through `2026-09-02.md` plus `tactic-tagger-review-2026-09-12.md`). Caught immediately via `git status --short reports/` (all six showed as working-tree deletions, none staged); restored with `git restore` before any commit, confirmed `git diff --stat` empty against HEAD for all six. No data was lost and nothing was ever staged or committed in the deleted state.
- **Concurrent commits from another session landed on this same branch mid-plan:** two unrelated commits (`e02e6f576` "docs: capture exploration — train first-session retention (SEED-166)" and `5aec294c9` "docs(seed-166): silent snap-back...") were authored by the user's own concurrent activity between this plan's Task 1 and Task 2 commits — confirmed by `git show --stat` (both touch only `.planning/seeds/SEED-166-train-first-session-retention.md`, zero overlap with this plan's files). This means the measured `commits: 5` in this SUMMARY's frontmatter includes 2 commits NOT authored by this plan; only `e6c96641c`, `db01c7af5`, `b4b4cfdec` belong to Plan 221-01. Flagging for `/gsd-verify-work`'s same-instrument check so it isn't misread as an extra untracked task commit.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Ready for plan 02** (or whichever plan lands the port fixes / registry removal next per the wave sequence) — the measurement instrument this whole phase is judged by now exists, is frozen, and is green.
- **The pre-fix baseline is locked in as `REALGAME_REAL_SHARE_FLOOR`** — any later plan touching `tactic_detector.py`, `forcing_line_gate.py` or `flaws_service.py` must re-run `uv run pytest tests/scripts/tagger -q` and expects `real_share` to RISE for sacrifice/clearance/intermezzo/x-ray (D-05/D-01/D-09/D-07 respectively); a regression below the seeded floor fails the gate immediately.
- **Operator spot-check outstanding (D-13, harvested at end-of-phase per `workflow.human_verify_mode = end-of-phase`):** the labels above were assigned entirely by this executor. Per plan design this is not a blocking gate now — it surfaces in `221-UAT.md` at phase verification. Verbatim instructions for that check:

  > Operator spot-check of the labels (D-13). Open `fixtures/tagger/realgame_tags.csv` and review ~20 rows stratified across motif and orientation — include at least 4 sacrifice, 4 clearance, 2 intermezzo and 2 x-ray rows plus a few from the fork/hanging-piece/mate control. For each, read `san_line` and `eval_at_firing` and judge whether the `label` and `rationale` are defensible. Record every disagreement (row_id, your label, the reason) in the phase SUMMARY; a systematic disagreement pattern means the labels must be revised before the prod retag, and plan 07's deploy gate is the stop point where that happens.

- `uv run pytest -n auto -x` (whole suite, excluding the tagger harness per `pyproject.toml`'s `addopts`) passed 4612/4612 (19 skipped) — nothing outside this plan's scope regressed.

## Self-Check: PASSED

All 9 key files found on disk; all 3 task commit hashes found in `git log --oneline --all`.

---
*Phase: 221-tactic-tagger-real-game-precision-winning-floor-predicate-ti*
*Completed: 2026-09-12*
