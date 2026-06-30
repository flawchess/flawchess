---
phase: 141-jsonb-schema-gate-logic
reviewed: 2026-06-29T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - app/models/game_flaw.py
  - app/services/forcing_line_gate.py
  - alembic/versions/20260629_185459_0b6ac7a4b59a_add_pv_lines_blobs_to_game_flaws.py
  - tests/services/test_forcing_line_gate.py
  - tests/test_game_flaws_model.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 141: Code Review Report

**Reviewed:** 2026-06-29
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 141 delivers two nullable deferred JSONB columns on `game_flaws` and a pure-math
forcing-line gate module. The implementation is structurally sound: the deferred=True
guard, migration chain, mate-priority hierarchy, and gate predicate helpers are all
correct. No critical bugs or security issues were found.

One warning-level finding: the blob-shape documentation in `game_flaw.py` specifies
`su — second_uci (str | null)` but the corresponding `PvNode` TypedDict in
`forcing_line_gate.py` declares `su: str` (non-optional). This inconsistency will trap
Phase 142 blob writers who follow the model comment and emit `null` for `su` when
there is no second legal move, producing blobs that violate the TypedDict contract.

Three info items follow: an intentional but unusual unused import, a named boundary
test that does not test the stated boundary, and an untested (though conservatively
handled) edge case in the cp-vs-mate mixed node path.

## Warnings

### WR-01: `su` field is `str | null` in the model comment but `str` (non-optional) in `PvNode`

**File:** `app/models/game_flaw.py:115` and `app/services/forcing_line_gate.py:86`

**Issue:** The model's blob-shape comment on line 115 documents `su` as `(str | null)`,
implying `null` is a valid value when there is no legal second move:

```
su — second_uci (str | null): second-best-move UCI string (e.g. "e2e4").
```

The canonical TypedDict that the gate (and Phase 143 re-tagger) use declares `su: str` —
non-optional. The gate test helpers and in-code conventions use `su=""` (empty string)
as the sentinel for "no second legal move", not `None`. These two representations are
mutually exclusive and the contract is split across two files:

- `game_flaw.py` comment: `null` is acceptable.
- `PvNode` TypedDict: `str` is required.

Phase 142 writers consulting the model comment will write `su: null`, producing JSONB
blobs with `"su": null`. When Phase 143 constructs a `PvNode` from such a blob (or when
`ty check` validates the construction), the `None` value will not satisfy `su: str`,
and any code path that treats `node["su"]` as a string (format, display, UCI parsing)
will fail at runtime with an `AttributeError` or `TypeError`.

The gate itself does not access `node["su"]` in any computation, so this phase is not
affected at runtime. The bug lands in Phase 142/143.

**Fix:** Align the two artifacts to use the empty-string sentinel throughout.

In `app/models/game_flaw.py`, change line 115:
```python
#   su — second_uci (str): second-best-move UCI string (e.g. "e2e4"),
#          or "" when there is no legal second move (mirrors the PvNode TypedDict).
```

In `app/services/forcing_line_gate.py`, the TypedDict docstring (lines 78-79) already
says "or empty string if there is no legal second move" — that is the correct spec.
No change needed there beyond confirming the `su: str` declaration is intentional.

---

## Info

### IN-01: `LICHESS_K` is imported but never used in module logic

**File:** `app/services/forcing_line_gate.py:44`

**Issue:** `LICHESS_K` is imported from `eval_utils` and immediately suppressed with
`# noqa: F401` to signal "we depend on the same sigmoid, we define no new one." The
module docstring already explains this rationale. An unused import with a lint
suppression is a non-standard pattern that adds noise to the import block and sets
a precedent for `# noqa` usage in a file that otherwise has clean lint.

**Fix:** Remove the import and strengthen the module docstring comment instead:

```python
from app.services.eval_utils import (
    eval_cp_to_expected_score,
    eval_mate_to_expected_score,
)
```

In the module docstring under "Constant provenance / ONLY_MOVE_WIN_PROB_MARGIN":
```
# Reuses eval_utils.LICHESS_K coefficient via eval_cp_to_expected_score /
# eval_mate_to_expected_score — no new sigmoid defined (D-07).
```

### IN-02: `test_boundary_at_margin_not_forced` does not test the stated boundary

**File:** `tests/services/test_forcing_line_gate.py:116-123`

**Issue:** The test is named and documented as verifying the strict `>` boundary for
`ONLY_MOVE_WIN_PROB_MARGIN`, but the implementation simply asserts "well below margin"
values fail — it never constructs a node where `delta == ONLY_MOVE_WIN_PROB_MARGIN`
exactly (the actual boundary). A delta of `0.35` would require inverting the sigmoid
numerically, which is non-trivial, but the test name misleads future readers into
thinking the exact boundary was checked.

```python
def test_boundary_at_margin_not_forced(self) -> None:
    """A delta exactly equal to ONLY_MOVE_WIN_PROB_MARGIN does not pass (strictly greater required)."""
    # ...
    node = _cp_node(b=250, s=180)  # well below margin  <- comment confirms no actual boundary test
    assert is_solver_node_forced(node, "white") is False
```

**Fix:** Rename the test to accurately describe what it covers, or add the exact
boundary check. The exact threshold cp can be found by binary-searching for the pair
where `p_best - p_second` is within `1e-6` of `0.35`, or use `pytest.approx` on the
win-prob delta:

```python
def test_sub_margin_gap_not_forced(self) -> None:
    """A gap clearly below 0.35 margin is not forced (covers the < boundary side)."""
    node = _cp_node(b=250, s=180)
    assert is_solver_node_forced(node, "white") is False
```

### IN-03: No test for `bm=None, sm!=None` mixed node (best is cp, second-best is an opponent's mate)

**File:** `tests/services/test_forcing_line_gate.py` (missing), `app/services/forcing_line_gate.py:181-185`

**Issue:** The gate handles the case `bm=None, sm!=None` conservatively:
`_resolve_mate_priority` returns `None` (fall-through) because `bm is None`, then in
`is_solver_node_forced` the fallthrough block finds `s is None` and returns `False`
(malformed-blob guard). This is the correct, conservative disposition — a node where
the best move is a cp move (+300cp) but the second-best leads to the opponent mating
is a genuinely forced position (solver must play the cp move to avoid being mated),
yet the gate returns `False`, under-crediting the forcing line.

The comment says "Malformed blob (mate/cp mismatch). Be conservative." In practice
this node structure is valid (MultiPV=2 can produce `b=300, bm=None, s=None, sm=-3`
for a position where the engine's second choice hands the opponent a forced mate).
No test exercises this path, so the comment's claim about malformation is untested.

**Fix:** Add a test and clarify the comment:

```python
def test_best_cp_second_opponent_mate_conservative(self) -> None:
    """Best is cp, second-best leads to opponent mating: conservative False (sm != None, s = None)."""
    # b=300 (solver ahead), sm=-3 (opponent mates via second move).
    # Gate conservatively returns False because s is None (no cp for second-best).
    # The position IS forced in practice; this is an acknowledged under-credit.
    node = PvNode(b=300, bm=None, s=None, sm=-3, su="e7e5")
    assert is_solver_node_forced(node, "white") is False
```

And in the gate source (line 184), clarify the comment:
```python
# s is None with sm != None means best is cp-scored but second leads to the
# opponent mating. The win-prob formula cannot apply without a cp for `s`.
# Conservative: return False (under-credits forced lines, no false positives).
```

---

_Reviewed: 2026-06-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
