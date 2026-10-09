---
phase: 235-train-grading-server-answer-key
reviewed: 2026-10-07T00:00:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - alembic/versions/20261007_120000_c5e8a2d7b914_drill_solves_recheck.py
  - app/models/drill_solve.py
  - app/repositories/train_repository.py
  - app/routers/train.py
  - app/schemas/train.py
  - app/services/train_pool.py
  - frontend/src/components/train/TrainReveal.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/train/trainBubbleState.ts
  - frontend/src/hooks/useTrainGradingEngine.ts
  - frontend/src/lib/trainBotCopy.ts
  - frontend/src/lib/trainGuessLabels.ts
  - frontend/src/lib/trainRecheck.ts
  - frontend/src/types/train.ts
  - CHANGELOG.md
  - tests/repositories/test_train_repository.py
  - tests/routers/test_train.py
  - tests/schemas/test_train_recheck_schema.py
  - tests/services/test_train_pool.py
  - frontend/src/components/train/__tests__/TrainReveal.test.tsx
  - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
  - frontend/src/components/train/__tests__/trainBubbleState.test.ts
  - frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts
  - frontend/src/lib/__tests__/trainRecheck.test.ts
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 235: Code Review Report

**Reviewed:** 2026-10-07
**Depth:** standard
**Files Reviewed:** 24
**Status:** issues_found

## Summary

Reviewed the phase 235 diff (`e4897d1d0..HEAD`) of the backend answer-key funnel
(`answer_key_for`, `_attach_answer_keys`, `_resolve_grade`, `_disagreement_accepted`),
the `recheck` column and schema, and the frontend grading hook rebuild
(keyed anchor, `recheckMove`, bubble state, D-15 copy).

Verified mechanically: `ruff check`, `ty check app/ tests/`, `scripts/check_function_size.py`
(no depth breaches), `tsc -b`, eslint on the touched frontend files, and the four backend
test modules (414 passed). I also probed the `SolveRequest` boundary: JSON ints for the
strict-float ES fields are accepted, depth is clamped to 255, an unknown key inside
`recheck` drops the whole record to None, and a null depth drops it too (the client
sends 0, so this does not occur in practice).

Traced and found sound:
- Composition-time and solve-time keys both go through `answer_key_for` with the same
  inputs, including the new unconditional `game_positions.best_move` read in
  `_classify_sr_solve`. All four return paths of `compose_and_materialize_session` pass
  through `_attach_answer_keys`.
- The herring row sharing `(user, game, ply)` with a `game_flaws` row is guarded by the
  `is_sr` gating, with a test.
- `user_id` is in every SR join (IDOR). The recheck column is omitted from the claim
  UPDATE when absent, so it stays SQL NULL (asyncpg JSONB null pitfall avoided).
- The lost-claim path reads `recheck.accepted` from the stored row (first outcome wins).
- `_resolve_grade` precedence (server-graded move beats a confirmed claim) and the
  `_disagreement_accepted` checks match D-02, D-10 and D-14.
- Terminal-position scoring (`terminalSearchResult`) gets mate sign and stalemate right.

No correctness bugs or security defects were found on the main paths. The findings below
are robustness and maintainability issues.

## Warnings

### WR-01: A re-check that outlives its timeout keeps driving the engine and can starve the reveal search

**File:** `frontend/src/hooks/useTrainGradingEngine.ts:1051-1062` (and `1128-1157`)
**Issue:** `recheckMove` races `recheckMoveInner` against `TRAIN_RECHECK_TIMEOUT_MS`,
but on timeout it only resolves `null`. The inner async function is not cancelled. The
generation is not bumped, and the inner function has no generation or settled check
between its two sequential searches (the only check is at line 1064, after both).

If the key search lands just after the timeout, the inner function dispatches the played
search. That 3 s search goes through `search()`. If the reveal has meanwhile started its
`startGameMoveSearch` (state `thinking`), `search()` sends `stop` and replaces the queued
dispatch. The reveal's own search promise is then never resolved, so the PLAYED IN GAME
line fails after `TRAIN_GRADING_TIMEOUT_MS`. The reverse ordering has the same problem:
the zombie search occupies the engine for up to 3 s. The scenario requires a wedged or
very slow engine (two 3 s searches fit well inside 12 s), so it is rare, but the stated
design goal (D-20) is that a re-check failure must not affect anything else.

**Fix:** Pass a cancellation token into `recheckMoveInner` and check it before dispatching
each search:
```ts
const cancelled = { value: false };           // set to true by the timeout callback
...
const keyRaw = await searchAfterMove(afterKeyFen, generation, ...);
if (cancelled.value || generation !== generationRef.current) return null;
const playedRaw = await searchAfterMove(afterPlayedFen, generation, ...);
```
Alternatively bump `generationRef` on timeout so the existing generation guards discard
the late work.

### WR-02: `useTrainGradingEngine` hook body has grown to roughly 790 lines

**File:** `frontend/src/hooks/useTrainGradingEngine.ts:461-1251`
**Issue:** The hook grew by about 300 lines this phase (`recheckMoveInner`, `recheckMove`,
the anchor refs). The file is now 1251 lines and `useTrainGradingEngine()` is a single
~790-line function. The root `CLAUDE.md` says to refactor bloated code on sight when
editing a function clearly past the ~100 logic-line guidance, and this phase is a GSD
plan, so it is in scope. The seams are already visible: the UCI line handler inside the
Worker effect (lines 671-770) and the three settle-once timeout wrappers (`gradeMove`,
`recheckMove`, `startGameMoveSearch`) all repeat the same `settled` plus timer shape.
**Fix:** Extract a shared `raceWithTimeout(promise, ms, onTimeout)` helper (the
`settled`/`clearTimeout` boilerplate is now duplicated three times) and move the UCI
message handler plus the `recheck*` logic out of the main hook body. Adding a fourth
copy of the wrapper is what made `recheckMove`'s "never rejects" variant diverge subtly
from the other two.

## Info

### IN-01: Positional booleans in `ResolvedGrade(...)` construction

**File:** `app/repositories/train_repository.py:~2860` (accepted-disagreement branch of `_resolve_grade`)
**Issue:** `return ResolvedGrade("good", True, True, None, None)` passes two adjacent
positional booleans (`correct_guess`, `disagreement`). The other two return sites in the
same function use keywords, so this one is the only call where a swap would silently
invert meaning.
**Fix:**
```python
return ResolvedGrade(
    effective_quality="good",
    correct_guess=True,
    disagreement=True,
    graded_es_before=None,
    graded_es_after=None,
)
```

### IN-02: Mangled header comment in `trainBubbleState.ts`

**File:** `frontend/src/components/train/trainBubbleState.ts:6-14`
**Issue:** The doc comment edit left one very long line
(`...closer look…": the same ... outcome bot's verdict row replaces it when the reveal opens. No layout jump, no vanishing bot. Extracting this resolution OUT of`)
that was not re-wrapped. Cosmetic, but it is now the longest line in the file and breaks
the surrounding wrap.
**Fix:** Re-wrap the comment paragraph to the file's existing width.

### IN-03: Server trusts client-asserted ES numbers for the D-14 guess credit

**File:** `app/repositories/train_repository.py:2781-2825` (`_disagreement_accepted`)
**Issue:** The sanity checks (outcome confirmed, both ES pairs rate the move good, live
type sharp, not key, not runner-up, tier good) are all computed from client-supplied
numbers, so a tampered client can claim a "confirmed" re-check on any sharp off-key move
and earn the guess point for a "several" guess. This is within the accepted risk in
D-05, and since `puzzle_type` is now delivered pre-attempt a client can simply guess
"critical" on every sharp puzzle anyway. It is recorded here because the leaderboard
(Phase 230) consumes `correct_guess`. The stored `recheck.accepted` flag plus the full
ES pairs make abuse detectable per user after the fact.
**Fix:** None required. If leaderboard integrity ever matters, add a per-user rate of
accepted disagreements to the review query for `drill_solves.recheck`.

### IN-04: `_classify_sr_solve` now always reads `game_positions.best_move`

**File:** `app/repositories/train_repository.py:2688-2698`
**Issue:** The read was previously gated on `missed_pv_lines` being truthy and is now
unconditional whenever the solve has a `game_id` (intentional, to keep the solve-time key
identical to composition). This costs one extra PK lookup per blob-less SR solve and
changes the earlier guarantee that a blob-less row does no `game_positions` read. The
comment at the change site explains the reason, so this is only a note for anyone relying
on the old read pattern.
**Fix:** None required.

---

_Reviewed: 2026-10-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
