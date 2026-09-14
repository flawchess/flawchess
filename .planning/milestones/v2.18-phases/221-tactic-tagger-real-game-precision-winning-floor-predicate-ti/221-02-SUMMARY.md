---
phase: 221-tactic-tagger-real-game-precision-winning-floor-predicate-ti
plan: 02
subsystem: tactic-detector
tags: [tactic-tagger, cook-port, dispatch, precision-harness, oracle-comparison]

requires:
  - phase: 221-01
    provides: the real-game gate scoring harness + REALGAME_REAL_SHARE_FLOOR (not
      touched by this plan, but the pre-fix baseline it froze is what later plans
      re-measure against)
provides:
  - Seven fixture-verified cook-port fixes to app/services/tactic_detector.py
    (deflection OR, fork gate removal, trapped-piece revert, discovered-attack
    return+depth=k, boden/double-bishop file-test, self-interference undispatchable)
  - A documented, oracle-verified finding that detect_boden_or_double_bishop_mate
    has a much larger (684-row) firing gap unrelated to the file-edge hypothesis —
    NOT fixed here, flagged for a future phase
affects: [221-03, 221-04, 221-05, 221-06, 221-07]

actuals:
  tokens: 8281
  tasks: 3
  commits: 3
  plan_head_before: 760cce1ef4668f619e0cf783f780c2ad2743775e

tech-stack:
  added: []
  patterns:
    - "anchor a fix by FUNCTION not by string when two detectors share a visually
      identical guard line (discovered-attack vs skewer's recapture check)"
    - "run scripts/research/oracle_compare.py BEFORE writing an unverified fix; if
      the divergence table shows a different root cause than the plan's hypothesis,
      stop and record the finding rather than shipping a guess"

key-files:
  created: []
  modified:
    - app/services/tactic_detector.py
    - tests/services/test_tactic_detector.py
    - tests/scripts/tagger/precision_floors.py

key-decisions:
  - "Boden/double-bishop fix 6 implemented ONLY the oracle-verified 1-row bucket
    mismatch (cook's asymmetric file-relation formula), NOT the plan's assumed
    file-edge XOR bug (which turned out not to exist) and NOT the much larger
    684-row firing gap the oracle actually surfaced — that gap is a separate,
    undiagnosed root cause out of scope for TAGFIX-05, documented below."
  - "precision_floors.py comment updates scoped to the six motifs each fix directly
    targets (fork, deflection, trapped-piece, discovered-attack, boden-mate) plus
    self-interference's SUPPRESSED_MOTIFS note; incidental TP redistribution on
    other motifs from winner-take-all dispatch (attraction, double-check, pin,
    promotion, sacrifice, skewer, under-promotion, capturing-defender) is recorded
    in this SUMMARY's before/after table rather than in 8+ separate trailing
    comments that would immediately go stale as later plans (03-06) touch the same
    detectors again."
  - "discovered-attack's PRECISION_FLOOR raised 0.93 -> 0.95 (both splits now exactly
    1.000, ~5pp headroom, matching the file's house convention) to lock in the
    zero-FP gain from fix 4. No other floor changed value."

requirements-completed: [TAGFIX-05]

coverage:
  - id: D1
    description: "Deflection's promotion branch restored to cook's single OR (attacks(orig) OR promotion+same-file+reachable), replacing an if/elif that silently skipped the attacks disjunct for every promotion move"
    requirement: TAGFIX-05
    verification:
      - kind: unit
        ref: "tests/services/test_tactic_detector.py::test_positives_fire_expected_motif[deflection] (two new named fixture rows, kwRAz + 9WsPX, one per disjunct)"
        status: pass
      - kind: other
        ref: "uv run pytest tests/scripts/tagger -q (TRAIN TP 490->618, FP unchanged at 2, no floor lowered)"
        status: pass
    human_judgment: false
  - id: D2
    description: "detect_fork's D-01 relevance gate (skip when material at line end is below line start) removed entirely — not cook's rule, measured costing 130 detections for zero precision"
    requirement: TAGFIX-05
    verification:
      - kind: unit
        ref: "tests/services/test_tactic_detector.py::test_positives_fire_expected_motif[fork] (new fixture: fork fires at depth 2 despite a down-material overall trend)"
        status: pass
      - kind: other
        ref: "uv run pytest tests/scripts/tagger -q (TRAIN TP 1168->1195 across tasks 1-3, FP unchanged at 3)"
        status: pass
    human_judgment: false
  - id: D3
    description: "_piece_is_trapped's empty-escape-set exclusion reverted — an attacked, unpinned, non-pawn/non-king piece with zero legal escapes is now trapped, matching cook's immobile-attacked rule"
    requirement: TAGFIX-05
    verification:
      - kind: unit
        ref: "tests/services/test_tactic_detector.py::TestTrappedPieceCookPredicate::test_empty_escape_set_fires_trapped (direct _piece_is_trapped unit call)"
        status: pass
      - kind: other
        ref: "uv run pytest tests/scripts/tagger -q (TRAIN TP 576->622, FP unchanged at 0)"
        status: pass
    human_judgment: false
  - id: D4
    description: "detect_discovered_attack's recapture guard now returns (short-circuits the whole predicate) instead of continue, anchored by function so detect_skewer's identical-looking guard is untouched; depth is now the pov move index k, not k-1"
    requirement: TAGFIX-05
    verification:
      - kind: unit
        ref: "tests/services/test_tactic_detector.py::TestDiscoveredAttackD11PortFixes::test_recapture_short_circuits_whole_predicate"
        status: pass
      - kind: unit
        ref: "tests/services/test_tactic_detector.py::TestDiscoveredAttackD11PortFixes::test_depth_equals_pov_move_index_k"
        status: pass
      - kind: unit
        ref: "tests/services/test_tactic_detector.py::TestDiscoveredAttackD11PortFixes::test_recapture_guard_untouched_in_skewer"
        status: pass
      - kind: other
        ref: "uv run pytest tests/scripts/tagger -q (TRAIN FP 5->0, TEST FP 4->0, precision 0.990/0.982 -> 1.000/1.000; floor raised 0.93->0.95)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Boden/double-bishop file-relation test corrected to cook's actual asymmetric formula, verified against scripts/research/oracle_compare.py before implementation; the much larger firing-gap finding the oracle surfaced is documented, not fixed"
    requirement: TAGFIX-05
    verification:
      - kind: unit
        ref: "tests/services/test_tactic_detector.py::test_positives_fire_expected_motif[boden-mate] (no regression on existing fixtures)"
        status: pass
      - kind: other
        ref: "scripts/research/oracle_compare.py + a scratch diagnostic script (see '## Boden/double-bishop oracle finding' below) confirming the mis-bucket count dropped 1->0 with no new mismatches"
        status: pass
    human_judgment: true
    rationale: "The oracle-verified root-cause pivot (from the plan's file-edge hypothesis to cook's actual asymmetric formula) and the decision to document rather than fix the larger firing gap are judgment calls a human should review before this is treated as fully settled — the diagnostic script is not committed to the repo."
  - id: D6
    description: "self-interference removed from _TIER3_REGISTRY (undispatchable); TacticMotifInt.SELF_INTERFERENCE, _INT_TO_MOTIF[14], _MOTIF_TO_INT and detect_self_interference all remain for existing storage/tests"
    requirement: TAGFIX-05
    verification:
      - kind: unit
        ref: "tests/services/test_tactic_detector.py::TestTacticMotifInt::test_tier3_registry_excludes_self_interference"
        status: pass
      - kind: unit
        ref: "tests/services/test_tactic_detector.py tests/services/test_tactic_comparison_service.py -q (three pre-existing regression tests pass unmodified: test_all_29_motifs_encoded, test_suppressed_motifs_documented_and_storable, test_family_mapping_excludes_suppressed_tier3)"
        status: pass
      - kind: other
        ref: "uv run pytest -n auto -x (4616 passed, 19 skipped — full suite, nothing outside scope regressed)"
        status: pass
    human_judgment: false

duration: ~2h 15min (approximate — session start not precisely instrumented; based on tool-call volume and the three commit timestamps 17:41-17:58 CEST plus prior research/measurement time)
completed: 2026-09-12
status: complete
---

# Phase 221 Plan 02: Seven Fixture-Verified Cook-Port Fixes Summary

**Restored six real cook-alignment divergences in `app/services/tactic_detector.py` (deflection's promotion OR, fork's relevance gate, trapped-piece's empty-escape exclusion, discovered-attack's recapture short-circuit + depth=k, the boden/double-bishop file test) and took the dead `self-interference` motif out of dispatch — discovered-attack's false-positive rate dropped to zero on both splits, and the boden/double-bishop fix was re-derived from a direct oracle comparison after the plan's original file-edge hypothesis was measured and disproved.**

## Performance

- **Duration:** ~2h 15min (approximate)
- **Started:** ~2026-09-12T13:45Z (approximate)
- **Completed:** 2026-09-12T15:58:28Z
- **Tasks:** 3 completed
- **Files modified:** 3 (`app/services/tactic_detector.py`, `tests/services/test_tactic_detector.py`, `tests/scripts/tagger/precision_floors.py`)

## Accomplishments

- **Fix 1 (deflection, D-12):** condition 10's promotion branch restored to cook's single OR — `square in grandpa_board.attacks(orig_sq)` OR (`is_promotion AND same_file AND pov_attacks_from_init`) — replacing an if/elif that silently skipped the attacks disjunct for every promotion move. TRAIN TP 490→618 (+128), FP unchanged (2); TEST TP 197→247 (+50), FP 0→1 (still 0.996, well above the 0.92 floor).
- **Fix 2 (fork, D-12):** the D-01 "relevance gate" (skip a depth>0 fork when material at the line's end is below its start) removed entirely — cook has no such gate. TRAIN TP 1168→1184 in task 1 (further to 1195 by task 3 via freed dispatch slots), FP unchanged (3).
- **Fix 3 (trapped-piece, D-12):** the empty-escape-set early `return False` deleted; the existing Gate-5 fallthrough now correctly returns True for an attacked, unpinned, non-pawn/non-king piece with zero legal escapes, matching cook's immobile-attacked rule. TRAIN TP 576→622 (+46), FP unchanged (0).
- **Fix 4 (discovered-attack recapture, D-12):** the recapture guard now `return`s (short-circuits the whole predicate) instead of `continue`-ing past it, anchored by FUNCTION so `detect_skewer`'s visually identical (and correct) guard is untouched. TRAIN FP 5→0, TEST FP 4→0 — precision 0.990/0.982 → 1.000/1.000 on both splits.
- **Fix 5 (discovered-attack depth, D-11):** depth is now the pov move index `k` (matching `detect_skewer`'s own convention), not the prior port's `max(0, k-1)`. Exactly one hand-confirmed fixture flips motif under this change (re-labelled `fork` with a D-11 note, moved from `_DISCOVERED_ATTACK_FIXTURES` to `_FORK_FIXTURES`); nine other discovered-attack fixtures shift depth by one without changing motif (unaffected, per plan).
- **Fix 6 (boden/double-bishop, D-12):** oracle-verified. See "Boden/double-bishop oracle finding" below — the plan's file-edge hypothesis was disproved by `scripts/research/oracle_compare.py`, so the fix implemented is cook's *actual* asymmetric file-relation formula (verified by reading cook's source for comparison only, never copied), which corrects exactly the 1 row where both detectors already fire but disagree on bucket. TRAIN TP 441→442 (+1).
- **Fix 7 (self-interference, D-12):** the `("self-interference", SELF_INTERFERENCE)` tuple removed from `_TIER3_REGISTRY`; the dispatcher iterates only that registry, so int 14 can never win dispatch again. `TacticMotifInt.SELF_INTERFERENCE`, `_INT_TO_MOTIF[14]`, `_MOTIF_TO_INT["self-interference"]` and `detect_self_interference` all remain callable/importable for existing persisted rows and the three pre-existing regression tests, which pass unmodified.
- Every fix-site comment was rewritten to describe the new behavior (CLAUDE.md bug-fix-comment discipline) — no comment describing removed behavior was left in place.
- No `PRECISION_FLOOR` value was ever lowered. `discovered-attack` was raised 0.93→0.95 to lock in its zero-FP gain; all other floors are unchanged in value (only their measurement comments updated where this plan's fixes directly moved that motif's counts).

## Boden/double-bishop oracle finding (fix 6 root-cause pivot)

Per the plan's own instruction ("before writing it, run `scripts/research/oracle_compare.py` and confirm ... If the oracle shows a different cause, stop and record the finding rather than shipping a guess"), I ran the oracle comparison before touching this detector:

```
motif                    both  cookOnly  oursOnly  neither   err
bodenMate                 602       175         0    25872     0
doubleBishopMate            5       510         1    26133     0
```

`cookOnly` for `bodenMate` (175) and `doubleBishopMate` (510) means cook fires that motif but our detector fires **neither** motif at all — this is a **firing gap**, not a bucket misclassification, and it is much larger than the plan's "6 rows move double-bishop → boden" hypothesis. A follow-up diagnostic script (calling both detectors directly, not committed to the repo — scratch analysis only) isolated the two populations precisely:

```
{'match': 607, 'ours_none_cook_boden': 174, 'ours_none_cook_dbl': 510,
 'ours_wrong_bucket_boden_to_dbl': 1, 'ours_wrong_bucket_dbl_to_boden': 0,
 'ours_fires_cook_none': 0}
```

Only **1 row** total is a genuine bucket mismatch (`ours_wrong_bucket_boden_to_dbl`); 684 rows (174+510) are cases where our detector returns `(None, None, None)` entirely (usually because `boards[-1].is_checkmate()` is `False` on our parsed board even though cook's own checkmate determination fires — confirmed by direct inspection of one `none_cook_boden` example) while cook fires. That is a structurally different, undiagnosed problem — almost certainly a mate-detection or PV-scope difference, not anything to do with file-relation geometry — and is **out of scope for this plan's seven listed port fixes**.

For the 1 genuine bucket-mismatch row (`byLsg`), reading cook.py's real formula (for oracle-verification purposes only — no source copied into this repo) showed it is **not** a symmetric "opposite sides" XOR as RESEARCH assumed, but an asymmetric test keyed on python-chess's own bishop-iteration order:

```
(bishop_squares[0] LEFT of king's file) == (bishop_squares[1] RIGHT of king's file)
```

This differs from the prior symmetric `(b1<king) != (b2<king)` port specifically when the **second** bishop (by ascending square index) sits **on** the king's file — the prior code silently treated on-file as right-of-file for that bishop only. The implemented fix matches cook's asymmetric formula exactly; re-running the diagnostic afterward confirmed the mismatch count dropped 1→0 with no new mismatches introduced (`match` 607→608).

**Recommendation for a future phase:** investigate why `detect_boden_or_double_bishop_mate` (and likely other mate detectors sharing the same `boards[-1].is_checkmate()` gate) misses 684 CC0 rows cook tags as boden/double-bishop-mate — both motifs already map to the same `mate` family in `FAMILY_TO_MOTIF_INTS`, so the user-facing impact of NOT chasing this now is zero, but the detector's true recall on these two motifs is far lower than the 100% TRAIN precision numbers suggest (recall was never the gated metric here).

## Per-motif before/after (TRAIN 18,632 rows / TEST 8,017 rows, all three tasks combined)

| Motif | TRAIN TP b→a | TRAIN FP b→a | TRAIN P b→a | TEST TP b→a | TEST FP b→a | TEST P b→a |
|---|---|---|---|---|---|---|
| anastasia-mate | 460→460 | 0→0 | 1.000→1.000 | 219→219 | 0→0 | 1.000→1.000 |
| arabian-mate | 537→537 | 0→0 | 1.000→1.000 | 251→251 | 0→0 | 1.000→1.000 |
| attraction | 854→852 | 0→0 | 1.000→1.000 | 383→383 | 0→0 | 1.000→1.000 |
| back-rank-mate | 891→891 | 0→0 | 1.000→1.000 | 358→358 | 0→0 | 1.000→1.000 |
| **boden-mate** | **441→442** | 0→0 | 1.000→1.000 | 161→161 | 0→0 | 1.000→1.000 |
| capturing-defender | 347→349 | 0→0 | 1.000→1.000 | 136→137 | 0→0 | 1.000→1.000 |
| clearance | 399→399 | 0→0 | 1.000→1.000 | 159→159 | 0→0 | 1.000→1.000 |
| **deflection** | **490→618** | 2→2 | 0.996→0.997 | **197→247** | 0→1 | 1.000→0.996 |
| **discovered-attack** | **490→456** | **5→0** | **0.990→1.000** | **216→208** | **4→0** | **0.982→1.000** |
| discovered-check | 672→672 | 33→33 | 0.953→0.953 | 276→276 | 19→19 | 0.936→0.936 |
| double-check | 232→231 | 0→0 | 1.000→1.000 | 77→77 | 0→0 | 1.000→1.000 |
| dovetail-mate | 522→522 | 0→0 | 1.000→1.000 | 249→249 | 0→0 | 1.000→1.000 |
| en-passant | 1219→1221 | 0→0 | 1.000→1.000 | 529→531 | 0→0 | 1.000→1.000 |
| **fork** | **1168→1195** | 3→3 | 0.997→0.997 | **509→514** | 0→0 | 1.000→1.000 |
| hanging-piece | 631→631 | 0→0 | 1.000→1.000 | 271→271 | 0→0 | 1.000→1.000 |
| hook-mate | 602→602 | 0→0 | 1.000→1.000 | 213→213 | 0→0 | 1.000→1.000 |
| interference | 338→338 | 1→1 | 0.997→0.997 | 160→160 | 0→0 | 1.000→1.000 |
| intermezzo | 462→462 | 0→0 | 1.000→1.000 | 198→198 | 0→0 | 1.000→1.000 |
| mate | 2543→2543 | 0→0 | 1.000→1.000 | 1094→1094 | 0→0 | 1.000→1.000 |
| pin | 967→979 | 2→2 | 0.998→0.998 | 417→420 | 0→0 | 1.000→1.000 |
| promotion | 1816→1709 | 0→0 | 1.000→1.000 | 784→740 | 0→0 | 1.000→1.000 |
| sacrifice | 409→397 | 0→0 | 1.000→1.000 | 186→183 | 0→0 | 1.000→1.000 |
| skewer | 472→477 | 0→0 | 1.000→1.000 | 217→222 | 0→0 | 1.000→1.000 |
| smothered-mate | 474→474 | 0→0 | 1.000→1.000 | 242→242 | 0→0 | 1.000→1.000 |
| **trapped-piece** | **576→622** | 0→0 | 1.000→1.000 | 253→268 | 0→0 | 1.000→1.000 |
| under-promotion | 253→237 | 0→0 | 1.000→1.000 | 116→105 | 0→0 | 1.000→1.000 |
| x-ray | 269→269 | 0→0 | 1.000→1.000 | 106→106 | 0→0 | 1.000→1.000 |

**Bold** rows are motifs this plan's seven fixes directly target. All other TP movements (attraction, capturing-defender, double-check, en-passant, pin, promotion, sacrifice, skewer, under-promotion) are winner-take-all dispatch redistribution: freed or newly-contested dispatch slots from the six changed detectors, not a change to those detectors themselves. No FP count rose for any motif on TRAIN; deflection's TEST FP rose 0→1 (still comfortably above its 0.92 floor at 0.996 precision) as the one measured tradeoff of restoring the promotion OR.

## Task Commits

Each task was committed atomically:

1. **T-221-02-01: Restore the three recall-costing cook divergences (deflection OR, fork gate, trapped-piece empty escape)** — `5abf03e0d` (feat)
2. **T-221-02-02: Discovered-attack recapture return and depth = k (D-11), plus the boden file edge** — `ce4ad59bd` (feat)
3. **T-221-02-03: Take `self-interference` out of dispatch while keeping int 14 storable** — `bb4186894` (feat)

**Plan metadata:** committed separately per `git_commit_metadata` (see `docs(221-02)` commit below).

## Files Created/Modified

- `app/services/tactic_detector.py` — the seven port fixes, all fix-site comments rewritten
- `tests/services/test_tactic_detector.py` — 2 new deflection fixtures, 1 new fork fixture, 1 re-labelled discovered-attack→fork fixture, 1 rewritten trapped-piece test, 3 new discovered-attack behavioral tests, 1 new self-interference registry test
- `tests/scripts/tagger/precision_floors.py` — measurement comments updated for fork, deflection, trapped-piece, discovered-attack (floor raised 0.93→0.95), boden-mate; `SUPPRESSED_MOTIFS` self-interference entry annotated with the Phase 221 undispatchable note

## Decisions Made

- Scoped `precision_floors.py` comment updates to the six motifs this plan's fixes directly target, rather than chasing every incidental TP ripple from dispatch redistribution (documented instead in the before/after table above) — those ripples will move again as plans 03-06 touch the same detectors, so per-line comment churn there would be immediately stale.
- Implemented fix 6 from cook's *actual* verified formula (read from the local AGPL clone for oracle-comparison purposes only, per the existing AGPL-boundary convention — prose/behavior only, no source copied into this repo) rather than the plan's hypothesized symmetric XOR, because the oracle disproved the hypothesis before any code was written.
- Did not attempt to close the 684-row boden/double-bishop firing gap the oracle surfaced — out of scope for TAGFIX-05's seven listed fixes; documented above for a future phase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fix 6 implemented from the oracle-verified formula, not the plan's hypothesized one**
- **Found during:** Task 2 (boden/double-bishop file edge)
- **Issue:** The plan's RESEARCH.md hypothesized a symmetric "opposite sides" XOR bug producing ~6 reclassified rows. Running `scripts/research/oracle_compare.py` per the plan's own explicit instruction showed the real discrepancy is a 684-row firing gap unrelated to file geometry, with only 1 genuine bucket-mismatch row — and that row's cause is cook's actual asymmetric file-relation formula, not a symmetric XOR.
- **Fix:** Implemented the asymmetric formula (verified against cook's source for comparison only), which correctly resolves the 1 real mismatch without touching the separate, larger, undiagnosed firing gap.
- **Files modified:** `app/services/tactic_detector.py`
- **Verification:** Diagnostic re-run confirmed the mismatch count dropped 1→0 with zero new mismatches; `uv run pytest tests/scripts/tagger -q` and `tests/services/test_tactic_detector.py -q` both green, no floor lowered.
- **Committed in:** `ce4ad59bd` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — the plan's own explicit "stop and record if the oracle disagrees" instruction was followed, and the disproved hypothesis was corrected in favor of the oracle-verified one rather than shipped as a guess).
**Impact on plan:** No scope creep. The fix delivered is narrower than the plan anticipated (1 row, not ~6), and the larger gap the oracle revealed is explicitly deferred rather than silently absorbed or ignored.

## Issues Encountered

- **Self-caught working-tree incident (no lasting impact):** `scripts/research/oracle_compare.py` writes `oracle_disagreements.json` to the project root as a side effect of running it (not parameterized to a tmp path). This produced one untracked file after the first run; caught via `git status --short` before any commit and deleted — never staged or committed.
- **`gsd_run windows append` failed cleanly:** attempted to record the boden/double-bishop firing-gap finding in the cross-phase `.planning/WINDOWS.md` ledger; the command reported a pre-existing table/JSON disagreement for an unrelated row (id 8) in that file, not caused by this plan. Per the executor protocol the ledger is best-effort and optional — no write was attempted or made, and the finding is fully documented in this SUMMARY instead (the required fallback location per the plan's own instruction for this exact scenario).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Ready for plan 03 (or whichever plan lands next per the wave sequence) — all seven port divergences are cook-aligned, every fix-site comment describes the new behavior, and the fixture/precision-floor gate is green with real headroom on every floor this plan touched.
- **Carried forward:** the boden/double-bishop 684-row firing gap (see finding above) is unfixed and undiagnosed — flag for a future phase; not blocking for this milestone since both motifs already map to the same `mate` family.
- `uv run pytest -n auto -x` (whole suite, excluding the tagger harness per `pyproject.toml`'s `addopts`) passed 4616/4616 (19 skipped) — nothing outside this plan's scope regressed.

## Self-Check: PASSED

All 3 modified files found on disk with the expected changes; all 3 task commit hashes (`5abf03e0d`, `ce4ad59bd`, `bb4186894`) found in `git log --oneline --all`.

---
*Phase: 221-tactic-tagger-real-game-precision-winning-floor-predicate-ti*
*Completed: 2026-09-12*
