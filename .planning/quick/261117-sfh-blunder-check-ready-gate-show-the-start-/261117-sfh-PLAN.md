---
phase: quick-261117-sfh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/schemas/blunder_check.py
  - app/services/blunder_check_service.py
  - app/routers/blunder_check.py
  - tests/routers/test_blunder_check_drill.py
  - CHANGELOG.md
  - frontend/src/types/blunderCheck.ts
  - frontend/src/api/client.ts
  - frontend/src/hooks/useBlunderCheckSession.ts
  - frontend/src/lib/blunderCheckDrill.ts
  - frontend/src/lib/__tests__/blunderCheckDrill.test.ts
  - frontend/src/lib/trainBotCopy.ts
  - frontend/src/lib/__tests__/trainBotCopy.test.ts
  - frontend/src/components/train/blunder-check/BlunderCheckDrill.tsx
  - frontend/src/components/train/blunder-check/BlunderCheckTab.tsx
  - frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx
autonomous: true
requirements:
  - QUICK-261117-sfh

estimate:
  tokens: 130000
  raw_tokens: 130000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "L-01/L-05: POST /blunder-check/sessions/{id}/windows/{pos}/start on a fresh window (every position of a session, not only the first) returns awaiting_ready=true, answered=[], the first judged move as prompt, timer_remaining_ms equal to the full MOVE_TIMER_SECONDS*1000, stamps blunder_check_windows.started_at, and inserts NO blunder_check_answers row."
    - "L-05: POST .../windows/{pos}/begin inserts the first prompt row with prompted_at = the begin request's now_utc and returns the same WindowStartResponse shape with awaiting_ready=false and the real timer; an answer 13 s after a begin that followed a 120 s gate is graded on its merits (not a timeout) with server_elapsed_ms 13000."
    - "L-05: a reload during the gate (start again before begin) returns the gate again with the full timer and still no answer row; begin is idempotent (a second begin, or a start after Ready, reports the remaining time from the ORIGINAL prompted_at and never re-stamps it)."
    - "L-05: an answer while the gate is up is refused 409 stale_prompt with no points and no row; begin before start is 409 not_started; begin on an ended window is 409 window_ended; begin on a foreign or unknown session/window is 404; a non-beta user gets 403."
    - "L-01/L-02: in the browser a fresh window shows its start position (board oriented to the user's side, no arrow, no timer) and the host bubble says 'Check out the position, you play {white|black}. It's your opponent's turn.' ('It's your turn.' when the start FEN has the user to move) with a Ready button (data-testid blunder-check-btn-ready) inside the bubble; nothing auto-starts and no request is sent however long the user waits."
    - "L-03: Ready sends exactly one begin request (double clicks included) and then the existing lead-in runs unchanged: LEAD_IN_START_DELAY_MS, the opponent's ply, the prompt with the server's 10 s countdown; a failed begin lands on the error screen."
    - "L-04: no migration, no score versioning or comparability field; CHANGELOG [Unreleased] carries a user-facing bullet."
  artifacts:
    - path: app/services/blunder_check_service.py
      provides: "start_window opens the Ready gate (no prompt row), begin_window issues the first prompt, shared _window_start payload builder, WindowStart.awaiting_ready"
      contains: "async def begin_window"
    - path: app/routers/blunder_check.py
      provides: "POST /sessions/{session_id}/windows/{position}/begin (thin, _guarded), awaiting_ready in _start_response"
      contains: "/begin"
    - path: app/schemas/blunder_check.py
      provides: "WindowStartResponse.awaiting_ready"
      contains: "awaiting_ready: bool"
    - path: tests/routers/test_blunder_check_drill.py
      provides: "_begin helper, gate-aware _started helper, Ready-gate timing, idempotency, reload and order tests"
      contains: "def _begin"
    - path: frontend/src/lib/blunderCheckDrill.ts
      provides: "ready_gate and beginning phases, READY_CONFIRMED and WINDOW_BEGUN events"
      contains: "WINDOW_BEGUN"
    - path: frontend/src/lib/trainBotCopy.ts
      provides: "blunderCheckReadyCopy(side, sideToMove)"
      contains: "blunderCheckReadyCopy"
    - path: frontend/src/components/train/blunder-check/BlunderCheckDrill.tsx
      provides: "ReadyGate bubble with the Ready button, useWindowBeginner effect"
      contains: "blunder-check-btn-ready"
  key_links:
    - from: "frontend/src/components/train/blunder-check/BlunderCheckDrill.tsx useWindowBeginner"
      to: "app/services/blunder_check_service.py begin_window -> blunder_check_repository.insert_prompt"
      via: "useBlunderCheckSession().beginWindow -> blunderCheckApi.beginWindow -> POST .../begin; prompted_at = begin's now_utc"
      pattern: "beginWindow"
    - from: "app/services/blunder_check_service.py start_window"
      to: "_window_start (no answer rows => awaiting_ready=True)"
      via: "one shared payload builder for start and begin, so the gate and the post-Ready payload cannot drift"
      pattern: "awaiting_ready"
    - from: "frontend/src/lib/blunderCheckDrill.ts windowLoaded"
      to: "ready_gate -> READY_CONFIRMED -> beginning -> WINDOW_BEGUN -> lead_in"
      via: "response.awaiting_ready"
      pattern: "ready_gate"
---

<objective>
Add a Ready gate to every blunder-check window: the window loads paused on its start position, the host bubble names the user's side and whose turn it is, and the opponent's lead-in move plus the 10 s prompt clock start only when the user presses Ready.

Purpose: users said blunder check feels like being catapulted into someone else's bullet game. Today `start_window` stamps the first prompt's `prompted_at` at load, so the clock (and the 15 s answer ceiling) already runs while the user is still orienting. A client-only pause would turn any study longer than a few seconds into a timeout, so the clock origin moves to a new server "begin" step.

Output: a `begin` endpoint and an `awaiting_ready` flag on the window payload (no migration), the reducer's `ready_gate`/`beginning` phases, the Ready bubble, updated and new tests, a CHANGELOG bullet.

Locked owner decisions (cited as L-NN in the tasks):
- L-01: every window of a session, not only the first, loads paused on the start position instead of auto-playing the lead-in.
- L-02: the avatar speech bubble says "Check out the position, you play white|black. It's your opponent's turn." (side from the window orientation) with a Ready button inside the bubble. Untimed, no auto-start.
- L-03: on Ready, the existing lead-in sequence (opponent's move replay, then the prompt with the 10 s timer) runs exactly as today.
- L-04: no score versioning or comparability handling; a somewhat higher first-move accuracy is accepted.
- L-05 (orchestrator constraint): the first prompt's `prompted_at` is stamped by the begin step, so the clock starts only after Ready. A reload during the gate shows the gate again with no time lost; a reload after Ready keeps the original `prompted_at` exactly as today. Prefer no DB migration.

Planner discretion (decided here):
- No migration. `start` still stamps `blunder_check_windows.started_at` (the window was opened, the gate is up) but no longer inserts the first `blunder_check_answers` row; `begin` inserts it. "Gate up" is exactly "started window with no answer rows". Bonus metric for later: Ready-gate study time is the first answer row's `prompted_at` minus the window's `started_at`.
- `begin` returns the same `WindowStartResponse` as `start` (awaiting_ready=false), built by one shared helper, so start and begin can never disagree.
- The gate payload still carries `lead_in_ucis` and the first judged move's arrow (accepted in the threat model: neither is key material).
- The bubble's turn sentence is derived from the start FEN's side to move vs the orientation, so a window whose lead-in is 0 plies (first judged ply 0, `max(0, first_ply - LEAD_IN_PLIES)` in `app/services/blunder_check_candidates.py`) says "It's your turn." instead of a false claim.
- Ready is the bubble's single primary CTA: `variant="default"`. No Umami event: Phase 249 D-19 ("no Umami event for blunder check") is enforced by a test in BlunderCheckTab.test.tsx, and begin creates a DB row anyway.
</objective>

<coverage_audit>
| Source item | Covered by |
|-------------|-----------|
| GOAL: window pauses on the start position until Ready | Task 1 (server gate), Task 2 (reducer gate), Task 3 (UI) |
| L-01 every window, not only the first | Task 1 test on a second window, Task 2 reducer test after NEXT_WINDOW, Task 3 session-end flow presses Ready per window |
| L-02 bubble copy + Ready inside the bubble, untimed, no auto-start | Task 3 (blunderCheckReadyCopy, ReadyGate bubble, 60 s idle test) |
| L-03 lead-in unchanged after Ready | Task 2 (WINDOW_BEGUN -> lead_in, constants untouched), Task 3 (lead-in timing test after Ready) |
| L-04 no score versioning | No schema/version field anywhere; truth 7 |
| L-05 clock starts at begin, reload semantics, no migration | Task 1 tests (gate reload, 120 s gate then 13 s answer, idempotent begin, post-Ready reload) |
| Orchestrator: reducer tests for gate + Ready transition | Task 2 |
| Orchestrator: backend timing tests (no time during gate, clock at begin, idempotent, reload) | Task 1 |
| Orchestrator: update tests that assume auto-start | Task 1 (_started helper, tracer test), Task 2 (begun() helper), Task 3 (reachFirstPrompt, finishWindowWithBlunderCall, inline flows) |
| Orchestrator: CHANGELOG [Unreleased] bullet | Task 1 |
| Orchestrator: repo rules (thin router, Literal, return types, now_utc dependency, no magic numbers, depth <= 4, testid, sparing em-dashes) | Every task's action and verify (check_function_size, eslint max-depth) |
</coverage_audit>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@frontend/CLAUDE.md
@app/services/blunder_check_service.py
@app/routers/blunder_check.py
@app/schemas/blunder_check.py
@frontend/src/lib/blunderCheckDrill.ts
@frontend/src/components/train/blunder-check/BlunderCheckDrill.tsx

Key facts verified at planning time (HEAD 925119733):
- `start_window` (app/services/blunder_check_service.py ~290-343) calls `mark_window_started` then `insert_prompt(move_index=_FIRST_MOVE_INDEX, ply=window.first_ply, prompted_at=now_utc)` and builds `WindowStart` from `answers_for_window`. `insert_prompt` is `ON CONFLICT (window_id, move_index) DO NOTHING`, so a repeat keeps the original stamp. `mark_window_started` only stamps when `started_at IS NULL`.
- `_load_answerable` raises `not_started` when `started_at` is NULL and `stale_prompt` when there is no open row, so an answer during the gate is already a 409 `stale_prompt` with no code change. The frontend's stale-prompt path re-fetches the window (it lands back on the gate).
- `ConflictReason` already has `not_started`, `window_ended`, `session_closed`; no new literal is needed.
- `timer_remaining_ms(prompted_at, now)` and `MOVE_TIMER_SECONDS`, `MS_PER_SECOND` live in app/services/blunder_check_grading.py; `_build_outcome` already uses `MOVE_TIMER_SECONDS * MS_PER_SECOND` for a fresh prompt.
- Router routes use `_guarded(...)` (commit, 404/409/422 mapping, Sentry capture) and `NowUtc` (dev_now_utc). Paths are relative to `APIRouter(prefix="/blunder-check")`.
- tests/routers/test_blunder_check_solution.py imports `_started`, `_ok`, `_call`, `_setup` from tests/routers/test_blunder_check_drill.py; `_started` is also used there to resume a caught window during the better-move step (start returns `better_move`, so begin must NOT be called then).
- Frontend: `IMMERSIVE_PHASES` in BlunderCheckTab.tsx lists every in-window phase; the new phases must join it or the tab bar flashes in during the gate. `sideToMoveFromFen(fen): 'white' | 'black'` already exists in frontend/src/lib/liveFlaw.ts. `TrainBotBubble` takes `state` ('prompt' is valid), children (copy) and `actions` (buttons row).
- Baselines: `uv run pytest tests/routers/test_blunder_check_drill.py tests/routers/test_blunder_check_solution.py -n auto -q` -> 56 passed; frontend blunderCheckDrill + trainBotCopy tests -> 129 passed; src/components/train/blunder-check/__tests__/ -> 81 passed.
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Server Ready gate end to end: start opens the gate, begin starts the clock (HTTP -> service -> repository -> Postgres)</name>
  <files>app/schemas/blunder_check.py, app/services/blunder_check_service.py, app/routers/blunder_check.py, tests/routers/test_blunder_check_drill.py, CHANGELOG.md</files>
  <read_first>
    - app/services/blunder_check_service.py (WindowStart dataclass ~127-141, _open_row, _check_startable, _resume_better_move, start_window ~290-343, _load_answerable, _build_outcome)
    - app/routers/blunder_check.py (_guarded, _start_response, start_window route)
    - app/schemas/blunder_check.py (WindowStartResponse ~84-102)
    - tests/routers/test_blunder_check_drill.py (helpers 186-270, tracer test 282-319, constants 326-342, _started/_ok 358-367, ceiling/reload tests 461-520, payload test 522-536, order/IDOR/non-beta tests 563-613 and 716-721)
    - tests/routers/test_blunder_check_solution.py lines 80-120 (how _started is reused for the better-move resume)
  </read_first>
  <behavior>
    - Gate on start: a fresh window's start returns awaiting_ready=True, answered=[], prompt == first judged move (move_index 1), timer_remaining_ms == 10000, writes started_at and NO answer row.
    - Reload during the gate: start again 120 s later returns the same gate (awaiting_ready True, timer 10000), still zero answer rows, started_at unchanged.
    - Clock starts at begin: start at T0, begin at T0+120 s -> awaiting_ready False, timer 10000, exactly one row with prompted_at == T0+120 s; a "safe" answer at T0+133 s on a herring is correct_safe (not timeout_safe) with server_elapsed_ms 13000. With the old code this answer would be a timeout (133 s after the start stamp).
    - Idempotent begin: begin at T0+120, advance 6 s, begin again -> timer 4000, still one row stamped T0+120; start after Ready (reload) -> awaiting_ready False, timer 4000, same prompt (today's reload semantics).
    - Order: answer during the gate -> 409 stale_prompt, window points 0, no row; begin before start -> 409 not_started; begin on an ended window -> 409 window_ended; begin by another user / unknown window -> 404; non-beta begin -> 403.
    - Every window gates (L-01): after window 0 ends, start of window 1 also returns awaiting_ready True.
    - Better-move resume unchanged: start on a caught window waiting for its better move returns awaiting_ready False with better_move set.
  </behavior>
  <action>
    Implements L-05 (clock origin at begin, reload semantics, no migration) and the server half of L-01. Write the new tests first (RED: they fail against current start_window, which stamps the prompt at load), then implement (GREEN).

    Schema (app/schemas/blunder_check.py): add `awaiting_ready: bool` to `WindowStartResponse` with a comment: true while the window sits on its Ready gate (start was called but no prompt is issued yet, so no clock runs); `prompt` is then the first judged move and `timer_remaining_ms` the full countdown it will get; false on every begin response and on any reload after Ready.

    Service (app/services/blunder_check_service.py):
    - Add `awaiting_ready: bool = False` as the last field of the `WindowStart` dataclass (after `better_move`), with a one-line comment. `_resume_better_move` keeps the default False.
    - Add a module constant for the full countdown (e.g. `_FULL_TIMER_MS: Final = MOVE_TIMER_SECONDS * MS_PER_SECOND`) and use it in the gate payload and in `_build_outcome` instead of the inline product (no magic numbers).
    - Extract the WindowStart construction from `start_window` into one helper, e.g. `async def _window_start(session, window, *, session_id: int, rows: list[BlunderCheckAnswer], now_utc: datetime.datetime) -> WindowStart`. When `rows` is empty it returns the gate: `answered=[]`, `prompt=PromptData(_FIRST_MOVE_INDEX, _arrow_uci(window, window.first_ply))`, `timer_remaining_ms=_FULL_TIMER_MS`, `awaiting_ready=True`. Otherwise it keeps today's logic exactly (open row or 409 window_ended, answered moves, `timer_remaining_ms(open_row.prompted_at, now_utc)`, awaiting_ready False). Explicit return types everywhere; keep nesting depth <= 3.
    - `start_window`: keep `_resume_better_move`, `_check_startable`, the `earlier_windows_ended` check and `mark_window_started`; REMOVE the `insert_prompt` call; then load rows and return `_window_start(...)`. Update its docstring: start opens the window on its Ready gate (L-01/L-05) and issues no prompt, so no time runs; a reload during the gate returns the gate again; after Ready the open prompt keeps its original `prompted_at` (D-18). Add the bug-context comment at the removed call: the first prompt used to be stamped here, so the clock ran while the user was still looking at the position (quick 261117-sfh).
    - New `async def begin_window(session, *, user_id: int, session_id: int, position: int, now_utc: datetime.datetime) -> WindowStart`: `get_window_for_user` (None -> BlunderCheckNotFoundError), `_check_startable(header, window)` (session_closed / window_ended), `window.started_at is None` -> `BlunderCheckConflictError("not_started")`, then `insert_prompt(window_id=window.id, move_index=_FIRST_MOVE_INDEX, ply=window.first_ply, prompted_at=now_utc)` (ON CONFLICT DO NOTHING makes a repeat keep the original stamp: idempotent, never buys time), load rows, return `_window_start(...)`. Docstring: Ready on the gate; the clock starts here; idempotent. No new repository function and no SQL in the service (insert_prompt and answers_for_window already exist).
    - Update the module docstring's first paragraph to mention the Ready gate (start opens it, begin issues the first prompt). Mention that `started_at` marks the gate opening and the first answer row's `prompted_at` marks Ready.

    Router (app/routers/blunder_check.py): add `awaiting_ready=start.awaiting_ready` to `_start_response`. Add `@router.post("/sessions/{session_id}/windows/{position}/begin", response_model=WindowStartResponse)` `async def begin_window(session_id: SessionIdPath, position: PositionPath, session: Annotated[AsyncSession, Depends(get_async_session)], user: BetaUser, now_utc: NowUtc) -> WindowStartResponse` that mirrors `start_window`: `_guarded(session, blunder_check_service.begin_window(...), user_id=..., session_id=..., position=...)` then `_start_response`. Relative path only, no logic in the router, docstring "Ready on the gate: issue the first prompt and start its clock (idempotent)."

    Tests (tests/routers/test_blunder_check_drill.py):
    - Add `"awaiting_ready"` to `_START_KEYS`. Add `async def _begin(token: str, session_id: int, position: int) -> httpx.Response` posting to `{_BASE}/{session_id}/windows/{position}/begin`.
    - Make `_started(s, position)` gate-aware (what the client does): call `_start`, assert 200; if the body's `awaiting_ready` is true, call `_begin`, assert 200 and return the begin body; else return the start body. Update its docstring. This keeps every existing flow (and test_blunder_check_solution.py, which imports `_started`) on the real path, including the better-move resume where begin must not be called.
    - Tracer test `test_tracer_start_and_catch_position_one_blunder`: also assert `body["awaiting_ready"] is True` and `body["timer_remaining_ms"] == _FULL_TIMER_MS`, then `_begin` (assert 200, awaiting_ready False) before the existing answer.
    - `test_payload_shapes_leak_no_key_material`: also take the raw gate body from `_start` before `_started`, and assert its key set is `_START_KEYS` and it carries none of `_FORBIDDEN_KEYS`.
    - Extend `test_idor_another_users_session_and_window_answer_404` with a begin by the other user (404) and `test_non_beta_user_is_refused_on_the_drill_routes` with `_begin(token, 1, 0)` (403).
    - New section "Ready gate (quick 261117-sfh)" with a named constant `_GATE_STUDY_S = 120` (well past ANSWER_CEILING_S) and these tests, each using the existing `clock` fixture and `_answer_rows`/`_window_row` helpers: `test_ready_gate_start_opens_the_gate_without_a_prompt`, `test_ready_gate_reload_shows_the_gate_again_with_no_time_lost`, `test_ready_gate_time_never_counts_toward_the_answer_ceiling` (herring: start, advance _GATE_STUDY_S, begin, advance _BEFORE_CEILING_S, answer safe -> correct_safe, rows[0].prompted_at == _T0 + _GATE_STUDY_S, server_elapsed_ms == _BEFORE_CEILING_S * 1000), `test_ready_gate_begin_is_idempotent_and_never_buys_time` (uses _RELOAD_DELAY_S and _RELOAD_REMAINING_MS; second begin and a post-Ready start both report 4000, one row, original stamp), `test_ready_gate_answer_and_begin_out_of_order_are_rejected` (answer during gate -> 409 stale_prompt + 0 points + no row; begin before start -> 409 not_started; after the window ends, begin -> 409 window_ended), and `test_ready_gate_every_window_opens_on_the_gate` (two windows: play window 0 to its end via `_started`/`_ok`, then raw `_start` of window 1 returns awaiting_ready True with no answer row for it).
    - Existing tests that go through `_started` keep their assertions unchanged (e.g. `test_ceiling_reload_keeps_the_original_prompt_stamp`: start+begin at T0 gives 10000, the reload 6 s later gives 4000).

    CHANGELOG.md: under `## [Unreleased]` -> `### Changed`, append: "- Blunder check (beta): every sequence now opens paused on its starting position, and the host tells you which side you play and whose turn it is. Press Ready when you have looked at the position: the opponent's move and the 10-second timer only start then." (no em-dash).

    Run `uv run ruff format app/ tests/` and `uv run ruff check . --fix` before the verify command.
  </action>
  <verify>
    <automated>uv run pytest tests/routers/test_blunder_check_drill.py tests/routers/test_blunder_check_solution.py tests/repositories/test_blunder_check_repository.py -n auto -q && uv run ruff format --check app/ tests/ && uv run ruff check . && uv run ty check app/ tests/ scripts/ && uv run python scripts/check_function_size.py app/ --fail-over-depth 4</automated>
  </verify>
  <done>All drill, solution and repository blunder-check tests pass (56 prior router tests plus the new Ready-gate tests); ruff format/check, ty and the nesting gate are clean; start on a fresh window issues no prompt row and reports awaiting_ready True; begin stamps the first prompt at its own instant and is idempotent; CHANGELOG has the bullet. No Alembic revision was created.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Frontend contract and state machine: awaiting_ready, beginWindow transport, ready_gate -> beginning -> lead_in</name>
  <files>frontend/src/types/blunderCheck.ts, frontend/src/api/client.ts, frontend/src/hooks/useBlunderCheckSession.ts, frontend/src/lib/blunderCheckDrill.ts, frontend/src/lib/__tests__/blunderCheckDrill.test.ts</files>
  <read_first>
    - frontend/src/lib/blunderCheckDrill.ts (DrillState/DrillEvent unions 114-156, betterMoveResumed, windowLoaded 240-263, leadInTick, nextWindow, drillProgress, drillReducer)
    - frontend/src/lib/__tests__/blunderCheckDrill.test.ts (fixtures 26-113, lead-in tests 141-161, resume tests 163-240, line ~256, WINDOW_LOADED-after-stale tests 701-743)
    - frontend/src/types/blunderCheck.ts (WindowStartResponse)
    - frontend/src/api/client.ts lines 380-416 (blunderCheckApi)
    - frontend/src/hooks/useBlunderCheckSession.ts
  </read_first>
  <behavior>
    - WINDOW_LOADED with awaiting_ready true (from loading_window) -> phase ready_gate: window.shownUcis is [], prompt and timerMs come from the response, sessionPoints from the response; drillProgress shows the window's position and pot.
    - In ready_gate, LEAD_IN_TICK, ANSWER_SUBMITTED, ADVANCE_TICK and WINDOW_BEGUN return the same state object (nothing plays, nothing is answerable).
    - READY_CONFIRMED: ready_gate -> beginning with the same window and prompt; a second READY_CONFIRMED in beginning returns the same state; READY_CONFIRMED in lead_in or prompt returns the same state.
    - WINDOW_BEGUN in beginning with a fresh begin response -> lead_in with shownUcis [] and timerMs = the begin response's timer_remaining_ms; LEAD_IN_TICKs then replay the lead-in and hand over to the prompt exactly as before (L-03).
    - WINDOW_BEGUN whose response already has answered moves (another tab answered) -> prompt with them applied (server state wins); WINDOW_BEGUN with awaiting_ready true -> error phase.
    - L-01: after NEXT_WINDOW, a WINDOW_LOADED with awaiting_ready true for position 1 lands in ready_gate at position 1.
    - WINDOW_LOADED with awaiting_ready false keeps today's behavior (fresh-after-Ready reload -> lead_in with the server's remaining time; answered moves -> prompt; better_move -> better_move).
  </behavior>
  <action>
    Implements the client half of L-01 and L-05 and keeps L-03 (lead-in constants untouched). Write the reducer tests first (RED), then the code (GREEN).

    Types (frontend/src/types/blunderCheck.ts): add `awaiting_ready: boolean` to `WindowStartResponse`, mirroring the Pydantic comment from Task 1 (true while the window waits on its Ready gate; prompt is the first judged move and timer_remaining_ms the full countdown; false on begin and on reloads after Ready). Update the interface's doc comment ("Window start (or reload) and begin").

    API client (frontend/src/api/client.ts, blunderCheckApi): update the `startWindow` doc comment (a fresh window comes back paused on its Ready gate, awaiting_ready). Add a `beginWindow(sessionId: number, position: number)` member next to `startWindow`, same shape: POST (no body) to `/blunder-check/sessions/{sessionId}/windows/{position}/begin`, typed `WindowStartResponse`, returning `r.data`. Doc comment: Ready, issues the first prompt and starts its clock; idempotent, a repeat reports the real time left.

    Hook (frontend/src/hooks/useBlunderCheckSession.ts): add `const beginWindow = useMutation<WindowStartResponse, Error, WindowRef>({ mutationFn: ({ sessionId, position }) => blunderCheckApi.beginWindow(sessionId, position) })`, return it, and update the header comment from "six mutations" to "seven mutations". No Sentry call (global MutationCache handles it).

    Reducer (frontend/src/lib/blunderCheckDrill.ts):
    - Header doc: the loop is now loading -> Ready gate -> lead-in replay -> prompt ...; the gate is untimed and the server starts the clock at begin (L-05).
    - DrillState: add `({ phase: 'ready_gate'; prompt: Prompt; timerMs: number } & InWindow)` and `({ phase: 'beginning'; prompt: Prompt; timerMs: number } & InWindow)` with short comments (ready_gate: start position shown, waiting for Ready; beginning: Ready pressed, the begin request is in flight).
    - DrillEvent: add `{ type: 'READY_CONFIRMED' }` and `{ type: 'WINDOW_BEGUN'; response: WindowStartResponse }`.
    - Refactor `windowLoaded` so its body after the phase guard lives in a shared helper (e.g. `windowFromServer(session: DrillSession, response: WindowStartResponse, forceResume: boolean): DrillState`): better_move -> betterMoveResumed; `response.awaiting_ready` -> ready_gate with shownUcis [] (checked after better_move, before the resume logic); otherwise today's resumed/lead_in logic unchanged. `windowLoaded` keeps accepting loading_window and grading and passes `forceResume = state.phase === 'grading'`.
    - `readyConfirmed(state)`: only ready_gate -> `{ ...state, phase: 'beginning' }`, else return state unchanged.
    - `windowBegun(state, response)`: only from beginning (else return state); `response.awaiting_ready` -> `{ phase: 'error', message: UNEXPECTED_RESPONSE_MESSAGE }`; otherwise `windowFromServer(state.session, response, false)`.
    - Wire both into `drillReducer`. `drillProgress` needs no change (its default branch covers phases that carry a window); verify it compiles. Keep every function shallow (eslint max-depth 4).

    Tests (frontend/src/lib/__tests__/blunderCheckDrill.test.ts):
    - Add `awaiting_ready: false` to the `windowStart()` fixture default (the begin / post-Ready shape).
    - Add a `begun(response: WindowStartResponse = windowStart()): DrillState` helper: SESSION_READY, WINDOW_LOADED with `{ ...response, awaiting_ready: true, answered: [], better_move: null }`, READY_CONFIRMED, WINDOW_BEGUN with `response`. Switch the fresh-window callers to it: `atPrompt()`, the 'lead-in' describe block (lines ~143 and ~158) and the `leadIn = loaded()` at ~256. Resume tests keep `loaded(...)` (a reload after answers has awaiting_ready false). The inline WINDOW_LOADED sequences at ~468 and ~530 may stay: they model a reload after Ready with nothing answered, which still replays the lead-in.
    - New `describe('ready gate (L-01, L-05)')` covering every bullet of the behavior block above, using `asPhase` and `toBe` identity checks for ignored events, and a distinct timer constant for the begin response so the test proves timerMs comes from begin.
    - Leave the 'animation budget' tests untouched (L-03 keeps the constants).
  </action>
  <verify>
    <automated>( cd frontend && npm test -- --run src/lib/__tests__/blunderCheckDrill.test.ts && npm run lint && npm run build )</automated>
  </verify>
  <done>The reducer tests (existing plus the new ready-gate block) pass; lint (max-depth 4) and `tsc -b` + vite build pass; the hook exposes `beginWindow` and the client posts to `.../begin`.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Ready bubble on the board: copy, Ready button, begin request, immersive gate, tab tests on the real gated flow</name>
  <files>frontend/src/lib/trainBotCopy.ts, frontend/src/lib/__tests__/trainBotCopy.test.ts, frontend/src/components/train/blunder-check/BlunderCheckDrill.tsx, frontend/src/components/train/blunder-check/BlunderCheckTab.tsx, frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx</files>
  <read_first>
    - frontend/src/components/train/blunder-check/BlunderCheckDrill.tsx (InWindowState 85-89, showsPromptArrow, useWindowLoader 216-240, WindowView 438-536, useAnswering 549-605, BlunderCheckDrill switch 695-755)
    - frontend/src/components/train/blunder-check/BlunderCheckTab.tsx lines 36-50 (IMMERSIVE_PHASES)
    - frontend/src/components/train/TrainBotBubble.tsx (props: persona, state, nudgeNonce, actions, children)
    - frontend/src/lib/trainBotCopy.ts lines 200-222 and 822-852 (copy style, blunder-check copy)
    - frontend/src/lib/liveFlaw.ts line 36 (sideToMoveFromFen)
    - frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx (api mock 52-80, global beforeEach 212-240, window-loop fixtures 373-492, tests at 504, 625, 649, 892-961, session-end helpers 1369-1392, D-19 test 1456+)
  </read_first>
  <behavior>
    - blunderCheckReadyCopy('white', 'black') === "Check out the position, you play white. It's your opponent's turn."; ('black', 'white') -> "...you play black. It's your opponent's turn."; ('white', 'white') -> "Check out the position, you play white. It's your turn."; no output contains "your move" or an em-dash.
    - Tab: after Start, a fresh window shows the start FEN, no arrow, no timer, no Good/Blunder buttons, the gate copy and an enabled Ready button; 60 s of fake time later the board is unchanged and neither begin nor answer was called (untimed, no auto-start, L-02).
    - Tab: Ready calls beginWindow(7, 0) once, then the lead-in plays after LEAD_IN_START_DELAY_MS and the prompt opens with the 10s countdown (L-03); a double click on Ready sends one begin; a rejected begin shows the blunder-check-error screen.
    - Tab: every window gates (L-01): the session-end flow presses Ready on both windows; a reload with answered moves (awaiting_ready false) still resumes straight on the prompt with the server's remaining time (D-18 tests unchanged in substance).
  </behavior>
  <action>
    Implements L-02 (copy, Ready inside the bubble, untimed) and the UI side of L-01 and L-03.

    Copy (frontend/src/lib/trainBotCopy.ts): add `export function blunderCheckReadyCopy(side: 'white' | 'black', sideToMove: 'white' | 'black'): string` returning "Check out the position, you play {side}. It's your opponent's turn." when `sideToMove !== side`, else "Check out the position, you play {side}. It's your turn." (straight apostrophes like the surrounding copy, no em-dash). Doc comment: the blunder-check Ready gate bubble (L-02); the turn sentence follows the start FEN so a window with no lead-in ply does not claim the opponent moves first. Add its tests to frontend/src/lib/__tests__/trainBotCopy.test.ts (the four behavior cases).

    Drill host (frontend/src/components/train/blunder-check/BlunderCheckDrill.tsx):
    - Header doc: the window first waits on its Ready gate (start position, host bubble, Ready); the lead-in, the countdown and everything after start only after Ready.
    - Add `'ready_gate' | 'beginning'` to `InWindowState`; `showsPromptArrow` returns false for them (as for lead_in).
    - Add `type BeginWindowAsync = BlunderCheckSession['beginWindow']['mutateAsync']` and `useWindowBeginner(state, dispatch, beginWindow)` mirroring `useWindowLoader`: active only in phase 'beginning'; on success dispatch `{ type: 'WINDOW_BEGUN', response }`; on failure dispatch FAILED with 'Failed to start the sequence'; cancelled flag in the cleanup. Begin is idempotent server-side, so a StrictMode double effect is harmless.
    - Add a small `ReadyGateBubble` component (persona, orientation, startFen, beginning, onReady): a `TrainBotBubble` with `state="prompt"`, children `<p data-testid="blunder-check-ready-copy">` showing `blunderCheckReadyCopy(orientation, sideToMoveFromFen(startFen))` (import sideToMoveFromFen from '@/lib/liveFlaw'), and `actions` = one `Button` `variant="default"` (single primary CTA per frontend/CLAUDE.md), `className={TRAIN_BUTTON_CLASS}`, `disabled={beginning}`, `onClick={onReady}`, `data-testid="blunder-check-btn-ready"`, label "Ready". Wrap the bubble region in an element with `data-testid="blunder-check-ready-gate"`. No timer is rendered in this bubble. No Umami call (Phase 249 D-19, enforced by the tab test).
    - `WindowView`: add an `onReady: () => void` prop; when the phase is ready_gate or beginning render `ReadyGateBubble` (window.orientation, window.startFen, beginning = phase === 'beginning'), otherwise the existing question bubble unchanged. Rendering the gate inside WindowView keeps the board mounted from the gate into the lead-in (no remount flicker) and keeps `useMoveSounds` counting from the start position, so the opponent's ply still sounds. If the question bubble markup makes WindowView long, extract it into its own small component; keep nesting <= 4.
    - In `BlunderCheckDrill`: `const handleReady = useCallback((): void => dispatch({ type: 'READY_CONFIRMED' }), [dispatch])`, call `useWindowBeginner(state, dispatch, session.beginWindow.mutateAsync)` next to `useWindowLoader`, add `case 'ready_gate':` and `case 'beginning':` to the WindowView group of the switch, pass `onReady={handleReady}`. `useAnswering` needs no change: its timer only runs in 'prompt' and reads timerMs only in lead_in/prompt.

    Tab container (frontend/src/components/train/blunder-check/BlunderCheckTab.tsx): add 'ready_gate' and 'beginning' to `IMMERSIVE_PHASES` (after 'loading_window'), so the tab bar does not flash in while the gate is up.

    Tab tests (frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx):
    - Add `const beginWindow = vi.fn<(sessionId: number, position: number) => Promise<WindowStartResponse>>()` and `beginWindow: (sessionId: number, position: number) => beginWindow(sessionId, position)` to the `blunderCheckApi` mock; reset it in the global beforeEach.
    - Make begin mirror the server: its default implementation returns the latest start payload with `awaiting_ready: false` (e.g. read the last entry of `startWindow.mock.results`, or keep a module-level `lastStart` the start mocks write), and it must NOT call the `startWindow` mock (tests at ~946, ~960 and ~1106-1111 assert startWindow call counts). Executor's choice of mechanism within those constraints.
    - The `windowStart()` fixture defaults to `awaiting_ready: true` (what start returns for a fresh window). The reload fixtures that carry `answered: ANSWERED_FIRST_MOVE` (~895, ~923, ~949) set `awaiting_ready: false`.
    - Add `async function pressReady(): Promise<void>` (click `blunder-check-btn-ready`, then `await advance(50)` so begin resolves) and call it after the window loads in `reachFirstPrompt`, `finishWindowWithBlunderCall` (before its lead-in advances, so both windows of the session-end flow gate), and the inline flows of the tests at ~504 and ~625.
    - Rework the test at ~504 into the gate story: after Start assert the start FEN, no arrows, `blunder-check-btn-ready` enabled, no `blunder-check-btn-safe` and no `blunder-check-timer`; then pressReady and keep the existing lead-in/arrow assertions.
    - New tests in 'window loop': (a) "a fresh window waits on its start position until Ready, untimed": override start with a realistic one-ply lead-in (start_fen = applyUcis(START_FEN, ['e2e4']), lead_in_ucis ['e7e5'], orientation 'white'), assert `blunder-check-ready-copy` text is "Check out the position, you play white. It's your opponent's turn.", advance 60_000 ms, assert board unchanged and beginWindow/answer not called, then pressReady and assert beginWindow called once with (7, 0), the opponent ply appears after LEAD_IN_START_DELAY_MS and the prompt shows '10s'; (b) "a double click on Ready sends one begin request" (begin mock pending, two clicks, called once, button disabled); (c) "a failed begin ends on the error screen" (begin rejects -> `blunder-check-error`).
    - Extend 'never says "your move" during the drill (D-09)' to also check the page text while the gate is up.
  </action>
  <verify>
    <automated>( cd frontend && npm test -- --run src/lib/__tests__/blunderCheckDrill.test.ts src/lib/__tests__/trainBotCopy.test.ts src/components/train/blunder-check/__tests__/ && npm run lint && npm run build && npm run knip )</automated>
  </verify>
  <done>All blunder-check component tests (81 prior, updated for the gate, plus the new gate tests), the reducer tests and the copy tests pass; lint, build and knip are clean; the Ready button has data-testid blunder-check-btn-ready, sits inside the host bubble, and is the only way the lead-in starts.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser -> API (`POST .../windows/{position}/begin`, `.../start`) | Untrusted path params (session_id, position) and untrusted timing: the client decides when to call begin and when to answer |
| API -> Postgres (`blunder_check_answers.prompted_at`) | The server-side clock origin the answer ceiling (D-18) is measured from |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-sfh-01 | Elevation of privilege (IDOR) | `begin_window` route/service | high | mitigate | Route uses `BetaUser` (403 for non-beta) and `SessionIdPath`/`PositionPath` bounds (422); service loads via `get_window_for_user(user_id=...)`, which scopes by the authenticated user (404 for foreign or unknown ids). Task 1 extends the IDOR and non-beta tests with begin. |
| T-sfh-02 | Tampering (buying answer time) | `begin_window`, `start_window`, `insert_prompt` | medium | mitigate | `insert_prompt` is ON CONFLICT DO NOTHING, so a repeated begin or a reload never re-stamps `prompted_at`; the reported timer is computed from the original stamp. An answer before begin is refused (409 stale_prompt, no row, no points). Task 1 tests: idempotent begin reports 4000 ms after 6 s, one row with the original stamp; answer during the gate rejected. |
| T-sfh-03 | Information disclosure | gate payload (`lead_in_ucis`, first `prompt.move_uci`) | low | accept | Neither is key material: whether the arrow is a blunder, the key, the case and later moves stay server-side (D-16); `_FORBIDDEN_KEYS` test runs on the gate body too. A devtools user can study the first arrow without a clock, but an engine already evaluates it inside the 10 s window, and the owner accepted a higher first-move accuracy (L-04). |
| T-sfh-04 | Denial of service | begin endpoint spam | low | accept | Same cost as start (two indexed reads and one no-op insert per call), beta-gated and authenticated; no new unbounded work. |
| T-sfh-SC | Tampering | npm/pip/cargo installs | low | accept | No package is installed or added; no lockfile changes. |
</threat_model>

<verification>
- Task verify commands above, in order (backend first: the frontend relies on the begin route existing).
- Backend regression: test_blunder_check_drill.py + test_blunder_check_solution.py were 56 passed at HEAD 925119733; after this plan they pass with the new Ready-gate tests added.
- No migration: `git status --porcelain alembic/` shows nothing new.
- The full pre-merge gate in CLAUDE.md (ruff format/check, ty on app/tests/scripts and analysis/, check_function_size, `uv run pytest -n auto -x`, frontend lint/build/test/knip) runs once before the squash-merge to main; it is the orchestrator's integration step, not part of each task.
</verification>

<success_criteria>
- A fresh window of any position loads paused on its start position with the L-02 bubble copy and a Ready button inside the bubble; no countdown, no auto-start.
- Ready triggers exactly one begin request; the server stamps the first prompt then; the lead-in and the 10 s prompt run exactly as before (L-03).
- Reload during the gate returns the gate with no time lost; reload after Ready keeps the original prompted_at (L-05); begin is idempotent.
- No migration and no score versioning (L-04); CHANGELOG [Unreleased] bullet present.
- All touched backend and frontend test files pass; ruff, ty, the nesting gate, eslint, tsc build and knip are clean.
</success_criteria>

<output>
Create `.planning/quick/261117-sfh-blunder-check-ready-gate-show-the-start-/261117-sfh-SUMMARY.md` when done
</output>
