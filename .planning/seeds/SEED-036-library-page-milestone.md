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

**Decision (user, 2026-06-03):** S1 — two new top-level pages, **Library** and **Train**, and the existing thin **Overview** page is folded into Library as a subtab. (Train ships in SEED-037, after this milestone; this milestone adds the Library entry and folds in Overview.)

**Amendment (user, 2026-06-04 — `/gsd-explore`):** **Import folds into Library as a subtab too**, dropping top-level nav to **4** (+Admin): `Library · Openings · Endgames · Train · (Admin)`. This keeps the mobile bottom-nav comfortable even after Train ships (5 was the crowding concern). Library's subtabs become **`Import · Games · Analysis · Overview`**, and the name is reinforced: a library is a collection you stock (Import) then browse. **The page-structure decision below reflects this amendment; the original 2026-06-03 S1 nav (`Import · Library · …`) is superseded.**

**Amendment (user + Claude, 2026-06-05 — `/gsd-explore`):** **Subtab bar becomes `Import · Games · Flaws · Overview` (4 chips); a new **Flaws** subtab is added and **Analysis** is removed from the subtab bar, becoming a deep-link detail route.** The three browse/analysis surfaces are distinguished by **unit of analysis**, which is what keeps them from collapsing into each other (the "do we even need both?" worry that motivated this session):

- **Games** — row = a *game*. A whole-archive game **browser**. Explicitly **no chessboard and no opening filter** — a position/opening filter is the Openings page's job; adding it here would re-create the Openings → Games surface and erase the distinction. Cards mirror the Openings game card plus per-game mistake counts and an **optional mini eval-progression sparkline** (analyzed games only). Filters = the existing metadata filters (color, TC, recency, opponent, rated) **+ mistake-count thresholds** (min blunders / mistakes / misses / missed-wins). The above-list panel is the **mistake-stats panel** (the milestone centerpiece), **NOT** a copy of Overview's Results-by-TC / Results-by-Color charts — those stay in Overview so two surfaces don't drift out of sync; a cheap WDL bar is fine.
- **Flaws** — row = a *single flawed position* (one game yields several rows). Each row is a **miniboard with the marked move** (reuse the Openings Insights miniboard) + severity/category. A mistake **browser**, and the natural feeder for SEED-037 (FlawFix).
- **Analysis** — the full-width single-game **workspace** (board + stepper + move list + eval bar + "show better move"). It is a **detail view, not a browse peer**: it only means anything once a game is loaded, so it is **not a subtab chip**. It lives at `/library/analysis/{game_id}?ply={N}`, reached only by deep-link from a Games card ("Analyze") or a Flaws miniboard, with "Back to Games" / "Back to Flaws" preserving filter state. May promote to a **top-level tab** later (cheap — a nav entry + route move); deferred, not decided now.

**Naming — "Flaws" as the umbrella term (DECIDED).** "Flaws" is the **surface / category name** for the five severities (inaccuracy / mistake / blunder / miss / missed-win). It's the only candidate that both ties to the brand (FlawChess → Flaws → FlawFix) **and** doesn't collide with a member tier — "Mistakes" fails because *mistake* is itself one of the tiers. **Usage rule:** "Flaws" names the surface/category only; per-move labels and counts use the precise terms (**"1 blunder · 2 mistakes," never "3 flaws"**), because *flaw* reads as a persistent trait, not a discrete move-event. The earlier "rename Analysis → Flaws" idea **dissolves** — both names are kept for two distinct surfaces (Flaws = mistake list, Analysis = board workspace).

**Scope note:** this **supersedes the `Import · Games · Analysis · Overview` subtab list and the "Analysis subtab" framing below** where they conflict. Phase 104 (in progress) migrates only Import + Overview and is unaffected; the Games / Flaws / Analysis split lands in the later phases (seed phase-decomposition items 4–6, now needing a Flaws surface + an Analysis detail route rather than an Analysis subtab).

- **Library** — whole-game / cross-game analysis hub, and the **one always-accessible page** (it contains Import, so it can never be import-gated). Subtabs (reuse the existing Radix URL-routed tab pattern — `<Tabs variant="brand">`, `navigate('/library/<tab>')`, deep-linkable — from Openings/Endgames), in order:
  - **Import** — the existing `/import` page moved in as the **leftmost** subtab and the **zero-game landing** (Home's gameless-user redirect now targets `/library/import`). Always accessible. Migrate `/import` → `/library/import`, keep a redirect from `/import`.
  - **Games** — filterable archive + mistake-type filters + mistake-stats panel. The milestone's headline surface and the **returning-user default** (a user with games lands here, not on Overview). Import-gated at the subtab level.
  - **Analysis** — full-width board, entered from a game card or a specific mistake. Import-gated at the subtab level. (The original seed's worry that "Analysis" overpromises engine analysis is moot — it genuinely does engine analysis now: eval bar + on-demand best move.)
  - **Overview** — the existing `/overview` page (`frontend/src/pages/GlobalStats.tsx`: per-platform/TC ELO timelines, WDL by TC and color) **moved in** as the **last** subtab, repositioned as a supplementary all-games dashboard (no longer the default/top-of-funnel). Always accessible. Migrate `/overview` → `/library/overview`, keep a redirect from `/overview`.
  - Funnel: **Import (stock the library) → Games (filtered subset + mistakes) → Analysis (one game/mistake) → Overview (all-games dashboard, supplementary).**

**Gating / landing consequences (planner must handle):**
- **Gating moves from route-level to subtab-level.** Library itself is never import-gated; its **Games** and **Analysis** subtabs sit behind the import-required guard, while **Import** and **Overview** are always open. Openings/Endgames/Train stay route-gated exactly as today.
- **Default subtab is state-dependent**, so default ≠ leftmost for returning users: zero games → **Import**, has games → **Games**. The existing conditional-redirect logic in `Home.tsx` extends to cover this.
- The **`totalGames === 0` notification dot** moves from the Import nav item to the **Library** nav item.
- **Redirects:** `/import` → `/library/import` and `/overview` → `/library/overview`, to preserve bookmarks and onboarding links.

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

### Mistake classification ruleset — RESOLVED (2026-06-05, closes Q-CLASS thresholds)

Verified against `lila` source (see `.planning/notes/lichess-judgment-source.md`). **Severity (inaccuracy/mistake/blunder) is Lichess-identical; `from-winning` and `miss` are orthogonal FlawChess tags that never alter the Lichess label.** This supersedes the draft thresholds and the "Missed Tactic" / "missed-punishment" framing.

**Scale correction (critical, the load-bearing finding).** Lichess judges on its `winningChances` scale, which is **[−1, +1]**, with cutoffs 0.10 / 0.20 / 0.30. Our `eval_cp_to_expected_score` returns **[0, 1]** = `(winningChances + 1) / 2`, i.e. **half that scale**, so Lichess's thresholds **halve** on our ES scale. An early draft used 0.10/0.20/0.30 directly on the ES scale — that was **2× too lenient** (a "blunder" would have needed ~330 cp near equality vs Lichess's ~165 cp).

**Constants (our [0,1] ES scale, mover POV):**
```python
INACCURACY_DROP = 0.05    # = Lichess 0.10 on [-1,1], halved
MISTAKE_DROP    = 0.10     # = Lichess 0.20
BLUNDER_DROP    = 0.15     # = Lichess 0.30
FROM_WINNING_ES = 0.85     # FlawChess tag threshold (~+470 cp), NOT a Lichess concept
```

**Severity** (per move, from the *mover's* POV — so opponent moves are classified too, which the `miss` tag needs):
- `drop = ES_before − ES_after` (side-to-move signed, matching lila's `info.color.fold(-d, d)`).
- Blunder if `drop ≥ 0.15`; Mistake if `drop ≥ 0.10`; Inaccuracy if `drop ≥ 0.05`; else none. Highest band wins.
- **Pure drop, NO position guard** — Lichess applies no absolute-strength guard. The draft's `ES_before < 0.85` gate is **dropped** (it was itself a divergence from Lichess and caused a discontinuity at 0.85); **no losing-side floor** is added either (the sigmoid's saturation already suppresses decided-position noise).

**Tags** (orthogonal, additive — never change the severity label):
- **`from-winning`**: `ES_before ≥ 0.85`. The draft's separate "Missed Win" / "Blunder (from winning)" classes **collapse** into `<severity> + from-winning`.
- **`miss`**: the move is a severity-flagged error AND the opponent's *immediately preceding* move was itself a Mistake or Blunder (eval spike, then the player gives it back on the very next ply). Renamed from "Missed Tactic"; it is an **adjacency tag on an existing error, not its own detection rule**. The draft's ES-must-*increase* rule was conceptually broken: a stored eval already prices in best play, so the punishment shows up as a jump on the *opponent's* move, not as a rise on the player's — the player capitalizes by *maintaining* ES, not growing it, and "failed to capitalize" is just a normal drop that happens to follow an opponent error.

**Extended attribution tags (added 2026-06-05, from a review of chess.com/lichess classification criticisms — see research note).** All orthogonal, all additive (none change the severity label), all in the cheap data quadrant (eval-only, eval+clocks, eval+result, or a stored column).

**Full tag set at a glance** (8 tags; D = differentiated vs chess.com/lichess, TS = table-stakes):

| Tag | Data dep | D/TS | What it tells the user |
|-----|----------|------|------------------------|
| `miss` | eval-only | TS | failed to punish the opponent's error on the next ply |
| `unpunished` | eval-only | D | your blunder the opponent let slide ("got away with it") |
| `from-winning` | eval-only | D | bled a clearly-won position (`ES_before ≥ 0.85`) |
| `result-changing` | eval + result | D | this error actually flipped the game outcome |
| `time-pressure` | eval + clocks | D | forced rush — low clock; clock-management problem |
| `hasty` | eval + clocks | D | unforced rush — fast move on a comfortable clock; discipline |
| `knowledge-gap` | eval + clocks | D | took adequate time, still wrong; the one to study (FlawFix) |
| `phase` | stored column | TS | opening / middlegame / endgame |

`time-pressure` / `hasty` / `knowledge-gap` are a **mutually-exclusive tempo dimension** (at most one per error). `miss` + `from-winning` were adopted in the ruleset above; the rest are detailed below.

- **`time-pressure`** *(eval + clocks)* — error played on a low clock (forced rush). Diagnosis: clock-management problem.
- **`hasty`** *(eval + clocks)* — "unforced rush": a fast move played with a *comfortable* clock. Diagnosis: discipline, not time.
- **`knowledge-gap`** *(eval + clocks)* — the residual tempo state: an error made *after spending adequate/long time* (not fast). Diagnosis: genuine understanding/calculation gap — more time wouldn't have helped, so it is the highest-value error to study and the one **FlawFix (SEED-037) should prioritize**. (Chosen over "blind spot," which is reserved for the pattern-level recurring-theme feature below — a *single* slow-but-wrong move isn't a blind spot; a *repeated* one is.)
  - These three form a **tempo dimension**: every error carries *at most one* of {`time-pressure`, `hasty`, `knowledge-gap`}, derived from (move-time, clock-state). `hasty` vs `time-pressure` split on clock comfort; `knowledge-gap` is the not-fast case.
- **`unpunished`** *(eval-only)* — your blunder whose *immediately following* opponent move failed to recover the eval (you "got away with it"). The mirror of `miss` (your `unpunished` = the opponent had a `miss`), but a distinct *user-facing* filter since the user only sees their own moves. Surfaces blunders never learned from because the scoreboard didn't punish them.
- **`result-changing`** *(eval + game result)* — the error flipped the actual game outcome (winning→drawn/lost, drawn→lost). Ties a flaw to its real consequence; also the principled catch for the already-decided blind spot below.
- **`phase`** *(stored `phase` column, ~free)* — opening / middlegame / endgame; enables "you blunder most in the endgame" at the stats layer.

**Already-decided blind spot — accepted, with a catch.** Pure-drop + sigmoid saturation inherits lichess's most-cited substantive gap: in a very won position (ES ≳ 0.97) you can shed large material with a sub-threshold win% move and it won't flag. Accepted for v1 because such cases rarely change the result, and `result-changing` catches the ones that do. **Rejected alternative:** a material-swing overlay tag (flag "lost ≥X material, no compensation" from the stored `material_imbalance`, independent of eval drop) — cheap and would visibly beat lichess here, but deferred as low-value/noisy for v1. Revisit if real data shows meaningful missed flags.

**Recurring-theme insights — forward pointer, NOT a per-move tag.** The most-cited coach gap ("you keep doing X") is a *cross-game aggregate*, and naming the theme needs motif detection. It belongs at the **mistake-stats / insights layer** (overlaps SEED-037 Train), not the per-move classifier. Logged so it isn't lost; out of scope for the classification tags.

**Explicitly skipped:** `only-move`/forced (needs the 2nd-best eval we don't store → an engine call, not eval-only; defer to on-demand enrichment) and a "Brilliant"-style positive label (expensive, off-brand — FlawChess flags flaws, not confetti — and the single most-mocked chess.com feature; skip, likely permanently).

**OPEN — time-threshold calibration (TBD).** The `time-pressure` / `hasty` / `knowledge-gap` split needs concrete move-time and clock thresholds, and a decision on whether "fast" / "low clock" are **absolute** or **relative to the base clock / time control** (a 5 s move is fast in classical, normal in bullet). Same calibration bucket as the drop thresholds — tune against real data, do not hard-code in this seed.

**Mate handling — Option B (DECIDED), divergence noted:**
- Map a mate eval to its **±1000 cp-equivalent ES** (≈ 0.998 / 0.002) and run the normal drop thresholds. **Do NOT reuse `eval_mate_to_expected_score`'s hard 1.0/0.0 in drop math** — that converter was built for the endgame expected-score-averaging path; hard 1.0/0.0 mis-sizes mate-transition swings.
- **Known divergence from Lichess:** Lichess routes cp↔mate *transitions* through a separate `MateAdvice` ladder keyed on the non-mate cp endpoint (±999 / ±700), so it still flags e.g. "walked into mate from an already-lost position" as an Inaccuracy. Option B's plain sigmoid **under-flags** these (mate≈0.998 vs +1500 cp≈0.996 ⇒ ~0 drop ⇒ no flag). Accepted as a v1 simplification — mate transitions are rare. The full `MateAdvice` ladder is documented in the research note for a possible later Option-A upgrade. Revisit only if mate-edge gaps surface in real data.

**`eval_utils.py` compatibility:** the cp sigmoid `1/(1+exp(-0.00368208·cp))` already matches Lichess's `winningChances` (rescaled), and Lichess does **not** clamp cp in its judgment path, so our un-clamped function is correct as-is for cp judgments. Only mate needs the ±1000 cp mapping above (don't reuse the hard-1.0/0.0 converter for drops).

**Game-level rollup (filters):**
```python
my_inaccuracies = count(Inaccuracy)
my_mistakes     = count(Mistake)
my_blunders     = count(Blunder)          # includes from-winning blunders
my_misses       = count(miss-tagged errors)
# Every tag is also a filterable/aggregatable dimension, e.g.:
my_unpunished     = count(unpunished-tagged errors)
my_result_changing = count(result-changing errors)
errors_by_tempo   = {time-pressure, hasty, knowledge-gap} histogram   # tempo dimension
errors_by_phase   = {opening, middlegame, endgame} histogram
# from-winning stays an analytic sub-tag (exposable as a "squandered wins" filter later);
# tempo/phase power the stats-panel breakdowns. Not all become top-level filter toggles in v1.
```

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

- **Q-CLASS: RESOLVED (2026-06-05).** Thresholds, the two error kinds, and mate handling are all settled — see "Mistake classification ruleset" above and `.planning/notes/lichess-judgment-source.md`. Summary: severity = Lichess-identical on halved drop constants (0.05/0.10/0.15 on our [0,1] ES scale), pure-drop with no position guard, `from-winning` + `miss` as orthogonal tags, mate via Option B (±1000 cp mapping, divergence noted).
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
4. **Library page shell + subtabs (frontend).** New `/library` route with **`Import · Games · Flaws · Overview`** subtabs (reuse Radix URL-routed tab pattern; **Analysis is a deep-link detail route, not a chip** — see 2026-06-05 amendment). **Migrate two routes in:** `/import` → `/library/import` and `/overview` → `/library/overview` (move `Import.tsx` and `GlobalStats.tsx`, add redirects from both). Subtab-level import gating (Games/Analysis gated, Import/Overview always open); state-dependent default landing (zero games → Import, has games → Games); move the zero-game notification dot to the Library nav item. Games subtab: archive layout (existing filters + mistake-type control), game cards with mistake badges + "no analysis" state, mobile drawer.
5. **Flaws subtab + Analysis detail route.** Flaws = filterable miniboard list of flawed positions (reuse Openings Insights miniboard + marked move). Analysis = full-width detail route `/library/analysis/{game_id}?ply={N}` (board + stepper + move list + mistake markers + jump-to-mistake + material/eval timeline + eval bar + "show better move" wired to the best-move endpoint), deep-linked from Games cards and Flaws rows. (May split into two phases if large.)
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

**2026-06-05 extended attribution tag set (user + Claude, `/gsd-explore`, grounded in chess.com/lichess criticism research):**
- Added six attribution tags beyond severity, all in the cheap data quadrant: **`time-pressure`**, **`hasty`** (unforced rush), **`knowledge-gap`** (slow-and-still-wrong) — a mutually-exclusive **tempo dimension** — plus **`unpunished`** ("got away with it"), **`result-changing`** (flipped the game outcome), and **`phase`**. With the earlier `miss` + `from-winning`, the full set is eight tags.
- **Naming:** `hasty` for unforced rush (vs `time-pressure`); `knowledge-gap` for the slow-but-wrong residual ("blind spot" deliberately reserved for the pattern-level recurring-theme feature).
- **Already-decided blind spot accepted** (inherited from lichess's pure-drop sigmoid) — `result-changing` is the principled catch; a material-swing overlay tag was considered and **deferred** (low-value/noisy for v1).
- **Recurring-theme insights** = forward pointer to the stats/insights layer (overlaps SEED-037), NOT a per-move tag. **`only-move`** and a **"Brilliant"** positive label explicitly skipped (engine-call cost / off-brand / most-mocked feature).
- **OPEN:** time-threshold calibration for the tempo split (absolute vs relative-to-base-clock) — same tuning bucket as the drop thresholds, not hard-coded.

**2026-06-05 mistake classification ruleset — closes Q-CLASS thresholds (user + Claude, `/gsd-explore`, lila source-verified):**
- **Severity = Lichess-identical**, but thresholds **halve** on our scale: Lichess judges on `winningChances` [−1,+1] (cutoffs 0.10/0.20/0.30); our `eval_cp_to_expected_score` returns [0,1] = `(wc+1)/2`, so our drop constants are **0.05 (inaccuracy) / 0.10 (mistake) / 0.15 (blunder)**. An early draft's 0.10/0.20/0.30-on-ES was 2× too lenient.
- **Pure drop, no position guard** (matches lila `CpAdvice`): drop the draft's `ES_before < 0.85` gate and add no losing-side floor; the sigmoid's saturation is the only suppression. Removes the 0.85 discontinuity.
- **`from-winning` tag** (`ES_before ≥ 0.85`) replaces the "Missed Win" / "Blunder-from-winning" classes — severity + tag, not a parallel ladder.
- **`miss` tag** = an error whose immediately-preceding opponent move was a Mistake/Blunder (adjacency tag, renamed from "Missed Tactic"). The draft's ES-must-increase rule was conceptually broken (stored eval already prices in best play; capitalizing = maintaining ES, not raising it). Detectable from stored evals alone, no `ES_best`/engine needed → keeps the seed's "no engine at detection time" architecture.
- **Mate = Option B** (DECIDED): map mate → ±1000 cp-equivalent ES, run normal thresholds; do NOT reuse `eval_mate_to_expected_score`'s hard 1.0/0.0 in drop math. Diverges from Lichess's separate `MateAdvice` ladder (under-flags mate transitions from decided positions) — accepted v1 simplification, ladder documented for a later Option-A upgrade.
- **`eval_utils.py`**: cp sigmoid already matches Lichess and needs no clamp for judgment; only mate needs the ±1000 cp mapping.
- Source facts captured in `.planning/notes/lichess-judgment-source.md` (lila `Advice.scala`, scalachess `eval.scala`).

**2026-06-05 Games/Flaws/Analysis split + Flaws naming (user + Claude, `/gsd-explore`):**
- **Subtab bar → `Import · Games · Flaws · Overview` (4 chips).** New **Flaws** subtab added; **Analysis** removed from the bar.
- **Three surfaces distinguished by unit of analysis:** Games (row = game; whole-archive browser), Flaws (row = single flawed position; miniboard list), Analysis (single-game board workspace).
- **Games subtab:** no chessboard / no opening filter (that's Openings' job — adding it would duplicate Openings → Games). Cards = Openings game card + per-game mistake counts + optional mini eval sparkline. Filters = metadata + mistake-count thresholds. Above-list panel = mistake-stats panel only; Results-by-TC / Results-by-Color stay in Overview (no duplication).
- **Analysis = deep-link detail route** `/library/analysis/{game_id}?ply={N}`, not a subtab chip (it's a detail/workspace view, not a browse peer). Reached from a Games card or a Flaws miniboard; "Back to Games" / "Back to Flaws" preserves filter state. Possible future promotion to a top-level tab — deferred.
- **"Flaws" = umbrella/surface term** for inaccuracy/mistake/blunder/miss/missed-win. Chosen because it's brand-aligned (FlawChess → Flaws → FlawFix) and doesn't collide with a member tier (unlike "Mistakes"). Usage rule: surface/category name only; per-move counts use precise terms ("1 blunder · 2 mistakes," never "3 flaws"). The "rename Analysis → Flaws" idea dissolved — both names kept for two distinct surfaces.
- **Open for next session:** the severity categorization rules (inaccuracy/mistake/blunder/miss/missed-win thresholds + the "miss / missed-win" definitions) — user has researched a specific ruleset; ties into Q-CLASS.

**2026-06-04 nav refinement (user + Claude, `/gsd-explore`):**
- **Import folds into Library as a subtab**, dropping top-level nav to **4** (+Admin): `Library · Openings · Endgames · Train · (Admin)`. Motivation: keep the mobile bottom-nav comfortable after Train ships (5 was the crowding concern).
- Library subtab order set to **`Import · Games · Analysis · Overview`**. Import leftmost; **Overview demoted to last** as a supplementary dashboard (no longer the default/top-of-funnel).
- **State-dependent landing:** zero-game user → Import subtab; returning user → **Games** subtab (the milestone's headline surface), confirmed acceptable by user.
- **Gating moves to subtab level:** Library always accessible (hosts Import); Games/Analysis import-gated; Import/Overview always open. Zero-game notification dot moves to the Library nav item. Redirects: `/import` → `/library/import`, `/overview` → `/library/overview`.
- Supersedes the 2026-06-03 S1 nav (`Import · Library · …`).

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
