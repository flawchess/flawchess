# Phase 182: Style Levers - Context

**Gathered:** 2026-07-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Engine-level bot style capability, frontend-only, **no UI**: per-style opening-book steering, draw contempt + resign/draw-offer policy, prior reweighting by move features (Human rungs), and score shaping + variance preference (Light/Deep rungs) — all as new bot-only style params. Covers STYLE-01..05. The persona registry, Bots-page UI, avatars/bios (Phase 183) and ELO calibration (Phase 184) are explicitly out of scope.

</domain>

<decisions>
## Implementation Decisions

### Style param shape
- **D-01: Raw numeric knobs at the engine layer.** Engine code (`selectBotMove`, book weighting, draw/resign policy) consumes only a numeric `BotStyleParams` object (feature multipliers, score bonuses, contempt, resign thresholds). No style names in engine code.
- **D-02: The 4 named style→knob bundles ship in this phase as plain exported data constants** (Attacker / Trickster / Grinder / Solid Wall), which Phase 183's persona registry references per persona. Success criteria get verified against the real bundles, not throwaway configs.
- **D-03: Absent style = untouched code path.** Style params are optional everywhere (`BotSettings.style?: BotStyleParams`). When `undefined`, the exact current code runs — no reweight call, no shaping pass, default `maiaPolicyWeighting` book, Phase 169 draw-gate behavior. Custom mode (PERS-04) and the calibration baseline are provably unchanged by construction, not by tuned-away math.

### Opening books (STYLE-01)
- **D-04: Re-weight within ECO via the existing `BookWeightingFn` seam** (`openingBook.ts` D-06 contract: a persona re-weights what is on the menu, never changes the menu or the exit rules). Candidate generation, `BOOK_POLICY_FLOOR`, and `BOOK_PLY_CAP` stay untouched. Style lines not in the ECO corpus simply can't be booked — accepted.
- **D-05: Claude curates the per-style line lists from `openings.tsv` at plan/execute time**, both colors per style: Attacker = gambits/attacking systems; Trickster = the `trollOpenings` SAN lines + swindle/trap lines; Grinder = exchange/simplifying variations; Wall = system openings (London/Colle/Stonewall/Caro-Kann-type). User reviews the lists during UAT. Note: `data/trollOpenings.ts` stores position keys, not SAN lines — the SAN lines live in its comments and must be (re)curated as prefix lists.
- **D-06: Strong boost (~×20–50)** on style-line continuations so the bot follows its book essentially whenever a style line is available; Maia plausibility breaks ties among style lines; the raw-policy floor exit still protects against absurd continuations.

### Resign & draw policy (STYLE-02)
- **D-07: Policy-only in this phase.** Pure would-offer / would-accept-with-contempt / resign functions + `useBotGame` wiring ship now. Bot **resignation surfaces now** (game-end infra already exists); the bot's outgoing draw-offer banner/buttons land with Phase 183's UI. This deliberately supersedes Phase 169's D-02/D-03 (bot never offers/never resigns) for styled bots only — unstyled bots keep the old behavior per D-03 above.
- **D-08: Human rungs (800–1400) never resign** — authentic for low-rated play and requires no new signal (blend-0 bots never compute a `practicalScore`). Light/Deep personas resign when `practicalScore` stays below a style threshold for N consecutive own turns past a minimum move number (hysteresis; thresholds are style params).
- **D-09: One signed contempt knob per style, two consumers** (expected-score units, e.g. Grinder high-positive, Wall slightly negative). The accept gate treats a draw as worth `0.5 − contempt`; the same knob feeds Deep-regime score shaping as a malus/bonus on draw-ish moves.

### Prior reweighting & score shaping (STYLE-03/04)
- **D-10: Variance signal = additive optional child-score-spread field on `RankedLine`**, reported by `mctsSearch` — a statistic the tree already computes, not new search machinery; additive so analysis-board consumers are untouched.
- **D-11: Verification = deterministic unit tests + a Node measurement script** in the calibration-harness family: run each style over N sampled positions, report per-style feature-frequency shift vs unstyled baseline (e.g. Attacker checks/captures +X%) into `reports/data/`. Strength deltas are Phase 184's job, not this phase's.
- **D-12: Claude hand-tunes magnitudes at execute time** (feature multipliers per style; score bonuses in small expected-score units ~0.02–0.05), iterating against the measurement script until the shift is visible without gross strength distortion; final values documented, user reviews the script's report in UAT.

### Claude's Discretion
- Exact `BotStyleParams` sub-structure and file placement (suggest `lib/engine/` for engine-consumed parts, following the pure/orchestration split).
- Prior-reweighting feature set: keep to the seed's cheap chess.js flags (check, capture, pawn advance/storm, exchange/trade, retreat); exact set and per-style values are tuning territory under D-12.
- Resign threshold/hysteresis defaults, draw-offer trigger conditions and cooldowns (mirror `DRAW_OFFER_COOLDOWN_MOVES` symmetry where sensible).
- Measurement-script position sampling strategy and N.
- Specific curated line lists per style (D-05 — user reviews in UAT).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone & requirements
- `.planning/seeds/SEED-098-bot-personas-playstyle-layer.md` — the locked explore decisions: persona-pins-everything, rung→preset→lever table, perceptibility-per-effort build order, honesty constraints, live caveats (Maia sac-blindness, D-02/WR-04, BOT-03)
- `.planning/REQUIREMENTS.md` — STYLE-01..05 definitions + out-of-scope table

### Engine code (the seams this phase extends)
- `frontend/src/lib/engine/selectBotMove.ts` — the pure orchestrator; regime dispatch, `BotSettings`, the D-02 `policyTemperature` structural exclusion, D-07/BOT-03 symmetric-ELO invariant
- `frontend/src/lib/engine/botSampling.ts` — pure helpers (`samplePolicy`, `sampleRankedLines`, `argmaxLine`, `fallbackMove`, `mulberry32`); MUST stay pure (STYLE-05)
- `frontend/src/lib/engine/openingBook.ts` — the `BookWeightingFn` D-06 persona seam, floor/ply-cap exit rules (do not parameterize), `maiaPolicyWeighting` reference implementation
- `frontend/src/lib/botDrawGate.ts` — current accept-gate (near-equal band + endgame gate) and the Phase 169 never-offer/never-resign docs this phase supersedes for styled bots
- `frontend/src/hooks/useBotGame.ts` — where book → `selectBotMove` → draw gate are wired (book weighting call at ~line 343; `rootPracticalScore` tracking ~line 434)
- `frontend/src/lib/engine/types.ts` — `RankedLine` (gains the optional spread field), `SearchBudget`, `EngineSnapshot`
- `frontend/src/data/trollOpenings.ts` — Trickster source material (position keys + SAN lines in comments)
- `frontend/src/lib/playStyle.ts` — the three presets (Human 0 / Light 0.05 / Deep 0.5) that map rungs to regimes

### Calibration compatibility (Phase 184 consumes this phase's params)
- `scripts/calibration-harness.mjs` — imports `selectBotMove` directly; style params must be passable there; harness games start from mid-opening FENs so the book layer is structurally outside calibration
- `reports/data/bot-strength-lookup.json` — the measured Human/Light/Deep ranges that dictate the rung→preset mapping

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BookWeightingFn` seam in `openingBook.ts`: purpose-built for exactly this phase; per-style weighting = curated prefix list + boost multiplier composed over `maiaPolicyWeighting`.
- `samplePolicy`/`weightedPick` proportional sampling: unnormalized weights are fine — no renormalization step needed for the boost (documented in `maiaPolicyWeighting`).
- `wouldBotAcceptDraw`'s null-sentinel discipline: extend, don't replace — contempt shifts the draw value, the null-refuses and endgame-gate rules stay.
- `mulberry32` seeded rng: use for deterministic distribution tests.
- `scripts/calibration-harness.mjs` + `scripts/lib/` patterns: the measurement script should follow this family's conventions (Node, imports app code via `@/` alias).

### Established Patterns
- Pure-helpers-vs-impure-orchestrator split (`botSampling.ts` vs `selectBotMove.ts` D-09): reweighting and score shaping must land as pure, separately-exported helpers; `selectBotMove` only gains orchestration calls.
- Structural invariants by type: `policyTemperature` is excluded from `BotSettings.budget` by `Omit<>` — new style fields must not weaken this; keep `BotStyleParams` a separate optional field, never merged into the budget.
- Tunables as named exported constants with docstrings explaining the tuning rationale (`BOOK_POLICY_FLOOR` style).

### Integration Points
- `selectBotMove` blend≤0 branch: prior reweighting hooks between `deps.policy()` and `samplePolicy`.
- `selectBotMove` search branch: score shaping transforms `rankedLines` before `argmaxLine`/`sampleRankedLines`.
- `useBotGame` book call site (~line 343): swap default weighting for the style's `BookWeightingFn` when style params present.
- `useBotGame` game-loop: resign check after each bot search completes; draw-offer policy evaluated on the bot's turn (UI consumption in 183).
- `mctsSearch` → `RankedLine`: additive optional child-score-spread field.

</code_context>

<specifics>
## Specific Ideas

- Style identities from the seed: Attacker = aggressive/complicating (checks/captures/pawn storms boosted); Trickster = defensive/complicating, traps at low rungs + swindle mode/high variance at 1600+; Grinder = trade-happy, steers to endgames, never resigns early (its training value: playing it exercises exactly what FlawChess measures); Solid Wall = defensive/simplifying, system book.
- Maia-3 sac-blindness is accepted Attacker flavor — do not attempt to fix or work around it in this phase.
- Prior art the seed cites: Chessiverse "Move Curator" score-handicap selection; chess.com persona bots.

</specifics>

<deferred>
## Deferred Ideas

- Bot outgoing draw-offer UI (banner + accept/decline) — Phase 183, alongside the Bots-page persona UI.
- Per-persona strength offsets and measured ELO labels — Phase 184.
- Personas above 1800 / ladder extension — SEED-114 (dormant).
- Positional-theme steering — explicitly out of scope (REQUIREMENTS.md).

### Reviewed Todos (not folded)
- `172-deferred-review-findings` — analysis-page gem-sweep review findings; unrelated to bot style (keyword-noise match).
- `2026-03-11-bitboard-storage-for-partial-position-queries` — DB storage idea; unrelated.
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label` — frontend chart bug; unrelated.

</deferred>

---

*Phase: 182-Style Levers*
*Context gathered: 2026-07-21*
