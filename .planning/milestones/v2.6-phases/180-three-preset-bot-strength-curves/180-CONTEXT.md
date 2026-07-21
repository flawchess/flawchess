# Phase 180: Three-preset bot strength curves - Context

**Gathered:** 2026-07-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Measure the FlawChess bot's strength as a function of `bot_elo` at three blend presets
(**Human=0**, **Light=0.05**, **Deep=0.5**) on the Phase-173 internal anchor scale, and measure
the cross-family style-inflation gap `G_preset = rating_vs_Maia − rating_vs_SF` for each preset.
Output is a per-preset strength curve (per-`bot_elo` internal rating + per-cell CIs) plus the
per-preset `G_preset`, feeding SEED-104's shipping lookup curves.

**This phase delivers the harness + measurement machinery + a validated pilot; the full overnight
sweep is an operator-run (HUMAN-UAT) step folded in after.** No human ground truth is played
(SEED-103 is closed). Pure calibration/measurement — **no app, API, schema, or UI change.**

**In scope:**
- Harness fixes to `scripts/calibration-harness.mjs`: (1) import `calibration-internal-scale.mjs`
  and window/pick anchors by `INTERNAL_RATING` (not nominal `bot_elo` — the bug that clamped the
  2026-07-12 run); (2) locate-then-measure two-pass for bot cells; (3) both anchor families
  enabled (Maia-argmax rungs AND Stockfish skill levels); (4) per-cell CIs.
- Fit path: extend `scripts/calibration_anchor_fit.py` to fit each bot cell holding the 10 anchors
  fixed at their `INTERNAL_RATING`, with separate vs-Maia / vs-SF fits so `G_preset` falls out.
- A pilot proving the harness (logic tests + a small real-engine pilot) before the operator sweep.
- The operator-run full sweep + fitted per-preset curves + `G_preset` + a findings note, folded
  in as a HUMAN-UAT step (mirrors the 173 findings note).

**Out of scope:**
- The absolute human pin `C` (literature-sourced; lives in SEED-104).
- Building SEED-104's shipping lookup / slider ranges / preset cards.
- Any change to the shipped bot (`selectBotMove`), the app, or persisted data.
- Playing real humans (SEED-103, closed 2026-07-19).
</domain>

<decisions>
## Implementation Decisions

### Run scope & "done" definition
- **D-01:** Split delivery. The phase completes when the harness fixes land and are proven on a
  pilot. The full ~1,440-game (~18-22h) sweep, the fitted curves, `G_preset`, and the findings
  note are an **operator-run HUMAN-UAT step** folded in afterward — the overnight run does NOT sit
  on the phase's interactive critical path. (Matches the CLAUDE.md "flag long runs as HUMAN-UAT"
  ethos; keeps the phase reviewable.)

### Pilot gate (proves the harness before the operator sweep)
- **D-02:** Both layers required: (a) unit / `*.check.mjs` logic tests on the new internal-scale
  windowing + two-pass cell-selection using fabricated providers (no real engines, deterministic);
  AND (b) a small real-engine pilot of 1–2 real cells at low N confirming: sane ratings, correct
  anchor windowing on `INTERNAL_RATING`, both anchor families firing, and `--resume` integrity.

### Grid design
- **D-03:** **Per-preset, non-uniform grids** (locked shape): three separate rows, Human skewed to
  the low end, Light the middle, Deep the high end, overlapping in the middle, ~5 `bot_elo` points
  each. Each preset's honest slider range (SEED-104) drives its point placement.
- **D-04:** **Exact `bot_elo` point values are a planner/researcher output**, chosen after
  inspecting `INTERNAL_RATING` spacing and anchor bracketing — evidence-based placement, not
  guessed here. (Seed example {700,1100,1500,1900,2300} is illustrative only.)

### Games budget
- **D-05:** Games-per-(cell, anchor) on the measure pass is a **planner decision** — set from a
  precision target given the measured anchor spacing, within the seed's 24–30 band (24 → ±71/anchor
  → ~±35 combined; 30 → ~±64/anchor at ~25% more wall-clock). Applies to the operator sweep budget,
  not the pilot.

### Fit & output artifact
- **D-06:** **Extend `scripts/calibration_anchor_fit.py`** (the existing Bradley-Terry/Elo fitter)
  rather than reimplementing in JS. Hold the 10 anchors fixed at their `INTERNAL_RATING`; fit each
  bot cell's rating with **separate vs-Maia and vs-SF fits** so `G_preset = rating_vs_Maia −
  rating_vs_SF` is a direct output. Emit a bot-curves JSON mirroring
  `reports/data/anchor-ladder-internal-scale.json` (ratings + CIs), consistent method with 173,
  CIs for free.

### Two-pass anchor selection
- **D-07:** **Reuse the Phase-173 `scripts/lib/calibration-anchor-schedule.mjs`** probe→measure +
  connectivity/cross-family guard (informative [0.2, 0.8] band, `rescueConnectivity`/`bandDistance`
  rescue). Adapt as needed for bot-vs-anchor cells (173 scheduled anchor-vs-anchor pairs). Locate
  pass ≈ 8 games vs 2 widely-spaced anchors to place a cell, then measure vs the 3–4 anchors
  bracketing that estimate on `INTERNAL_RATING`.

### Locked upstream (from SEED-102, not re-discussed)
- Blend values `{0, 0.05, 0.5}` — three presets, fixed. Human = one Maia policy call, no search,
  sample raw policy; Light/Deep = full MCTS, `tau = TAU_MAX·(1−blend)`, `TAU_MAX = 0.1`.
- Cross-family split is a **first-class output**, not a sanity check (2026-07-12 run used Maia
  anchors only — the omission this fixes).
- Also log near-free: Maia-agreement rate, Stockfish-agreement rate, ACPL, blunder rate, draw
  rate, game length (confirm the three presets play differently).
- Primary output is on the **internal anchor scale** — NOT human ELO. Absolute human ELO comes
  only from `C` in SEED-104.

### Claude's Discretion
- Exact `bot_elo` point values per preset (D-04), measure-pass games/cell (D-05), and the precise
  adaptation of the 173 schedule module to bot cells (D-07) are all planner/researcher calls.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source seed & consumer
- `.planning/seeds/SEED-102-iso-strength-surface-sweep.md` — the full spec for this run: three
  presets, grid, cross-family split, harness fixes required, budget, caveats. Authoritative.
- `.planning/seeds/SEED-104-iso-strength-inversion-table.md` — the downstream consumer; defines the
  offset model `human_blitz = internal_rating − G_preset + C` and what artifact shape it needs.
- `.planning/seeds/closed/SEED-103-lichess-bot-ground-truth-calibration.md` — closed; why there is
  no human ground truth (context for the no-human decomposition).

### Phase-173 foundation (the ruler + methodology)
- `.planning/notes/2026-07-15-anchor-ladder-self-calibration-findings.md` — internal ratings, the
  ~2.8x compression verdict, Finding 4 (cross-family style residuals). Read before placing grid
  points (D-04) and interpreting `G_preset`.
- `.planning/notes/2026-07-13-bot-calibration-findings.md` — original bot blend-calibration
  findings (the 0.5→1 leg buying +154/+198/+375 ELO; the clamped 2026-07-12 run).
- `scripts/lib/calibration-internal-scale.mjs` — the `INTERNAL_RATING` table (GENERATED; the ruler,
  `maia1500 == 1500` pin).
- `reports/data/anchor-ladder-internal-scale.json` — ratings + CIs + residuals; the artifact shape
  the bot-curves JSON should mirror (D-06).

### Reused code
- `scripts/calibration-harness.mjs` — bot-vs-anchor harness (CLI/TSV/game-loop) to fix.
- `scripts/lib/calibration-anchor-schedule.mjs` — probe→measure scheduler + connectivity guard to
  reuse (D-07).
- `scripts/calibration_anchor_fit.py` — Bradley-Terry/Elo fitter to extend (D-06).
- `scripts/lib/calibration-anchors.mjs` — anchor movers (`maiaArgmaxMove`, `SF_SKILL_ELO`,
  `anchorRatingFor`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/calibration-harness.mjs`: CLI flags already exist (`--elo`, `--blends`, `--anchors`,
  `--games-per-cell`, `--seed`, `--out-dir`, `--stockfish-procs`, `--resume`); TSV writer opens
  once per run; `--resume` re-derives grid-order prefix. So blend `{0,0.05,0.5}` and games/cell are
  runtime flags, not code — the code work is internal-scale windowing + two-pass + both-families +
  CIs. Currently windows anchors by `ANCHOR_ELO_WINDOW` on nominal `bot_elo` (the bug).
- `scripts/lib/calibration-anchor-schedule.mjs`: pure-logic, engine-free, unit-testable
  probe→measure scheduler with `scoreInInformativeBand` ([0.2,0.8]), `checkConnectivity`
  (fail-loud, `MIN_CROSS_FAMILY_EDGES` cross-family floor), and `rescueConnectivity`/`bandDistance`
  rescue added mid-173-run. Directly reusable for the two-pass (D-07).
- `scripts/calibration_anchor_fit.py`: Bradley-Terry/Elo fit → per-anchor internal ratings + 95%
  CIs + residuals JSON. Extend to fit bot cells with anchors pinned (D-06).
- Anchor families: 5 Maia argmax rungs (700/1100/1500/1900/2300) + 5 Stockfish Skill Levels
  (0/3/5/8/10), all with measured `INTERNAL_RATING` — they interleave (sf3≈maia1100, sf5≈maia1500,
  sf8 between maia1900/2300; sf0 weakest, sf10 strongest).

### Established Patterns
- Two-pass probe (≈8 games, cheap triage on informative band) → measure (24 games on informative
  links), cross-family links prioritized to the ≥2 connectivity floor — the exact pattern 173's
  anchor sweep used.
- Findings note as the human-readable deliverable (residuals aren't legible in the TSV/JSON alone);
  the 173 note is the template.
- Fabricated-provider determinism tests (`*.check.mjs`) let the selection/fit logic be proven
  without real engines — the basis for the D-02 pilot's logic-test layer.

### Integration Points
- The bot mover is the shipped provider-agnostic `selectBotMove` blend path (the harness "measures
  the shipped bot, not the old" per its header) — do NOT modify it; only feed `bot_elo`/`blend`.
- Fit output JSON is the interface to SEED-104 (D-06); it must carry per-preset per-`bot_elo`
  ratings + CIs + `G_preset`.
</code_context>

<specifics>
## Specific Ideas

- "Deep is a ceiling, not a different feel" — inside `(0,1)` blend is only a softmax temperature
  dial; Light and Deep run the same MCTS at the same depth, differing only in sampling determinism.
  The one qualitative cliff on the axis is blend 0 (no search) vs blend >0 (search) = Human↔Light.
  Do not market/interpret Deep as "deeper."
- Read any cell leaning heavily on `sf0` or `maia700` (both style-outliers per 173 Finding 4) with
  that caveat in mind.
- Budget baseline: ~82 games/hr at `--stockfish-procs 4` (raise if cores allow).
</specifics>

<deferred>
## Deferred Ideas

- **Absolute human-ELO pin `C` and the shipping lookup curves / honest per-preset slider ranges /
  preset cards** — SEED-104, gated on this phase's outputs.
- **Bot personas / play-style layer** — SEED-098, downstream of calibrated presets.

None of the discussion drifted outside the phase's measurement scope.
</deferred>

---

*Phase: 180-three-preset-bot-strength-curves*
*Context gathered: 2026-07-19*
