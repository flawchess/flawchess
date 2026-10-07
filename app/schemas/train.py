"""Pydantic v2 schemas for the Train API (Phase 189).

POOL-10 / P-01: `TrainPuzzle` is the pre-attempt payload and carries no
answer key — see its class docstring for the exact-equality contract this
schema exists to enforce. Phase 211: vetted-move material (`VettedMove`,
`SolveResponse.vetted_moves`, the graded-ES pair) lives on `SolveResponse`
— produced only once the attempt is already recorded — and never on
`TrainPuzzle`.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import date, datetime
from typing import Annotated, Final, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    ValidationError,
    ValidatorFunctionWrapHandler,
    field_validator,
)

from app.services.train_scheduler import REMINDER_HOUR_MAX, REMINDER_HOUR_MIN


class TrainPuzzle(BaseModel):
    """One pre-attempt puzzle.

    POOL-10 / P-01 (LOCKED): the pre-attempt payload carries no answer key.
    `last_move_uci` (190-02, SOLV-02) describes the position's ARRIVAL — the
    half-move immediately before `ply`, i.e. the opponent's (or the user's
    own) prior move — so the solve screen can animate/highlight it. It does
    not reveal what to play next, so it does not reopen POOL-10. `best_move`,
    `pv`, `puzzle_type`, and `source` remain forbidden: adding any of them
    here re-opens the POOL-10 leak this schema exists to close — the
    client's exact-match/grading path runs entirely client-side against its
    own vendored Stockfish WASM output (see 189-01-PLAN.md P-01). Do not add
    fields here without re-reading that decision.

    `game_id` is `int | None` (Phase 192 Plan 02, D-01/D-05): a red herring's
    source-game link is nullable provenance — `None` here means either the
    herring's source game has been deleted (the puzzle is still fully
    servable off its `herring_pool` row, D-03) or the pool row was never
    linked to a game in the first place. Never used as an identity key
    client-side; a puzzle's identity within a session is `position`.
    """

    position: int
    game_id: int | None
    ply: int
    fen: str
    side_to_move: Literal["white", "black"]
    last_move_uci: str | None


class SolvedResult(BaseModel):
    """One recorded solve's outcome, part of `TrainSessionResponse.solved_results`.

    Quick task 260728-tgc (BUGFIX-TRAIN-SCORE-CROSSDEVICE): one entry per
    `drill_solves` row with `solved_at IS NOT NULL`, in `position` order. The
    client aggregates these with its own points formula
    (`frontend/src/lib/trainScore.ts`, `scorePuzzle` + `aggregateSessionScore`)
    — that file stays the single source of truth for per-session display
    (LOCKED, Option B). This response deliberately carries NO precomputed
    score integer. Phase 230 D-01 later added a deliberate server port of the
    three scoring constants for the weekly leaderboard aggregate only
    (`app.services.train_score`), pinned to trainScore.ts by
    `tests/services/test_train_score_parity.py`.

    Not an answer-key leak: `correct_guess`, `move_quality`, and (Phase 222,
    TRAINBOT-04/D-17) `source`/`item_status`/`due_date` were ALL already
    returned by `SolveResponse` for each of these same positions at the
    moment they were attempted — this endpoint just re-serves outcomes the
    client already saw once, from the server instead of a device-local
    cache. The `PuzzleRevealResponse` 409 gate (which protects the actual
    answer key — best move, PV, puzzle type) is untouched and continues to
    protect UNSOLVED positions only. Entries here carry no `position`,
    `game_id`, `ply`, or best-move field, so they reveal nothing about
    puzzles still to be attempted in the session.

    `due_date` (D-17 caveat): this is the item's CURRENT value, not a frozen
    at-solve-time snapshot — identical within one session, and arguably more
    truthful for a "when does it come back" statement across a re-composed
    one (e.g. after a later solve in the same session re-advanced the ladder).
    `item_status`/`due_date` are `None` for `source in ("red_herring",
    "sharp_filler")`, which carry no SR bookkeeping (mirrors `SolveResponse`'s
    own nullability).
    """

    correct_guess: bool
    move_quality: Literal["good", "inaccuracy", "wrong"]
    source: Literal["sr_item", "red_herring", "sharp_filler"]
    item_status: Literal["active", "mastered", "parked"] | None
    due_date: date | None


class TrainSessionResponse(BaseModel):
    """Response for POST /train/sessions — a composed or resumed session.

    `session_id` is nullable: per the repository's explicit "write NO
    drill_sessions row when nothing qualifies" contract, a request that finds
    no eligible puzzle returns `session_id=None`, `puzzle_count=0`,
    `puzzles=[]` rather than a persisted empty session.

    `requested_count` is the settings value of N (`puzzles_per_session`);
    `blob_pending_count` is the number of the user's own qualifying blunders
    still waiting on opportunistic tier-4 analysis to populate their answer
    key. A caller seeing `puzzle_count < requested_count` MUST read
    `blob_pending_count` to tell "still analyzing" (non-zero) apart from
    "genuinely caught up" (zero) — removing either field re-hides the
    Pitfall 4 signal this schema exists to surface.

    `solved_results` (260728-tgc) is one `SolvedResult` per recorded solve in
    `position` order — see that schema's docstring. Empty for a freshly
    composed session and for the no-eligible-material (`session_id is None`)
    case. This is what makes "Scored today" correct on a device that never
    saw the original solve responses (the reproduced prod bug: a
    localStorage-only tally read "0 of 18" on a second device).

    `is_warmup` (Phase 206, D-06/D-07) is frozen at composition and derived
    purely from material scarcity — `True` iff the session contains zero
    surviving SR_ITEM puzzles at the moment it was (re-)composed. It is
    never derived from session ordinal, session count, or account age, and
    the client performs no arithmetic to reproduce it: it is a single
    server-computed boolean to branch on (T-191-24).
    """

    session_id: int | None
    session_date: date
    expires_on: date
    puzzle_count: int
    requested_count: int
    solved_count: int
    blob_pending_count: int
    puzzles: list[TrainPuzzle]
    solved_results: list[SolvedResult]
    is_warmup: bool


# Phase 233 (SEED-190): per-puzzle telemetry boundary. Mirrored by the frontend in
# frontend/src/lib/trainTelemetry.ts (plain integer literals, regex-parity-tested).
# Schema version stamped as `v` on both patches (a `Literal[1]` cannot reference it).
TELEMETRY_SCHEMA_VERSION: Final = 1
# D-04: a forgotten tab must not record a 9-hour think; a data-quality cap, not a security bound.
TELEMETRY_DURATION_CAP_MS: Final = 30 * 60 * 1000
# Cap on prev/next/token steps through a reveal line (D-14).
TELEMETRY_LINE_STEPS_CAP: Final = 50
# Cap on free-play moves played on the reveal board (D-14).
TELEMETRY_EXPLORE_MOVES_CAP: Final = 50
# Cap on card counts (the reveal shows at most 4 cards today).
TELEMETRY_CARDS_CAP: Final = 10


def _clamp_to(cap: int) -> Callable[[object], object]:
    """Build a BeforeValidator that rounds and clamps a number into [0, cap].

    Clamps instead of rejecting (precedent `_clip` in app/schemas/users.py): a
    client clock delta can be fractional or marginally out of range, and a 422
    would throw away the whole record. A bool is returned unchanged (bool is an
    int subclass, strict int must still reject it), as is anything non-numeric
    (or a non-finite float) so strict validation rejects it.
    """

    def _clamp(value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return value
        if isinstance(value, float) and not math.isfinite(value):
            return value
        return max(0, min(cap, round(value)))

    return _clamp


TelemetryDurationMs = Annotated[
    int,
    BeforeValidator(_clamp_to(TELEMETRY_DURATION_CAP_MS)),
    Field(ge=0, le=TELEMETRY_DURATION_CAP_MS, strict=True),
]
TelemetryCardCount = Annotated[
    int,
    BeforeValidator(_clamp_to(TELEMETRY_CARDS_CAP)),
    Field(ge=0, le=TELEMETRY_CARDS_CAP, strict=True),
]
TelemetryLineSteps = Annotated[
    int,
    BeforeValidator(_clamp_to(TELEMETRY_LINE_STEPS_CAP)),
    Field(ge=0, le=TELEMETRY_LINE_STEPS_CAP, strict=True),
]
TelemetryExploreMoves = Annotated[
    int,
    BeforeValidator(_clamp_to(TELEMETRY_EXPLORE_MOVES_CAP)),
    Field(ge=0, le=TELEMETRY_EXPLORE_MOVES_CAP, strict=True),
]


class SolveTelemetry(BaseModel):
    """Client-measured think-time telemetry riding on the solve POST (Phase 233).

    D-01: validated at the boundary (`extra="forbid"`, typed and capped fields,
    a `v` schema-version key), so nothing unvalidated reaches the JSONB column.
    D-02: `guess_ms` is board shown -> guess pressed, `move_ms` is guess pressed
    -> move played, both measured client-side (the server cannot measure this,
    puzzles are pre-materialized at composition). D-04: only visible time is
    counted; the hidden span is stored as `think_hidden_ms` here and as
    `review_hidden_ms` on the review patch. The two are distinct keys on purpose
    (refinement of D-04's single `hidden_ms`): the per-key last-write-wins merge
    would otherwise let the review flush overwrite the think value. D-09:
    `client` is a closed Literal. `resumed` marks a timer that restarted after a
    reload or remount. D-05: never an input to grading, scoring, the SR ladder or
    the leaderboard.
    """

    model_config = ConfigDict(extra="forbid")

    # Must equal TELEMETRY_SCHEMA_VERSION (a Literal cannot reference the constant).
    v: Literal[1]
    client: Literal["mobile", "desktop"] | None = None
    guess_ms: TelemetryDurationMs | None = None
    move_ms: TelemetryDurationMs | None = None
    think_hidden_ms: TelemetryDurationMs | None = None
    resumed: StrictBool | None = None


class ReviewTelemetry(BaseModel):
    """Client-measured reveal telemetry flushed once per puzzle (Phase 233).

    D-03: accumulated in the reveal and flushed via the review route on Next and
    on page unload; no per-click events. D-07: `exit` is required, the abandon
    analysis derives "puzzle N was shown" from puzzle N-1's `exit == "next"`.
    `exit` is a closed enum with no third value: "next" means the user pressed
    Next on the reveal, "pagehide" means the user left the reveal WITHOUT pressing
    Next (page hidden or unloaded, in-app route change or screen unmount, leaving
    via Analyze). A reveal can be flushed with "pagehide" several times and then
    with "next" (the user came back), so every counter is a cumulative TOTAL,
    never a delta: each later flush overwrites per key via the jsonb merge.
    D-14: the closed counter set (no flip counter, no Solution-return counter),
    plus `review_board_moves` (quick 261007-axc).
    D-04: `review_hidden_ms` is the hidden-tab span of the review (the solve
    patch carries `think_hidden_ms`, distinct keys so the merge cannot collide).

    No wrap validator here (unlike `SolveRequest.telemetry`): the body IS the
    telemetry, so a bad body is a normal 422.
    """

    model_config = ConfigDict(extra="forbid")

    # Must equal TELEMETRY_SCHEMA_VERSION (a Literal cannot reference the constant).
    v: Literal[1]
    # "next" = pressed Next on the reveal; "pagehide" = left the reveal WITHOUT
    # pressing Next (page hidden/unloaded, route change or unmount, Analyze).
    exit: Literal["next", "pagehide"]
    review_ms: TelemetryDurationMs | None = None
    review_hidden_ms: TelemetryDurationMs | None = None
    # D-12: distinct cards inspected at least once, and the number shown.
    review_cards_opened: TelemetryCardCount | None = None
    review_cards_total: TelemetryCardCount | None = None
    review_line_steps: TelemetryLineSteps | None = None
    review_explored: StrictBool | None = None
    # Every user-played free-play move: board moves plus Stockfish engine-line clicks.
    review_explore_moves: TelemetryExploreMoves | None = None
    # Quick 261007-axc: only the moves played on the board by hand (drag or tap),
    # a subset of review_explore_moves. Absent on rows from older clients.
    review_board_moves: TelemetryExploreMoves | None = None
    review_analyze_opened: StrictBool | None = None
    # D-13: the Phase 222 first-reveal walkthrough was active on this reveal.
    review_walkthrough: StrictBool | None = None


class SolveRequest(BaseModel):
    """Body for POST /train/sessions/{session_id}/solve.

    P-02 (LOCKED) / SEED-119: the client asserts a three-way `move_quality`
    tier (the backend never grades the move — grading is still entirely
    client-side, see the module/plan docstrings) but NEVER `correct_guess`
    or `puzzle_type` — those are computed server-side from the live
    `game_flaws` blob so the sharp/soft ground truth is never handed to the
    client before the attempt (T-189-18/T-189-11). The server derives the
    spaced-repetition ladder's pass/fail boolean from `move_quality`
    (`!= "wrong"`) — see `app.repositories.train_repository.record_solve`.

    Phase 211 (D-03/D-07) narrows the sentence above: as of this phase the
    backend DOES grade the move for the one case where it owns the truth —
    a `played_move` matching the server-certified key (the soft blob's `su`,
    or a qualifying herring ladder entry). The client's assertion is still
    required in every request and still authoritative for every OFF-key move
    (D-04's accepted residual); for a key move the server recomputes the
    tier from its own stored evals and discards the client's value. This is
    the same shape as the pre-existing `_compute_correct_guess` override —
    the client can never assert a verdict it does not own. The request
    schema itself is unchanged (P-01 intact: the client cannot know the key
    before attempting).

    Phase 233 (SEED-190): `telemetry` is optional so a stale frontend bundle
    still solves. Invalid telemetry never costs the solve (D-02): a malformed
    object is dropped to None and only the telemetry is lost. It is never an
    input to grading (D-05).
    """

    position: int
    guess: Literal["critical", "several"]
    # UCI move string: 4 chars normal (e.g. "e2e4"), 5 chars promotion (e.g. "e7e8q").
    played_move: str = Field(min_length=4, max_length=5)
    move_quality: Literal["good", "inaccuracy", "wrong"]
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


class VettedMove(BaseModel):
    """One server-certified "also fine" alternative move (Phase 211, D-01).

    The wire twin of `app.services.train_pool.VettedMove` (same name,
    different module — mapped field-by-field at the router). Deliberately
    thin: only the UCI and its pre-classified quality tier cross the wire;
    the underlying expected scores stay server-side (the graded-ES pair on
    `SolveResponse` covers the one move that needs numbers client-side).

    POST-ATTEMPT-ONLY material: this model appears exclusively on
    `SolveResponse`, which is produced solely by `record_solve` after the
    attempt row is resolved. Never add it to `TrainPuzzle` (P-01) or
    `SolveRequest`.

    D-01 amendment (2026-08-16): quality "best" marks the deep best move
    itself, served first on a soft puzzle alongside the certified
    second-best (`game_positions.best_move` supplies the UCI; su-only when
    unavailable) so the "several fine moves" copy is always backed by a
    displayable alternative after the client filters its own best/played
    arrows out of the row.
    """

    uci: str
    quality: Literal["best", "good", "inaccuracy"]


class SolveResponse(BaseModel):
    """Response for POST /train/sessions/{session_id}/solve.

    `item_status`/`streak`/`due_date` are None for a red-herring puzzle,
    which carries no SR bookkeeping (POOL-08). `correct_guess` is always the
    server-computed verdict, never an echo of the client's own guess.

    SEED-119: `correct_move` retains its exact prior meaning — the
    spaced-repetition ladder's pass/fail verdict, which is also what the
    reveal's check/cross mark reads. `move_quality` is the new three-way
    scoring tier the client's points formula consumes; it is NOT a synonym
    for `correct_move` (an "inaccuracy" tier still means `correct_move=True`).

    Phase 206 (RESEARCH Pitfall 1): `source` mirrors `puzzle_type`'s existing
    shape and lands synchronously with this response — the client's D-19
    your-game predicates read `verdict.source`, never the separate,
    asynchronously-fetched `PuzzleRevealResponse.source`, to avoid a
    post-solve window where a real SR puzzle misrenders as suppressed.

    Phase 211 (D-01/D-03/D-07, amended 2026-08-16): `vetted_moves` is the
    server's certified "also fine" set for this puzzle — the deep best plus
    the blob's `su` for a soft puzzle (best-first; su-only when
    `game_positions.best_move` is unavailable), the good-band ladder entries
    for a herring, always empty for sharp/sharp-filler — and is what the
    reveal's legend row + green arrows render (never the client engine's own
    alternatives). `graded_es_before`
    / `graded_es_after` are non-null EXACTLY when this call claimed the row
    AND the played move matched a vetted entry (the server override): they
    carry the same mover-POV expected scores the overridden `move_quality`
    was computed from, so the client can re-classify the board badge from
    the SAME numbers the score came from — display and recorded verdict can
    never diverge for a key move.
    """

    correct_guess: bool
    correct_move: bool
    move_quality: Literal["good", "inaccuracy", "wrong"]
    puzzle_type: Literal["sharp", "soft", "herring"]
    source: Literal["sr_item", "red_herring", "sharp_filler"]
    item_status: Literal["active", "mastered", "parked"] | None
    streak: int | None
    due_date: date | None
    session_complete: bool
    vetted_moves: list[VettedMove]
    graded_es_before: float | None
    graded_es_after: float | None


class PuzzleRevealResponse(BaseModel):
    """Response for GET /train/sessions/{session_id}/puzzles/{position}/reveal.

    Reachable ONLY after the attempt is recorded (409 otherwise — T-189-17):
    the puzzle type and the in-game move are unreachable before `solved_at`
    is set.

    190.1-03 (D-01/D-05): this response is DELIBERATELY thin. The answer key
    it carries is the puzzle type, the in-game move (SAN + UCI), and a
    tactic-lines pointer — no `best_move`, `best_move_san`, or `pv` field.
    The best move, the best line, and every eval shown in the reveal panel
    are computed CLIENT-SIDE by the grading engine (`useTrainGradingEngine.ts`),
    never derived or stored here — a server-stored Stockfish eval and the
    client's own WASM search are not guaranteed to agree bit-for-bit
    (project_eval_nondeterminism), so this endpoint must never be a second,
    contradicting source of truth for a number the reveal panel displays.

    `played_in_game_move_uci` (190.1-01, D-05) is the UCI counterpart of
    `played_in_game_san`, behind the identical 409 gate — the client uses it
    to dispatch its own reveal-time engine search (T-190.1-01/T-190.1-02).

    `has_tactic_lines` is a POINTER, not a payload: when True, the client
    calls the existing `GET /api/library/flaws/{game_id}/{ply}/tactic-lines`
    endpoint for the steppable PV line. Train adds no second PV-fetching
    surface — see 189-05-PLAN.md's key_links.

    `game_id` is `int | None` (Phase 192 Plan 02, D-01/D-05): `None` means the
    puzzle's source game has since been deleted. The client hides the Analyze
    deep-link in that case (D-09) rather than disabling it — nothing else on
    the reveal panel references the game either way.
    """

    game_id: int | None
    ply: int
    fen: str
    played_in_game_san: str | None
    played_in_game_move_uci: str | None
    puzzle_type: Literal["sharp", "soft", "herring"]
    source: Literal["sr_item", "red_herring", "sharp_filler"]
    has_tactic_lines: bool
    # Phase 206 (D-20): the sharp filler's motif label. None for every
    # SR_ITEM/RED_HERRING row.
    motif: str | None


#: Phase 222 (TRAINBOT-05, D-11/D-12): the path parameter for
#: POST /train/onboarding/{step}. FastAPI 422s any value outside this set
#: before the handler body runs — no hand-rolled validation, and the
#: repository maps each member through a fixed column lookup (never a
#: string interpolated into SQL, never `getattr` on a request-supplied name).
OnboardingStep = Literal["intro", "reveal_walkthrough", "sr_explained"]


class TrainSettingsResponse(BaseModel):
    """Response for GET/PUT /train/settings.

    `reminder_enabled`/`reminder_hour` (Phase 201, REMIND-01/D-18) are the
    user-owned reminder configuration, round-tripped through this same
    settings surface so it is fully testable before Phase 202 builds any UI.
    `reminder_last_sent_on` is deliberately absent — it is the reminder job's
    own watermark (D-06), never readable or writable by a client.
    `reminder_intent_at` (Phase 203, OFFER-03/OFFER-05/D-02/D-15) is the
    OPPOSITE of `reminder_last_sent_on`: it IS client-writable (stamped when
    the user taps the iOS install affordance), so it appears here.

    `intro_seen_at`/`reveal_walkthrough_seen_at`/`sr_explained_at` (Phase 222,
    TRAINBOT-05, D-11/D-12/D-13) are the three bot-onboarding "explanation
    seen" watermarks. Like `reminder_last_sent_on`, each is a server-owned
    fact — but unlike it, all three ARE readable here (so the client can
    branch on them without a second fetch) while remaining absent from
    `TrainSettingsUpdate`: they are stamped ONLY by the dedicated
    `POST /train/onboarding/{step}` endpoint on stepper completion, never by
    a settings PUT. No backfill (D-13): every row that predates these
    columns reads back NULL on all three, meaning "never seen."

    `has_mobile_subscription` (Phase 222 UAT round 5) is a derived, read-only
    fact: whether ANY of the account's push subscriptions came from a mobile
    browser (`push_repository.MOBILE_USER_AGENT_PATTERN`). The desktop score
    screen uses it to replace the phone QR handoff with a "reminders on your
    phone" line — a per-device subscription probe can never answer that.
    """

    timezone: str
    weekday_mask: int
    puzzles_per_session: int
    reminder_enabled: bool
    reminder_hour: int
    reminder_intent_at: datetime | None
    intro_seen_at: datetime | None
    reveal_walkthrough_seen_at: datetime | None
    sr_explained_at: datetime | None
    has_mobile_subscription: bool


class TrainSettingsUpdate(BaseModel):
    """Body for PUT /train/settings.

    A separate schema from `TrainSettingsResponse` (not one schema reused for
    both directions) so a PUT body can never smuggle a server-owned field.
    `weekday_mask`/`puzzles_per_session`/`reminder_hour` bounds mirror the
    `train_settings` table's CHECK constraints exactly. `reminder_last_sent_on`
    is deliberately absent for the same reason it is absent from
    `TrainSettingsResponse` — see that class's docstring.

    `reminder_intent_at` has NO default (required-but-nullable), a deliberate
    choice per D-02: this schema is a full-replace PUT body, so a defaulted
    field would let a payload that omits the key silently clear a
    previously-recorded install intent. Omitting the key must 422 loudly
    instead. No bound validator: a timestamp has no injection surface
    (RESEARCH.md Security Domain V5).
    """

    timezone: str
    weekday_mask: int = Field(ge=0, le=127)
    puzzles_per_session: int = Field(ge=1, le=50)
    reminder_enabled: bool
    reminder_hour: int = Field(ge=REMINDER_HOUR_MIN, le=REMINDER_HOUR_MAX)
    reminder_intent_at: datetime | None

    @field_validator("timezone")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        """D-06: reject an unresolvable IANA timezone with 422, never persist it.

        A stored bad zone would silently shift every future due-date and
        session-window computation (`local_today` falls back to UTC for a
        legacy bad value already on a row, but nothing new may be written
        that way).
        """
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Unrecognized IANA timezone: {value!r}") from exc
        return value


class TrainProgressResponse(BaseModel):
    """Response for GET /train/progress (PROG-01/PROG-04).

    Phase 193 (SEED-121) replaced Phase 191's weekly D-18 settled-streak
    snapshot with a per-scheduled-day tick + a 0-7 depletable shield:
    `session_streak_count` (was `settled_streak_weeks`; the wire field spells
    out the D-02 unit — it counts completed scheduled-day SESSIONS, not
    settled weeks) and `shield_level` (was `flame_state`, a 3-state enum;
    now a plain int) come from the persisted tick snapshot on
    `train_settings`, lazily advanced by this same request
    (`app.repositories.train_repository.settle_streak_snapshot`). There is
    no display overlay any more — the returned values are always exactly
    what is persisted. `current_week_required` is None when
    `weekday_mask == 0` ("train anytime" has no denominator to show);
    otherwise it is the popcount of the scheduled-day mask (no special-
    casing — nothing gates on this value any more).
    `mastered_count`/`parked_count` are computed on the fly from
    `drill_items` (D-05, unaffected by the tick snapshot — only the
    streak/shield portion is persisted).

    `waiting_count`/`pool_state`/`next_due_date` are the server-side signals
    the nav badge and the two PROG-05 empty states need: `waiting_count` is
    an upper-bound estimate of puzzles waiting right now (never a promise of
    exact session size — see
    `app.repositories.train_repository.get_waiting_puzzle_count`).
    `pool_state` is the single discriminant the client branches on for the
    empty states: `"no_material"` means the user has never had any
    qualifying material (cold start); `"exhausted"` means material existed
    but nothing is waiting and nothing is still analyzing; `"available"`
    covers every other case, including a zero-`drill_items` user whose own
    blunders are still being analyzed (that is "catching up", not a cold
    start). `next_due_date` is the earliest date an ACTIVE item will next
    resurface, or null when nothing will (the "All caught up!" empty state's
    date).

    `streak_reset_notice` (was `streak_lost_last_week`) is derived from the
    RESULTING state (never from "did this call settle the reset"), so it
    survives a page reload and self-clears once the user trains again.

    `badge_visible` (Plan 02, D-09/D-10) is a DISPLAY HINT ONLY — it gates no
    server-side authorization, and the number the nav badge shows still
    comes from `waiting_count`. True when `waiting_count > 0` AND (today is
    a scheduled day per the user's `weekday_mask` OR an already-open
    unexpired session still has unsolved puzzles left to rescue). The client
    performs no day-of-week or timezone math of its own — it has no
    `weekday_mask` and no clean way to reproduce `local_today`, so this
    field is the single source of truth for whether the badge should show.
    """

    session_streak_count: int
    shield_level: int
    current_week_completed: int
    current_week_required: int | None
    streak_reset_notice: bool
    mastered_count: int
    parked_count: int
    waiting_count: int
    pool_state: Literal["no_material", "exhausted", "available"]
    next_due_date: date | None
    badge_visible: bool


LeaderboardBoardKind = Literal["points", "accuracy"]
LeaderboardVisibility = Literal["public", "hidden", "guest"]
MedalKind = Literal["gold", "silver", "bronze"]


class LeaderboardMedals(BaseModel):
    """Lifetime medal counts of one row's user (Phase 231). Counts only, no user id."""

    model_config = ConfigDict(from_attributes=True)

    gold: int
    silver: int
    bronze: int


class LeaderboardPodiumEntry(BaseModel):
    """One medal on last week's podium: the medal, a read-time masked name and a viewer flag."""

    model_config = ConfigDict(from_attributes=True)

    medal: MedalKind
    name: str
    is_viewer: bool  # True only on the viewer's own entry; carries no user id


class LeaderboardLastWeek(BaseModel):
    """Last week's podium and the viewer's own non-medal rank on one board (Phase 231)."""

    model_config = ConfigDict(from_attributes=True)

    week_start: date  # the previous ISO Monday (UTC)
    podium: list[LeaderboardPodiumEntry]  # gold, silver, bronze; every tied name listed
    viewer_final_rank: int | None  # only when the viewer has a row with no medal (D-03)


class LeaderboardRow(BaseModel):
    """One displayed row of a weekly leaderboard (Phase 230).

    Deliberately carries no user id or email: rows are keyed by position only,
    and the viewer's own row is marked `is_viewer`.
    """

    model_config = ConfigDict(from_attributes=True)

    rank: int | None  # None marks a tentative Accuracy entry (listed below every qualified row)
    name: str
    value: int  # points (Points board) or floored accuracy percent (Accuracy board)
    puzzles: int  # all solves (Points) or non-filler solves (Accuracy)
    tentative: bool  # Accuracy only: puzzles < 20; always False on Points
    is_viewer: bool
    # "public" on every row except the viewer's own hidden/guest row.
    visibility: LeaderboardVisibility
    gap_before: bool  # True on the first row after skipped ranks
    gap_after: bool  # True on the last shown row when ranks below it are cut
    medals: LeaderboardMedals  # lifetime tally, zero counts when the user has no medals


class LeaderboardViewer(BaseModel):
    """The viewer's standing on one board."""

    model_config = ConfigDict(from_attributes=True)

    rank: int | None  # None while the viewer is a tentative Accuracy entry (unranked)
    # Rank without the current session's solves (D-12). Null when no session_id
    # was supplied, the viewer had no entry before the session, or the viewer is
    # tentative with or without the session (no delta across the cutoff).
    rank_without_session: int | None
    tentative: bool
    puzzles_to_qualify: int  # 0 on Points and once qualified
    visibility: LeaderboardVisibility


class LeaderboardPassTarget(BaseModel):
    """The nearest strictly-better row and the points needed to pass it."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    points_needed: int


class LeaderboardBoard(BaseModel):
    """One board: sliced rows, the viewer's standing, and the Points pass target."""

    model_config = ConfigDict(from_attributes=True)

    rows: list[LeaderboardRow]
    viewer: LeaderboardViewer | None
    pass_target: LeaderboardPassTarget | None  # Points board only
    # The immediately previous ISO week only (D-07); null when that board awarded no
    # medal and the viewer has no non-medal row there (D-08).
    last_week: LeaderboardLastWeek | None


class TrainLeaderboardResponse(BaseModel):
    """Response for GET /train/leaderboard: both weekly boards for the viewer.

    No user ids or emails, by design; rows key only by position.
    """

    model_config = ConfigDict(from_attributes=True)

    week_start: datetime
    week_end: datetime
    seconds_remaining: int
    points: LeaderboardBoard
    accuracy: LeaderboardBoard


# About a year of both boards. Caps the unclaimed read and the claim body, so a dialog's
# POST built from a GET is always valid.
MEDAL_CLAIM_MAX_ITEMS: Final = 100


class UnclaimedMedal(BaseModel):
    """One medal the caller has not yet seen celebrated (Phase 231, D-11).

    Carries no row id or user id: a medal is identified by its (week_start, board) pair,
    the per-user natural key the claim POST echoes back.
    """

    model_config = ConfigDict(from_attributes=True)

    week_start: date  # the Monday (UTC)
    board: LeaderboardBoardKind
    medal: MedalKind
    value: int  # final points, or floored accuracy percent
    shared: bool  # another row of the same week, board and medal exists (a tie)


class UnclaimedMedalsResponse(BaseModel):
    """Response for GET /train/medals/unclaimed: newest week first, Points before Accuracy."""

    model_config = ConfigDict(from_attributes=True)

    medals: list[UnclaimedMedal]


class MedalKey(BaseModel):
    """The natural key of one medal in a claim request: no row id, no user id."""

    week_start: date
    board: LeaderboardBoardKind


class ClaimMedalsRequest(BaseModel):
    """Body of POST /train/medals/claim: the shown medals' keys, never "all unclaimed"."""

    medals: list[MedalKey] = Field(min_length=1, max_length=MEDAL_CLAIM_MAX_ITEMS)


__all__ = [
    "MEDAL_CLAIM_MAX_ITEMS",
    "ClaimMedalsRequest",
    "LeaderboardBoard",
    "LeaderboardBoardKind",
    "LeaderboardLastWeek",
    "LeaderboardMedals",
    "LeaderboardPassTarget",
    "LeaderboardPodiumEntry",
    "LeaderboardRow",
    "LeaderboardViewer",
    "LeaderboardVisibility",
    "MedalKey",
    "MedalKind",
    "PuzzleRevealResponse",
    "SolveRequest",
    "SolveResponse",
    "SolvedResult",
    "TrainLeaderboardResponse",
    "TrainProgressResponse",
    "TrainPuzzle",
    "TrainSessionResponse",
    "TrainSettingsResponse",
    "TrainSettingsUpdate",
    "UnclaimedMedal",
    "UnclaimedMedalsResponse",
    "VettedMove",
]
