---
phase: 123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big
plan: 03
type: execute
wave: 3
depends_on: ["123-02"]
files_modified:
  - scripts/remote_eval_worker.py
  - tests/test_remote_eval_worker.py
autonomous: true
requirements: ["SEED-051-D-1", "SEED-051-D-2", "D-06", "D-08", "D-10"]
nyquist_compliant: true

must_haves:
  truths:
    - "The worker per-cycle runs the D-06 ladder: POST /lease?scope=explicit → if 204, POST /entry-lease → if 204/empty, POST /lease?scope=idle (entry-ply slots between tier-1 and tier-3)"
    - "Entry-ply positions are evaluated with EnginePool.evaluate (depth-15), NOT evaluate_nodes_with_pv (1M-node), and submitted as {game_id, ply, eval_cp, eval_mate}"
    - "Each worker self-assigns a distinctive ID (random ~8-char base36 default; --worker-id override validated < 10 chars) sent via the X-Worker-Id header on every call"
    - "Entry-ply is ON by default (no opt-in flag, D-08); the server-side D-5 gate makes always-on cost nothing when there's no big import"
  artifacts:
    - path: "scripts/remote_eval_worker.py"
      provides: "D-06 ladder in _run_cycle, _eval_entry_positions depth-15 path, --worker-id flag, X-Worker-Id header, random worker-id generator"
      contains: "entry-lease"
    - path: "tests/test_remote_eval_worker.py"
      provides: "Worker-id generation/validation + ladder-sequencing tests"
      contains: "worker_id"
  key_links:
    - from: "scripts/remote_eval_worker.py::_run_cycle"
      to: "/api/eval/remote/entry-lease"
      via: "D-06 ladder, fired when scope=explicit returns 204"
      pattern: "entry-lease"
    - from: "scripts/remote_eval_worker.py::_eval_entry_positions"
      to: "EnginePool.evaluate"
      via: "depth-15 eval (NOT evaluate_nodes_with_pv)"
      pattern: "pool.evaluate"
    - from: "scripts/remote_eval_worker.py httpx.AsyncClient"
      to: "X-Worker-Id header"
      via: "set once on the client alongside X-Operator-Token"
      pattern: "X-Worker-Id"
---

<objective>
Upgrade the worker CLI: orchestrate the D-06 three-rung ladder across endpoints, add the depth-15 entry-ply eval path, self-assign a distinctive worker ID, and transport it via the `X-Worker-Id` header.

Purpose: This is the client half of the fan-out. The worker drives the ladder (tier-1 explicit → entry-ply → tier-3 idle) so entry-ply slots between tier-1 and tier-3 with no preemption (D-1/D-6). The distinctive worker ID makes the `leased_by` / `entry_eval_leased_by` columns (D-09) actually useful in prod. Entry-ply is always-on (D-08) — the server's D-5 gate already makes it free when there's no big import. Old worker binaries still work (scope-absent, header-absent defaults from Plan 02), so deploy server first, upgrade workers at leisure.

Output: The ladder in `_run_cycle`, `_eval_entry_positions`, the `--worker-id` flag + generator, the `X-Worker-Id` header wiring, and worker-side tests.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

@.planning/phases/123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-/123-CONTEXT.md
@.planning/phases/123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-/123-RESEARCH.md
@.planning/phases/123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-/123-PATTERNS.md
@.planning/phases/123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-/123-02-SUMMARY.md

# Read these source files first for exact analog shapes:
@scripts/remote_eval_worker.py
@app/services/engine.py
@app/schemas/eval_remote.py
</context>

## Artifacts this phase produces (Plan 03 subset)

- `_eval_entry_positions(pool, positions)` — new depth-15 helper (`pool.evaluate`, NOT `evaluate_nodes_with_pv`); returns `{game_id, ply, eval_cp, eval_mate}`
- D-06 ladder in `_run_cycle` — explicit → entry-lease → idle
- `--worker-id` CLI flag (default None → random ~8-char base36; override validated < 10 chars)
- random worker-id generator at process startup
- `X-Worker-Id` HTTP header on the httpx client (alongside `X-Operator-Token`)

<tasks>

<task type="auto">
  <name>Task 1: Worker-ID generation + --worker-id flag + X-Worker-Id header</name>
  <files>scripts/remote_eval_worker.py</files>
  <read_first>
    @scripts/remote_eval_worker.py (`parse_args` — the `--workers`/`--idle-sleep` validation pattern; the `httpx.AsyncClient(headers={"X-Operator-Token": token}, ...)` wiring; `run_worker` signature threading).
    PATTERNS.md "scripts/remote_eval_worker.py" section (the `--worker-id` validation + header wiring excerpts).
    RESEARCH Pitfall 5 (VARCHAR(16) overflow — validate < 10 chars; base36 ~8 chars).
  </read_first>
  <action>
    Add a `--worker-id` argument to `parse_args` (default None, metavar "ID", help text noting "Distinctive worker identity for leased_by columns; default: random ~8-char base36"). After parse, if `args.worker_id is not None and len(args.worker_id) >= 10`: `parser.error("--worker-id must be < 10 chars")` (mirror the existing `--workers` validation; this is an expected user-input ValueError — do NOT Sentry-capture). Generate a random default at process startup when none is given: ~8-char base36 (e.g. from `secrets`/`uuid`, truncated; must fit VARCHAR(16) per D-09 with headroom). Thread the resolved worker_id through `run_worker` → the httpx client.

    Set the `X-Worker-Id` header ONCE on the `httpx.AsyncClient` alongside the existing `X-Operator-Token` (no per-call change): `headers={"X-Operator-Token": token, "X-Worker-Id": worker_id}`.
  </action>
  <verify>
    <automated>uv run python -c "import scripts.remote_eval_worker" && uv run ty check scripts/remote_eval_worker.py</automated>
  </verify>
  <acceptance_criteria>
    `--worker-id` exists, validates < 10 chars (rejects a 10+ char value via parser.error). A random ~8-char base36 default is generated when the flag is absent. The `X-Worker-Id` header is set on the httpx client alongside `X-Operator-Token`. `ty check` clean.
  </acceptance_criteria>
  <done>Worker self-assigns a distinctive ID (random default or validated --worker-id) and transports it via X-Worker-Id; ty clean.</done>
</task>

<task type="auto">
  <name>Task 2: Depth-15 entry-ply eval path + D-06 ladder in _run_cycle</name>
  <files>scripts/remote_eval_worker.py</files>
  <read_first>
    @scripts/remote_eval_worker.py (`_eval_positions` [the full-ply analog — copy its shape but swap the engine call], `_run_cycle`/`_run_loop` [the single-lease cycle to restructure], the full-ply submit POST body shape).
    @app/services/engine.py (`EnginePool.evaluate` — depth-15, returns `tuple[int|None, int|None]`; `evaluate_nodes_with_pv` — the 1M-node mode that must NOT be used for entry-ply).
    PATTERNS.md "scripts/remote_eval_worker.py" section (the `_eval_entry_positions` body + the D-06 ladder excerpt) and the Anti-Patterns table (evaluate vs evaluate_nodes_with_pv).
  </read_first>
  <action>
    Add `_eval_entry_positions(pool, positions)`: reconstruct boards with `chess.Board(str(p["fen"]))`, eval each with `pool.evaluate(b)` (depth-15 — engine.py; CRITICAL: NOT `pool.evaluate_nodes_with_pv`, the 1M-node full-ply mode — RESEARCH Anti-pattern: mixing makes entry-ply ~10x slower and wrong-budget). Gather the evals (these are independent EnginePool tasks, not one AsyncSession — gather is fine here). Return `[{game_id, ply, eval_cp, eval_mate}]` from the `(cp, mate)` tuples. Entry-ply carries NO best_move/pv.

    Restructure `_run_cycle` into the D-06 ladder: `POST /api/eval/remote/lease?scope=explicit` → if 204, `POST /api/eval/remote/entry-lease` (gated server-side by the D-5 probe) → if 204/empty, `POST /api/eval/remote/lease?scope=idle` (tier-3, handle as today). On a 200 from `/entry-lease`: run `_eval_entry_positions` on the returned `{game_id, ply, fen}[]`, then `POST /api/eval/remote/entry-submit` with `{sf_version, evals}` (the entry-submit body shape from Plan 02's `EntrySubmitRequest`). Entry-ply is ON by default — no opt-in flag (D-08). Busy paths (tier-1, entry-ply) stay 1-2 calls; only the fully-idle path makes all 3 round-trips. Keep the existing error handling / retry-loop discipline (Sentry capture on the final attempt only, never per transient failure; never embed variables in messages).
  </action>
  <verify>
    <automated>uv run python -c "import scripts.remote_eval_worker" && uv run ty check scripts/remote_eval_worker.py && uv run ruff check scripts/remote_eval_worker.py</automated>
  </verify>
  <acceptance_criteria>
    `_eval_entry_positions` calls `pool.evaluate` (depth-15), NOT `evaluate_nodes_with_pv`, and returns cp/mate only. `_run_cycle` runs the explicit→entry-lease→idle ladder; entry-ply is unconditional (no opt-in flag). `/entry-submit` POST carries `{sf_version, evals}`. `ty check` + `ruff check` clean.
  </acceptance_criteria>
  <done>Worker drives the D-06 ladder with a depth-15 entry-ply path, always-on; ty + ruff clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Worker-side tests — ID generation/validation + ladder sequencing</name>
  <files>tests/test_remote_eval_worker.py</files>
  <read_first>
    @scripts/remote_eval_worker.py (the new `--worker-id` validation, the generator, the `_run_cycle` ladder, `_eval_entry_positions`).
    Check whether `tests/test_remote_eval_worker.py` already exists; if so extend it, otherwise create it (mirror an existing CLI/unit test module's import + pytest-asyncio style — grep the tests/ dir for an existing `remote_eval_worker` or `parse_args` test first).
  </read_first>
  <behavior>
    - worker_id_default_length: a generated default worker-id is < 10 chars and base36 (fits VARCHAR(16)).
    - worker_id_override_too_long: `--worker-id` with a 10+ char value raises SystemExit (parser.error); a < 10 char value is accepted as-is.
    - ladder_explicit_first: with /lease?scope=explicit returning 200 work, the cycle evaluates + submits via /submit and does NOT call /entry-lease (busy tier-1 path stays 1-2 calls). (Mock the httpx client / endpoints.)
    - ladder_entry_then_idle: with scope=explicit → 204, the cycle calls /entry-lease; on its 200 it submits via /entry-submit; on its 204 it falls through to scope=idle.
    - entry_eval_uses_depth15: `_eval_entry_positions` calls `pool.evaluate` (assert via a mock/spy that `evaluate_nodes_with_pv` is NOT called).
  </behavior>
  <action>
    Add/extend `tests/test_remote_eval_worker.py` with the above. For ladder sequencing, mock the httpx responses (status codes + bodies) and assert the call order / which submit endpoint is hit. For `_eval_entry_positions`, pass a fake/mock `EnginePool` whose `evaluate` returns a known `(cp, mate)` and assert `evaluate_nodes_with_pv` is never invoked. For the CLI validation, call `parse_args` with a too-long `--worker-id` and assert `SystemExit`. Keep these unit-level (no DB, no real Stockfish) so they run fast in the suite.
  </action>
  <verify>
    <automated>uv run pytest tests/test_remote_eval_worker.py -x</automated>
  </verify>
  <acceptance_criteria>
    All worker tests pass: default ID length/charset, --worker-id length validation, ladder call-order for the busy-tier-1 / entry / idle paths, and the depth-15 (not 1M-node) entry-eval assertion. Unit-level (mocked client + engine), no DB/Stockfish dependency.
  </acceptance_criteria>
  <done>Worker-id generation/validation and the D-06 ladder + depth-15 path are covered by green automated tests.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/test_remote_eval_worker.py -x` green.
- `uv run pytest -n auto` full suite green (wave merge gate).
- `uv run ty check app/ tests/ scripts/remote_eval_worker.py` clean; `uv run ruff check .` clean.
- Grep guard: `_eval_entry_positions` uses `pool.evaluate`, not `evaluate_nodes_with_pv` (`grep -v '^#' scripts/remote_eval_worker.py | grep -A6 '_eval_entry_positions' | grep -c evaluate_nodes_with_pv` == 0 inside that helper).
- Backward-compat (manual, see VALIDATION.md): an old worker (no scope, no X-Worker-Id) still drains full-ply and never touches entry-ply; leased_by falls back to "remote-worker".
</verification>

<success_criteria>
- Worker runs the D-06 ladder (explicit → entry-lease → idle).
- Entry-ply evaluated at depth-15 (EnginePool.evaluate), not 1M-node.
- Distinctive worker ID (random default or validated --worker-id) sent via X-Worker-Id.
- Entry-ply always-on (D-08); the server D-5 gate makes it free when no big import.
- Worker tests green; full suite green; ty + ruff clean.
</success_criteria>

<output>
Create `.planning/phases/123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-/123-03-SUMMARY.md` when done.
</output>
