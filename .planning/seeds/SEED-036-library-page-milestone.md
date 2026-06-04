---
id: SEED-036
status: dormant
planted: 2026-06-04
planted_during: 2026-06-04 split of SEED-010 into Library (this seed) + Train (SEED-037)
lineage: split from SEED-010 (planted 2026-05-01, reworked 2026-06-03); SEED-010 closed
trigger_when: ready to start the next milestone, OR when user invokes `/gsd-new-milestone` for the Library page
scope: milestone (multi-phase)
---

# SEED-036: Library — eval-driven mistake archive + per-mistake analysis

> **Lineage.** Split out of SEED-010 (now closed) on 2026-06-04. SEED-010 covered both the whole-game analysis page and the spaced-repetition trainer; those are now two seeds. This seed owns the **Library page**; the trainer is **SEED-037 (Train)**. The page name reverted **Review → Library** in the same split (all live tracking docs already say "SEED-010 Library"; "Review" was a short-lived 2026-06-03 working name and is dropped).

> **2026-06-03 origin rework (carried over from SEED-010).** The original v1 centered on a **material-delta filter** as the headline new game-level filter, with tactical/eval filters explicitly deferred behind eval coverage. That framing is **obsolete**: FlawChess now stores per-ply Stockfish evals for analyzed Lichess games, so eval-driven **mistake/blunder filters** are feasible today and become the headline. The material-delta filter is **dropped** (it was a pre-eval proxy). The data layer is kept training-aware so SEED-037 (Train) can consume the same mistake-detection layer. The original decision log is preserved at the bottom for provenance.

## Why This Matters

FlawChess slices data by **position** (Openings) and by **type** (Endgames). There is no surface that operates on **whole games**, and nothing surfaces a player's **mistakes** — where in a game they went wrong, how often, of what severity. Users have to click out to lichess to find and step through a blunder.

We now have the data to close this: `game_positions.eval_cp` / `eval_mate` are stored **per-ply for every analyzed Lichess game** (parsed from the `%eval` annotations Lichess returns with `evals=true`). From that we can derive, server-side, exactly which plies were inaccuracies / mistakes / blunders, aggregate them across a filtered set of games, and deep-link each one to a board.

The Library page introduces:

1. A **mistake-type filter dimension** over the game archive ("show my bullet games from the last 90 days that contain a blunder"), derived on-the-fly from stored per-ply evals.
2. A **mistake-stats panel** above the filtered list: how often each mistake type occurs across the selection, normalized so it's comparable, with a trend over time.
3. A **per-game / per-mistake viewer** (board, stepper, move list, eval bar/timeline) that jumps straight to a mistake ply and can show the better move via an **on-demand server-side best-move endpoint**.

This is also the data foundation for **SEED-037 (Train)**: the same mistake-detection layer feeds the spaced-repetition trainer, and Train's move-grading reuses this milestone's best-move endpoint.

## When to Surface

- User invokes `/gsd-new-milestone` and signals readiness to start the Library milestone.
- Do NOT surface mid-milestone. This is a large milestone (new page, new derived-filter, new stats endpoint, new viewer, new best-move endpoint).

## Page structure — DECIDED (S1 + Overview folded into Library)

**Decision (user, 2026-06-03):** S1 — two new top-level pages, **Library** and **Train**, and the existing thin **Overview** page is folded into Library as a subtab. Final top-level nav: `Import · Library · Openings · Endgames · Train · (Admin)`. Net change is one new top-level entry (Train); Overview demotes to a subtab, so nav crowding is contained. (Train ships in SEED-037, after this milestone; this milestone adds the Library entry and folds in Overview.)

- **Library** — whole-game / cross-game analysis hub. Subtabs (reuse the existing Radix URL-routed tab pattern — `<Tabs variant="brand">`, `navigate('/library/<tab>')`, deep-linkable — from Openings/Endgames):
  - **Overview** — the existing `/overview` page (`frontend/src/pages/GlobalStats.tsx`: per-platform/TC ELO timelines, WDL by TC and color) **moved in** as the default Library subtab. All-games-scoped and thin, so it's the natural top of the funnel. Migrate `/overview` → `/library` (default tab) or `/library/overview`; keep a redirect from `/overview`.
  - **Games** — filterable archive + mistake-type filters + mistake-stats panel.
  - **Analysis** — full-width board, entered from a game card or a specific mistake. (The original seed's worry that "Analysis" overpromises engine analysis is moot — it genuinely does engine analysis now: eval bar + on-demand best move.)
  - Funnel: **Overview (all games) → Games (filtered subset + mistakes) → Analysis (one game/mistake).**

Notes:
- **Time Management** is NOT a top-level page — it lives in the Endgames Stats tab (+ homepage blurb). Unaffected by this restructure.
- Page name **"Library"** is the decided name (reverted from the short-lived "Review"). Alternatives weighed and rejected during exploration: "Mistakes" (too narrow for Overview + plain archive), "Games" (collides with the Games subtab inside Openings/Endgames), "Archive" (undersells analysis), "Analysis" (overloads the chess.com/lichess "engine analysis" connotation, and collides with the Library Analysis subtab).
- Open detail for discuss-phase: is Library (landing on Overview) the post-import app landing? Probably yes — confirm.

## v1 Scope (eval-driven, Lichess-analyzed games only)

### Coverage reality — read this first

Every mistake filter and mistake stat is a **subset** of the user's library:
- **chess.com**: no per-move eval from their API (only game-level accuracy). Excluded from mistake features in v1.
- **lichess, unanalyzed**: per-ply `eval_cp` is NULL. Excluded.
- **lichess, analyzed**: full per-ply eval present. **This is the only in-scope set for mistake features.**

Consequences the planner MUST handle:
- The Games subtab needs a clear, first-class **"this game has no engine analysis"** state — never imply a clean game when we simply lack evals.
- The mistake-stats panel must be explicit about the denominator (computed over analyzed games only, N shown).
- **Measure real coverage on prod before planning** (fraction of Lichess games with full per-ply eval; fraction of all games). This number decides whether v1 feels rich or sparse and whether chess.com coverage-expansion (Deferred) needs to be pulled forward. See Q-COV below.

### Games subtab — filterable archive

Reuses every existing game filter via `app/repositories/query_utils.py::apply_game_filters()` (time control, platform, rated, opponent type, recency, color). Adds the new mistake-type filter.

Each row is a **game card** showing existing summary fields plus:
- Mistake badges (e.g. counts of inaccuracy / mistake / blunder for the user in that game).
- Existing out-link to lichess.
- "Analyze" link → Analysis subtab with the game loaded, ideally landing on the first mistake.

**List defaults:** date played descending; pagination matching the existing Openings → Games subtab pattern; no user-controllable sort in v1.

### New filter: Mistake type (derived, not precomputed-column)

Filter the archive to games containing at least one mistake of a selected severity, derived **on-the-fly from stored per-ply `eval_cp` / `eval_mate`**. No new import, no new column at the `games` level (mirrors the original seed's "filter on-the-fly" decision; benchmark before adding any index — an index on `game_positions(game_id, ply)` already exists / may suffice; confirm).

**The eval→expected-score mapping is ALREADY SOLVED — do not rebuild it.** `app/services/eval_utils.py::eval_cp_to_expected_score(eval_cp, user_color)` / `eval_mate_to_expected_score(...)` implement the Lichess sigmoid (`LICHESS_K = 0.00368208`), return [0,1] user-POV, and are already reused across endgame stats. Mistake severity is a **drop in this expected score between consecutive plies** for the side to move. There is no per-ply win%-drop derivation today (only span-level gaps in `endgame_service.py`); that LAG-over-plies derivation is the new work.

**What still needs RESEARCH (Q-CLASS), do not hard-code in this seed:** the *classification layer* on top of the (solved) expected-score drop —
- The **thresholds** that bucket an expected-score drop into inaccuracy / mistake / blunder (Lichess's own cutoffs are a reference, but confirm; expected-score drops behave better than raw cp in already-decided positions, which is exactly why we use the sigmoid).
- Distinguish **two kinds of error** (user request):
  - **Player mistakes** — the user's own move dropped their win%.
  - **Opponent misses ("missed punishment")** — the opponent's move *handed* the user a swing, and the user's *reply* failed to capitalize (didn't play a clearly-best converting move). This is a distinct, valuable signal and a harder definition.
- The filter UI should let the user pick severity (inaccuracy / mistake / blunder) and likely the kind (my-mistakes vs missed-punishment), pending the research outcome.

### Detection + best-move architecture

- **Detection**: pure derivation over existing `eval_cp` per ply. Server-side query/service, no engine at detection time. Lives near `query_utils.py` / a new mistakes service.
- **Best move on demand**: a **single-position server endpoint** (e.g. `POST /api/analysis/best-move` taking a FEN, returning best move + eval, maybe top-N PV). One position is fast on the existing Stockfish `EnginePool`. Used by the Analysis subtab's "show the better move" and **reused by SEED-037 (Train) for move grading**.
  - **This reintroduces server-side Stockfish — but bounded.** It is single-position, user-initiated, and categorically different from the full-game-at-import server-side SF that is **permanently off the table** (OOM history, CLAUDE.md 2026-03-22 / FLAWCHESS-3Q). The endpoint MUST be rate-limited / queued (and concurrency-capped against the existing pool) so it cannot regress into the same OOM failure mode. The planner should treat this as a threat-modeled surface.

### Mistake-stats panel (Games subtab)

Above the games list, over the filtered (analyzed-only) set:
- Counts and **rates per mistake type**, normalized (per game and/or per 100 moves) so selections of different sizes are comparable.
- **Trend over time** (mistake rate by month / recency window), the headline insight — "am I blundering less than I used to?"
- Analyzed-game count N, shown explicitly as the denominator.
- Keep WDL bar if cheap, but the mistake metrics are now the centerpiece (the original seed's "WDL-bar-only, no conversion%" stance is superseded).

### Analysis subtab — per-mistake viewer

Full page width. Hosts:
- Chessboard with click/keyboard navigation through plies. Read-only stepping; the **best-move endpoint** supplies "what was better here" on demand (this is the one place a user-driven engine call happens in v1).
- **Move list (SAN)** — numbered, current ply highlighted, click-to-jump. Primary navigation alongside arrow keys.
- **Mistake markers** on the move list / timeline; "jump to next mistake" affordance. Landing on a mistake is the primary entry from a game card.
- Player names + colors, per-ply clocks, **material-balance timeline** (from `material_imbalance`, always available), **Stockfish eval timeline + eval bar** (analyzed games only; hide cleanly otherwise).
- Phase markers (opening/middlegame/endgame) from the stored `phase` column.
- "Back to Games" preserving filter state.

### Material-delta filter — REMOVED

The original seed's headline filter (preset slider −3..+3, 4-ply sustainment, on-the-fly material-window query) is **cut**. It was a proxy for "failed conversion / successful recovery" built before per-ply evals existed; eval-driven mistake filters and the existing Endgame conversion/recovery stats cover the intent better. `material_imbalance` is still used for the material timeline in the viewer, just not as a filter.

### Mobile

Drawer pattern from Openings on the Games subtab. Analysis subtab stacks indicators below the board (planner confirms in UI design). Standard tab control for subtab switching.

## Open questions for milestone discuss-phase

- **Q-CLASS (research): mistake classification thresholds + kinds.** The eval→expected-score mapping is solved (`eval_utils.py`); research is only (a) the expected-score-drop thresholds for inaccuracy/mistake/blunder, and (b) the "opponent miss / missed punishment" definition. Do this BEFORE specifying the filter UI. This is the biggest unknown.
- **Q-COV (research/measurement): eval coverage.** What fraction of Lichess games (and of all games) have full per-ply eval on prod today? Drives how rich v1 feels and whether chess.com coverage-expansion is near-term.
- **Q-NAME: RESOLVED.** Page name is **Library** (reverted from "Review").
- **G-1: URL deep-linking.** `/library/analysis/{game_id}?ply={N}` + Games-subtab filter state in query params (Openings precedent). Recommended default; confirm.
- **G-2: drill-in wiring from existing pages.** Which stat surfaces link into Library and with what preset? Pick a small concrete subset (e.g. Endgame conversion/recovery bars → archive pre-filtered to relevant losses; Insights endpoints linking to specific mistake plies) and explicitly defer the rest rather than leaving drill-in aspirational.

## Research items (before/early in the milestone)

Mistake classification is the load-bearing research. References:
- **Lichess** win-probability model + judgment thresholds (the `lila` "WinPercent" / advice logic) — the canonical eval→win%→severity mapping.
- **lichess-puzzler** (https://github.com/ornicar/lichess-puzzler) — how Lichess turns eval swings into tactical positions; relevant to both mistake detection and (later, SEED-037) training-puzzle selection.
- **chess_detect** (https://github.com/aslyamov/chess_detect) — eval-swing-based mistake/tactic detection reference.

## Deferred extensions (separate seeds / later)

### Spaced-repetition blunder training → SEED-037 (Train)

Moved out into its own seed in the 2026-06-04 split. SEED-037 owns the trainer, FSRS scheduler, GM-coach collaboration, and the already-built `/train-sketch` prototype. **Data-layer awareness for THIS milestone:** keep the mistake-detection service cleanly reusable — return mistake plies with enough context (FEN, side, eval before/after) for the trainer to consume directly — and keep the best-move endpoint general. Because best move is computed on-demand (not stored), there is no reimport risk for the trainer.

### chess.com (and unanalyzed-lichess) eval coverage expansion

chess.com has no API evals, so chess.com games are excluded from mistake features in v1. Two candidate mechanisms to expand coverage later (needs its own discuss-phase):
- **Client-side Stockfish** in the browser analyzing the user's games and **POSTing evals back** to the server for storage (see SEED-012).
- **Selective server/external analysis** — e.g. analyze only recent games for users who actually engage with the training feature, on our box or an external service.
Both have cost/abuse/consistency trade-offs (and eval non-determinism across engines/machines — see the project's eval-nondeterminism note). Defer until the prod coverage measurement (Q-COV) shows it's needed.

### Tactical motif classification (missed forks / pins)

Classifying *which* motif a mistake involved (fork/pin/etc.) on top of the eval-swing signal. Higher noise, not needed to ship value. Eval-swing "you blundered here" is enough for v1 and for training. Revisit only with clear product demand. (See SEED-012.)

## Out of Scope — permanently

- **Full-game server-side Stockfish at import time.** Will not happen (CPU/memory, OOM history). The on-demand single-position best-move endpoint is the *only* sanctioned server-side engine use, and only because it's bounded.
- **Tactical filters using only geometric pattern detection (no eval).** Too noisy.

## Phase Decomposition (rough sketch — planner refines)

Likely 4-6 phases:

1. **Mistake-detection service + classification.** Derive per-ply mistakes from stored `eval_cp` using the researched win%-drop method; expose player-mistakes and opponent-misses; tests against benchmark/dev data. (Gated on Q-CLASS research.)
2. **Mistake-type filter (backend).** Extend the game-filtering path so the archive can filter to games containing mistakes of a given severity/kind. Benchmark the query; add an index only if needed.
3. **Best-move endpoint.** Single-position `POST /api/analysis/best-move` on the existing EnginePool, rate-limited/queued/concurrency-capped, threat-modeled. (Reused by SEED-037 Train.)
4. **Library page shell + subtabs (frontend).** New `/library` route with Overview/Games/Analysis subtabs (reuse Radix URL-routed tab pattern). **Migrate `/overview` → Library's Overview subtab** (move `GlobalStats.tsx`, add redirect). Games subtab: archive layout (existing filters + mistake-type control), game cards with mistake badges + "no analysis" state, mobile drawer.
5. **Analysis subtab — viewer.** Board + stepper + move list + mistake markers + jump-to-mistake + material/eval timeline + eval bar + "show better move" wired to the best-move endpoint.
6. **Mistake-stats panel.** Counts/rates per type, normalized, trend over time, analyzed-game denominator; wired to filter state.

(May merge 5+6 or split 4 if the layout is large.)

## Breadcrumbs

- `app/services/eval_utils.py` — `eval_cp_to_expected_score` / `eval_mate_to_expected_score` (Lichess sigmoid, `LICHESS_K`). The solved eval→expected-score mapping the mistake-severity drop is built on. Reuse, do not reinvent.
- `app/models/game_position.py` — per-ply `eval_cp` / `eval_mate` (Lichess `%eval` when analyzed), `material_imbalance` (signed, always present), `phase`, clocks, three Zobrist hashes. The data the mistake layer reads.
- `app/models/game.py` — game-level `white_acpl` / `black_acpl` and `white_blunders` etc. (imported from Lichess analysis). Cheap source for card badges / sanity-checking derived per-ply counts.
- `app/services/zobrist.py` (~lines 182–198) — where per-ply eval is extracted from the PGN at import. Confirms full-ply coverage for analyzed games.
- `app/services/normalization.py` (~lines 401–439) and `app/models/game.py` (~lines 111–120) — game-level Lichess judgment counts (`white_blunders` etc.). Useful for the card badges / sanity-checking derived counts, but per-ply judgment is NOT stored (we derive it).
- `app/repositories/query_utils.py::apply_game_filters()` — single source for game filtering; the mistake-type filter integrates here / in a sibling mistakes service.
- `app/services/lichess_client.py` (~lines 92–100) — the `evals=true` / `accuracy=true` request params.
- `app/services/eval_drain.py`, `scripts/backfill_eval.py` — server-side entry-ply eval backfill (NOT full-game). Context for why coverage is what it is; not the source for mistake detection.
- `frontend/src/components/Openings/` — board component, mobile drawer, filter sidebar, subtab control, Games-subtab pagination to reuse.
- `frontend/src/components/Endgames/` — stats-panel + WDL-bar layout reference.
- `frontend/src/hooks/useEvalCoverage.ts` — existing eval-coverage progress plumbing.

## Source / decision log

**2026-06-04 split (user + Claude):**
- SEED-010 split into **SEED-036 (Library, this seed)** + **SEED-037 (Train)**; SEED-010 closed with a pointer to both.
- Page name reverted **Review → Library**; Q-NAME resolved.
- Library milestone scope unchanged from the SEED-010 2026-06-03 rework, minus the trainer (now SEED-037).

**2026-06-03 rework session (user + Claude) — carried over from SEED-010:**
- **Material-delta filter dropped** — pre-eval proxy, superseded by eval-driven mistake filters.
- **Mistake filters are the headline**, derived on-the-fly from stored per-ply `eval_cp`; Lichess-analyzed games only in v1.
- **Best move = on-demand single-position server endpoint**, not client-side Stockfish and not stored-at-import. Bounded server-side SF, must be rate-limited.
- **Two mistake kinds**: player's own mistakes vs opponent misses the player failed to punish — flagged for research, not yet specified.
- **Mistake classification needs research first** (win%-drop method; references: Lichess win-model, lichess-puzzler, chess_detect).
- **chess.com eval coverage** expansion (client-side SF send-back, or selective server/external analysis for training users) deferred to its own thread.
- Server-side full-game SF at import stays permanently out of scope.
- **Eval→expected-score is already solved** (`eval_utils.py`, Lichess sigmoid). Q-CLASS narrowed to just the classification *thresholds* (expected-score-drop cutoffs) + the "opponent miss" definition. No per-ply win%-drop derivation exists yet — that's the new work.
- **Page structure DECIDED: S1.** Two new top-level pages **Library** + **Train**; existing **Overview** folded into Library as its default subtab (Library = Overview · Games · Analysis). Final nav `Import · Openings · Endgames · Library · Train`. Time Management stays inside Endgames.

---

**Original 2026-05-01 explore-session decision log (SUPERSEDED where it conflicts with the rework above; kept for provenance):**
- Page name "Library" chosen over "Analysis page"; entry from both stat drill-downs and standalone search; game cards link to platform AND internal viewer.
- Tactical filters split: material-based filters ship v1, tactical (motif) filters deferred. *(Reworked: material filter cut; eval-driven mistake filters now ship v1; motif classification still deferred.)*
- Material-delta filter shape: preset slider −3..+3, fixed 4-ply sustainment, phase-anywhere, user POV. *(Reworked: removed.)*
- Stats panel: WDL bar + count only; conversion%/recovery% rejected. *(Reworked: mistake counts/rates + trend are the centerpiece; WDL kept only if cheap.)*
- Data model: filter on-the-fly from `game_positions`, no precomputed columns. *(Retained — applies to mistake derivation too.)*
- Move list (SAN) as primary viewer navigation; date-desc list default; pagination matching Openings Games subtab; no game-level bookmarks in v1. *(Retained.)*
- Deep-linking (G-1) and drill-in wiring (G-2) left for discuss-phase. *(Retained.)*
