# Phase 148: Pipeline & tactic correctness fixes (code-review 2026-07-02) - Context

**Gathered:** 2026-07-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix five silent-data-loss / production-only-correctness defects surfaced by the
2026-07-02 fable code review. Each fix ships with a unit test and a verify loop. No
new capabilities, no refactors beyond the fix sites, no performance/headroom work
(those were explicitly deferred to seeds in the triage — see Deferred Ideas).

The five items (todo numbering):

1. **Tactic production defects** — `has_forced_mate` no-op (deep mates never tag) +
   `fen_map` stores `board_fen()` (drops ep/castling → parse failures + corrupt PV
   boards). Files: `app/services/tactic_detector.py`, `app/services/flaws_service.py`.
2. **Entry-ply drain all-fail circuit breaker** — `evals_completed_at` stamped even
   on a dead pool. File: `app/services/eval_drain.py` (+ `engine.py` docstring).
3. **Quintile significance test anti-conservative** — overlapping cohorts treated as
   independent → false "significant" verdicts. File: `app/services/endgame_service.py`.
4. **One malformed platform game aborts the whole import** — unguarded per-game
   normalization. Files: `app/services/chesscom_client.py`, `app/services/lichess_client.py`.
5. **Entry-submit batch-scoping minimum guard.** File: `app/routers/eval_remote.py`.

</domain>

<decisions>
## Implementation Decisions

User chose "leave the decisions to you" on every fork. The four genuine forks are
resolved below; the rest of each item follows the todo's prescribed fix verbatim.

### Item 1 — tactic mate fallback (recall vs precision)
- **D-01:** On a truncated forced-mate PV (`has_forced_mate` set but the capped PV
  doesn't end in `is_checkmate()`), **tag generic `mate`** — do NOT suppress.
  Rationale: `has_forced_mate` derives from a real engine mate score; the PV is only
  truncated at `PV_CAP_PLIES = 12`, so the mate is genuine, not a false positive.
  Suppressing would drop a real tag (the current bug). Skip geometry-dependent mate
  subtypes when the line is truncated — we cannot verify the mating pattern.
- **D-02:** The `fen_map` fix stores full `board.fen()` in the **detector-internal**
  map only (for `parse_san` / PV replay). Keep `board_fen()` for Zobrist position
  comparisons per the CLAUDE.md rule — do not swap those call sites.
- **D-03:** Add `has_forced_mate` flag coverage (zero today). Research MUST re-run the
  tactic precision gate after this change — newly-tagging deep mates can shift
  `fixtures/tagger/*.csv` scores; confirm no motif regresses below its precision floor.

### Item 3 — quintile stats fix depth
- **D-04:** Use the **covariance-correction term**, not a full paired test. Track the
  shared-game count `m` per (tc, quintile) and subtract the anti-correlated covariance
  (`+2m·cov/(n_u·n_o)` in the SE). Reuses the existing `compute_score_difference_test`
  path; point estimates are unaffected; least invasive. Also fix the wrong
  independence docstring at `endgame_service.py:2140-2143`.

### Item 5 — entry-submit scoping depth
- **D-05:** Ship the **minimum guard** — add `entry_eval_lease_expiry > now()` to the
  submit guard. Do NOT build the full echoed-`game_ids`-intersection path; it's
  operator-error-triggered and the shipped worker uses random ids (low real-world
  likelihood). The fuller version is captured as a deferred idea.

### Plan decomposition
- **D-06:** Recommend splitting into subsystem-cohesive plans so each has an isolated
  test + verify loop; final decomposition is the planner's call. Natural seams:
  (a) tactics = item 1, (b) eval-lease correctness = items 2 + 5 (both eval-pipeline
  lease/submit), (c) stats covariance = item 3, (d) import robustness = item 4.
  Whatever the grouping, **every one of the five items gets its own test + verify**.

### Claude's Discretion
- Exact test fixture selection and the precise covariance algebra are left to
  research/planning, constrained by the decisions above and the verification notes
  in the source todo.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase source (primary — read first)
- `.planning/todos/pending/2026-07-03-code-review-pipeline-tactic-correctness-phase.md`
  — the five items with exact fix strategy, file:line anchors, and per-item
  verification. This is the authoritative spec for the phase.
- `.planning/notes/2026-07-03-code-review-fable-triage.md` — triage rationale: why
  these five are in-scope and what was explicitly deferred (SEED-077/078) or dropped.
- `reports/code-review-fable-2026-07-02.md` — the underlying review (full detail per
  finding; the todo/triage distill it).

### Tactic detection (item 1)
- `app/services/tactic_detector.py` §`has_forced_mate` (~2462-2490) — the no-op branch.
- `app/services/flaws_service.py` (~443-451) — `fen_map` construction.
- `app/services/precision_floors.py` — per-motif precision floors + `SUPPRESSED_MOTIFS`;
  the gate that must not regress. See memory `project_tactic_precision_gate_vs_fixtures`.
- Tests MUST build detector boards via the conftest `build_detector_board`
  (PreFlawFEN + push), NOT `chess.Board(fen)` — see memory
  `project_tactic_detector_flaw_move_context`.

### Eval pipeline (items 2, 5)
- `app/services/eval_drain.py` — entry-ply drain (~2304-2308 stamp site;
  ~2556-2570 the WR-05 full-ply breaker to mirror).
- `app/services/engine.py` (~380-382) — `EnginePool` docstring to correct.
- `app/routers/eval_remote.py` (~746-813) — entry-submit stamping.
- Related closed work / lease invariants: memories
  `project_atomic_eval_submit_incremental_lease`,
  `project_atomic_submit_staledata_and_8b`.

### Stats (item 3)
- `app/services/endgame_service.py` (~2140-2143 docstring; ~2326-2328 fix site) +
  `compute_score_difference_test`. Established method — see memory
  `feedback_wilson_chess_score` (don't editorialize methodology).

### Import (item 4)
- `app/services/chesscom_client.py` (~325-330), `app/services/lichess_client.py`
  (~184-188) — unguarded `normalize_*_game` calls. CLAUDE.md per-game try/except rule.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **WR-05 all-fail breaker** in `eval_drain.py` (~2556-2570) is the exact pattern to
  mirror for item 2 (release lease, one aggregated Sentry event, sleep — do NOT stamp).
- **conftest `build_detector_board`** — the faithful detector-board builder for item 1
  tactic tests.
- **`compute_score_difference_test`** — reuse for item 3; add the covariance term
  around it rather than replacing it.

### Established Patterns
- Per-game try/except + skip + ONE aggregated Sentry capture is already how PGN parse
  is handled; item 4 extends the same pattern to normalization (not yet guarded).
- Sentry rules (CLAUDE.md): no variables in messages; aggregate on last/aggregated
  event, not per transient failure.

### Integration Points
- Item 1 `fen_map` change is detector-internal only; Zobrist/position-comparison call
  sites using `board_fen()` stay untouched.

</code_context>

<specifics>
## Specific Ideas

- The five items are largely independent and touch different subsystems; there is no
  cross-item ordering dependency beyond "each verifies on its own."
- Verification targets from the source todo: tactic mate-fallback unit test + an
  ep/castling flaw fixture; a dead-pool drain test (lease released, NOT stamped); a
  shared-cohort significance test asserting SE widens; a malformed-game import test
  asserting skip + job completes.

</specifics>

<deferred>
## Deferred Ideas

- **Item 5 full scoping** — return claimed `game_ids` from `/entry-lease` and stamp
  only the echoed/intersected set. Deferred in favor of the minimum guard (D-05);
  capture as a seed if the worker ever moves off random ids.
- **SEED-077** — per-request `game_positions` aggregation elimination (import-time
  columns). Explicitly deferred in the triage; not this phase.
- **SEED-078** — chess.com archive streaming (OOM headroom). Explicitly deferred.
- Report items #8/#12/#13/#15 and tactic-recall (#14/6.2.1) — not scheduled; see triage.

### Reviewed Todos (not folded)
- None to fold — the phase's own source todo is the spec; the todo-match tool only
  surfaced unrelated keyword hits (WR-01 frontend, bitboard storage).

</deferred>

---

*Phase: 148-pipeline-tactic-correctness-fixes-code-review-2026-07-02*
*Context gathered: 2026-07-04*
