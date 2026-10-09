# Phase 235: Train Grading Anchored to the Server Answer Key - Pattern Map

**Mapped:** 2026-10-07
**Files analyzed:** 17 (new + modified)
**Analogs found:** 16 / 17

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/schemas/train.py` (TrainPuzzle fields, `SolveRecheck`, `SolveRequest.recheck`, `SolveResponse.disagreement`, docstrings) | schema | request-response | same file: `SolveTelemetry` + `_drop_invalid_telemetry` (:276-326) | exact |
| `app/models/drill_solve.py` (`recheck` column) | model | CRUD | same file `telemetry` column (:188-198) | exact |
| `alembic/versions/<ts>_<rev>_drill_solves_recheck.py` (new) | migration | - | `alembic/versions/20261005_120000_a7c3e9d41f02_drill_solves_telemetry.py` | exact |
| `app/services/train_pool.py` (`PuzzleAnswerKey`, `answer_key_for`, `ServerGradedMove`) | service (pure) | transform | same file `VettedMove` (:312-337), `vetted_moves_from_pv_node`, `classify_puzzle_type` (:262-309) | exact |
| `app/repositories/train_repository.py` (`ComposedPuzzle` fields, key attach query, `SolveClassification.graded_moves`, `_override_for_key_move`, pure grade resolver, recheck write) | repository | CRUD | same file `record_solve` (:3005-3060), `_override_for_key_move` (:2550), `_compute_correct_guess` (:2564) | exact |
| `app/routers/train.py` (TrainPuzzle mapping, pass recheck dump) | router | request-response | same file :104-113 and :155-166 | exact |
| `tests/schemas/test_train_recheck_schema.py` (new) | test | - | `tests/schemas/test_train_telemetry_schema.py` | exact |
| `tests/schemas/test_train_recheck_parity.py` (optional) | test | - | `tests/schemas/test_train_telemetry_parity.py` | exact |
| `tests/routers/test_train.py` (payload shape, recheck column) | test | - | same file `_telemetry_row` (:3186), `test_pre_attempt_payload_shape` (:1090), `test_solve_response_key_set_is_exactly_the_wire_contract` (:1665) | exact |
| `tests/repositories/test_train_repository.py` | test | - | same file `test_record_solve_overrides_key_move_grade` (:4195) | exact |
| `tests/services/test_train_pool.py` | test | - | existing `classify_puzzle_type` / `vetted_moves_from_pv_node` tests | role-match |
| `frontend/src/types/train.ts` | type | - | same file optional `SolveResponse.vetted_moves?` (:187-199) | exact |
| `frontend/src/hooks/useTrainGradingEngine.ts` (anchor, `recheckMove`, node-cap per dispatch, constants) | hook | event-driven (worker) | same file `dispatchNow` (:347-375), `QueuedDispatch` (:149), gradeMove timeout race (:762-772, :798-848) | exact |
| `frontend/src/lib/trainRecheck.ts` (new) | utility (pure) | transform | `frontend/src/lib/liveFlaw.ts` (pure classifier) | role-match |
| `frontend/src/components/train/TrainSolveScreen.tsx` + `trainBubbleState.ts` + `frontend/src/lib/trainBotCopy.ts` | component | event-driven | `GRADING_COPY` (`trainBotCopy.ts:200`), bubble `grading` kind (`trainBubbleState.ts:58`) | exact |
| `frontend/src/lib/trainGuessLabels.ts` + `TrainReveal.tsx` | utility/component | transform | `guessFeedbackProse` (:73-90) | exact |
| `frontend/src/lib/__tests__/trainRecheck.test.ts` (new) | test | - | none specific; plain vitest unit | no close analog needed |

## Pattern Assignments

### `app/schemas/train.py` - `SolveRecheck` + `SolveRequest.recheck`

**Analog:** same file, `SolveRequest` (:276-326). Copy the field + wrap validator verbatim with renamed types:

```python
    telemetry: SolveTelemetry | None = None

    @field_validator("telemetry", mode="wrap")
    @classmethod
    def _drop_invalid_telemetry(
        cls, value: object, handler: ValidatorFunctionWrapHandler
    ) -> SolveTelemetry | None:
        """Drop malformed telemetry to None instead of 422-ing the solve (D-02).

        No logging and no Sentry capture: a malformed object comes from a stale
        or tampered client and is an expected condition, not a bug.
        """
        try:
            return handler(value)
        except ValidationError:
            return None
```

- `SolveRecheck(BaseModel)` with `model_config = ConfigDict(extra="forbid")`, `v: Literal[1]`, `outcome: Literal["confirmed", "resolved"]`, ES floats `Field(ge=0, le=1, allow_inf_nan=False, strict=True)`, capped depth ints (named constants like `TELEMETRY_*_CAP`).
- Keep `SolveRequest` itself without `extra="forbid"` (stale bundles).
- Rewrite docstrings: `SolveRequest` (":... The request schema itself is unchanged (P-01 intact...)" sentence is now false), `TrainPuzzle`, `PuzzleRevealResponse`, module docstring :1-9. Add a dated "Phase 235 (SEED-192)" paragraph in the same style as the Phase 211 / Phase 233 paragraphs.
- New TrainPuzzle fields: `key_move_uci: str | None = None`, `puzzle_type: Literal["sharp","soft","herring"] | None`, `runner_up_uci: str | None = None`. Avoid names containing `vetted_moves` / `graded_es_` (test :1732-1740).

### `app/models/drill_solve.py` - `recheck` column

**Analog:** `telemetry` (:188-198):

```python
    telemetry: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True, default=None
    )
```
Add a comment block like the telemetry one, but stating: written once per solve (plain set, not `||` merge), IS a grading input (D-14), NULL when no re-check ran.

### `alembic/versions/<ts>_<rev>_drill_solves_recheck.py`

**Analog:** `20261005_120000_a7c3e9d41f02_drill_solves_telemetry.py` (whole file). `down_revision = 'f4b9d2c7e815'` (current head per RESEARCH). Body:

```python
def upgrade() -> None:
    op.add_column('drill_solves', sa.Column('recheck', postgresql.JSONB(none_as_null=True), nullable=True))

def downgrade() -> None:
    op.drop_column('drill_solves', 'recheck')
```
Docstring: why a separate column from telemetry (Phase 233 D-05), no backfill, metadata-only.

### `app/services/train_pool.py` - `PuzzleAnswerKey`, `answer_key_for`, `ServerGradedMove`

**Analog:** `VettedMove` (:312-337): frozen dataclass domain value with a long docstring explaining es_before/es_after semantics:

```python
class VettedMove:
    uci: str
    quality: Literal["best", "good", "inaccuracy"]
    es_before: float
    es_after: float
```
- `ServerGradedMove(uci, tier: Literal["good","inaccuracy","wrong"], es_before, es_after)` same shape; do NOT add sharp `su` to `vetted_moves` (displayed as "Also fine").
- Severity via `classify_severity` / `expected_score_for` (never a second sigmoid); SR mover color via `mover_color_for_ply`, herring via stored `HerringPool.mover_color`.
- `answer_key_for` pure, unit-tested without DB; legality check with python-chess.

### `app/repositories/train_repository.py`

**Analog for the override (D-02):** `_override_for_key_move` (:2550-2561), first-match by UCI:

```python
def _override_for_key_move(played_move: str, vetted: list[VettedMove]) -> VettedMove | None:
    for entry in vetted:
        if entry.uci == played_move:
            return entry
    return None
```
Retype to take `graded_moves: list[ServerGradedMove]`; key entry must come first so `su == best_uci` resolves to good. `SolveClassification` (:2432-2438) gains `graded_moves` (and the runner-up info).

**Analog for the D-14 resolver:** `_compute_correct_guess` (:2564-2575), a small pure sibling. Extract the decision block of `record_solve` (:3013-3039, `effective_quality` derivation) into a pure `_resolve_grade(...)` returning `(effective_quality, correct_guess, disagreement_accepted)` so `record_solve` does not grow (depth gate).

**Analog for the write (D-18):** `record_solve` :3047-3057:

```python
    claim_values: dict[str, Any] = { "guess": ..., "correct_guess": correct_guess, "solved_at": now_utc }
    # D-01: add the column ONLY when there is a patch. Omitting it keeps "no
    # telemetry" a true SQL NULL ...
    if telemetry is not None:
        claim_values["telemetry"] = _merged_telemetry(telemetry)
```
For recheck: `if recheck is not None: claim_values["recheck"] = {**recheck, "accepted": accepted}` (plain set). Lost-claim re-read path (:3092-3110) must return stored values consistently.

**Key attach:** one query after `_materialize_session_rows` / in `load_session_puzzles` (:1286-1421), joining `GamePosition` and `GameFlaw` on `(user_id, game_id, ply)` and selecting `HerringPool.ladder` explicitly (deferred column, MissingGreenlet on resume otherwise).

### `app/routers/train.py`

**Analog:** :104-113 (TrainPuzzle field-by-field mapping, add three fields) and :155-166:

```python
            telemetry=(
                body.telemetry.model_dump(exclude_none=True) if body.telemetry is not None else None
            ),
```
Add `recheck=body.recheck.model_dump() if body.recheck is not None else None`. Error handling already wraps with rollback + `sentry_sdk.set_context("train", ...)`.

### Backend tests

- `tests/schemas/test_train_recheck_schema.py`: copy `test_train_telemetry_schema.py` structure (`_SOLVE_KWARGS` dict typed `dict[str, Any]`, `pytest.mark.parametrize` for malformed values, assert `SolveRequest.model_validate({..., "recheck": bad}).recheck is None`).
- `tests/routers/test_train.py`: copy `_telemetry_row` (:3186-3198) into `_recheck_row` selecting `recheck, recheck IS NULL, jsonb_typeof(recheck)`; update equality tests at :1090-1121 and :1665-1700.
- `tests/repositories/test_train_repository.py`: copy `test_record_solve_overrides_key_move_grade` (:4195) for sharp `su` -> recorded `wrong`, `vetted_moves == []`; add resume-path key test near `test_resume_serves_herring_with_deleted_source_game`.
- Every non-guest Game insert needs finally-cleanup (eval lottery isolation memory).

### `frontend/src/hooks/useTrainGradingEngine.ts`

**Analog:** `dispatchNow` (:347-375). Node cap is hard-coded today:

```ts
      worker.postMessage(`setoption name MultiPV value ${width}`);
      worker.postMessage(`position fen ${fen}`);
      worker.postMessage(`go movetime ${movetimeMs} nodes ${TRAIN_GRADING_MAX_NODES}`);
```
Add `maxNodes` as a parameter that travels with `width`/`movetimeMs` through `QueuedDispatch` (:149-157), the readyok drain (:483), and the stop-queue drain (:524), and the `search(fen, generation, width, movetimeMs)` signature (:385-425).
- Constants block :78-109 (`TRAIN_GRADING_MOVETIME_MS = 1500`, `TRAIN_GRADING_MAX_NODES = 2000000`, `TRAIN_GRADING_TIMEOUT_MS = 8000`): add `TRAIN_RECHECK_MOVETIME_MS = 3000`, `TRAIN_RECHECK_MAX_NODES`, `TRAIN_RECHECK_TIMEOUT_MS` there with a JSDoc each.
- Timeout race: copy the gradeMove wrapper (:762-772 / :798-848) for `recheckMove`; on timeout/error resolve to "keep 1.5s grade" (D-20), never throw to caller.
- `startGrading(fen)` (:613-634) becomes `startGrading(fen, keyUci | null)`; null keeps today's width-1 root search (D-07).
- Adding `recheckMove` to `TrainGradingEngine` requires updating hand-built mocks (`TrainReveal.test.tsx:148`, `TrainSolveScreen.restoredGameArrow.test.tsx:144`).

**Test analog:** `frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts` `class MockWorker` (:63) and describe blocks `width-1 mount search (211-02 Task 1)` (:659) and `consistent evals & display clamp` (:868): assert posted `position fen` / `go movetime ... nodes ...` strings.

### `frontend/src/types/train.ts`
Optional fields only (`key_move_uci?: string | null`, `puzzle_type?`, `runner_up_uci?`, `SolveResponse.disagreement?`), one `?? null` / `?? false` default at the consumer, mirroring `vetted_moves?` (:187-199).

### `frontend/src/lib/trainBotCopy.ts` / `trainBubbleState.ts` / `TrainSolveScreen.tsx`
Add `RECHECK_COPY = 'Taking a closer look…'` next to `GRADING_COPY` (`trainBotCopy.ts:200`); select via an `isRechecking` flag or `{kind:'grading', recheck: boolean}` at `trainBubbleState.ts:58`; render site `TrainSolveScreen.tsx:629-636`. Give the recheck bubble its own `data-testid` (frontend/CLAUDE.md).

### `frontend/src/lib/trainGuessLabels.ts`
**Analog:** `guessFeedbackProse` (:73-90), early-return chain. Add a new FIRST guard (extra params `disagreement: boolean`, `keySan: string | null`):

```ts
  if (disagreement && keySan) return `${keySan} is the engine's first choice, but your move holds up too.`;
```
Six existing strings stay verbatim. Tests: `TrainReveal.test.tsx` `describe('guessFeedbackProse')` (:1745) - add a case for both guesses; existing calls need the new args.

## Shared Patterns

### Drop-invalid optional boundary payload
**Source:** `app/schemas/train.py:314-326`. Apply to `SolveRequest.recheck`. A bad recheck never fails the solve; on non-sharp live type the server records it with `accepted: false` (Pitfall 4) and grants nothing.

### Omit-when-absent JSONB
**Source:** `app/repositories/train_repository.py:3053-3057` + model `JSONB(none_as_null=True)`. Apply to `recheck` write; tests check `recheck IS NULL` is true when absent.

### Server overrides client assertions it owns
**Source:** `_compute_correct_guess` / `_override_for_key_move`. Apply to D-02 (`su`) and D-14 (disagreement credit) as small pure helpers.

### Sentry
Router `except Exception` block in `app/routers/train.py` already captures with `set_context("train", ...)`; no new except blocks needed. Validation drops do NOT capture.

### Stale-bundle tolerance
Optional TS fields with nullish defaults; server accepts bodies without `recheck`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `frontend/src/lib/trainRecheck.ts` (`shouldRecheck`, payload builder) | utility | transform | No existing re-check concept; write as a small pure module (liveFlaw.ts style), ensure every export is consumed (knip). |

## Metadata

**Analog search scope:** app/schemas, app/models, app/repositories, app/services, app/routers, alembic/versions, tests/{schemas,routers,repositories}, frontend/src/{hooks,lib,components/train,types}
**Files scanned:** ~15
**Pattern extraction date:** 2026-10-07
