# Phase 105: Mistake-Detection + Classification + Tagging Service (on-the-fly) - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning
**Source:** Distilled from the SEED-036 `/gsd-explore` session (2026-06-05) — the seed IS the discuss output. No separate discuss-phase pass; all decisions below are locked in `.planning/seeds/SEED-036-library-page-milestone.md`.

<domain>
## Phase Boundary

**Delivers:** A server-side service that, given a Lichess-analyzed game, derives **on-the-fly** from stored per-ply evals every flaw the user made — a **severity** (inaccuracy / mistake / blunder) plus **attribution tags** — and returns typed per-flaw objects ready for downstream surfaces (Games / Flaws / Analysis subtabs) and SEED-037 Train to consume.

**Backend only. No UI. No HTTP endpoint wiring** (the service is consumed by later phases). Comprehensive unit tests + a sanity-check against the game-level Lichess columns are the deliverable proof.

**In scope:**
- Per-ply expected-score (ES) derivation reusing `eval_utils`, with mate via Option B.
- Severity classification (pure expected-score drop, mover POV, no position guard).
- All eight attribution tags.
- A typed flaw-object output contract.
- Explicit "no engine analysis" result for chess.com / unanalyzed-lichess games.
- Tests, incl. close-not-identical agreement with the game-level Lichess B/M/I columns.

**Explicitly OUT of scope (later phases / seed-only):** Games/Flaws/Analysis UI, the mistake-stats panel, the mistake-type **filter integration** into `apply_game_filters()`, the best-move endpoint, card tag-chips + color-by-family, and **materialization** (the service stays on-the-fly; design so materialization is a drop-in later optimization).
</domain>

<decisions>
## Implementation Decisions (LOCKED — from SEED-036)

### Severity (Lichess-identical, halved thresholds)
- Lichess judges on its `winningChances` scale **[−1, +1]** with cutoffs 0.10 / 0.20 / 0.30. Our `eval_cp_to_expected_score` returns **[0, 1]** = `(winningChances + 1) / 2`, i.e. **half** the scale, so the thresholds halve:
  - `INACCURACY_DROP = 0.05`, `MISTAKE_DROP = 0.10`, `BLUNDER_DROP = 0.15` (named constants — no magic numbers).
- `drop = ES_before − ES_after` from the **mover's POV** (side-to-move signed, matching lila `info.color.fold(-d, d)`). Highest band wins.
- **Pure drop, NO position guard** — no `ES_before < 0.85` gate, no losing-side floor. The sigmoid's saturation is the only suppression (matches lila `CpAdvice`).
- ES via `app/services/eval_utils.py::eval_cp_to_expected_score`. Lichess does NOT clamp cp in the judgment path, so the existing un-clamped function is correct as-is for cp.

### Mate — Option B (DECIDED)
- Map a mate eval to its **±1000 cp-equivalent ES** (≈ 0.998 / 0.002) and run the normal drop thresholds. **Do NOT reuse `eval_mate_to_expected_score`'s hard 1.0/0.0 in drop math** (built for endgame averaging; mis-sizes mate transitions).
- Accepted divergence: lila routes cp↔mate transitions through a separate `MateAdvice` ladder; Option B under-flags those. Documented, fine for v1. (Ladder spec in the research note if ever upgrading to Option A.)

### Eight attribution tags (orthogonal, additive — never change the severity label)
- `miss` *(eval-only)* — an error whose **immediately-preceding opponent move** was itself a Mistake/Blunder (requires classifying opponent moves too). Adjacency tag, NOT an ES-increase rule.
- `unpunished` *(eval-only)* — the user's blunder whose **immediately-following opponent move** failed to recover the eval (the mirror of `miss`; distinct user-facing signal).
- `from-winning` *(eval-only)* — `ES_before ≥ 0.85` (`FROM_WINNING_ES`).
- `result-changing` *(eval + game result)* — the error flipped the actual outcome (winning→drawn/lost, drawn→lost).
- `time-pressure` *(eval + clocks)* — error on a low clock (forced rush).
- `hasty` *(eval + clocks)* — fast move on a **comfortable** clock (unforced rush).
- `knowledge-gap` *(eval + clocks)* — error after **adequate/long** time (not fast).
- `phase` *(stored `phase` column)* — opening / middlegame / endgame.
- **Tempo dimension:** every flaw carries **exactly one** of {`time-pressure`, `hasty`, `knowledge-gap`}, derived from (move-time, clock-state).

### On-the-fly, not materialized
- Derive severity + all tags **per request** from stored per-ply evals (+ clocks, `phase`, `material_imbalance`, result, colors). **No new columns / table / migration / reimport.**
- Performance accepted as "not great" for v1 (cost is the later aggregate pass, not a single game). **Design the service interface so materialization is a drop-in later optimization** (same contract; cache/persist once the ruleset freezes).

### Output contract
- Each flaw = a typed structured object: **ply, FEN, side, severity, tags, eval before/after** (the shape Games/Flaws/Analysis/Train consume). Use a TypedDict/dataclass per project ty rules.

### Coverage / "analyzed"
- A game is "analyzed" iff **≥ 90% of its per-ply positions have `eval_cp`/`eval_mate`** (bimodal-gap coverage-ratio method, `reports/benchmark/benchmark-eval-coverage-2026-05-25.md`). chess.com / unanalyzed-lichess → explicit "no engine analysis" result, never a false zero-flaw game.

### Claude's Discretion
- Service location/naming (e.g. `app/services/mistakes_service.py`), exact TypedDict/dataclass field names, whether per-ply derivation is Python-side or a SQL `LAG` window (benchmark later; correctness first), test-fixture construction, an optional dev-only validation script comparing derived counts to the game-level columns.
- **Initial tempo thresholds** (the one genuinely open value): pick documented defaults for "fast move" / "low clock", with the absolute-vs-relative-to-base-clock question resolved pragmatically (lean relative-to-base-clock); on-the-fly makes retuning free.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (researcher, planner, executor) MUST read these before planning or implementing.**

### Design contract (read first)
- `.planning/seeds/SEED-036-library-page-milestone.md` — full design: the "Mistake classification ruleset — RESOLVED" section, the 8-tag set + at-a-glance table, the on-the-fly/test-oracle decision, and the 2026-06-05 decision log entries. **This is the authoritative spec for this phase.**
- `.planning/notes/lichess-judgment-source.md` — lila/scalachess source facts: the `winningChances` [−1,1] scale, the halving, the `MateAdvice` ladder, the criticism→tag mapping.

### Code to reuse / respect
- `app/services/eval_utils.py` — `eval_cp_to_expected_score` (Lichess sigmoid, `LICHESS_K`) and `eval_mate_to_expected_score`. Reuse the cp converter; do NOT reuse the hard-1.0/0.0 mate converter for drop math (see Mate decision).
- `app/models/game_position.py` — per-ply `eval_cp` / `eval_mate`, `material_imbalance`, `phase`, clocks, ply ordering, Zobrist hashes. The data the service reads.
- `app/models/game.py` — game-level `white_/black_blunders/mistakes/inaccuracies` (the **test oracle**, ~lines 115–120), `white_/black_acpl`, result + `user_color`, `evals_completed_at`.
- `app/repositories/query_utils.py` — `apply_game_filters()` (single source of game filtering; the later filter phase integrates here — this phase reads positions for a game, not the filter).
- `app/services/endgame_service.py` — span-level ES-gap precedent; reference for the new per-ply LAG-over-plies derivation.
</canonical_refs>

<specifics>
## Specific Ideas
- `miss` / `unpunished` require classifying **both** players' moves (per-mover ES drops), then checking ply adjacency — not just the user's moves.
- Move-time per ply = previous-same-side clock − current clock + increment (derive increment from the time control). First moves / book moves can have noisy times — handle gracefully.
- `result-changing`: the flaw is the move that crossed a result boundary given the game's actual result; define against ES bands + final result.
- Sanity-check test: derived per-game B/M/I counts vs `games.white_/black_*` columns should be **close, not identical** (our halved-but-equivalent thresholds vs Lichess's; plus our mate handling differs). Assert closeness, not equality.
- Security: this phase adds **no external input surface** (no endpoint, reads existing owned data) — the threat-modeled surface is the *later* best-move endpoint, not this. The PLAN threat_model block should state this and stay minimal.
</specifics>

<deferred>
## Deferred Ideas (NOT this phase)
- Mistake-type **filter** integration into `apply_game_filters()` (count-level on Games, full severity×tag on Flaws).
- Games subtab UI (cards, B/M/I badges, curated tag chips, color-by-family), mistake-stats panel (+ analyzed-%), Flaws subtab, Analysis detail route, best-move endpoint.
- **Materialization** / caching of classifications.
- Final tempo-threshold calibration (absolute vs relative-to-base-clock) against real data — this phase ships documented defaults.
- Option-A exact `MateAdvice` ladder.
</deferred>

---

*Phase: 105-mistake-detection-classification-tagging-service-on-the-fly*
*Context distilled 2026-06-05 from the SEED-036 explore session (no separate discuss-phase).*
