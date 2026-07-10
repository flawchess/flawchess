# Phase 155: React Hook + Anytime UI (Free Analysis) - Context

**Gathered:** 2026-07-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the real Phase 154 providers (`workerPool.ts` Stockfish pool + `maiaQueue.ts`
Maia policy worker) into a React-facing hook (`useFlawChessEngine`) and surface its
ranked **practical-play** lines on the free-analysis `/analysis` board via a new
`FlawChessEngineLines.tsx` display component. Lines appear immediately and refine live
as the search accumulates visits; each line shows its modal path (SAN) and an
objective-vs-practical score pair (DISPLAY-01..04).

**In scope:** the hook, the new card + eval-bar wiring on `/analysis`, live-refine
cadence, modal-path rendering, the score-pair badge, and the 3-card engine toggles.

**Out of scope (later phases):** board arrows + the high-contrast arrow color
(Phase 156, ARROW-01..04); game-review overlay integration (Phase 157, REVIEW-01..02).
The `SearchRunner`/`EngineProviders`/`SearchBudget`/`RankedLine`/`EngineSnapshot`
contract is frozen from Phase 153 and is NOT re-opened here.

</domain>

<decisions>
## Implementation Decisions

### Surface placement (DISPLAY-04)
- **D-01 New card, left column, above Maia:** A new `FlawChessEngineLines` card is
  stacked **above** the existing "Maia — Human Move Probability" card in the **left**
  column of `/analysis` (the same column the Maia card occupies today; see the current
  layout — Maia card left, board center, Stockfish card right). Not merged into the
  Stockfish card, not replacing it — the two engines stay visibly distinct so
  "practical vs objective disagreement reads as intentional." Apply to both desktop and
  the mobile takeover layout (mobile mirrors: the engine surface must be reachable there
  too, following the existing mobile tab / above-board conventions).

### Activation + toggles (DISPLAY-01)
- **D-02 On by default everywhere:** The FlawChess Engine runs by default on every
  position (desktop and mobile). The 2–4 SF pool + Maia queue lazy-spawn on first search
  (Phase 154 D-02). Accepted risk: this runs concurrently with the existing
  eval-bar / grading / Maia-chart workers before the SC4 real-device mobile-memory UAT.
  **SC4 (deferred from Phase 154) is the gate** — if mobile Safari can't hold it, a
  device-adaptive default (on desktop / off mobile) is the fallback, decided post-UAT.
- **D-03 Toggle switch in all 3 card headers:** Each engine card (Stockfish, Maia,
  FlawChess) gets its own on/off **toggle switch** in its header. The existing Stockfish
  header on/off control (`engineEnabled`, currently a header click) is upgraded to a
  proper switch for consistency. All three default ON.

### Eval bars — shared left slot, no third bar (POOL-04 / Phase 154 D-03)
- **D-04 Two board-flanking bars, left slot shared by precedence:** No third eval bar.
  - **Left slot** (today the Maia violet bar): shows **FC** (brown, label "FC") when the
    FlawChess Engine is enabled; falls back to **Maia** (violet, "Maia") when only Maia
    is on. FC takes precedence over Maia when both are enabled. The FC bar shows the
    engine's **practical-for-you** expected score (converted to a white-POV fraction).
  - **Right slot**: stays **Stockfish** (blue, "SF"). While the FlawChess Engine runs,
    the SF bar is fed the engine's **objective root eval** (`RankedLine.objectiveEvalCp`
    of the top line) — no separate standalone `useStockfishEngine` search on that
    position (this IS the Phase 154 D-03 handoff; because the engine is on by default,
    the handoff is effectively permanent while FC is on). Same scale/label ("SF").

### Branding / color (Phase 155 chrome only)
- **D-05 Brown accent + subtle gold headline, no card glow:** Add
  `FLAWCHESS_ENGINE_ACCENT` (brand **brown**) to `theme.ts`, alongside `STOCKFISH_ACCENT`
  (blue) and `MAIA_ACCENT` (violet). It tints the card frame + header caption + the "FC"
  eval-bar fill/cap, matching how the blue/violet accents tint their cards. A **subtle
  bronze/gold** highlight is reserved for the **headline practical score only** — NOT a
  card-wide glow (a glow fights the ~150ms live-refresh churn). Brown-on-charcoal reads
  fine on the card. **The high-contrast board-arrow color is a Phase 156 decision**
  (brown-on-brown-squares is not salient — likely a brighter gold/amber; the roadmap
  already reserves two new distinct arrow tokens for 156).

### Score-pair display (DISPLAY-02, DISPLAY-03)
- **D-06 Both numbers on the pawn scale, white POV:** Each line's badge shows the
  objective and practical scores **both on the pawn scale** (e.g. `+3.0` / `+0.9`),
  **both white-POV** (like the Stockfish eval bar — deliberately NOT side-to-move/"your"
  POV, which the user found confusing). The practical 0–1 expected score
  (`RankedLine.practicalScore`, root-STM) is converted to a white-POV pawn-equivalent via
  the inverse of the project's existing WDL/sigmoid util. Color-code the two numbers:
  **blue-tinted** objective, **brown/gold** practical.
  - *Copy nuance for planning:* since numbers are white-POV, the framing must not read
    "+0.9 for you" literally (that breaks when you're Black). "Practical for you" describes
    which engine models your likely play, not a POV flip. **Never** render "best move"
    unqualified (ARROW-04 principle starts here).
- **D-07 Modal path = SAN, ~5 plies + expand:** Each line renders its modal path
  (`RankedLine.modalPath`, UCI → SAN at the boundary) as clickable chips, showing the
  first ~5 plies with an expand chevron for the rest — mirroring the Stockfish
  `EngineLines` convention (`MAX_PLIES = 5`). The modal path maxes at 6–10 ply, so most
  lines show nearly fully. Walk the path from already-expanded tree nodes (may be short
  early in the search — that's expected, it deepens live).

### Anytime display (DISPLAY-01)
- **D-08 Top 3 lines:** The card shows the top **3** ranked practical lines (best +
  2 alternatives). More breadth than the Stockfish card's 2; Phase 156 arrows stay top-2.
- **D-09 Live-refine cadence:** Lines appear immediately from the first `onSnapshot` and
  reorder/update at a fixed batched cadence mirroring `RAPID_STEP_DEBOUNCE_MS` (150ms) —
  the same convention the existing engine hooks use — so updates neither jank nor flicker
  faster than a human can read. First-paint uses a fixed-height skeleton (reuse the
  `EngineLinesSkeleton` pattern) so the card height is stable as lines arrive.
- **D-10 Clickable graft-to-tree:** FlawChess Engine line move chips are clickable and
  graft the line as a sideline into the board tree — the exact same `onMoveClick(uciMoves)`
  interaction (+ hover miniboard preview) as the Stockfish `EngineLines` chips.

### Claude's Discretion (flag to researcher/planner)
- **Grading-worker binding under the 3-toggle split:** today a single `engineEnabled`
  gates BOTH `useStockfishEngine` (eval bar) AND `useStockfishGradingEngine` (which colors
  the Maia Moves-by-Rating chart). Splitting into 3 independent card toggles needs to
  decide what the grading worker binds to (likely the Maia card toggle, since it colors
  the Maia chart — but confirm). Researcher's call.
- **Maia card toggle vs the engine's internal Maia:** the Maia card toggle disables the
  Maia **chart** worker (`useMaiaEngine`). The engine's internal `maiaQueue` is a separate
  instance (Phase 154) and must keep running when FlawChess is on regardless of the Maia
  card toggle — turning off the Maia card must NOT starve the engine's policy.
- **The `useFlawChessEngine` hook shape:** trigger/debounce on position change, budget
  construction (`SearchBudget` — maxNodes/plies/concurrency/elo), abort-on-navigation
  (reuse the Phase 154 lifecycle/abort surface), and the "engine active" signal that
  drives the eval-bar handoff — all researcher/planner territory against the frozen
  `SearchRunner` contract.
- **ELO source for `budget.elo.{w,b}`:** reuse the existing `useMaiaEloDefault` /
  `selectedElo` plumbing already on the page (per-side ELO for the practical model).
- **Exact "FC"/"SF"/"Maia" bar cap labels and toggle persistence** (per-session vs
  persisted) — implementation detail.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frozen contract + upstream decisions (read first)
- `frontend/src/lib/engine/types.ts` — the FROZEN `EngineProviders` / `SearchBudget` /
  `RankedLine` / `EngineSnapshot` contract. `RankedLine` = `{rootMove(UCI),
  practicalScore(0–1 root-STM expected score), objectiveEvalCp(white-POV cp|null),
  modalPath(UCI[]), visits}`. Do NOT re-open.
- `frontend/src/lib/engine/guardrail.ts` — the frozen `SearchRunner` type + `onSnapshot`
  callback shape the hook drives.
- `.planning/phases/154-real-providers-stockfish-worker-pool-maia-queue/154-CONTEXT.md` —
  D-01..D-04 (adaptive pool sizing, lazy spawn, eval-bar mutual-exclusion obligation,
  Maia inference granularity). D-03 explicitly flagged the "engine active → pause eval
  bar" wiring to THIS phase (resolved here as D-04).
- `.planning/phases/153-pure-search-core-guardrail-backup-mcts-fallback/153-CONTEXT.md` —
  D-06 (practicalScore = root-STM expected score 0–1, never per-ply), D-07 (color-keyed
  ELO {w,b}), D-08 (UCI everywhere; convert to SAN only at the display boundary).
- `.planning/REQUIREMENTS.md` — DISPLAY-01..04 (this phase) + Out of Scope table (no bare
  "best move" framing; no dedicated Maia arrow layer).
- `.planning/ROADMAP.md` — Phase 155 goal + 4 success criteria; Phase 156/157 for
  awareness of what this phase must set up (arrow layer computed from `rankedLines`).

### Reusable implementation precedents
- `frontend/src/components/analysis/EngineLines.tsx` — the exact row pattern to mirror:
  eval badge (pill) + clickable SAN move chips (`onMoveClick(uciMoves)`) + hover MiniBoard
  preview + expand chevron (`MAX_PLIES = 5`), fixed-height `EngineLinesSkeleton`.
  `formatScore()` shows the pawn-scale convention (`+X.X`, `#±N` for mate).
- `frontend/src/pages/Analysis.tsx` — the page that composes everything: 3-column desktop
  + mobile tabs, the two flanking `EvalBar`s (`analysis-maia-eval-bar` violet left,
  Stockfish blue right), the `engineEnabled` toggle in the engine `CardHeader`, the
  `useMaiaEloDefault`/`selectedElo` plumbing, and the `useIsMobile` split. New card slots
  into the left column above `MaiaHumanPanel`.
- `frontend/src/components/analysis/EvalBar.tsx` — the bar component reused for the shared
  left-slot "FC"/"Maia" bar (accepts `accentColor`, `whiteFraction`, `evalCp`, `testId`).
- `frontend/src/lib/theme.ts` — `STOCKFISH_ACCENT` (blue), `MAIA_ACCENT` (violet); add
  `FLAWCHESS_ENGINE_ACCENT` (brown) + gold headline token here (single source of truth).
- `frontend/src/hooks/useMaiaEngine.ts`, `useStockfishGradingEngine.ts`,
  `useStockfishEngine.ts` — the `RAPID_STEP_DEBOUNCE_MS = 150` cadence + worker-lifecycle
  precedents the new hook follows.
- `frontend/src/lib/engine/workerPool.ts` + `maiaQueue.ts` (Phase 154) — the real
  providers the hook wires in.

### Supporting doc (user-opened during discussion)
- `docs/flawchess-engine-explained-2026-07-06.md` — background/explainer on the engine
  (opened in-IDE while discussing; context for the practical-vs-objective framing).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EngineLines.tsx` / `EngineLinesSkeleton` / `PvLineRow` / `formatScore` / `replayPvLine`:
  the FlawChess Engine card is structurally a sibling of this — badge + SAN chips + hover
  preview + expand, with a two-number (objective + practical) badge instead of one.
- `EvalBar` with `accentColor`/`whiteFraction`: powers the shared left-slot bar; the
  brown "FC" variant is one more accent, exactly like the existing violet Maia bar.
- `useMaiaEloDefault` + `selectedElo`: already on the page — feeds the engine's per-side
  `budget.elo`.

### Established Patterns
- Source-accent color coding of the two flanking bars + their cards (Phase 151.1):
  Stockfish blue, Maia violet — this phase adds FlawChess brown as the third source and
  makes the left slot precedence-based (FC > Maia).
- `useIsMobile` single-tree render (board mounts once): the new card must slot into both
  the desktop column and the mobile layout without duplicating stable `id`/`data-testid`s.
- `noUncheckedIndexedAccess` + Knip in CI; `data-testid` on every interactive element
  (toggles, line chips); `text-sm` floor except the approved dense-engine-surface `text-xs`
  exception already used by `EngineLines`.

### Integration Points
- New `FlawChessEngineLines.tsx` in `frontend/src/components/analysis/`; new
  `useFlawChessEngine.ts` hook in `frontend/src/hooks/` wiring `workerPool`/`maiaQueue`
  through the `SearchRunner`.
- The 3-toggle refactor touches the existing `engineEnabled` state and the eval-bar
  source selection in `Analysis.tsx` (left slot FC/Maia precedence; right slot SF sourced
  from the engine's objective root eval during a run).

</code_context>

<specifics>
## Specific Ideas

- User's layout reference: the current `/analysis` screenshot — Maia "Human Move
  Probability" card in the left column, board center (violet Maia bar left, blue Stockfish
  bar right), Stockfish 18 engine card + move list in the right column. The FlawChess
  Engine card goes directly **above the Maia card** in that left column.
- Branding intent: brand **brown** + a bronze/gold flourish "like the homepage," but the
  user themselves flagged a full glow as probably "too much" and noted brown arrows won't
  pop against the brown board squares (→ arrow color is a Phase 156 problem, likely
  gold/amber).
- Toggle model is the user's design: three card-level switches, FC eval bar labeled "FC"
  taking the left slot over Maia when both are on.
- Score pair: white-POV pawn scale for both numbers, "like Stockfish," to avoid the
  confusion of a your-POV flip.

</specifics>

<deferred>
## Deferred Ideas

- **Board arrows + the high-contrast FlawChess arrow color** — Phase 156 (ARROW-01..04).
  Brown-on-brown saliency is the real constraint there.
- **Game-review overlay integration** ("what you played vs practically best") — Phase 157
  (REVIEW-01..02).
- **Device-adaptive default** (on desktop / off mobile) — held as the SC4 fallback if the
  on-by-default mobile-memory UAT fails; not built unless needed.

### Reviewed Todos (not folded)
- *Bitboard storage for partial-position queries* (`2026-03-11-...md`) — database-layer
  idea, unrelated to this frontend phase. Not folded.
- *WR-01 — pt-33 is not a valid Tailwind class on the Score Y-axis label*
  (`2026-05-18-...md`) — a chart-axis styling nit on a different surface; not this phase.
  Not folded.

</deferred>

---

*Phase: 155-React Hook + Anytime UI (Free Analysis)*
*Context gathered: 2026-07-06*
