# Phase 236: Train Phone Grade Record & Instant Server Verdict - Pattern Map

**Mapped:** 2026-10-08
**Files analyzed:** 18 (new + modified)
**Analogs found:** 18 / 18 (all analogs are git-tracked in-repo code; most are the Phase 235 `recheck` plumbing)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/schemas/train.py` (PhoneGrade, PHONE_GRADE_SCHEMA_VERSION, wire ServerGradedMove, TrainPuzzle.server_graded_moves, SolveRequest.phone_grade, ReviewRequest) | model (Pydantic) | request-response validation | `SolveRecheck` + `_drop_invalid_recheck` (same file, 251-292, 402-415) | exact |
| `app/models/drill_solve.py` (phone_grade column) | model (ORM) | CRUD | `recheck` / `telemetry` JSONB columns (196-208) | exact |
| `alembic/versions/2026100x_..._drill_solves_phone_grade.py` (NEW) | migration | batch/DDL | `alembic/versions/20261007_120000_c5e8a2d7b914_drill_solves_recheck.py` | exact |
| `app/services/train_pool.py` (server_graded_moves_for, legality helper) | service (pure) | transform | `answer_key_for` (363-392), `legal_answer_key` (395-422), solve-time composition in `_classify_sr_solve` | exact |
| `app/repositories/train_repository.py` (ComposedPuzzle field, `_answer_keys_by_position` + mover_color, `_attach_answer_keys`, `_classify_*_solve`, `record_solve(phone_grade)`, `merge_solve_telemetry(phone_grade)`) | repository | CRUD | `record_solve` claim_values (3350-3376), `merge_solve_telemetry` (3173-3223) | exact |
| `app/routers/train.py` (compose mapping, solve, review body) | controller | request-response | existing solve route (~141-198) and review route (201-235) | exact |
| `tests/schemas/test_train_phone_grade_schema.py` (NEW) | test | unit | `tests/schemas/test_train_recheck_schema.py` | exact |
| `tests/routers/test_train.py` (phone_grade, review, key-set contract) | test | integration | `_recheck_row` helper (~3676-3700), `test_recheck_resubmit_keeps_first_record` (~3832), review tests (3484-3660), key-set assert (1145-1155) | exact |
| `tests/repositories/test_train_repository.py` (D-08 parity, resolve_grade) | test | integration | `test_compose_attaches_answer_keys_for_every_source` (~5390), resolve_grade tests (~5757) | exact |
| `tests/services/test_train_pool.py` (server_graded_moves_for) | test | unit | `TestAnswerKeyFor` | exact |
| `frontend/src/types/train.ts` | model (TS types) | — | `SolveRecheck` / `TrainPuzzle` TS types | exact |
| `frontend/src/lib/trainRecheck.ts` (or new `trainPhoneGrade.ts`) | utility | transform | `buildRecheckPayload` / `shouldRecheck` (same file) | exact |
| `frontend/src/hooks/trainGradingSupport.ts` (GradeResult.phoneReading) | utility/types | — | `GradeResult`, `RawSearchResult.depth` | exact |
| `frontend/src/hooks/useTrainGradingEngine.ts` (phoneReading, startGameMoveSearch serialization, onKeyLine) | hook | event-driven (Worker) | `gradeMoveInner` (645-736), `startGameMoveSearch` (842-893) | exact (self) |
| `frontend/src/hooks/useTrainPuzzleTelemetry.ts` (per-puzzle phone_grade slot) | hook | event-driven (flush) | existing review flush (reviewRef, 144-148) | exact (self) |
| `frontend/src/api/client.ts` (postReviewKeepalive body type) | service (API client) | request-response | `postReviewKeepalive` (345-369) | exact (self) |
| `frontend/src/components/train/TrainSolveScreen.tsx` | component | request-response + event-driven | `gradeAndSolve` / `runRecheck` (1105-1172) | exact (self) |
| `frontend/src/components/train/TrainReveal.tsx` | component | — | `train-game-line-loading` block (1204-1209), `buildLineBoxes` (268-317) | exact (self) |

## Pattern Assignments

### `app/schemas/train.py` — PhoneGrade (model, validation)

**Analog:** `SolveRecheck`, same file lines 251-292. Reuse value types verbatim (do not redefine):
```python
RecheckExpectedScore = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False, strict=True)]
RecheckDepth = Annotated[
    int,
    BeforeValidator(_clamp_to(RECHECK_DEPTH_CAP)),
    Field(ge=0, le=RECHECK_DEPTH_CAP, strict=True),
]

class SolveRecheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Must equal RECHECK_SCHEMA_VERSION (a Literal cannot reference the constant).
    v: Literal[1]
    outcome: Literal["confirmed", "resolved"]
    key_es: RecheckExpectedScore
    ...
    key_depth: RecheckDepth
    played_depth: RecheckDepth
```
New model: `v: Literal[1]`, `tier: Literal["good","inaccuracy","wrong"]`, `key_es`, `played_es`, `key_depth`, `played_depth`; constant `PHONE_GRADE_SCHEMA_VERSION: Final = 1` placed next to `RECHECK_SCHEMA_VERSION` (~175-178). Docstring must state "audit only, never a grading input (D-02); played == key records equal pairs (D-05)".

**Drop-invalid wrap validator** (lines 402-415) — copy for `SolveRequest.phone_grade` and `ReviewRequest.phone_grade`:
```python
    @field_validator("recheck", mode="wrap")
    @classmethod
    def _drop_invalid_recheck(
        cls, value: object, handler: ValidatorFunctionWrapHandler
    ) -> SolveRecheck | None:
        """Drop a malformed re-check to None instead of 422-ing the solve (D-18).
        Same contract as `_drop_invalid_telemetry`: no logging, no Sentry ..."""
        try:
            return handler(value)
        except ValidationError:
            return None
```
**ReviewRequest:** flat subclass `class ReviewRequest(ReviewTelemetry)` adding `phone_grade: PhoneGrade | None = None` + the wrap validator (RESEARCH Pattern 5). `ReviewTelemetry` (~295-337) itself untouched; `extra="forbid"` inherited.

**Wire ServerGradedMove:** follow the same-named wire-twin precedent `app.schemas.train.VettedMove` (~418-441) vs `app.services.train_pool.VettedMove`: only `uci: str` + `tier: Literal["good","inaccuracy","wrong"]`. `TrainPuzzle` (~34-73): `server_graded_moves: list[ServerGradedMove] = Field(default_factory=list)`. Update module docstring (1-10) and the `VettedMove` "never add to TrainPuzzle (P-01)" note (Pitfall 10).

---

### `app/models/drill_solve.py` — phone_grade column

**Analog:** `recheck` column (lines 196-208):
```python
    recheck: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True, default=None
    )
```
Add `phone_grade` identically with a comment block: audit-only, filter `played_move != key` for accuracy (D-05), written once by claim UPDATE or review coalesce (D-12).

---

### `alembic/versions/<ts>_<rev>_drill_solves_phone_grade.py` (NEW)

**Analog:** `alembic/versions/20261007_120000_c5e8a2d7b914_drill_solves_recheck.py` (whole file, 39 lines):
```python
revision: str = 'c5e8a2d7b914'
down_revision: Union[str, Sequence[str], None] = 'f4b9d2c7e815'
...
def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('drill_solves', sa.Column('recheck', postgresql.JSONB(none_as_null=True), nullable=True))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('drill_solves', 'recheck')
```
New: `down_revision = 'c5e8a2d7b914'` (current single head), column `phone_grade`. Copy the docstring style (why separate column, no backfill, metadata-only add).

---

### `app/services/train_pool.py` — server_graded_moves_for (pure service)

**Analogs:** `answer_key_for` (363-392) for signature/source gating style; `legal_answer_key` / `_legal_in` (395-422) for the legality filter; domain `ServerGradedMove` dataclass (575-638) whose `tier: Literal["good","inaccuracy","wrong"]` (587-588) is the return element. Body to copy is the solve-time derivation in `train_repository.py` `_classify_sr_solve` (2705-2721):
```python
    vetted_moves = (
        vetted_moves_from_pv_node(missed_pv_lines[0], mover_color, best_uci=best_uci)
        if missed_pv_lines else []
    )
    graded_moves = graded_moves_from_vetted(vetted_moves)
    if key.puzzle_type == "sharp" and missed_pv_lines:
        runner_up = sharp_runner_up_graded_move(missed_pv_lines[0], mover_color, key_uci=key.key_uci)
        if runner_up is not None:
            graded_moves.append(runner_up)
```
and herring (2621-2637): `graded_moves_from_vetted(vetted_moves_from_ladder(pool_row.ladder, mover))` with stored `mover_color` (never ply parity, train_pool.py:1071-1073). Full proposed function in RESEARCH Pattern 1. Keyword-only args, explicit return type, never raises.

---

### `app/repositories/train_repository.py`

**1. `record_solve` claim write** (analog lines 3350-3376):
```python
    if recheck is not None:
        claim_values["recheck"] = {**recheck.model_dump(), "accepted": resolved.disagreement}
    claim_result = await session.execute(
        update(DrillSolve)
        .where(..., DrillSolve.solved_at.is_(None))
        .values(**claim_values)
    )
```
Add `phone_grade: PhoneGrade | None` kwarg and `if phone_grade is not None: claim_values["phone_grade"] = phone_grade.model_dump()`. Do NOT pass into `_resolve_grade` (2838-2877).

**2. `merge_solve_telemetry` write-once** (analog 3173-3223): currently `.values(telemetry=_merged_telemetry(patch))`. Change to a `values` dict; when `phone_grade` given add `func.coalesce(DrillSolve.phone_grade, literal(phone_grade, JSONB))` (same `literal(..., JSONB)` bind as `_merged_telemetry`, 3173-3185). Keep `rowcount == 1` semantics and the `# ty: ignore[unresolved-attribute]` comment. No WHERE-guard on phone_grade (would 404 the second flush).

**3. Composition:** `ComposedPuzzle` (frozen dataclass, 184-210) gets `server_graded_moves: tuple[ServerGradedMove, ...] = ()`. `_answer_keys_by_position` (2244-2314) adds `HerringPool.mover_color` to the select and calls `server_graded_moves_for` with the same source gating used for `answer_key_for` (2299-2312). `_attach_answer_keys` (2317-2345) filters illegal UCIs and returns `()` when legal key is None.

**4. `_classify_sr_solve` / `_classify_herring_solve`** (2584-2727): replace inline derivation with `server_graded_moves_for(...)`, keep `vetted_moves` for display. `_classify_filler_solve` (2640-2657) unchanged.

---

### `app/routers/train.py`

**Analog:** review route (201-235), currently `body: ReviewTelemetry`, `patch=body.model_dump(exclude_none=True)`, False → 404 "Puzzle not found". Change to `body: ReviewRequest`, `patch=body.model_dump(exclude_none=True, exclude={"phone_grade"})`, `phone_grade=body.phone_grade.model_dump() if body.phone_grade is not None else None`. Solve route (~141-198): pass `body.phone_grade` through to `record_solve` exactly like `body.recheck`. Compose mapping (75-138): map `ComposedPuzzle.server_graded_moves` to wire `ServerGradedMove` list like `runner_up_uci`.

---

### `tests/schemas/test_train_phone_grade_schema.py` (NEW)

**Analog:** `tests/schemas/test_train_recheck_schema.py` lines 1-60+:
```python
from app.schemas.train import RECHECK_DEPTH_CAP, SolveRecheck, SolveRequest

_SOLVE_KWARGS: dict[str, Any] = {"position": 0, "guess": "several", "played_move": "e2e4", "move_quality": "good"}
_VALID_RECHECK: dict[str, Any] = {"v": 1, "outcome": "confirmed", "key_es": 0.6, ...}

def _with(**overrides: Any) -> dict[str, Any]: return {**_VALID_RECHECK, **overrides}
def _without(key: str) -> dict[str, Any]: ...

def test_valid_recheck_parses() -> None:
    request = SolveRequest.model_validate({**_SOLVE_KWARGS, "recheck": _VALID_RECHECK})
    assert request.recheck is not None
    assert request.recheck.model_dump() == _VALID_RECHECK

@pytest.mark.parametrize("bad", [_with(bogus=1), ...])  # each malformed -> None
```
Mirror for `phone_grade` on both `SolveRequest` and `ReviewRequest` (assert telemetry survives a dropped record; unknown top-level review key still raises).

---

### Backend integration tests

- `tests/routers/test_train.py`: copy `_recheck_row` helper (~3676-3700) for a `_phone_grade_row` asserting SQL NULL (`IS NULL`) when absent; copy `test_recheck_resubmit_keeps_first_record` (~3832) for D-13; extend review tests (3484-3660) for coalesce write-once and "not merged into telemetry"; update exact key-set assert (1145-1155), do not loosen.
- `tests/repositories/test_train_repository.py`: extend `test_compose_attaches_answer_keys_for_every_source` (~5390); add D-08 parity test (composition list == `_classify_and_certify_solve(...).graded_moves` uci/tier); extend resolve_grade tests (~5757) for path-3 payload tier.
- `tests/services/test_train_pool.py`: extend `TestAnswerKeyFor` style for `server_graded_moves_for` per source.

---

### `frontend/src/lib/trainRecheck.ts` — buildPhoneGradePayload, instantServerTier, shouldRecheck

**Analog:** same file lines 18-100:
```typescript
/** Mirrors RECHECK_SCHEMA_VERSION in app/schemas/train.py (the server accepts only this value). */
const RECHECK_SCHEMA_VERSION = 1 as const;

export function shouldRecheck(input: ShouldRecheckInput): boolean {
  const offKey =
    input.keyUci !== null &&
    input.playedUci !== input.keyUci &&
    input.playedUci !== input.runnerUpUci;
  if (!offKey) return false;
  ...
}

/** Map the camelCase readings to the snake_case wire record; a null depth is sent as 0. */
export function buildRecheckPayload(input: RecheckPayloadInput): SolveRecheck {
  return { v: RECHECK_SCHEMA_VERSION, ..., key_depth: input.keyDepth ?? 0, played_depth: input.playedDepth ?? 0, ... };
}
```
Add `serverGradedUcis: readonly string[]` to `ShouldRecheckInput` (D-11, keep `runnerUpUci`). New `PHONE_GRADE_SCHEMA_VERSION = 1 as const` (non-exported, no parity test, matches precedent), `buildPhoneGradePayload`, `instantServerTier` (RESEARCH Code Example 3 / Pattern 2). knip: export only what is imported. Tests: extend `src/lib/__tests__/trainRecheck.test.ts`.

### `frontend/src/types/train.ts`
Mirror `SolveRecheck` TS interface for `PhoneGrade`; add `ServerGradedMove {uci; tier: TrainMoveTier}`, `TrainPuzzle.server_graded_moves`, `SolveRequest.phone_grade?`, review body type.

### `frontend/src/hooks/trainGradingSupport.ts` + `useTrainGradingEngine.ts`
- `GradeResult.phoneReading?: PhoneReading | null` (optional: `trainRevealCache.ts:38`, shape check 102-117 restores old entries).
- `gradeMoveInner` keyed exits: played == key (669-680) → equal pairs from `anchor.es`/`anchor.depth`, tier good; after-played (689-728) → `afterRaw.depth`. Null for anchor-mismatch fallback (652-666), illegal-move fallback (683-695), `anchor.legacy`.
- Serialization: `playedSearchSettledRef` awaited in `startGameMoveSearch` (842-893) before `searchAfterMove`, generation check after await (RESEARCH Code Example 4). Preemption mechanism to avoid: `search()` stop+queue (376-387) and bestmove handler dropping pending (498-517). Reset in `startGrading` (597-631) / `abortGrading` (633-643).
- Timeout: reuse `raceWithTimeout` (trainGradingSupport.ts), never ad-hoc setTimeout.
- Tests: MockWorker harness in `useTrainGradingEngine.test.ts:69-86`; assert no `stop` posted.

### `frontend/src/hooks/useTrainPuzzleTelemetry.ts` + `frontend/src/api/client.ts`
Add a per-(sessionId, position) phone_grade slot guarded by the hook's existing `keyRef`; include in both Next and pagehide flushes via `postReviewKeepalive` (client.ts:345-369). `reviewRef` is only set when `hasVerdict` (144-148). Reset on puzzle change.

### `frontend/src/components/train/TrainSolveScreen.tsx`
- Branch at top of `gradeAndSolve` (1105-1172) on `instantServerTier`; instant path posts `move_quality: tier`, no `phone_grade`, no `isGrading` copy (Pitfall 7, `trainBubbleState.ts:60-67`), background rejection sets card status only, never `gradingError` (1131-1140).
- Normal path: capture 1.5 s `phoneReading` BEFORE `runRecheck` replaces `grade` (D-04); freeze in body (`setLastSolvePayload`, useTrainSession.ts:313-330).
- Puzzle-identity guard ref updated in puzzle effect (1054-1094) — Pitfall 4.
- `gradeResult === null` fallback sites: overlay/best arrow (1383-1399), `playedMoveQuality` (1356-1363), `pristineOverlayUcis` (1419-1425), eval-bar gate (1317-1336), Analyze cache (1601-1625, documented residual).

### `frontend/src/components/train/TrainReveal.tsx`
Loading visual: reuse `train-game-line-loading` block (1204-1209, `Loader2` + "Loading…"); add your/best pending + failed branches in card render (1137-1215) and `buildLineBoxes` (268-317); game-search effect deps (873-904) switch to a primitive best UCI. New containers need `data-testid` (e.g. `train-your-line-loading`).

## Shared Patterns

### JSONB omit-when-absent
**Source:** `app/repositories/train_repository.py` 3355-3365 + `app/models/drill_solve.py` 196-208. **Apply to:** both phone_grade write paths. Never assign Python `None` to the column (asyncpg writes JSON null).

### Drop-invalid wrap validator (no Sentry, no logging)
**Source:** `app/schemas/train.py` 402-415. **Apply to:** `SolveRequest.phone_grade`, `ReviewRequest.phone_grade`.

### Single-statement atomic guards
**Source:** claim UPDATE `solved_at.is_(None)` (record_solve) and `_merged_telemetry` coalesce (3173-3185). **Apply to:** D-12/D-13 write-once.

### Ownership in WHERE / 404 no oracle
**Source:** `merge_solve_telemetry` WHERE (user_id from auth) + router 404 mapping (routers/train.py 228-231). **Apply to:** review route change.

### Schema-version constant mirrored front/back
**Source:** `RECHECK_SCHEMA_VERSION` (train.py ~175, trainRecheck.ts:18-19). **Apply to:** `PHONE_GRADE_SCHEMA_VERSION`.

## No Analog Found

None. Every file has an in-repo analog; the hook serialization (Pitfall 1) and instant-path branch are new behavior inside existing files, with RESEARCH sketches as the pattern.

## Metadata

**Analog search scope:** app/schemas, app/models, app/repositories, app/services, app/routers, alembic/versions, tests/{schemas,routers,repositories,services}, frontend/src/{lib,hooks,components/train,api,types}
**Files scanned:** ~20 (line numbers for frontend sites taken from RESEARCH, verified this session by the researcher; backend excerpts re-read here)
**Pattern extraction date:** 2026-10-08
