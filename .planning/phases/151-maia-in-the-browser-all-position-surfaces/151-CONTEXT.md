# Phase 151: Maia in the Browser + All-Position Surfaces - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Add **Maia-3** (CSSLab "Chessformer", human move-prediction engine) as a second, *human*-model
engine on the existing `/analysis` board — running **entirely client-side** via
**onnxruntime-web in a Web Worker**, lazy-loaded only when the analysis board opens. For **every
position** (game mode AND free play), recomputed live on every board navigation with **no server
round-trip and zero DB writes**, surface:

- a **"Moves by Rating" chart** (Recharts + `theme.ts`): one probability line per candidate move
  over the ELO ladder, "you are here" reference line, played + engine-best moves emphasized,
  line set capped at top-N-by-peak ∪ {played, best};
- a **Maia eval bar on the LEFT of the board** (Stockfish bar stays on the RIGHT).

Plus: relicense the repo MIT → **AGPL-3.0**, and show a visible Maia attribution + offer-source
notice citing the Chessformer paper.

**This is a heavily pre-locked phase.** SEED-081, REQUIREMENTS.md (14 requirements: LIC/MAIA/SURF/VALID),
and spikes 004–006 already fixed most of the WHAT and much of the HOW. This discussion resolved the
handful of genuinely-open HOW decisions below; everything else flows from the requirements + seed.

**Explicitly OUT of scope (this phase / this milestone):** Pillar C aggregate rollup, any DB
write / persistence of Maia signals, `game_flaws` schema change, the flaw salience×trainability
verdict (that is Phase 152), server-side/remote-worker Maia inference, SEED-082 human-playable-line
engine, and any Maia model fine-tuning/modification (unmodified model only — AGPL §13).

</domain>

<decisions>
## Implementation Decisions

### Layout & placement (Area 1)
- **D-01:** Desktop is a **3-column layout** mirroring the product thesis (**left = human/Maia,
  right = engine/Stockfish**): **left column = the "Moves by Rating" chart** (~340–380px, like the
  existing right panel) | **center = Maia eval bar + board + Stockfish eval bar** | **right column
  = engine card + variation tree + board controls** (the current right panel). The Maia expected-score
  bar hugs the board's LEFT edge (SURF-04); the Stockfish bar stays on the RIGHT.
- **D-02:** Trade-off accepted: a left-column chart is **narrower** than a below-board one, so it
  shows fewer ELO x-axis ticks. User chose the thematic left-grouping over max chart width. Keep it
  legible at ~360px (compact axis, top-N cap already limits line count).
- **D-03:** Mobile adds a **4th tab**; final tab order is **Moves | Eval | Human | Tags**. The
  "Human" tab holds the Moves-by-Rating chart (full width when selected). Board + both eval bars
  stay always-visible above the tab strip.
  - **Open detail for planning:** free play currently has **no** mobile tab strip (only the move
    list). The Human chart must still appear in free play — planner to decide: show it below the
    board, or introduce a minimal Moves | Human tab pair in free play. Not a user decision; keep it
    consistent with the tabbed game-mode surface.

### Maia eval bar rendering (Area 2)
- **D-04:** The LEFT Maia bar renders a **single expected-score fill** — collapse the WDL head to
  `E = W + 0.5·D` (0..1) and draw one vertical fill, a clean **mirror of the Stockfish cp bar**
  (same "how good for white" grammar, side-by-side consistent). Not the 3-segment W/D/L stack.
- **D-05:** White-POV, and it **flips with board orientation** exactly like the existing
  `EvalBar` `flipped` prop. (The full WDL vector is still computed — it feeds the chart / future
  Phase 152 practical-severity reframe — but the *bar* shows only expected score.)

### ELO conditioning + "you are here" (Area 3)
- **D-06:** An **interactive ELO selector** drives the "you are here" reference line, available
  across modes (exploration/scouting: "how do players at each level handle this?").
- **D-07:** Selector **defaults**: game mode → the **user's color rating-at-game-time**
  (`games.white_rating` / `games.black_rating` per MAIA-04, never the frozen snapshot rating);
  free play → the **user's current platform rating** (from `useUserProfile()`), else a **1500**
  midpoint fallback. The selector lets the user move off the default to explore other levels.
- **D-08 (Claude's discretion / research):** ELO ladder **range + granularity** for the chart
  x-axis and the selector bounds are set to the model's supported/trained range (provisional
  ~1100–2000, ~100-ELO steps, matching maiachess.com) — **confirm against the actual
  `maia3_simplified.onnx` ELO input contract during the hands-on pass**; do not hard-code a range
  the model wasn't trained on.

### Model size + execution backend (Area 4)
- **D-09:** Start with **`maia3_simplified.onnx`** (the artifact maiachess.com ships) / the
  **smallest Maia-3**; **WASM baseline** (works on mobile Safari), **feature-detect and prefer
  WebGPU** when available.
- **D-10:** **Upgrade to a larger model (23M/79M) ONLY if the VALID-01 live-eyeball gate shows
  poor calibration.** VALID-01 is measure-and-judge, **not** a hard ship-block for the chart/bar —
  the ephemeral in-browser surface IS the quality gate. Download-size + per-position latency
  (desktop + phone; single call vs ELO sweep; WASM vs WebGPU) are **measured during the phase**
  (MAIA-06), not guessed here.

### Claude's Discretion
- Chart color mapping for candidate-move lines (reuse `theme.ts`; played + best emphasized) —
  spike 006 already prototyped the shape; production port to Recharts is mechanical.
- Worker hook shape (mirror `useStockfishEngine` — lifecycle, tab-hide pause, adaptive debounce,
  stale-guard), ephemeral session cache scope/size (board-session only, no persistence — MAIA-05).
- Attribution notice placement (visible surface citing CSSLab repo + AGPL text + model artifact +
  Chessformer paper — LIC-02); planner to pick the surface (analysis-page info, footer, or About).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone scope & requirements
- `.planning/ROADMAP.md` §"Phase 151" — goal, 6 success criteria, requirement list.
- `.planning/REQUIREMENTS.md` — LIC-01/02, MAIA-01…06, SURF-01…05, VALID-01 (the locked v1
  requirements for this phase); also the explicit Out-of-Scope table.
- `.planning/seeds/SEED-081-maia3-human-flaw-enrichment-milestone.md` — the locked design
  (three signals, browser-only + ephemeral-cache rationale, AGPL 4-condition posture, chart
  line-cap rule, chart-everywhere / verdict-on-flaws split, model-as-data license reading).

### Feasibility spikes (de-risking — read before the hands-on pass)
- `.planning/spikes/004-maia3-onnx-browser-feasibility/README.md` — client-side feasibility
  VALIDATED; architecture (encoder transformer + GAB + 64×64 attention policy head + mean-pooled
  WDL head); `maia3_simplified.onnx` exists publicly; rough size table (5M≈20MB / 23M≈90MB /
  79M≈320MB fp32, ~¼ quantized); the 3 remaining hands-on items (tensor I/O, size/latency, op support).
- `.planning/spikes/005-agpl-client-bundle-gate/README.md` — license PARTIAL/conditional; the
  4 conditions to stay clean (unmodified model as data via MIT onnxruntime-web, own MIT glue,
  attribution/offer-source, no fine-tune). NOTE: milestone chose to **relicense to AGPL** (LIC-01),
  which removes the ambiguity entirely.
- `.planning/spikes/006-moves-by-rating-chart/README.md` + `.planning/spikes/006-moves-by-rating-chart/index.html`
  — the working chart prototype (Ne4 hump + O-O mirror, you-are-here marker, top-N∪{blunder,best}
  cap, theme colors). Production Recharts port is mechanical.

### Integration report & open questions
- `.planning/research/maia-3-integration.md` — full license + technical integration report
  (AGPL, PyTorch/UCI, 5M/23M/79M, WDL value head).
- `.planning/research/questions.md` — Q-013 (per-move prob extraction — mechanism confirmed,
  tensor-I/O contract is hands-on item 1), Q-014 (Maia-WDL ↔ Stockfish comparability — open,
  answered live via VALID-01), Q-015 (ELO range / low-rating calibration / is the value head
  ELO-conditioned — open, answered live), Q-016 (model-size vs latency — narrowed to hands-on
  measurement).

### External (source the artifact + encoding here — not in-repo)
- Reference client (authors run Maia in-browser via onnxruntime-web):
  https://github.com/CSSLab/maia-platform-frontend — locate `maia3_simplified.onnx` + its
  board/ELO encoding + output tensor layout here.
- Model / paper: https://github.com/CSSLab/maia3 · weights https://huggingface.co/UofTCSSLab ·
  Chessformer paper (arXiv 2605.19091).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/hooks/useStockfishEngine.ts` — the **template for a `useMaiaEngine` worker hook**:
  classic (non-module) Web Worker lifecycle, ready/analyzing state, adaptive debounce
  (`RAPID_STEP_DEBOUNCE_MS`), stale-result guard, tab-hide pause (D-04). Mirror its structure; the
  message protocol differs (onnxruntime-web inference, not UCI).
- `frontend/src/pages/Analysis.tsx` — the integration site: `boardRow` (where the LEFT Maia bar
  slots in beside the board + right `EvalBar`), the desktop board-column / side-panel structure
  (to be reworked into the D-01 3-column layout), and the mobile `Tabs` block (add the D-03
  "Human" tab). Also `useGameOverlay`, `useLibraryGame` (rating-at-game-time via
  `gameData.white_rating`/`black_rating`), the `LIVE_EVAL_CACHE_MAX` ephemeral-cache pattern.
- `frontend/src/components/analysis/EvalBar.tsx` — template for the Maia expected-score bar
  (`flipped` prop, vertical fill). D-04/D-05.
- `frontend/src/hooks/useUserProfile.ts` — free-play default ELO source (D-07). Read rating from
  `useUserProfile().data` (NOT `useAuth().user`, which has no rating — cf. beta-gating memory).
- Recharts (already a dep, `recharts@^3.8.1`) + `frontend/src/lib/theme.ts` (WDL_WIN/DRAW/LOSS
  and accent colors) for the chart. `EvalChart` below-board pattern is a Recharts reference.
- `.planning/spikes/006-moves-by-rating-chart/index.html` — the chart prototype to port.

### Established Patterns
- **Client-side WASM engine in a Web Worker, lazy-loaded, tab-hide paused** is already the norm
  (Stockfish, Phase 136). Maia rides the same pattern — never in the initial bundle (MAIA-02).
- Vendored engine asset served from `frontend/public/engine/` (Stockfish precedent) — the
  `maia3_simplified.onnx` + onnxruntime-web wasm artifacts follow the same "runtime data asset"
  serving approach.
- COOP/COEP headers already handled for WASM threads (Phase 136 CI guard) — verify onnxruntime-web
  requirements against the existing setup.
- Browser-automation rules: `data-testid` on the ELO selector, tab triggers, and chart/bar
  containers; `text-sm` floor; `theme.ts` colors only.

### Integration Points
- New surfaces attach to the existing `/analysis` page (game mode `?game_id&ply` + free-play
  `?fen`); no new route, no new backend endpoint, no schema/migration (D-4 continues).
- The Maia worker reads a FEN (+ ELO) from board state and returns a normalized per-legal-move
  distribution + WDL; the chart consumes the per-ELO curve, the bar consumes expected score.

</code_context>

<specifics>
## Specific Ideas

- **Product-thesis layout is deliberate:** left side of the board = human/Maia (chart + expected-score
  bar), right side = engine/Stockfish (cp bar + engine lines). "Engines are flawless, humans play
  FlawChess" framed on either side of the board (D-01).
- **The chart is a general exploration/scouting tool**, not flaw-only — hence the interactive ELO
  selector (D-06): "how do players at each level handle this?" The Phase 152 flaw *verdict* is the
  overlay that only appears on flaw moves; this phase ships the always-on chart + bar.
- The spike-006 `index.html` is the visual target for the chart (hump/mirror shapes, you-are-here
  marker, top-N∪{played,best} cap).

</specifics>

<deferred>
## Deferred Ideas

- **Phase 152 (next):** salience×trainability verdict banner (FLAW-01/02), Maia-WDL practical-severity
  reframe of the flaw (FLAW-03), precision-first withhold on low-confidence buckets (FLAW-04). This
  phase deliberately ships chart+bar for ALL positions; the flaw *interpretation* is Phase 152.
- **v2 / future persistence-gated milestone:** Pillar C aggregate weakness rollup (AGG-01/02),
  `game_flaws` schema + flaw-node backfill, SEED-082 human-playable-line engine (Maia-filtered
  Stockfish). Revisit only after this phase proves Maia calibration is trustworthy.
- **3-segment W/D/L bar rendering** was offered and not chosen (D-04 picked single expected-score
  fill). Noted in case the practical-severity work in Phase 152 wants the fuller WDL split.

### Reviewed Todos (not folded)
- `2026-03-11-bitboard-storage-for-partial-position-queries.md` — DB/storage feature; off-scope for
  a zero-DB browser phase. Not folded.
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md` — stale frontend nit on a different
  chart's Y-axis label; unrelated to the Maia chart. Not folded (worth a standalone quick-fix later).

</deferred>

---

*Phase: 151-maia-in-the-browser-all-position-surfaces*
*Context gathered: 2026-07-05*
