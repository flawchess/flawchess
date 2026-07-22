# Requirements: FlawChess — Milestone v2.7 Bot Personas & Playstyle Layer

**Defined:** 2026-07-21
**Core Value:** Position-precise WDL analysis on top of users' actual games; the Bots page gives users calibrated, honest-strength opponents to practice against — v2.7 makes those opponents feel like distinct characters.
**Source:** SEED-098 (explore sessions 2026-07-12 + 2026-07-21, locked decisions), on the v2.6 measured-strength substrate (Phases 173/180/181).

## v2.7 Requirements

### Persona Roster (PERS)

- [ ] **PERS-01**: User can browse a roster of 24 named bot personas (4 styles × 6 rungs, 800–1800) on the Bots page, each showing name, avatar, bio, style, and ELO label
- [ ] **PERS-02**: User can start a game against any persona in one action; the persona pins the complete opponent (preset, ELO, style params, opening book, resign/draw-offer policy) — no persona × strength picker
- [ ] **PERS-03**: Persona definitions live in a single typed registry mapping each slot to its full config, with each rung's preset dictated by the measured ranges (800–1400 Human, 1600 Light/Deep, 1800 Deep)
- [ ] **PERS-04**: Custom mode keeps the raw (ELO, preset) knobs unchanged for power users

### Style Levers (STYLE)

- [x] **STYLE-01**: Each persona plays a style-specific opening book (Trickster reuses `frontend/src/lib/trollOpenings.ts`; other styles get curated books)
- [x] **STYLE-02**: Personas apply style-specific draw contempt and resign/draw-offer policy (e.g. Grinder never resigns early)
- [x] **STYLE-03**: Human-rung personas (800–1400) get prior reweighting — Maia policy probs multiplied by move-feature weights via a cheap chess.js move classifier (checks, captures, pawn storms, exchanges)
- [x] **STYLE-04**: Light/Deep-rung personas (1600–1800) get score shaping — style bonus/malus on `practicalScore` before the existing softmax in `selectBotMove`, including variance preference from MCTS child-score spread
- [x] **STYLE-05**: Style params are NEW bot-only fields (never the analysis-board `policyTemperature` per D-02/WR-04, never derived from the player per BOT-03); `botSampling.ts` helpers stay pure

### Calibration (CAL — continues from v2.3's CAL-03)

- [ ] **CAL-04**: Every persona's labeled ELO is a calibrated ELO measured on the Phase-173 internal anchor scale via the Phase-180 harness (~24 cells × ~4 anchors × ~24 games ≈ 2 overnight runs), with a per-persona offset absorbing the style-induced strength delta
- [ ] **CAL-05**: Strength labels honor the honesty constraints — bottom rung acknowledges the ~900 measured floor (both weakest Human cells are `beyond_ladder` extrapolations), top rung capped at 1800 (Deep's measured ceiling)

### Avatars & Identity (AVAT)

- [ ] **AVAT-01**: 24 AI-generated avatar portraits in one consistent style, manually curated, committed as static assets
- [ ] **AVAT-02**: Each persona has a name and short bio conveying its style identity and per-tier story (e.g. Trickster: cheap trap lines at 800–1200, swindle mode + high-variance preference at 1600+)

## Future Requirements

Deferred. Tracked but not in the current roadmap.

- **SEED-114**: Ladder extension above ~1900 internal (stronger anchors + raised search budget) to unlock personas above the 1800 rung

## Out of Scope

| Feature | Reason |
|---------|--------|
| Positional-theme steering ("loves the bishop pair") | WASM Stockfish returns one cp number, not eval components |
| Persona × strength picker | Persona-pins-everything is a locked decision; Custom mode covers power users |
| Adaptive style (derived from player rating/play) | BOT-03 invariant — bot stays non-adaptive and measurable |
| Measurably distinct play per style | Goal is *perceived* personality; cheap levers, small strength deltas |
| Personas above 1800 | Deep's measured ceiling; gated on SEED-114 (dormant) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PERS-01 | Phase 183 | Pending |
| PERS-02 | Phase 183 | Pending |
| PERS-03 | Phase 183 | Pending |
| PERS-04 | Phase 183 | Pending |
| STYLE-01 | Phase 182 | Complete |
| STYLE-02 | Phase 182 | Complete |
| STYLE-03 | Phase 182 | Complete |
| STYLE-04 | Phase 182 | Complete |
| STYLE-05 | Phase 182 | Complete |
| CAL-04 | Phase 184 | Pending |
| CAL-05 | Phase 184 | Pending |
| AVAT-01 | Phase 183 | Pending |
| AVAT-02 | Phase 183 | Pending |

**Coverage:**

- v2.7 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0 ✓

**Phase mapping rationale:** Style levers (Phase 182) build the engine-level capability first — bot-only style params in `botSampling.ts`/`selectBotMove.ts`, no UI. Persona registry + Bots page (Phase 183) wires those levers into 24 named personas with a real UI, shipped with provisional (raw preset) ELO labels — fully user-shippable on its own. Calibration (Phase 184) then runs the harness against the finished personas and swaps in measured ELO labels, honoring the floor/ceiling honesty constraints. Each phase is independently shippable; labels simply get more honest over the sequence.

---
*Requirements defined: 2026-07-21*
*Last updated: 2026-07-21 after roadmap creation (Phases 182-184)*
