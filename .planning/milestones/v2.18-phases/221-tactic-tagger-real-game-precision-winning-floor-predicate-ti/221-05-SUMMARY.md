---
phase: 221-tactic-tagger-real-game-precision-winning-floor-predicate-ti
plan: 05
subsystem: tactic-tagger
tags: [tactic-detector, sacrifice, clearance, cook-divergence, real-game-gate]

requires:
  - phase: 221-01
    provides: the real-game gate scoring harness + REALGAME_REAL_SHARE_FLOOR
      pre-fix baseline this plan's real-game measurement compares against
  - phase: 221-04
    provides: the per-tier winning floor and D-11 discovered-attack depth=k
      fix this plan's dispatch-redistribution numbers are measured on top of
provides:
  - "app/services/tactic_detector.py: SACRIFICE_CLEARANCE_MAX_DEPTH constant;
    _sacrifice_deficit_persists (D-05 persistence check); detect_sacrifice
    now requires the deficit to hold at boards[k+3] or the line to end;
    _clearance_prior_move_is_valid extended with the D-07 vacating-piece
    restriction; _clearance_line_is_used (D-07 line-is-used clause);
    _clearance_check_move_is_valid (condition 7, extracted to hold the
    function under the PLR0912 branch gate); detect_clearance now enforces
    all three D-06/D-07 additions plus the shared depth cap"
  - "tests/services/test_tactic_detector.py: TestSacrificePersistenceAndDepthCap
    (9 tests), TestClearanceContextWorkedExamples /
    TestClearancePriorMoveValidVacatingPiece / TestClearanceLineIsUsed /
    TestClearanceDepthCap (14 tests total) -- all fixtures are synthetic,
    hand-verified 'material lab' positions, not real games"
  - "tests/scripts/tagger/precision_floors.py: the D-05/D-07 deliberate-
    divergence record above the sacrifice/clearance PRECISION_FLOOR entries,
    cross-referenced from the module docstring"
  - "reports/tactic-tagger/tactic-tagger-2026-09-12.md regenerated with the
    post-strengthening CC0 and real-game tables"
  - "An UNRESOLVED, explicitly-documented finding: uv run pytest
    tests/scripts/tagger -q currently FAILS (sacrifice real-game floor
    breach; clearance real-game NO-ROWS) -- see Known Issues below. This is
    the state plan 06 (and possibly a human decision on sacrifice) must
    resolve; this plan does not touch REALGAME_REAL_SHARE_FLOOR per its own
    explicit constraint."
affects: [221-06, 221-07]

actuals:
  tokens: 11731
  tasks: 3
  commits: 3
  plan_head_before: 115388f8f2a0194ed11d79141072dd12791c2039

tech-stack:
  added: []
  patterns:
    - "synthetic 'material lab' fixtures: an empty chess.Board built via
      set_piece_at with a minimal geometry (a blocked ray piece + a
      non-king/pawn or king/pawn 'blocker' + a neutral filler piece), used to
      hand-construct and verify exact material-diff trajectories or
      clearance geometries that would be impractical to find in real games
      -- every fixture verified with a standalone script calling
      detect_sacrifice/detect_clearance directly before being transcribed
      into the test file"
    - "extract-to-hold-the-branch-gate: when a strengthening adds a new
      condition and trips ruff's PLR0912 branch-count gate, extract an
      EXISTING (unrelated to the new condition) branch into its own
      module-level helper rather than touching the new condition's logic"

key-files:
  created: []
  modified:
    - app/services/tactic_detector.py
    - tests/services/test_tactic_detector.py
    - tests/scripts/tagger/precision_floors.py
    - reports/tactic-tagger/tactic-tagger-2026-09-12.md

key-decisions:
  - "The plan's literal acceptance-criteria example ('a line where the
    deficit at k==2 does not persist but a second sacrifice at k==4 does ->
    fires at depth 4') is mathematically UNREACHABLE given D-05's own spec:
    persistence(k) reads boards[k+3], which is EXACTLY gate(k+2)'s own
    boards[k+1] -- if persistence fails (board shows recovery), the very
    next candidate's gate reads the identical board and fails too. Proven
    by direct construction attempt, not asserted. Implemented the reachable
    form instead: k=2's gate is not met (proceeds past it), k=4's gate is
    met and the line ends -> fires at depth 4, which is the achievable
    version of 'the scan continues rather than short-circuiting' under a
    depth-4 cap (only two candidates ever exist)."
  - "The plan's 'six CONTEXT worked examples' actually names only 5 in
    CONTEXT.md (2 accept via check + 3 reject); the plan's own task2 action
    text explicitly asks for a THIRD accept case testing the
    higher-value-or-hanging branch (since both named accept examples fire
    via check). Authored that third accept fixture myself, arriving at 6
    total fixtures as the plan's acceptance criteria require."
  - "Extracted condition 7 (the existing check-gives-a-king-move guard) into
    _clearance_check_move_is_valid -- not a D-07 addition, but required to
    keep detect_clearance's branch count under ruff's PLR0912 gate (13 > 12)
    once the D-07 conditions were added. Function-size depth/LOC gate
    (scripts/check_function_size.py) was never breached; only ruff's
    separate branch-count lint rule was."
  - "Four real prod _CLEARANCE_FIXTURES rows and two cross-motif regression
    rows (in _PIN_FIXTURES / _INTERMEZZO_FIXTURES) no longer fire as
    clearance under the strengthened predicate -- verified each rejection
    reason individually (pawn-vacating move, or line-not-used) rather than
    assuming. The four removed clearance rows were replenished by the three
    new CONTEXT accept fixtures (net 11 -> 10, clearing the >=10 fixture-
    richness bar); the two cross-motif rows were relocated to
    _HARD_NEGATIVES (still proving pin/intermezzo don't wrongly win, now via
    None instead of via clearance winning the tiebreak)."
  - "Did NOT touch REALGAME_REAL_SHARE_FLOOR, per the plan's explicit
    instruction that this floor stays at plan 01's pre-fix baseline. This
    means `uv run pytest tests/scripts/tagger -q` does not pass at the end
    of this plan -- see Known Issues. Weakening D-05 or raising
    SACRIFICE_CLEARANCE_MAX_DEPTH to force it green was explicitly
    prohibited and was not done."

requirements-completed: [TAGFIX-03, TAGFIX-04]

coverage:
  - id: D1
    description: "detect_sacrifice requires the material deficit to persist at boards[k+3] (the next pov move) or the line to end, caps the scan at depth 4 shared with clearance, and keeps a single orientation-agnostic predicate (D-05/D-06/D-08)"
    requirement: TAGFIX-03
    verification:
      - kind: unit
        ref: "tests/services/test_tactic_detector.py::TestSacrificePersistenceAndDepthCap (9 tests: recovered/persists/line-ends/gate-boundary/cap-at-4-fires/cap-at-6-blocked/idempotency/direct-helper-boundary/no-orientation-param)"
        status: pass
      - kind: other
        ref: "uv run pytest tests/scripts/tagger -q -k test_detector_precision_and_recall (CC0 gate: sacrifice TRAIN TP 397->177, TEST TP 183->70, FP 0->0 both splits, precision 1.000 held)"
        status: pass
    human_judgment: false
  - id: D2
    description: "detect_clearance rejects king/pawn vacating moves and lines that aren't used, caps at depth 4, stays under the PLR0912 branch gate via an extracted helper, and reproduces all six CONTEXT worked examples in the stated direction"
    requirement: TAGFIX-04
    verification:
      - kind: unit
        ref: "tests/services/test_tactic_detector.py::TestClearanceContextWorkedExamples / TestClearancePriorMoveValidVacatingPiece / TestClearanceLineIsUsed / TestClearanceDepthCap (14 tests total)"
        status: pass
      - kind: other
        ref: "uv run pytest tests/scripts/tagger -q -k test_detector_precision_and_recall (CC0 gate: clearance TRAIN TP 399->216, TEST TP 159->90, FP 0->0 both splits, precision 1.000 held)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both deliberate cook divergences documented in precision_floors.py in the same change as the code; both floors' measurement comments updated; no PRECISION_FLOOR value lowered; the post-strengthening real-game table measured and recorded with explicit clearance verdicts"
    requirement: TAGFIX-03
    verification:
      - kind: other
        ref: "uv run python -c check for D-05/D-07/deliberate text in precision_floors.__doc__ (pass); git diff shows both floor VALUES unchanged at 0.93, only trailing comments updated"
        status: pass
      - kind: other
        ref: "uv run pytest tests/scripts/tagger -q — FAILS (test_realgame_real_share_floor: sacrifice below its frozen floor, clearance below REALGAME_MIN_ROWS_FOR_FLOOR). See Known Issues."
        status: fail
    human_judgment: true
    rationale: "The real-game gate failure is a genuine, measured, D-05/D-07-faithful consequence this plan is explicitly forbidden from silencing (no floor edits, no depth-cap relaxation). Resolving it requires a decision — plan 06's designed keep-or-suppress branch for clearance, and a NEW, not-previously-anticipated decision for sacrifice (whether 0.32 was too optimistic a floor for a 16-row sample, or whether D-05 is too aggressive on 'compensated' sacrifices) — that only a human or a later plan can make."

duration: ~2h (approximate — extensive fixture-construction and real-game measurement work; system clock in this session did not track wall time reliably across tool calls)
completed: 2026-09-12
status: complete
---

# Phase 221 Plan 05: Sacrifice Persistence, Clearance Strengthening, and the Real-Game Measurement Summary

**Sacrifice now requires its material deficit to survive the next pov move (or the line to end) and caps its scan at depth 4; clearance rejects king/pawn vacating moves and lines that don't check-or-attack, sharing the same depth cap — both changes hold their CC0 precision floors exactly as designed, but the real-game gate they were built to improve now fails for BOTH motifs, and this plan's own constraints forbid fixing that here.**

## Performance

- **Duration:** ~2h (approximate)
- **Tasks:** 3 completed
- **Files modified:** 4 (`app/services/tactic_detector.py`, `tests/services/test_tactic_detector.py`, `tests/scripts/tagger/precision_floors.py`, `reports/tactic-tagger/tactic-tagger-2026-09-12.md`)

## Accomplishments

- **Task 1 (TAGFIX-03, D-05/D-06/D-08):** `SACRIFICE_CLEARANCE_MAX_DEPTH: int = 4` added beside `MIN_SACRIFICE_DROP`. New `_sacrifice_deficit_persists(boards, pov, initial, k)` reads `boards[k+3]` (the board after the NEXT pov move): accepts unconditionally when the line ends first, otherwise requires the deficit to still hold. `detect_sacrifice`'s loop gained the depth-cap `break` and the persistence check; when the deficit is met but doesn't persist, the loop `continue`s (scans on) rather than returning not-fired. D-08 verified structurally: `detect_sacrifice`'s signature is exactly `{boards, moves, pov}`, no orientation parameter.
- **Task 2 (TAGFIX-04, D-06/D-07):** `_clearance_prior_move_is_valid` gained an `init_board` parameter and now rejects a king- or pawn-vacating prior move. New `_clearance_line_is_used(board_after, dest, pov)` mirrors `detect_fork`'s victim loop: accepts on check, or on an attacked opponent piece that is strictly higher-value or undefended (reusing `_is_defended`/`_PIECE_VALUES`, no hand-rolled attackers check). `detect_clearance` wires in the depth cap, the extended prior-move check, and the new line-used condition as its 10th condition. Adding the new condition pushed the function's branch count over ruff's PLR0912 limit (13 > 12); extracted the pre-existing condition 7 (check-implies-not-a-king-move) into `_clearance_check_move_is_valid` to bring it back under the gate without touching D-07's own logic.
- **Task 3 (documentation + measurement):** Added the deliberate-divergence block above the `sacrifice` and `clearance` `PRECISION_FLOOR` entries in `precision_floors.py` (cross-referenced from the module docstring), updated both entries' measurement comments with the new TP/FP numbers, regenerated the tactic-tagger report, and measured the full real-game table. **Did not** touch `REALGAME_REAL_SHARE_FLOOR` (explicitly forbidden by the plan) and **did not** act on clearance's keep-or-suppress decision (explicitly plan 06's).
- Full backend suite (`uv run pytest -n auto -x`): 4684 passed, 19 skipped. `ruff check .`, `ty check app/ tests/ scripts/`, `ruff format --check` (on the three files this plan touched), and `check_function_size.py` (1051 functions, no breaches) all clean.

## CC0 fixture (PRECISION_FLOOR gate) — before/after

Both motifs measured with `precision_floors.PRECISION_FLOOR` unchanged in value (0.93 for both); only the trailing measurement comments moved. **No FP count rose for either motif on either split** — precision holds at 1.000 throughout, exactly as D-05/D-07 require.

| Motif | Split | TP before → after | FP before → after | Precision before → after | Recall before → after |
|---|---|---|---|---|---|
| sacrifice | TRAIN | 397 → 177 | 0 → 0 | 1.000 → 1.000 | 0.111 → 0.050 |
| sacrifice | TEST | 183 → 70 | 0 → 0 | 1.000 → 1.000 | 0.118 → 0.045 |
| clearance | TRAIN | 399 → 216 | 0 → 0 | 1.000 → 1.000 | 0.457 → 0.247 |
| clearance | TEST | 159 → 90 | 0 → 0 | 1.000 → 1.000 | 0.449 → 0.254 |

"Before" = the state after plans 02+04 landed (measured this session by temporarily monkeypatching `detect_sacrifice`/`detect_clearance` back to their pre-this-plan bodies in a fresh process and re-scoring the same fixture — not git-reverting). No other motif's FP count changed; all other TP movement across both splits is winner-take-all dispatch redistribution from the freed sacrifice/clearance candidate slots (attraction, deflection, discovered-attack, discovered-check, double-check, en-passant, fork, interference, intermezzo, pin, promotion, skewer, trapped-piece, under-promotion, x-ray all shifted by small amounts, 0 FP change on any of them) — consistent with the pattern plan 02's SUMMARY already documented for the earlier port fixes.

## Real-game table (post-strengthening) — full 29-motif measurement

Scored via `tests/scripts/tagger/test_detector_precision.py::_compute_realgame_metrics` against the SAME frozen 164-row `fixtures/tagger/realgame_tags.csv` plan 01 sampled before any code in this phase changed. `before_n`/`before_share` are frozen (label-only, never change); `surviving`/`real_surviving`/`suppressed`/`real_share` are re-derived by re-running the current detector.

| Motif | before_n | before_share (frozen) | surviving | real_surv | suppressed | real_share (now) | Δ vs before_share |
|---|---:|---:|---:|---:|---:|---:|---:|
| **sacrifice** | 16 | 0.375 | 9 | 2 | 7 | **0.222** | **−0.153** |
| **clearance** | 16 | 0.4375 | 3 | 2 | 13 | **0.667** | **+0.229** |
| intermezzo | 16 | 0.750 | 16 | 12 | 0 | 0.750 | 0.000 (untouched by this plan) |
| x-ray | 16 | 0.875 | 16 | 14 | 0 | 0.875 | 0.000 (untouched by this plan) |
| discovered-check | 4 | 0.750 | 4 | 3 | 0 | 0.750 | 0.000 |
| interference | 4 | 0.750 | 4 | 3 | 0 | 0.750 | 0.000 |
| promotion | 4 | 0.750 | 3 | 2 | 1 | 0.667 | −0.083 (incidental; not gated) |
| self-interference | 4 | 0.750 | 0 | 0 | 4 | NaN | fully suppressed (already undispatchable since plan 02; unrelated to this plan) |
| trapped-piece | 4 | 0.750 | 4 | 3 | 0 | 0.750 | 0.000 |
| under-promotion | 4 | 0.750 | 4 | 3 | 0 | 0.750 | 0.000 |
| en-passant | 4 | 1.000 | 3 | 3 | 1 | 1.000 | 0.000 (1 row suppressed, remainder still 3/3) |
| all other 18 motifs | 4 each | 1.000 | 4 | 4 | 0 | 1.000 | 0.000 |

**Clearance's explicit verdicts (for plan 06's keep-or-suppress decision):**
- **Real-share at or above 0.80? NO** — measured 0.667 (2/3), below the 0.80 bar, though notably ABOVE its frozen never-regress floor (0.38).
- **Surviving count clears REALGAME_MIN_ROWS_FOR_FLOOR (8)? NO** — only 3 of 16 rows survive (13 correctly suppressed by the D-07 strengthening). This is the more decisive fact: even setting the 0.80 bar aside, the denominator is far too thin to trust.

**Report path:** `reports/tactic-tagger/tactic-tagger-2026-09-12.md` (regenerated via `PYTHONPATH=. uv run python scripts/tactic_tagger_report.py`, `Wrote ... (142 lines)`).

## The new divergence block (precision_floors.py)

Verbatim text added above the `clearance` PRECISION_FLOOR entry:

```
# Phase 221 TAGFIX-04 (D-06/D-07, plan 05, DELIBERATE divergence from cook —
# see the module docstring's Phase 221 paragraph): three additions to cook's
# 9-condition chain. (1) The vacating (prior pov) move must not be a king or
# pawn move (a dev hand review found 9 of 12 sampled clearance tags were king
# retreats, pawn pushes, or piece shuffles — not real clearances). (2) The
# clearing move must actually USE the newly-opened line (gives check, or
# attacks a higher-value or hanging opponent piece) — cook has no such test.
# (3) The scan caps at SACRIFICE_CLEARANCE_MAX_DEPTH=4 (shared with
# sacrifice, D-06) — dev average firing depth for clearance was 3.73 vs
# 0.00-1.35 for the geometric motifs. Recall falls by design (measured:
# TRAIN TP 399->216 recall 0.457->0.247, TEST TP 159->90 recall 0.449->0.254);
# precision must NOT fall and does not (1.000 -> 1.000 both splits, 0 FP
# throughout). A future precision pass must NOT relax these three additions
# to recover fixture recall; if a real-game measurement finds the cut too
# soft, SACRIFICE_CLEARANCE_MAX_DEPTH is the lever, never a re-litigation of
# D-07. `clearance`'s survival past this phase is contingent on a real-game
# real-share bar of 0.8 (REALGAME_REAL_SHARE_FLOOR below, measured in the
# same plan) — decided by plan 06, not this one.
```

And above the `sacrifice` entry:

```
# Phase 221 TAGFIX-03 (D-05/D-06, plan 05, DELIBERATE divergence from cook —
# see the module docstring's Phase 221 paragraph): cook's predicate fires
# whenever pov is down >= MIN_SACRIFICE_DROP at ANY pov move from the 2nd
# onward, with no recovery test and no depth limit — 32% of cook's own
# sacrifice puzzles are delayed recaptures / zwischenzugs, which is exactly
# the shape this drops. D-05 requires the deficit to still hold after the
# NEXT pov move (boards[k+3]), or the line to end first; D-06 caps the scan
# at SACRIFICE_CLEARANCE_MAX_DEPTH=4 (shared with clearance; dev average
# firing depth 4.78 vs 0.00-1.35 for the geometric motifs). Recall falls by
# design (measured: TRAIN TP 397->177 recall 0.111->0.050, TEST TP 183->70
# recall 0.118->0.045); precision must NOT fall and does not (1.000 -> 1.000
# both splits, 0 FP throughout). A future precision pass must NOT relax the
# persistence rule or raise the depth cap to recover this recall — if a
# real-game measurement finds the cut too soft, the depth cap is the lever,
# never a re-litigation of D-05.
```

Plus a module-docstring cross-reference paragraph naming both motifs' orthogonal PRECISION_FLOOR/REALGAME_REAL_SHARE_FLOOR scoring and reiterating that the depth cap is the only sanctioned lever.

## Task Commits

Each task was committed atomically:

1. **T-221-05-01: Sacrifice persistence on `boards[k+3]` and the shared depth cap (D-05, D-06, D-08)** — `fb5949185` (feat)
2. **T-221-05-02: Strengthen `detect_clearance` — no king or pawn vacating move, the line must be used, depth capped (D-07)** — `99015a604` (feat) — also carries the sacrifice test additions from task 1 since both tasks' tests were written into the same file in one continuous session before any intermediate commit (detector code split remains clean and correctly attributed).
3. **T-221-05-03: Record the deliberate divergences and measure both gates for plan 06's decision** — `e90762c83` (docs)

**Plan metadata:** committed separately per `git_commit_metadata` (see `docs(221-05)` commit below).

## Files Created/Modified

- `app/services/tactic_detector.py` — `SACRIFICE_CLEARANCE_MAX_DEPTH`, `_sacrifice_deficit_persists`, rewritten `detect_sacrifice`; `_clearance_prior_move_is_valid` (extended), `_clearance_line_is_used`, `_clearance_check_move_is_valid`, rewritten `detect_clearance`
- `tests/services/test_tactic_detector.py` — `TestSacrificePersistenceAndDepthCap` (9 tests), `TestClearanceContextWorkedExamples` / `TestClearancePriorMoveValidVacatingPiece` / `TestClearanceLineIsUsed` / `TestClearanceDepthCap` (14 tests), 6 new/relocated clearance fixtures, 2 fixtures relocated to `_HARD_NEGATIVES`, 4 stale clearance fixtures removed with documentation
- `tests/scripts/tagger/precision_floors.py` — divergence blocks for both motifs, updated measurement comments, module-docstring cross-reference
- `reports/tactic-tagger/tactic-tagger-2026-09-12.md` — regenerated

## Decisions Made

See `key-decisions` in frontmatter — summarized: the plan's literal "k=2 fails, k=4 fires" acceptance example is mathematically unreachable under D-05's own spec (proven by construction, not asserted) and was implemented in its reachable form; the "six CONTEXT examples" required authoring a third accept fixture since CONTEXT.md only names two (both via check); condition 7 was extracted purely to satisfy ruff's branch-count gate; four stale real-prod clearance fixtures were removed and replenished by the three new CONTEXT fixtures; `REALGAME_REAL_SHARE_FLOOR` was deliberately left untouched per the plan's explicit constraint, which is the direct cause of the Known Issue below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `detect_clearance` branch count over ruff's PLR0912 gate after adding condition 10**
- **Found during:** Task 2, `uv run ruff check .`
- **Issue:** Adding the line-is-used condition pushed `detect_clearance` to 13 branches (limit 12).
- **Fix:** Extracted condition 7 (pre-existing, unrelated to D-07) into `_clearance_check_move_is_valid`.
- **Files modified:** `app/services/tactic_detector.py`
- **Verification:** `uv run ruff check .` and `check_function_size.py` both clean.
- **Committed in:** `99015a604` (Task 2 commit)

**2. [Rule 1 - Bug] Four `_CLEARANCE_FIXTURES` rows and two cross-motif regression rows broke under the strengthened predicate**
- **Found during:** Task 2, `uv run pytest tests/services/test_tactic_detector.py`
- **Issue:** Six pre-existing fixtures (four real-prod clearance positives, two clearance-wins-dispatch regression guards inside `_PIN_FIXTURES`/`_INTERMEZZO_FIXTURES`) no longer fire as clearance under D-07 — each individually traced to a specific rejection cause (pawn-vacating move, or line-not-used).
- **Fix:** Removed the four clearance rows with documentation explaining each rejection; relocated the two cross-motif rows to `_HARD_NEGATIVES` (they still prove pin/intermezzo doesn't wrongly win, now via `None`).
- **Files modified:** `tests/services/test_tactic_detector.py`
- **Verification:** Full test file green (108 passed, 7 skipped); `test_validated_motifs_have_enough_fixtures` clears the >=10 richness bar (11 -> 10 after removing 4 and adding 3 new CONTEXT fixtures).
- **Committed in:** `99015a604` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking lint gate, 1 bug/fixture-assumption break — both direct, unavoidable consequences of this plan's own strengthening landing correctly on pre-existing test infrastructure). **Impact:** No scope creep; both are exactly the kind of fixture churn the plan's own instructions anticipated ("existing clearance fixtures may no longer fire").

## Known Issues (NOT auto-fixed — requires a decision, flagged per Rule 4)

**`uv run pytest tests/scripts/tagger -q` does NOT pass as of this plan's final commit.** One test, `test_realgame_real_share_floor`, fails with TWO independent, both-measured, both-D-05/D-07-faithful findings:

1. **`sacrifice` real-share regression:** measured 0.222 (2/9 surviving rows are `real`), below its frozen floor (0.32). Root cause traced row-by-row (script output preserved in my session, not committed): several rows a human labelled `real` are attacking sacrifices that fully repay via a DIFFERENT tactical point 1-2 plies later (e.g., row 0064: a knight sac at k=2 that objectively wins with the position at +264cp, but the material fully recovers via an unrelated bishop capture at k=4) — this is EXACTLY the "delayed compensation" shape D-05 is designed to exclude, applied faithfully to a case a human judged differently. This is a **measured tension between D-05's literal spec and the operator-unverified real-game labels** (per 221-01's outstanding spot-check), not a code bug.
2. **`clearance` NO-ROWS:** only 3 of 16 rows survive (13 correctly suppressed), below `REALGAME_MIN_ROWS_FOR_FLOOR=8`. Clearance's real_share among survivors (0.667) actually PASSES its floor (0.38) — this is purely a denominator problem, and is **exactly the fact plan 06's keep-or-suppress decision needs** (see the explicit verdicts above: real-share < 0.80 AND row count too thin — both point toward suppression).

**Why this was not fixed here:** the plan explicitly forbids touching `REALGAME_REAL_SHARE_FLOOR` in this plan ("plan 06 raises them from the post-fix measurement") and explicitly forbids relaxing D-05/D-06/D-07 to recover any measurement this change deliberately gives up. Both root causes are confirmed faithful implementations of the plan's own D-05/D-06/D-07 spec (verified via direct code inspection and synthetic-fixture proofs, not assumed) — there is no code fix available within this plan's constraints. **This requires an explicit decision** from plan 06 (clearance, which the plan already anticipated) and a NEW decision this plan did not anticipate for sacrifice: either the 0.32 floor was too optimistic given the 16-row sample, or D-05's persistence rule is more aggressive on "compensated" sacrifices than the phase's design intended and needs its OWN dedicated real-game validation (e.g., a larger sacrifice sample, or an operator re-review of the specific rows named above) before the floor question can be answered.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Ready for plan 06**, with both facts it needs pre-computed: clearance's real-share (0.667, below 0.80) and surviving-row count (3, below the minimum-8 bar) — both point toward suppression, but the decision itself is plan 06's.
- **NOT ready to ship as-is:** the real-game gate is red. Before this phase can be considered done, either (a) plan 06 resolves clearance's fate AND a separate decision is made on sacrifice's floor/behavior, or (b) an operator explicitly accepts the current red gate as a known, documented, deliberate state pending the D-13 label spot-check.
- Carrying forward for plan 06: the exact clearance real-game numbers (surviving=3, real_surviving=2, suppressed=13, real_share=0.667) and the observation that its `real_share` alone would pass (0.667 > 0.38 floor) but the row count is decisively too thin to trust.
- Carrying forward as a NEW open question (not previously flagged in CONTEXT.md/RESEARCH.md): whether `sacrifice`'s real-game floor (0.32) needs revision given this plan's measured 0.222, or whether the specific "compensated sacrifice" rows need operator re-review as part of the still-outstanding D-13 spot-check (see 221-01-SUMMARY.md's "Operator spot-check outstanding").
- `uv run pytest -n auto -x` (whole suite, excluding the tagger harness per `pyproject.toml`'s `addopts`) passed 4684/4684 (19 skipped) — nothing outside this plan's scope regressed.
- `uv run ruff check .`, `uv run ty check app/ tests/ scripts/`, `uv run ruff format --check` (on this plan's three touched files), and `uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200` (1051 functions, no breaches) all clean.

## Self-Check: PASSED

All 4 modified files found on disk with the expected changes; all 3 task commit hashes (`fb5949185`, `99015a604`, `e90762c83`) found in `git log --oneline --all`.

---
*Phase: 221-tactic-tagger-real-game-precision-winning-floor-predicate-ti*
*Completed: 2026-09-12*
