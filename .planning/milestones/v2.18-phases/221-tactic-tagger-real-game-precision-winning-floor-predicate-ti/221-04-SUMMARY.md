---
phase: 221-tactic-tagger-real-game-precision-winning-floor-predicate-ti
plan: 04
subsystem: tactic-tagger
tags: [forcing-line-gate, winning-floor, tactic-detector, missed-orientation, cook-alignment]

requires:
  - phase: 221-02
    provides: seven fixture-verified cook-port fixes (D-11 discovered-attack depth=k,
      self-interference removed from _TIER3_REGISTRY) that this plan's floor map and
      firing-node reads assume are already in place
provides:
  - "app/services/tactic_detector.py: FIRING_FLOOR_TIER3_CP/FIRING_FLOOR_GEOMETRIC_CP,
    _MOTIF_FLOOR_CP (derived from the tier registries), floor_cp_for_motif() -- the
    gate's only import from the detector"
  - "app/services/forcing_line_gate.py: _solver_eval_at_firing, _passes_winning_floor,
    passes_winning_floor_fallback; apply_forcing_line_filter widened with two
    defaulted keywords (motif_int, pre_flaw_eval_mate); _is_already_winning derives
    the already-winning reject from eval_mate when cp is absent"
  - "app/services/flaws_service.py: _pre_flaw_eval_mate, _firing_floor_fallback_eval,
    _build_missed_board_with_stack; _classify_tactic_gated's gate now always runs on
    a non-empty blob and a blobless flaw faces the same tier floor via
    game_positions; the missed pass carries a one-move stack"
affects: [221-05, 221-06, 221-07]

actuals:
  tokens: 18184
  tasks: 3
  commits: 3
  plan_head_before: 2ed33d34ac611e5f956febb5e269a130efef2cef

tech-stack:
  added: []
  patterns:
    - "tier-to-floor map DERIVED from the dispatcher's own tier registries
      (_GEOMETRIC_REGISTRY / _TIER3_REGISTRY / _MOVE_TYPE_REGISTRY / MATE_MOTIFS)
      rather than re-listed by motif name, so a future registry change cannot
      silently arrive floor-less"
    - "widen a gate function by APPENDING defaulted keyword params after existing
      ones, never changing existing positional order -- keeps ~50 pre-existing
      call sites byte-identical"
    - "isolate a detector-level fix's dev-DB impact with a scratch (uncommitted)
      measurement script that toggles ONLY the one code path under test (stacked
      vs stackless board), holding every other Phase 221 change fixed, rather
      than running the full retag and conflating multiple plans' effects"

key-files:
  created: []
  modified:
    - app/services/tactic_detector.py
    - app/services/forcing_line_gate.py
    - app/services/flaws_service.py
    - tests/services/test_forcing_line_gate.py
    - tests/services/test_flaws_service.py
    - tests/scripts/test_ab_validate_gate.py
    - tests/scripts/test_retag_flaws.py

key-decisions:
  - "floor_cp_for_motif lives in tactic_detector.py beside the tier registries
    (D-01's literal instruction); forcing_line_gate.py imports it. This is the
    only cross-module import either file gains -- verified cycle-free (detector
    imports nothing app-internal)."
  - "_is_already_winning's cp/mate branches are exclusive, not additive: a
    present eval_mate decides via eval_mate_to_expected_score and NEVER falls
    through to the cp comparison, matching D-04's 'derived from eval_mate when
    cp is absent' wording exactly (not 'in addition to')."
  - "_firing_floor_fallback_eval keeps the orientation index switch (positions[n]
    vs positions[n-1]) inside ONE function rather than two inline reads at the
    call site -- this is the exact defensive shape T-221-16 the threat register
    calls for, mirroring the Phase 143 pre_flaw_eval_cp off-by-one class."
  - "_build_missed_board_with_stack degrades to None (never raises) on ply 0, a
    malformed previous SAN, or a missing fen_map[n-1] entry; the caller
    (_detect_tactic_for_flaw) falls back to the pre-existing stackless
    board_before in every case -- the dest-square gate deliberately keeps
    reading the ORIGINAL stackless board_before even when the stacked board is
    available, per the plan's explicit instruction (avoids a subtle
    SAN-disambiguation risk from rebinding that gate to a different object)."
  - "Retroactively wrote the #3968 plan-commit ledger sentinel after the fact
    (not created before the first commit this session) -- reconstructed from
    the branch's known pre-plan HEAD (2ed33d34a, the 221-03 completion commit
    visible in git log at session start) rather than skipped."

requirements-completed: [TAGFIX-01, TAGFIX-02, TAGFIX-06]

coverage:
  - id: D1
    description: "Per-tier winning floor (0cp geometric / +200cp tier-3+move-type) at the firing node, derived from the tier registries, exempting mate motifs and unreadable/placeholder nodes"
    requirement: TAGFIX-01
    verification:
      - kind: unit
        ref: "tests/services/test_forcing_line_gate.py::TestWinningFloorAtFiring (17 tests: boundary at 200/199 and 0/-1 both solver colors, mate exemption, unreadable-node exemption, odd-depth rounding)"
        status: pass
      - kind: unit
        ref: "tests/services/test_forcing_line_gate.py::TestConstants (floor_cp_for_motif representative + full-registry-coverage tests)"
        status: pass
      - kind: other
        ref: "uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200 (no breaches)"
        status: pass
    human_judgment: false
  - id: D2
    description: "apply_forcing_line_filter widened with two defaulted keywords (motif_int, pre_flaw_eval_mate) appended after margin -- every pre-existing call site (~50 gate tests, test_eval_drain.py, scripts/ab_validate_gate.py) keeps compiling and behaving byte-identically"
    requirement: TAGFIX-01
    verification:
      - kind: unit
        ref: "uv run pytest tests/services/test_forcing_line_gate.py tests/services/test_eval_drain.py -q (105/105 pre-existing + new tests pass unmodified)"
        status: pass
      - kind: other
        ref: "uv run python -c \"import inspect;from app.services.forcing_line_gate import apply_forcing_line_filter as a;p=inspect.signature(a).parameters;assert list(p)[-2:]==['motif_int','pre_flaw_eval_mate']\""
        status: pass
    human_judgment: false
  - id: D3
    description: "The gate is never skipped merely because pre_flaw_eval_cp is None (TAGFIX-02); the already-winning reject is derived from eval_mate via _pre_flaw_eval_mate when cp is absent (D-04), with the mate-firing-node exemption preserved"
    requirement: TAGFIX-02
    verification:
      - kind: unit
        ref: "tests/services/test_flaws_service.py::TestClassifyTacticGated (6 new TAGFIX-02 tests: gate-runs-on-none-cp behavioral proof, forced-mate reject white+black, mate-firing-node exemption, both-None still-runs, mate-against-solver sign check)"
        status: pass
      - kind: unit
        ref: "tests/services/test_flaws_service.py::TestClassifyTacticGatedBlobsPending (4 tests, byte-unmodified bodies -- git diff confirms no change inside the class)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A blobless flaw (pv_blob is None) still faces its tier's winning floor via a game_positions fallback (_firing_floor_fallback_eval + passes_winning_floor_fallback); the [] sentinel keeps its unconditional skip-everything semantics"
    requirement: TAGFIX-01
    verification:
      - kind: unit
        ref: "tests/services/test_flaws_service.py::TestClassifyTacticGated (6 new D-03 fallback tests: allowed/missed below-floor suppressed with DIFFERENT stored values per orientation, allowed/missed winning credited, both-columns-None credited, [] sentinel unaffected)"
        status: pass
      - kind: other
        ref: "fail-first orientation-index swap (idx = n-1 if allowed else n) -- 3 tests went RED with the swap in place, confirmed via a live revert-and-rerun (see body); reverted, full suite green again"
        status: pass
    human_judgment: false
  - id: D5
    description: "The missed pass builds board_before with a one-move stack (the opponent's previous move, D-09), unblocking detect_intermezzo's k=2 branch and detect_hanging_piece's recapture exclusion (D-10) on the missed side; every degradation path falls back to the stackless build with an asserted identical result"
    requirement: TAGFIX-06
    verification:
      - kind: unit
        ref: "tests/services/test_flaws_service.py::TestMissedOrientationParity (9 tests: stack shape+turn, intermezzo k=2 fires with a stackless control proving it doesn't without the fix, hanging-piece recapture suppressed vs credited, 3 degradation paths with explicit same-result assertions)"
        status: pass
      - kind: other
        ref: "uv run python -c \"...assert 'D-10' in inspect.getsource(detect_hanging_piece)\" (positive check the rewritten comment names the decision)"
        status: pass
      - kind: other
        ref: "dev-DB scratch measurement isolating only this fix: missed intermezzo 15->55 (allowed 64, now within 3x), missed hanging-piece 383->327 (56 rows newly suppressed)"
        status: pass
    human_judgment: false

duration: 3h 5min (approximate)
completed: 2026-09-12
status: complete
---

# Phase 221 Plan 04: Winning Floor, Gate-Always-Runs, and Missed-Orientation Parity Summary

**A per-tier winning floor at the firing node (0cp geometric / +200cp tier-3+move-type), a forcing-line gate that always runs (with a mate-derived already-winning reject and a game_positions fallback floor when there's no blob), and a missed pass that finally carries the opponent's previous move on its board stack — unblocking `detect_intermezzo`'s k=2 branch and `detect_hanging_piece`'s recapture exclusion on the missed side.**

## Performance

- **Duration:** ~3h 5min (approximate)
- **Tasks:** 3 completed
- **Files modified:** 7 (`app/services/tactic_detector.py`, `app/services/forcing_line_gate.py`, `app/services/flaws_service.py`, `tests/services/test_forcing_line_gate.py`, `tests/services/test_flaws_service.py`, `tests/scripts/test_ab_validate_gate.py`, `tests/scripts/test_retag_flaws.py`)

## Accomplishments

- **Task 1 (TAGFIX-01, D-01/D-02/D-03):** `tactic_detector.py` gained `FIRING_FLOOR_TIER3_CP = 200`, `FIRING_FLOOR_GEOMETRIC_CP = 0`, and a derived `_MOTIF_FLOOR_CP` map (built from `_GEOMETRIC_REGISTRY` + `HANGING_PIECE` + `_TIER3_REGISTRY` + `_MOVE_TYPE_REGISTRY`, exempting `MATE_MOTIFS`) exposed through `floor_cp_for_motif(motif_int)`. `forcing_line_gate.py` gained `_solver_eval_at_firing` (rounds an odd firing depth up to the solver node, `bm` before `b`), `_passes_winning_floor`, and `passes_winning_floor_fallback` (the blob-missing entry point). `apply_forcing_line_filter` gained two defaulted keywords (`motif_int`, `pre_flaw_eval_mate`) appended after `margin`, and its `pre_flaw_eval_cp` parameter widened to `int | None` — every pre-existing call site keeps compiling and behaving byte-identically (verified: 105/105 pre-existing gate + eval_drain tests pass unmodified, `scripts/ab_validate_gate` imports clean).
- **Task 2 (TAGFIX-02, D-04):** `_classify_tactic_gated`'s gate-skip condition dropped the `pre_flaw_eval_cp is not None` conjunct — the gate now always runs on a non-empty blob. New `_pre_flaw_eval_mate` and `_firing_floor_fallback_eval` helpers (both derived from the `positions` list every caller already passes — **no new parameter crossed `_classify_tactic_gated`'s signature**, so all four call sites are untouched). `_is_already_winning` widened to a two-branch form: a forced mate for the solver rejects outright (via `eval_mate_to_expected_score`); otherwise the existing 800cp comparison runs unchanged. The retained `blobs_pending` conjunct (which also keys on `pre_flaw_eval_cp is not None`) got an explicit comment recording that it is a DIFFERENT carve-out from the one TAGFIX-02 removed, per the threat register's T-221-20 mitigation.
- **Task 3 (TAGFIX-06, D-09/D-10):** New `_build_missed_board_with_stack(n, fen_map, positions)` builds the missed-pass decision board from `fen_map[n-1]` plus `positions[n-1].move_san` pushed — position-identical to the existing stackless build but with a real one-move stack. Wired into `_detect_tactic_for_flaw`'s missed branch with a fallback to the pre-existing stackless `board_before` on any degradation; the dest-square gate deliberately keeps reading the original stackless board. `detect_hanging_piece`'s recapture-exclusion comment rewritten to record that it now applies on both orientations (D-10) — no new detector branch needed, since the existing `if board_before.move_stack:` guard just starts firing once the missed board actually carries one.
- Fixed three pre-existing test consumers broken by the widened gate signature and the new fallback-floor behavior (see Deviations).

## Boundary test matrix (T-221-04-01, `TestWinningFloorAtFiring`)

| Value | Tier | Solver | Expected |
|---|---|---|---|
| 200 (b) | tier-3 (SACRIFICE) | white | credited |
| 199 (b) | tier-3 (SACRIFICE) | white | rejected |
| solver_cp=200 (mirrored, b=-200) | tier-3 (SACRIFICE) | black | credited |
| solver_cp=199 (mirrored, b=-199) | tier-3 (SACRIFICE) | black | rejected |
| 0 (b) | geometric (FORK) | white | credited |
| -1 (b) | geometric (FORK) | white | rejected |
| solver_cp=0 (mirrored, b=0) | geometric (FORK) | black | credited |
| solver_cp=-1 (mirrored, b=1) | geometric (FORK) | black | rejected |
| bm=3 at firing node | tier-3 (SACRIFICE) | white | credited (mate exemption) |
| b=-500 | MATE motif int | white | credited (motif-exempt) |
| b=-500 | motif_int=None | white | credited (back-compat) |
| odd firing_depth=1, rounds to idx2 | tier-3 (SACRIFICE) | white | reads idx2, not idx1 |
| bm set AND b set | — | — | `_solver_eval_at_firing` reads bm, ignores b |
| all-None placeholder node | tier-3 (SACRIFICE) | white | credited (unreadable → never suppress) |
| firing_depth past line end | tier-3 (SACRIFICE) | white | rejected by the pre-existing truncation check, NOT the floor (isolated via a direct `_passes_winning_floor` call returning True) |
| firing_depth=0 | tier-3 / geometric | white | floor-checked at node 0 (same cases as the first four rows) |

Full 17-test class collected via `uv run pytest tests/services/test_forcing_line_gate.py --collect-only -q | grep -c TestWinningFloorAtFiring`.

## Fail-first proof: D-03 orientation-index swap (T-221-04-02 acceptance criterion)

Temporarily swapped `_firing_floor_fallback_eval`'s orientation branches (`idx = n - 1 if orientation == "allowed" else n` instead of the correct `idx = n if orientation == "allowed" else n - 1`), then re-ran the D-03 fallback tests:

```
FAILED tests/services/test_flaws_service.py::TestClassifyTacticGated::test_d03_fallback_missed_winning_eval_credited
AssertionError: D-03: a winning missed-orientation fallback eval must be credited
assert None == <TacticMotifInt.HANGING_PIECE: 2>

FAILED tests/services/test_flaws_service.py::TestClassifyTacticGated::test_d03_fallback_both_columns_none_credited
AssertionError: D-03: an unreadable fallback (both columns None) must never suppress
assert None == <TacticMotifInt.HANGING_PIECE: 2>

3 failed, 2 passed, 153 deselected
```

All three went RED as predicted (the allowed-vs-missed tests use DIFFERENT stored eval values at `positions[5]` vs `positions[4]` specifically so a swapped index flips outcomes rather than coincidentally passing). Reverted the swap; full suite green again (158/158 in `test_flaws_service.py` at that point, 167/167 after task 3's additions).

## Dev allowed-vs-missed counts (T-221-04-03 acceptance criterion)

Measured with an uncommitted scratch script (`/tmp/.../measure_tagfix06.py`, deleted after use — never staged) that replays every currently-tagged flaw's MISSED orientation twice against the live detector: once with today's stackless board, once with `_build_missed_board_with_stack`'s stacked board, holding the PV/eval fixed. This isolates ONLY the D-09/D-10 effect (not conflated with plans 01–03's already-landed changes, which affect both measurements identically):

| | Allowed (unaffected) | Missed BEFORE (stackless) | Missed AFTER (stacked) |
|---|---:|---:|---:|
| intermezzo | 64 | 15 | 55 |
| hanging-piece | 1216 | 383 | 327 |

Missed intermezzo moved from 4.3x below allowed (64:15) to within 1.16x (64:55) — inside the phase's "missed intermezzo within 3x of allowed" acceptance target. Hanging-piece dropped by 56 rows (equal/greater-value recaptures now correctly excluded, D-10), from 383 to 327.

## Rewritten `_classify_tactic_gated` docstring (T-221-04-02 output requirement)

Exact current text (see `app/services/flaws_service.py`):

```
    """Run tactic detection then apply the forcing-line gate (D-02, SC4 single classify path).

    Calls _detect_tactic_for_flaw, then — only when a motif was detected AND
    pv_blob is a non-empty list — applies apply_forcing_line_filter at the
    given margin. If the line is non-forcing, returns (None, None, None, None)
    to suppress the motif.

    TAGFIX-02 (D-04): the gate ALWAYS runs on a non-empty blob now -- it is no
    longer skipped merely because pre_flaw_eval_cp is None. The already-winning
    reject is derived from _pre_flaw_eval_mate when cp is absent: a forced mate
    for the solver before the flaw is already winning and rejects a non-mate
    motif (mate-motif tags stay exempt via the gate's existing forced-mate
    carve-out). The rest of the gate (only-move, the per-tier winning floor,
    strips, one-mover discard) runs on the blob exactly as for cp-scored flaws.

    When pv_blob is None (pre-Phase-142 rows with no stored blob, or a flaw
    whose continuation blob has not yet been computed), the gate itself is
    still skipped -- but TAGFIX-01 / D-03 now applies the motif's per-tier
    winning floor directly from game_positions (_firing_floor_fallback_eval +
    forcing_line_gate.passes_winning_floor_fallback): no tag is skipped or
    suppressed merely for lacking a blob, but a blobless tag still faces the
    same "solver must be winning at the firing node" bar as a blob-backed one.

    D-06 sentinel: an empty list [] means the blob could not be assembled for this
    flaw (e.g. single-legal-move position, analysis gap). BOTH the gate and the
    D-03 fallback floor are SKIPPED for [] — same outcome as before (no
    suppression, raw kernel result returned). Gate condition is
    `pv_blob is not None and len(pv_blob) > 0`; the fallback condition is
    `pv_blob is None` exactly (never for []) — superseding the Phase-143
    Pitfall-2 wording that treated [] as a gate-eligible blob requiring the
    one-mover discard. apply_forcing_line_filter itself still rejects [] when
    called directly; the skip here is intentional and upstream of that call.

    blobs_pending (Phase 147, D-01/D-03): an independent, explicitly-passed signal
    (never derived from pv_blob) meaning the continuation blob for this flaw is
    deferred to a later tier-4 pass (the remote go-forward submit path). When True
    AND a motif was detected AND pv_blob is None AND pre_flaw_eval_cp is not None,
    the motif cannot yet be gate-checked, so it is suppressed to NULL rather than
    persisted raw/ungated. This self-heals when the tier-4 D-07 gated retag lands
    with the real blob. Mate-adjacent (pre_flaw_eval_cp is None) and the D-06 []
    sentinel are FINAL cases and are NEVER suppressed by this branch. T-221-20:
    this pre_flaw_eval_cp is not None conjunct is DELIBERATELY independent of the
    conjunct TAGFIX-02 removed from the gate-run condition above — it is the
    "mate-adjacent is a FINAL case, never suppressed by blobs_pending" carve-out,
    not the same condition. Do not consolidate the two.
    """
```

## Count of dev rows whose tag changed, per TAGFIX

Not separable at full precision within this plan's scope — a true "which tag changed because of exactly TAGFIX-01 vs TAGFIX-02 vs TAGFIX-06" count requires running the FULL classify path (including the other two fixes) against the same dev row, which conflates all three fixes' effects on any row where more than one applies (e.g., a mate-adjacent tier-3 tag is subject to both TAGFIX-01's floor and TAGFIX-02's mate-derived reject simultaneously). What IS separable and reported above: TAGFIX-06's isolated missed-intermezzo/hanging-piece delta (15→55, 383→327), measured by toggling only the stack-construction code path. TAGFIX-01/TAGFIX-02's combined effect is deferred to the phase's dev-retag smoke (a later plan per the phase sequencing in CONTEXT.md/RESEARCH.md), which will produce the four-bucket removed/survived/motif-shifted/depth-shifted report Plan 03 built specifically for that purpose.

## Task Commits

Each task was committed atomically:

1. **T-221-04-01: Tier-to-floor map beside the registries, and a winning-floor check at the firing node** — `3fa874f07` (feat)
2. **T-221-04-02: The gate always runs — mate-derived already-winning reject and the blob-missing fallback floor** — `33296bb26` (feat)
3. **T-221-04-03: Missed-orientation parity — a real move stack on the missed board (D-09, D-10)** — `a5aa4ae70` (feat)

**Plan metadata:** committed separately per `git_commit_metadata` (see `docs(221-04)` commit below).

## Files Created/Modified

- `app/services/tactic_detector.py` — `FIRING_FLOOR_TIER3_CP`, `FIRING_FLOOR_GEOMETRIC_CP`, `_MOTIF_FLOOR_CP`, `_MATE_MOTIF_INTS`, `floor_cp_for_motif`; rewritten `detect_hanging_piece` recapture-exclusion comment (D-10)
- `app/services/forcing_line_gate.py` — `_solver_eval_at_firing`, `_passes_winning_floor`, `passes_winning_floor_fallback`; widened `_is_already_winning` and `apply_forcing_line_filter`; rewritten `_is_forced_mate_firing` docstring paragraph (dead WR-02/SEED-079 prose replaced)
- `app/services/flaws_service.py` — `_pre_flaw_eval_mate`, `_firing_floor_fallback_eval`, `_build_missed_board_with_stack`; rewritten `_classify_tactic_gated` gate-skip logic + docstring; missed branch now builds a stacked detection board
- `tests/services/test_forcing_line_gate.py` — `TestWinningFloorAtFiring` (17 tests), `TestConstants` extensions (4 new tests)
- `tests/services/test_flaws_service.py` — 6 new TAGFIX-02 tests, 6 new D-03 fallback tests (all in `TestClassifyTacticGated`), `TestMissedOrientationParity` (9 tests)
- `tests/scripts/test_ab_validate_gate.py` — `_spy_gate` widened to accept the two new gate keywords (Rule 3 deviation)
- `tests/scripts/test_retag_flaws.py` — bare-`object()` positions replaced with `SimpleNamespace(eval_mate=None)` stand-ins; `_seed_parity_game` gained an `eval_cp_overrides` parameter; the en-passant parity fixture's ply-11 eval bumped to clear the new move-type floor (Rule 3 deviation)

## Decisions Made

- `floor_cp_for_motif` placement: `tactic_detector.py`, beside the tier registries it derives from (D-01's literal instruction) — the gate imports it, not the reverse, keeping the module's "no app-internal imports" property intact on the detector side.
- `_is_already_winning`'s cp/mate branches are exclusive (mate present → decide via mate, never fall through to cp) rather than additive, matching D-04's exact wording.
- `_firing_floor_fallback_eval` keeps the orientation index switch inside one function, not two inline reads at the call site — the explicit defensive shape the threat register's T-221-16 mitigation calls for.
- The dest-square gate in `_detect_tactic_for_flaw`'s missed branch deliberately keeps reading the original stackless `board_before`, never the new stacked board, per the plan's explicit instruction (avoids a subtle SAN-disambiguation risk from rebinding to a different board object).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `test_ab_validate_gate.py`'s `_spy_gate` needed the two new gate keywords**
- **Found during:** Task 2, full-suite verification (`uv run pytest -n auto -x`)
- **Issue:** `TestUngatedArmBypassesGate::test_ungated_arm_bypasses_gate` monkeypatches `apply_forcing_line_filter` with a fixed-signature spy that did not accept `motif_int`/`pre_flaw_eval_mate`, raising `TypeError` the moment `_classify_tactic_gated` started passing them.
- **Fix:** Widened `_spy_gate`'s signature with the same two defaulted keywords and threaded them through to the real function.
- **Files modified:** `tests/scripts/test_ab_validate_gate.py`
- **Verification:** `uv run pytest tests/scripts/test_ab_validate_gate.py::TestUngatedArmBypassesGate -q` green; full suite green after.
- **Committed in:** `33296bb26` (Task 2 commit)

**2. [Rule 3 - Blocking] `test_retag_flaws.py::TestPreFlawEvalParity`'s bare `object()` stand-ins lacked `.eval_mate`**
- **Found during:** Task 2, full-suite verification
- **Issue:** `_classify_tactic_gated` now reads `positions[n-1].eval_mate` directly inside the gate-run branch (via `_pre_flaw_eval_mate`), even when the detector itself is monkeypatched — the test's `[object(), object(), object()]` placeholder list raised `AttributeError`.
- **Fix:** Replaced with `SimpleNamespace(eval_mate=None)` stand-ins (matching the file's existing duck-typed-position convention for direct `_classify_tactic_gated` control calls).
- **Files modified:** `tests/scripts/test_retag_flaws.py`
- **Verification:** `uv run pytest tests/scripts/test_retag_flaws.py -q` green (12/12).
- **Committed in:** `33296bb26` (Task 2 commit)

**3. [Rule 1 - Bug] `test_retag_flaws.py`'s en-passant SC4-parity fixture broke under the new D-03 fallback floor**
- **Found during:** Task 2, full-suite verification
- **Issue:** `TestRetagLiveClassifyParity::test_en_passant_missed_parity` seeds every position with a uniform placeholder `eval_cp=0` and asserts `pv_blob=None` still credits `EN_PASSANT` (a move-type motif, floor +200cp). Before this plan, `pv_blob=None` unconditionally skipped ALL gating; now the D-03 fallback floor applies, and `0 < 200` suppressed the tag, breaking the test's own assertion (not a bug in the fix — the fixture's placeholder eval predates the floor it's now subject to).
- **Fix:** Added an `eval_cp_overrides` parameter to the shared `_seed_parity_game` helper and overrode the en-passant fixture's ply-11 eval (the missed-orientation white solver's fallback-read ply) to a clearly-winning value (300), documented inline as a TAGFIX-01/D-03 consequence.
- **Files modified:** `tests/scripts/test_retag_flaws.py`
- **Verification:** `uv run pytest tests/scripts/test_retag_flaws.py -q` green (12/12); the castling fixture (geometric HANGING_PIECE, 0-floor) needed no change since `eval_cp=0 >= 0`.
- **Committed in:** `33296bb26` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (2 blocking test-consumer fixes, 1 bug/fixture-assumption fix). **Impact:** all three are direct, unavoidable consequences of this plan's own widened gate signature and new fallback-floor behavior landing correctly on pre-existing test infrastructure — no scope creep, no unrelated code touched.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Ready for plan 05 (sacrifice/clearance predicates, TAGFIX-03/04) and later plans in this phase. The tier-floor map and the widened gate signature are the foundation those predicates' depth cap and floor checks build on.
- `_firing_floor_fallback_eval`'s orientation-index-swap fail-first proof and `_solver_eval_at_firing`'s odd-depth-rounding proof are both permanent regression guards against the exact off-by-one class Phase 143 already fixed once.
- `uv run pytest -n auto -x` (whole suite, excluding the tagger harness per `pyproject.toml`'s `addopts`) passed 4661/4661 (19 skipped) after all three tasks. `uv run pytest tests/scripts/tagger -q` passed 3/3 with no floor lowered.
- Plan 03's `TestRetagLiveClassifyParity` (SC4 no-drift guard) and `TestPreFlawEvalParity` both still pass — the retag and the live drain agree on the widened gate signature and the new fallback floor.
- TAGFIX-01/TAGFIX-02's combined per-motif dev impact is deferred to the phase's dev-retag smoke (see "Count of dev rows whose tag changed" above) — not a gap in this plan, a deliberate scope boundary given the two fixes' effects overlap on mate-adjacent tier-3 flaws.

## Self-Check: PASSED

All 7 modified files found on disk with the expected changes; all 3 task commit hashes (`3fa874f07`, `33296bb26`, `a5aa4ae70`) found in `git log --oneline --all`.

---
*Phase: 221-tactic-tagger-real-game-precision-winning-floor-predicate-ti*
*Completed: 2026-09-12*
