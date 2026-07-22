# Phase 184: Persona Calibration & Strength Honesty - Research

**Researched:** 2026-07-22
**Domain:** Extending an existing Node.js calibration harness (bot-vs-anchor game loop + two-pass locate/measure scheduler) with a style axis, running an operator overnight sweep, and fitting per-persona strength offsets via a stdlib Bradley-Terry MLE reused from Phase 180/181.
**Confidence:** HIGH — every load-bearing claim below is grounded in the actual committed source (calibration-harness.mjs, calibration-bot-cell-schedule.mjs, calibration_anchor_fit.py, gen_bot_strength_curves.py, personaRegistry.ts, bot-strength-lookup.json), not training-data recall.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Label semantics (retarget + measure)**
- D-01: Two-step retarget-then-measure. First re-seat each persona's `botElo` via the Phase-181 lookup (`reports/data/bot-strength-lookup.json` 100-step inversions, per the persona's own preset) so the underlying strength targets the rung (e.g. a Human rung 1400 gets `botElo` ~1900+, not 1400). Then harness-measure each persona cell WITH its style bundle active; the measured value (converted to approx blitz per Phase-181 conventions) becomes the displayed label. This replaces the 183 A1 placeholder (`botElo === rung`) entirely — both `botElo` and the label change.
- D-02: One-shot measurement. A single measurement round (~2 overnight runs, matching the SEED-098 budget). Whatever each persona measures is its label; the tilde format absorbs residual error. No correction pass is planned — if a persona lands far off its rung, that is the honest label.

**Ladder coherence**
- D-03: Labels round to nearest 50 (e.g. `~950`, `~1250`). Matches the ±50–100 CI scale without pseudo-precision; keeps 183 D-04's tilde format.
- D-04: Weak monotonicity within each style column, enforced by CI-pooling. If a higher rung measures below a lower rung within the same style, pool/nudge the violating neighbors to a shared label (PAVA-style, the same technique Phase 181 used on the preset curves). Ties are allowed — two adjacent rungs may both show `~1600`. Never display an inversion.
- D-05: Cross-style divergence at the same rung is shown as measured. attacker-1200 may read `~1150` while wall-1200 reads `~1250`; per-persona offsets are the point of CAL-04. The grid stays organized by rung; only the printed number differs.

**Honesty surfaces (CAL-05)**
- D-06: Bottom rung shows its measured/extrapolated value (~900) like every other persona, with the floor acknowledgment living in an info popover on the detail surface (not a qualifier on the card). Grid label format stays uniform.
- D-07: Global ~1800 cap. No persona label ever exceeds `~1800` (Deep's measured ceiling), regardless of rung. A styled cell measuring above pools down to `~1800`.
- D-08: Reusable measurement-disclosure popover on every persona's ELO label in the detail surface (all 24): what the number is (measured in bot-vs-engine games on the internal anchor ladder, approximate blitz scale). Follows the PercentileChip-disclosure convention; the bottom rung's floor note (D-06) is a variant line of this same popover. Popover bodies may use `text-xs` per the frontend exception.

**Run & pipeline**
- D-09: Operator-run overnight sweeps with a committed runbook (Phase 180 model). The phase ships: harness style-wiring, the 24-persona-cell schedule, and a runbook; the user runs the ~2 overnight sweeps under the resume-on-crash supervisor (`bin/preset-supervisor.sh` pattern — the onnxruntime-wasm OOB crash ~5–6h into blend>0 runs is a known failure mode and ledger resume self-heals). A final plan fits offsets and updates labels from the ledger. The phase gates on this HUMAN-UAT step.
- D-10: Calibrated values live in a generated TS file. Fit script writes `reports/data` JSON → a generator produces `frontend/src/generated/personaCalibration.ts` (or similar) keyed by `PersonaId`, holding both the retargeted `botElo` and the display label, CI drift-checked — exactly the `botStrengthCurves.ts` pattern. `personaRegistry.ts` consumes it; reruns are mechanical, no hand-transcription.
- D-11: Staleness is a documented policy, not a CI guard. A prominent doc comment in `botStyleBundles.ts` and the generated calibration file: changing style params (or ladder extension) invalidates persona calibration — re-run the sweep. No hash-guard automation.

### Claude's Discretion
- Harness style-wiring details (how `BotStyleParams` flows into the harness's `selectBotMove` call; the harness currently does NOT pass `style` — this is a prerequisite to build).
- Persona-cell schedule design: anchor selection/windowing by measured `INTERNAL_RATING`, games-per-cell split, opening FEN sampling (harness starts mid-opening, so style opening books are structurally outside measurement — accepted, per 182).
- Exact fit approach for per-persona offsets (single-parameter pinned-anchor MLE per cell, reusing `fit_bot_cell_rating`, is the obvious candidate) and internal→blitz conversion reuse (pooled `G_preset` + `BLITZ_OFFSET_C`).
- Retarget mechanics at the edges: the 800 rung clamps to the lookup's lowest available `bot_elo`; how far to trust `beyond_ladder` extrapolated lookup rows.
- Generated-file name/location and generator language (Python vs Node), following the `gen_*` + CI-drift-check convention.
- Popover copy (follows feedback_popover_copy_minimalism, but the disclosure requirements of D-08 override minimalism for this surface, mirroring the percentile-chip precedent).
- What the registry's `rung` field means post-calibration (it stays the grid-position key; `botElo` and label are calibration outputs).

### Deferred Ideas (OUT OF SCOPE)
- Ladder extension above ~1800 / large-animal personas >2000 — SEED-114 (dormant); D-07's global cap is the guard until then.
- Style-bundle retuning workflow (re-tune levers, then re-calibrate) — future work; this phase only documents the staleness policy (D-11).
- Measuring the strength effect of style opening books — structurally outside the harness (mid-opening FEN starts); accepted, not a gap to close here.
- Correction-pass re-measurement of far-off personas — explicitly not budgeted (D-02); revisit only if UAT shows labels wildly off.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CAL-04 | Every persona's labeled ELO is a calibrated ELO measured on the Phase-173 internal anchor scale via the Phase-180 harness (~24 cells × ~4 anchors × ~24 games ≈ 2 overnight runs), with a per-persona offset absorbing the style-induced strength delta | Architecture Patterns (harness style-wiring, persona-cell schedule, fit reuse), Code Examples, Common Pitfalls (persona/botElo collision) |
| CAL-05 | Strength labels honor the honesty constraints — bottom rung acknowledges the ~900 measured floor (both weakest Human cells are `beyond_ladder` extrapolations), top rung capped at 1800 (Deep's measured ceiling) | Architecture Patterns (D-06/D-07 mechanics already present in `bot-strength-lookup.json`), Code Examples (popover pattern) |
</phase_requirements>

## Summary

This phase is a data-pipeline + generated-artifact phase, not a new-feature phase: almost every mechanism it needs (two-pass locate→measure scheduler, resumable per-game ledger, single-parameter pinned-anchor MLE fit, PAVA monotone pooling, JSON→generated-TS codegen with CI drift-check, resume-on-crash supervisor) already exists and was purpose-built by Phases 173/180/181 for exactly this shape of problem. The real engineering surface is narrow: (1) thread `BotStyleParams` into the harness's one `selectBotMove` call (currently omitted — verified at calibration-harness.mjs:565-587), and (2) design a persona-cell schedule that is keyed by **persona identity**, not by `(bot_elo, bot_blend)` as the existing bot-cell schedule is — because after Phase 181 retargeting, **multiple personas collide on identical `(botElo, blend)` pairs** (see Common Pitfalls) while still needing independent measurement to capture the style-induced strength delta that is this phase's entire point.

The retargeting step (D-01) is already computable today with zero new code: `reports/data/bot-strength-lookup.json`'s `derived.<preset>.lookup` maps a target rung directly to a `bot_elo` (e.g. `human.lookup["1200"] = 1900`). The fit step reuses `fit_bot_cell_rating` (scripts/calibration_anchor_fit.py:455-498) unchanged, and the internal→approx-blitz conversion reuses the **already-computed per-preset** `g_preset_combined` values from `bot-strength-lookup.json`'s `components.<preset>.g_preset_combined` (human=40.95, light=186.24, deep=247.18) rather than refitting G per persona — CONTEXT.md's discretion note explicitly says to reuse pooled G, not rating_vs_sf, per persona.

**Primary recommendation:** Extend the harness minimally (add an optional `style` param to the one `selectBotMove` call site + a persona-id-keyed cell/ledger schema), write a NEW persona-cell schedule script mirroring `calibration-bot-cell-schedule.mjs`'s locate→bracket→measure shape but scheduling by persona (not botElo×blend), reuse `fit_bot_cell_rating` + PAVA + the pooled `g_preset_combined`/`BLITZ_OFFSET_C` conversion verbatim from the existing Python fit modules, and follow the `gen_bot_strength_curves.py` → `frontend/src/generated/botStrengthCurves.ts` → CI-drift-check pattern exactly for the new `personaCalibration.ts` artifact.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Harness style-wiring (BotStyleParams → selectBotMove) | Node calibration script (`scripts/`) | Frontend engine (`frontend/src/lib/engine/`, imported via alias hook) | The harness is a thin Node CLI that imports the LIVE `selectBotMove`/`BOT_STYLE_BUNDLES` from the frontend source tree (CAL-02 invariant) — it never reimplements engine logic |
| Persona-cell schedule (locate→bracket→measure, per persona) | Node calibration script (`scripts/lib/`) | — | Pure-logic, engine-free module mirroring `calibration-bot-cell-schedule.mjs`; unit-tested via `.check.mjs` fixtures, no engine/network |
| Overnight sweep execution + crash recovery | Operator-run shell script (`bin/`) | — | Mirrors `bin/preset-supervisor.sh` + `bin/run_bot_curves_sweep.sh`; HUMAN-UAT gated, not CI |
| Per-persona rating fit (Bradley-Terry MLE) + PAVA monotonicity + blitz conversion | Python fit script (`scripts/`) | — | stdlib-only, mirrors `calibration_anchor_fit.py` + `gen_bot_strength_curves.py`; no numpy/scipy (established convention) |
| Generated calibration artifact (`personaCalibration.ts`) | Build-time codegen (Python → TS) | Frontend registry (`frontend/src/lib/personas/personaRegistry.ts`) | Registry consumes calibrated `botElo`/label by `PersonaId`; CI drift-checks the generated file (mirrors `botStrengthCurves.ts`) |
| ELO label rendering (`~950`) | Frontend component (`PersonaCard.tsx`) | — | Currently renders `~${persona.rung}` (PersonaCard.tsx:58) — swaps to the calibrated label |
| Measurement-disclosure popover (D-08) | Frontend component (`PersonaDetailSurface.tsx`) | — | New Radix popover, mirrors `MetricStatPopover`/`PercentileChip` hover/tap shell exactly |

## Standard Stack

No new external dependencies. This phase extends existing in-repo tooling only:

| Component | Location | Purpose | Why reused, not replaced |
|-----------|----------|---------|---------------------------|
| Node calibration harness | `scripts/calibration-harness.mjs` | Bot-vs-anchor game loop, pool-backed, resumable per-game ledger | The bot's move selection MUST stay the live `selectBotMove` call (CAL-02 invariant) — this phase adds a `style` param to that existing call, it does not fork the harness |
| Two-pass scheduler primitives | `scripts/lib/calibration-bot-cell-schedule.mjs` | `internalRatingFor`, `pickLocateAnchors`, `locateEstimate`, `selectMeasureBracket`, `bracketBeyondLadder` | Pure functions, directly reusable for a persona-keyed schedule with no modification — only the caller's grouping key changes |
| Bradley-Terry / MLE fit | `scripts/calibration_anchor_fit.py` (`fit_bot_cell_rating`, `bootstrap_bot_cell_ci`) | Single-parameter pinned-anchor MLE rating fit + bootstrap CI | stdlib-only (`math`/`random`), proven on the exact same problem shape (one unknown-strength cell vs N fixed anchors) |
| PAVA isotonic pooling + JSON→TS codegen | `scripts/gen_bot_strength_curves.py` | Monotone fit, blitz conversion, generated-file emission, `--check` drift mode | Same D-04 monotonicity requirement, same codegen contract |
| Resume-on-crash supervisor | `bin/preset-supervisor.sh`, `bin/run_bot_curves_sweep.sh` | Auto-relaunches `--resume` on the known onnxruntime-web wasm OOB crash (~5-6h into blend>0 runs) | Exact same crash mode applies here (persona cells at Light/Deep blend are the majority of the 24) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Keying persona cells by `(botElo, blend, styleName)` triple | Deduplicating measurement by shared `(botElo, blend)` and only replaying style-specific plies | Rejected: style changes the ENTIRE game trajectory (prior reweighting / score shaping happens every ply), not a late-game branch — there is no valid replay-and-diverge shortcut; every persona needs its own full game set |
| Reusing Phase 181's already-fitted `g_preset_combined` per preset (locked choice, discretion note) | Refitting a fresh per-persona `g_preset` (rating_vs_maia − rating_vs_sf) from the persona-cell's own bracket | Rejected per CONTEXT.md discretion note: a persona cell plays far fewer games against each family (MIN_BRACKET_PER_FAMILY=2, shared across ~24 games) than Phase 180's cells did — a per-persona G refit would carry much wider bootstrap CIs than reusing the already-stable pooled value |

## Package Legitimacy Audit

N/A — this phase installs no new npm, PyPI, or cargo packages. It extends existing in-repo Node scripts and Python stdlib-only tooling (`scripts/calibration-harness.mjs`, `scripts/calibration_anchor_fit.py`, `scripts/gen_bot_strength_curves.py` and its lib modules). No `npm install` / `uv add` is expected as part of this phase's plans.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────┐
│ personaRegistry.ts (24) │  botElo=rung (A1 placeholder), style bundle ref
└──────────┬──────────────┘
           │ D-01: retarget via bot-strength-lookup.json
           ▼
┌──────────────────────────────────────┐
│ Retargeted (persona, botElo, blend,  │  botElo comes from
│ style) — 24 cells, NOT unique on     │  BOT_STRENGTH_LOOKUP[preset][rung]
│ (botElo, blend) alone (COLLISIONS)   │  (clamped at rung 800 → lookup floor)
└──────────┬───────────────────────────┘
           │ persona-cell schedule (NEW, keyed by PersonaId)
           ▼
┌────────────────────────────────────────────────────┐
│ locate pass (2 widest anchors, 8 games each)        │──▶ rough INTERNAL_RATING estimate
│  → selectMeasureBracket (nearest 4, cross-family    │
│    floor 2/2 Maia+SF)                                │
│  → measure pass (extend bracket to ~24 games/anchor)│
└──────────┬───────────────────────────────────────────┘
           │ each bot move: selectBotMove(fen, {elo, blend, style, budget}, ...)
           │                        ▲ NEW: style param (currently omitted)
           ▼
┌──────────────────────────────────────┐
│ Raw per-game ledger (persona-keyed)  │──▶ derived per-(persona,anchor) aggregate TSV
└──────────┬────────────────────────────┘
           │ operator overnight sweep, bin/preset-supervisor.sh (resume-on-crash)
           ▼
┌───────────────────────────────────────────────────────┐
│ Python fit (NEW script, mirrors calibration_anchor_fit)│
│  fit_bot_cell_rating(wins_vs_maia, games_vs_maia, ...) │──▶ rating_vs_maia per persona
│  approx_blitz = rating_vs_maia - g_preset_combined[preset] + BLITZ_OFFSET_C │
│  PAVA-pool WITHIN each style column (D-04) → tie/monotone labels │
│  clamp to global ceiling 1800 (D-07)                    │
└──────────┬──────────────────────────────────────────────┘
           │ gen_persona_calibration.py (mirrors gen_bot_strength_curves.py)
           ▼
┌────────────────────────────────────────┐
│ frontend/src/generated/                │  CI drift-check
│ personaCalibration.ts (NEW)             │  (git diff --exit-code)
└──────────┬───────────────────────────────┘
           │ consumed by PersonaId
           ▼
┌──────────────────────────┐     ┌──────────────────────────────┐
│ personaRegistry.ts       │────▶│ PersonaCard.tsx (~label)     │
│ (botElo + label sourced  │     │ PersonaDetailSurface.tsx     │
│  from generated file)    │     │ (~label + D-08 disclosure    │
└──────────────────────────┘     │  popover, mirrors            │
                                  │  MetricStatPopover/           │
                                  │  PercentileChip)              │
                                  └──────────────────────────────┘
```

### Recommended Project Structure

```
scripts/
├── calibration-harness.mjs                   # EXTEND: add optional style to selectBotMoveOnce (~line 565-587)
├── lib/
│   ├── calibration-persona-cell-schedule.mjs # NEW: mirrors calibration-bot-cell-schedule.mjs, keyed by PersonaId
│   └── calibration-persona-cell-schedule.check.mjs # NEW: pure-logic fixture test, no engine
├── calibration_persona_fit.py                # NEW: mirrors calibration_anchor_fit.py's --bot-input path, but
│                                              #      keyed by persona_id, reusing fit_bot_cell_rating verbatim
└── gen_persona_calibration.py                # NEW: mirrors gen_bot_strength_curves.py's codegen/--check pattern

bin/
├── run_persona_calibration_sweep.sh          # NEW: mirrors run_bot_curves_sweep.sh (parallel launch + combine + fit)
└── preset-supervisor.sh                      # REUSE as-is (already generic over name/blend/elo args)

reports/data/
├── persona-calibration-cells.tsv             # NEW: derived per-(persona,anchor) aggregate (fit input)
└── persona-calibration.json                  # NEW: fitted per-persona offsets + labels (mirrors bot-strength-lookup.json)

frontend/src/generated/
└── personaCalibration.ts                     # NEW: CI-drift-checked, keyed by PersonaId

frontend/src/lib/personas/
└── personaRegistry.ts                        # MODIFY: botElo + label sourced from personaCalibration.ts

frontend/src/components/bots/
├── PersonaCard.tsx                            # MODIFY: swap `~${persona.rung}` for the calibrated label
└── PersonaDetailSurface.tsx                   # MODIFY: add D-08 disclosure popover
```

### Pattern 1: Retargeting via the existing lookup (D-01) — no new inversion math

`reports/data/bot-strength-lookup.json` already contains everything needed to re-seat `botElo`:

```jsonc
// Source: reports/data/bot-strength-lookup.json (verified on disk)
"derived": {
  "human": { "range": {"floor": 900, "ceiling": 1400},
             "lookup": {"900": 1100, "1000": 1100, "1100": 1500, "1200": 1900, "1300": 1900, "1400": 1900} },
  "light": { "range": {"floor": 1500, "ceiling": 1600}, "lookup": {"1500": 1900, "1600": 1900} },
  "deep":  { "range": {"floor": 1600, "ceiling": 1800}, "lookup": {"1600": 1500, "1700": 1500, "1800": 2300} }
}
```

Also generated as `BOT_STRENGTH_LOOKUP`/`BOT_STRENGTH_RANGES` in `frontend/src/generated/botStrengthCurves.ts:9-13` — importable directly from a Node script via the frontend alias hook, exactly like the harness already imports `MAIA_ELO_LADDER`.

Retargeting rule per persona: `botElo = BOT_STRENGTH_LOOKUP[presetNameFor(persona.blend)][String(persona.rung)]`, with the 800 rung (below every preset's floor) clamped to the lookup's lowest key (e.g. human's `"900"` entry, i.e. `botElo = 1100`).

### Pattern 2: Harness style-wiring — the exact seam to extend

```js
// Source: scripts/calibration-harness.mjs:565-587 (current — verified on disk)
const selectBotMoveOnce = async (fen, rng) => {
  const botUci = await selectBotMove(
    fen,
    {
      elo: botElo,
      blend: botBlend,
      budget: { maxNodes, maxPlies, concurrency: FLAWCHESS_BOT_CONCURRENCY, stopRule: FLAWCHESS_BOT_STOP_RULE },
      // style: MISSING — this is the seam Phase 184 must extend
    },
    { policy: providers.policy, grade: providers.grade, rng },
  );
  ...
};
```

`selectBotMove`'s `BotSettings.style?: BotStyleParams` (frontend/src/lib/engine/selectBotMove.ts:92) and `useBotGame.ts`'s identical `BotGameSettings.style?: BotStyleParams` (frontend/src/hooks/useBotGame.ts:194) are the SAME bare, numeric-only shape `BOT_STYLE_BUNDLES[styleName]` resolves to (frontend/src/lib/engine/botStyleBundles.ts:195-200) — the harness needs only to thread `playGame({ ..., style })` down to this one call site. `playGame`'s signature (calibration-harness.mjs:539-552) and every caller in `runCell`/`playCellAnchorGames` need the same additional parameter threaded through.

### Pattern 3: Per-persona rating fit — reuse `fit_bot_cell_rating` unmodified

```python
# Source: scripts/calibration_anchor_fit.py:455-498 (verified on disk) — call unmodified
rating_vs_maia = fit_bot_cell_rating(wins_vs_maia, games_vs_maia, fixed_ratings)
# fixed_ratings = INTERNAL_RATING (scripts/lib/calibration-internal-scale.mjs / anchor-ladder-internal-scale.json),
# the same 10-anchor dict every existing fit call uses — unchanged for this phase.
```

Then convert to approx blitz using the PRESET's already-fitted pooled G (not a per-persona refit — CONTEXT.md discretion note):

```python
# Mirrors scripts/gen_bot_strength_curves.py's approx_blitz_points (D-01: pooled G, never rating_vs_sf)
G = {"human": 40.947876930543565, "light": 186.23527490876148, "deep": 247.17815365881333}  # from bot-strength-lookup.json components.<preset>.g_preset_combined
BLITZ_OFFSET_C = 40
approx_blitz = rating_vs_maia - G[preset_of(persona)] + BLITZ_OFFSET_C
```

Read these three `g_preset_combined` values from `reports/data/bot-strength-lookup.json`'s `components.<preset>.g_preset_combined` at fit time (do not hardcode — that JSON is the canonical, versioned source), rather than transcribing the literals above.

### Pattern 4: PAVA monotone pooling within a style column (D-04)

`scripts/gen_bot_strength_curves.py:109-131`'s `isotonic_fit` (a hand-rolled, stack-of-blocks Pool-Adjacent-Violators implementation, O(n), stdlib-only) is directly reusable: feed it `[(rung, approx_blitz), ...]` **per style, sorted ascending by rung** (not by bot_elo — the ordering axis here is rung, not botElo, since two rungs may already collide on botElo per the pitfall below). This produces pooled/tied labels exactly matching D-04's "ties allowed, never an inversion" contract. Apply the D-07 global ceiling (`min(approx_blitz, 1800)`) AFTER pooling, not before — clamping first would corrupt the monotonicity fit for the rungs below it if a genuine measured value exceeds 1800 mid-column.

### Anti-Patterns to Avoid

- **Keying the persona-cell schedule by `(botElo, blend)`** (mirroring the existing bot-cell schedule verbatim): silently merges distinct personas that share a retargeted `botElo`/`blend` pair (see Common Pitfalls) — the entire point of CAL-04 (style-induced delta) is lost if this happens.
- **Refitting `g_preset` per persona** instead of reusing the pooled per-preset value: CONTEXT.md's discretion note explicitly favors reuse; a persona cell's bracket has too few games per anchor-family to produce a stable independent G.
- **Clamping to 1800 before PAVA pooling**: corrupts the monotonicity fit for lower rungs in the same style column.
- **Running the bare harness driver for the overnight sweep** instead of `bin/preset-supervisor.sh`: the onnxruntime-web wasm OOB crash (~5-6h into a blend>0 preset) will kill an unsupervised run with no auto-resume.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bot-vs-fixed-anchor strength fit | A new logistic-regression / Elo-update loop | `fit_bot_cell_rating` (scripts/calibration_anchor_fit.py:455-498) | Already handles continuity correction, fail-loud validation, and the exact single-parameter-pinned-anchor MLE this problem needs |
| Bootstrap confidence intervals | A new CI method | `bootstrap_bot_cell_ci` (scripts/calibration_anchor_fit.py:592-632) | Parametric multinomial resample + refit, already proven on this exact cell shape |
| Monotone ordering / tie-pooling | A custom smoothing pass | `isotonic_fit` PAVA (scripts/gen_bot_strength_curves.py:109-131) | Hand-rolled, stdlib-only, O(n), exactly matches D-04's "pool the violating neighbors" semantics |
| Resumable durable per-game output | A new checkpoint/resume format | The existing raw-ledger pattern (calibration-harness.mjs:1150-1475, `RAW_LEDGER_COLUMNS`/`openLedgerWriter`/`applyPriorLedgerRows`) | Already solves seeded-PRNG replay, corrupt-ledger detection, and grid-change refusal — a persona axis is an additive column, not a new mechanism |
| Overnight crash recovery | A new supervisor loop | `bin/preset-supervisor.sh` (already generic over `<name> <blend> <elo-csv> [adopt-pid]`) | Directly reusable — pass a persona-sweep name/blend/elo triple per invocation, or extend its `launch()` function to accept a `--style` flag |
| Generated-file drift enforcement | A new hash-guard/checksum mechanism | The `--check` mode + `git diff --exit-code` CI step pattern (gen_bot_strength_curves.py:302-329; ci.yml:60-63) | Proven pattern across 3 generated files already (endgameZones, flawThresholds, botStrengthCurves) |
| Measurement-disclosure popover | A new tooltip/popover component | `MetricStatPopover`/`PercentileChip`'s Radix shell (100ms hover-open, Portal + Content side="top", identical animation classes) | D-08 explicitly names this precedent; `text-xs` is the documented CLAUDE.md exception for this exact component class |

**Key insight:** This phase's engineering risk is almost entirely in *scheduling* (getting the persona axis threaded through correctly without silently merging distinct personas), not in *fitting* or *codegen* — those two are copy-adapt jobs from Phase 180/181's already-hardened code.

## Common Pitfalls

### Pitfall 1: `(botElo, blend)` is NOT a unique key for a persona cell — verified real collisions exist today
**What goes wrong:** If the persona-cell schedule (or its TSV/ledger schema) keys cells by `(bot_elo, bot_blend)` — mirroring the existing bot-cell schedule's `cellKey()` (calibration-harness.mjs:922-924) verbatim — distinct personas with different style bundles will be silently treated as the same cell, and the loop will either double-count games into one accumulator or simply overwrite one persona's result with another's.
**Why it happens:** After D-01 retargeting, `RUNG_BLEND` (personaRegistry.ts:94-101) assigns the SAME preset blend to a rung across ALL 4 styles for rungs 800/1000/1200/1400 (`HUMAN_BLEND`) and 1800 (`DEEP_BLEND`) — and the coarse 100-step lookup collapses multiple rungs to the same `bot_elo` too. Concretely, verified against `bot-strength-lookup.json`:
  - Rung 1800, all 4 styles use `DEEP_BLEND` → `deep.lookup["1800"] = 2300` for every style → **4-way collision** at `(botElo=2300, blend=0.5)`.
  - Rung 1600: attacker/wall use `LIGHT_BLEND` (`light.lookup["1600"] = 1900`), trickster/grinder use `DEEP_BLEND` (`deep.lookup["1600"] = 1500`) → **two 2-way collisions**, `(1900, 0.05)` and `(1500, 0.5)`.
  - Rung 800 (clamped to floor) and rung 1000 both resolve to `human.lookup["900"/"1000"] = 1100` within EVERY style → collisions even within one style's own rung ladder.
**How to avoid:** Key the persona-cell schedule, the ledger schema, and the derived aggregate strictly by `PersonaId` (or an equivalent `(rung, style)` compound key) — never by `(botElo, blend)` alone. The locate/bracket anchor-selection logic can still safely reuse the SAME botElo-derived internal-rating estimate for two colliding personas as a starting point (their true strengths may be genuinely close), but their measured games and final fit MUST be tracked and reported independently.
**Warning signs:** A persona-cell aggregate TSV with fewer than 24 distinct row-groups, or a fit script whose output has fewer than 24 entries.

### Pitfall 2: `internal→approx_blitz` conversion needs `rating_vs_maia` specifically, not a combined bracket fit
**What goes wrong:** Fitting one combined internal rating against the mixed Maia+SF bracket (as `selectMeasureBracket` naturally assembles it) and then subtracting `g_preset_combined` produces a systematically biased approx-blitz number.
**Why it happens:** `g_preset_combined` (and the underlying `G_preset = rating_vs_maia - rating_vs_sf`, calibration_anchor_fit.py:635-666) is defined as the gap between two SEPARATE fits — one using only-Maia-family anchors, one using only-SF-family anchors (`fit_all_bot_cells`, calibration_anchor_fit.py:635-666, "the two families are NEVER merged before fitting"). The Phase 181 conversion formula (`approx_blitz_points`, gen_bot_strength_curves.py:134-145) subtracts `g_preset_combined` from a rating that was itself fit ONLY against Maia anchors.
**How to avoid:** Mirror `fit_all_bot_cells` exactly: fit each persona cell TWICE (once vs its bracket's Maia-family anchors, once vs its SF-family anchors), then use `rating_vs_maia - g_preset_combined[preset] + BLITZ_OFFSET_C` for the label. `rating_vs_sf` per persona is optional telemetry (useful for a sanity `g_preset` sanity-check per persona) but not part of the label formula.
**Warning signs:** Approx-blitz values that land far outside the preset's Phase 181 range (human 900-1400, light 1500-1600, deep 1600-1800) for a persona whose style doesn't plausibly explain that much delta.

### Pitfall 3: The onnxruntime-web wasm OOB crash WILL hit this sweep — it is not optional to guard against
**What goes wrong:** An unsupervised harness run crashes ~5-6h in with `RuntimeError: memory access out of bounds` from Maia policy inference (`nodePolicy` → `InferenceSession.run`), losing all progress since the last completed ledger flush if run without `--resume`.
**Why it happens:** Documented, reproduced failure mode (project memory `project_calibration_harness_wasm_oob_crash`; `bin/preset-supervisor.sh`'s own header comment) specific to long-lived onnxruntime-web wasm processes — a wasm linear-heap fault, not a system RAM issue. Persona cells at Light/Deep blend (14 of 24 personas: all 1600-rung + all 1800-rung + trickster-1600/grinder-1600) are exactly the blend>0 regime that triggers it.
**How to avoid:** Always launch the persona sweep through `bin/preset-supervisor.sh` (or a persona-sweep-specific clone of it), never the bare harness/scheduler script directly. The ledger's append-mode resume (calibration-harness.mjs:1217-1231, `openLedgerWriter`) already makes this safe — the supervisor only needs a correctly-parameterized `launch()` for the persona schedule's CLI shape.
**Warning signs:** A `run.log` showing the harness process exiting without a final `-cells.tsv`/aggregate write.

### Pitfall 4: `bracketBeyondLadder`'s two-sided check can produce a wrong-signed `beyond_ladder` flag if the estimate itself is off due to style
**What goes wrong:** `bracketBeyondLadder` (calibration-bot-cell-schedule.mjs:182-195) flags a cell as beyond the ladder edge based on the LOCATE-pass estimate. If a style shifts a persona's true strength substantially from its retargeted `botElo`'s "vanilla" strength (which is exactly what CAL-04 is measuring), the locate pass's 2-anchor rough estimate could sit near an edge even when the true measured value (after the fuller bracket) is comfortably inside the anchor ladder, or vice versa.
**Why it happens:** The locate pass uses only 2 widely-spaced anchors (`LOCATE_PASS_GAMES = 8` each) — a coarse first look, by design (calibration-bot-cell-schedule.mjs:77-87). This is an accepted tradeoff in the existing bot-cell schedule too, not new to personas, but is worth flagging because D-06's "bottom rung honestly flagged `beyond_ladder`" claim depends on this flag being trustworthy.
**How to avoid:** Treat `beyond_ladder` as advisory (as the existing code already does — "warn-and-proceed, never throw", per the docstring at calibration-bot-cell-schedule.mjs:182-189) and cross-check visually against the final fitted `approx_blitz` value landing outside `[900, 1800]` before writing D-06's floor-acknowledgment copy for a specific persona.
**Warning signs:** A persona flagged `beyond_ladder=true` whose final fitted value lands comfortably mid-range, or vice versa.

### Pitfall 5: Style-opening-book divergence at ply 1 is structurally invisible to this harness (accepted, not a bug to chase)
**What goes wrong:** A plan might try to make the harness start from style-specific opening lines (`styleOpeningLines.ts`/`trollOpenings.ts`) to more faithfully reproduce the shipped bot's book-following behavior.
**Why it happens:** The harness's `OPENING_BOOK` (scripts/lib/calibration-openings.mjs, 33 generic named lines) starts every game mid-opening from a fixed FEN — style opening books only affect the FIRST few plies from the true start position, which the harness never plays. This was already accepted as out-of-scope for Phase 182's calibration compatibility and is reiterated in this phase's Deferred Ideas.
**How to avoid:** Do not attempt to wire style opening books into the harness this phase — it is explicitly deferred. `bookBoost`-driven divergence from the harness's own generic 33-line book is not something this phase's measurement will reflect, and that is fine (it only affects ~2-4 plies out of every game).
**Warning signs:** A plan task proposing to import `styleLinesFor`/`trollOpenings.ts` into the calibration harness.

## Code Examples

### Retarget lookup (Pattern 1 applied to a concrete persona)

```ts
// attacker-1200: style=Attacker, rung=1200, blend=RUNG_BLEND[1200]=HUMAN_BLEND=0
// preset name for blend 0 is "human" (gen_bot_strength_curves.py PRESETS: {0.0: "human", 0.05: "light", 0.5: "deep"})
// BOT_STRENGTH_LOOKUP.human["1200"] = 1900  (frontend/src/generated/botStrengthCurves.ts:10)
// => retargeted botElo = 1900 for EVERY Human-rung-1200 persona regardless of style
```

### Persona cell key (fixes Pitfall 1)

```js
// Mirrors calibration-harness.mjs's cellKey() (line 922-924) but keyed by PersonaId,
// not (botElo, blend) — this is the load-bearing fix.
export function personaCellKey(personaId, anchorLabel) {
  return `${personaId}|${anchorLabel}`;
}
```

### Measurement-disclosure popover shell (D-08, mirrors MetricStatPopover/PercentileChip)

```tsx
// Mirrors frontend/src/components/popovers/MetricStatPopover.tsx (verified pattern:
// 100ms hover-open timeout, Portal + Content side="top" sideOffset={4}, text-xs body)
<PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
  <PopoverPrimitive.Trigger asChild>
    <span role="button" tabIndex={0} data-testid="persona-elo-disclosure" ... >
      <Search className="h-4 w-4" />
    </span>
  </PopoverPrimitive.Trigger>
  <PopoverPrimitive.Portal>
    <PopoverPrimitive.Content side="top" sideOffset={4} className="... text-xs ...">
      {/* D-08 body: measured in bot-vs-engine games on the internal anchor ladder,
          approximate blitz scale. Bottom-rung variant appends the floor note (D-06). */}
    </PopoverPrimitive.Content>
  </PopoverPrimitive.Portal>
</PopoverPrimitive.Root>
```

## State of the Art

| Old Approach (Phase 183, shipped) | Current Approach (this phase) | When Changed | Impact |
|--------------------------------|-------------------------------|---------------|--------|
| `botElo === rung` placeholder (personaRegistry.ts A1 note, lines 14-22) | `botElo` retargeted via Phase-181 lookup, label from actual harness measurement | Phase 184 | Both the engine-facing strength AND the displayed label change; a Human-rung-1400 persona goes from `botElo=1400` (weak, no search) to `botElo≈1900` (the actual strength needed to measure ~1400 approx blitz) |
| Grid label `~${persona.rung}` (raw preset input) | Grid label from `personaCalibration.ts` (measured, rounded to nearest 50, PAVA-pooled, 1800-capped) | Phase 184 | Card/detail-surface rendering swaps data source; no visual/layout change required |

**Deprecated/outdated:** The 183 A1 placeholder documented in `personaRegistry.ts`'s header comment (lines 14-22) is explicitly superseded by this phase — update that doc comment when the registry is modified, don't leave stale A1 prose alongside live calibrated data.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The persona-cell schedule should be keyed by `PersonaId` rather than reusing `(botElo, blend, styleName)` as a compound key | Architecture Patterns / Pitfall 1 | Low — both achieve the same uniqueness guarantee; `PersonaId` is simpler and already exists as a stable identifier in `personaRegistry.ts`, so this is a low-risk recommendation, not a verified requirement |
| A2 | Reusing the Phase-181 pooled `g_preset_combined` per preset (rather than refitting per persona) will produce acceptably tight labels at ~24 games/cell × ~4 anchors | Architecture Patterns Pattern 3 / Alternatives Considered | Medium — this is CONTEXT.md's own discretion-level guidance (not a verified numeric claim); if per-persona style shifts turn out to meaningfully change the TRUE `g_preset` (not just the internal rating), reusing the vanilla-preset G could introduce a small systematic bias in the approx-blitz conversion. The ±100-225 ELO bands already baked into `bot-strength-lookup.json`'s `band` field likely absorb this, but it has not been empirically verified for styled play |
| A3 | The generated-file/generator naming (`personaCalibration.ts` / `gen_persona_calibration.py`) is a reasonable choice | Architecture Patterns / Recommended Project Structure | None — CONTEXT.md D-10 explicitly says "(or similar)" and leaves the exact name to discretion |

**If this table is empty:** N/A — see entries above; none of these are compliance/security/retention-sensitive, all are implementation-detail-level and already flagged as Claude's Discretion in CONTEXT.md.

## Open Questions (RESOLVED)

1. **Does the persona-cell schedule need its own anchor-windowing logic, or can it reuse `calibration-bot-cell-schedule.mjs`'s functions verbatim by just changing the grouping key upstream?**
   - What we know: `internalRatingFor`, `pickLocateAnchors`, `locateEstimate`, `selectMeasureBracket`, `bracketBeyondLadder` are all pure functions that take anchor specs and a rating estimate — nothing in their signatures assumes a `(botElo, blend)` cell identity. They can very likely be imported and reused as-is; only the OUTER loop (`runCell`/`main()`'s grid iteration, and the ledger/aggregate schema) needs to change from `for elo × for blend` to `for personaId`.
   - What's unclear: Whether a NEW `scripts/lib/calibration-persona-cell-schedule.mjs` module is needed at all, or whether `calibration-bot-cell-schedule.mjs` can be imported directly by a new orchestration script with no duplication.
   - Recommendation: Default to importing the existing pure functions directly (no fork), and write only the NEW orchestration/ledger-schema code (persona-keyed grid loop, TSV/ledger columns) as a new file. Confirm at plan time by checking whether the existing functions' fail-loud checks (`internalRatingFor` throwing on an unmeasured anchor label) still make sense unchanged for a persona-driven estimate.
   - **RESOLVED:** Import the existing pure functions directly — no fork. Plan 184-01 Task 2 creates a new `scripts/lib/calibration-persona-cell-schedule.mjs` that imports `internalRatingFor`, `pickLocateAnchors`, `locateEstimate`, `selectMeasureBracket`, and `bracketBeyondLadder` verbatim from `calibration-bot-cell-schedule.mjs`, adding only persona-specific code (PersonaId keying + retargeting lookup). The anchor math is untouched; only the outer grouping key changes.

2. **Games-per-cell: reuse `DEFAULT_GAMES_PER_CELL=20` (harness default) or `24` (the real Phase-180/181 sweep's actual value, per `run_bot_curves_sweep.sh`)?**
   - What we know: The phase description's own budget line ("~24 cells × ~4 anchors × ~24 games") explicitly says 24, matching `bin/run_bot_curves_sweep.sh`'s `GAMES_PER_CELL=24` (not the harness's own CLI default of 20).
   - What's unclear: Nothing significant — this is settled by the phase description itself.
   - Recommendation: Use `--games-per-cell 24` explicitly in the persona sweep's runbook/supervisor invocation, matching the phase's stated budget and the Phase-180/181 precedent, rather than relying on the harness's lower CLI default.
   - **RESOLVED:** Use `--games-per-cell 24` explicitly in the persona sweep runbook/supervisor invocation, matching the phase budget and the Phase-180/181 precedent (not the harness's lower CLI default of 20).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js + `--import` alias hook (`scripts/lib/frontend-alias-hook.mjs`) | Harness execution | ✓ (already used by Phase 180/181 sweeps, proven working) | matches repo `node` | — |
| onnxruntime-web (Maia policy, wasm) | Harness bot moves | ✓ (proven in Phase 180/181 overnight sweeps) | pinned per Phase 174/151 memory | Known crash mode (Pitfall 3) has an established mitigation (supervisor) — not a blocker |
| Stockfish wasm pool (`stockfish-pool.mjs`) | Harness grading/anchors/adjudication | ✓ (proven) | vendored `stockfish-18-lite-single.js` | — |
| Python 3.13 + `uv` (stdlib only: `math`/`random`/`argparse`/`json`) | Fit + codegen scripts | ✓ | project-pinned | — |
| Operator machine capacity for an overnight run (per `run_bot_curves_sweep.sh` preflight: ~(N presets × stockfish-procs) + N Maia cores) | Overnight sweep | Depends on operator's machine at run time — not verifiable from this research session | — | The existing preflight check in `run_bot_curves_sweep.sh` (nproc vs footprint) already warns if oversubscribed; the persona sweep script should include an equivalent preflight |

**Missing dependencies with no fallback:** None identified — this phase reuses proven-working tooling from Phase 180/181, not new infrastructure.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (frontend) | Vitest (`frontend/package.json` `"test": "vitest run"`) |
| Framework (harness pure-logic) | Hand-rolled `.check.mjs` fixture assertions via `node:assert/strict`, run directly with `node --import ./scripts/lib/frontend-alias-hook.mjs <file>.check.mjs` — NOT part of `npm test`/CI automatically; these are manually invoked verification scripts (established convention: `calibration-bot-cell-schedule.check.mjs`, `calibration-anchors.check.mjs`, etc.) |
| Framework (Python fit/codegen) | No pytest — `gen_bot_strength_curves.py` ships its own `--check` drift-detection mode instead of unit tests; the new persona fit/codegen scripts should follow the same convention |
| Config file | `frontend/vite.config.ts` (Vitest config lives there per project convention) |
| Quick run command (frontend) | `npm test -- --run frontend/src/components/bots frontend/src/lib/personas` |
| Full suite command (frontend) | `npm test` (aliases to `vitest run`) |
| Quick check (harness pure-logic) | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-persona-cell-schedule.check.mjs` (NEW file) |
| Drift check (generated file) | `uv run python scripts/gen_persona_calibration.py --check` (NEW script, mirrors gen_bot_strength_curves.py:302-329) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CAL-04 | Persona-cell schedule selects/orders anchors correctly, produces per-persona (not per-botElo/blend) rows, no silent collisions | unit (pure-logic fixture) | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-persona-cell-schedule.check.mjs` | ❌ Wave 0 |
| CAL-04 | Harness's `selectBotMoveOnce` correctly forwards `style` to `selectBotMove` (byte-identical when style is undefined — mirrors the existing STYLE-05 absent-style invariant) | unit (existing determinism check pattern) | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-determinism.check.mjs` (extend) | ✅ (extend existing) |
| CAL-04 | Fit script produces one label per persona, reusing pooled G correctly | unit (Python) | New script's own `--check`/self-test mode, or a small fixture-based assertion mirroring the existing `.check.mjs` convention ported to Python — no pytest precedent for `scripts/` tooling in this repo | ❌ Wave 0 |
| CAL-05 | Bottom rung (800) labeled with floor acknowledgment; top rung (1800) never exceeds 1800 | unit (frontend) | `npm test -- --run frontend/src/lib/personas/__tests__/personaRegistry.test.ts` (extend) | ✅ (extend existing) |
| CAL-05 | Disclosure popover renders on every persona's ELO label in the detail surface | unit (frontend) | `npm test -- --run frontend/src/components/bots/__tests__/PersonaDetailSurface.test.tsx` (extend) | ✅ (extend existing) |
| CAL-04/05 | 24-persona-cell overnight sweep actually completes and produces usable offset data | manual / HUMAN-UAT | operator-run via `bin/preset-supervisor.sh`-style runbook — explicitly gated as HUMAN-UAT per D-09, not automatable | N/A (by design) |

### Sampling Rate
- **Per task commit:** `npm test -- --run frontend/src/components/bots frontend/src/lib/personas` + relevant `.check.mjs` files touched
- **Per wave merge:** `npm test` (full frontend suite) + `uv run python scripts/gen_persona_calibration.py --check` (once it exists) + `git diff --exit-code frontend/src/generated/personaCalibration.ts`
- **Phase gate:** Full frontend suite green + the operator-run overnight sweep (HUMAN-UAT) completed before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `scripts/lib/calibration-persona-cell-schedule.check.mjs` — pure-logic fixture test for the new persona-keyed scheduler (mirrors `calibration-bot-cell-schedule.check.mjs`)
- [ ] A Python-side fixture assertion for the new fit/codegen scripts (no pytest precedent for `scripts/`; follow the existing `--check` drift-mode convention rather than introducing pytest for this one script)
- [ ] Extend `calibration-determinism.check.mjs` to cover the new `style` param's absent-style byte-identical invariant

*(Frontend component tests for PersonaCard/PersonaDetailSurface/personaRegistry already exist and only need extension, not net-new infrastructure.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | This phase touches no auth surface — calibration is a build-time/offline data pipeline and a read-only display change |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A — no new endpoints, no new user-facing mutation |
| V5 Input Validation | Marginal | The new fit/codegen scripts should follow the existing fail-loud discipline (`fit_bot_cell_rating` already throws on malformed/empty input, `load_bot_cells`-style TSV schema validation) — reuse, don't relax |
| V6 Cryptography | No | N/A |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Silently-corrupted or mismatched-schema TSV/ledger fed into the fit script producing plausible-looking but wrong labels | Tampering | Mirror the existing fail-loud validation in `load_bot_cells`/`readPriorLedgerRows`/`readPriorTsvLines` (header-mismatch, truncated-final-line, and duplicate-key checks all throw rather than silently degrading) |
| A persona-cell collision (Pitfall 1) silently overwriting one persona's measured data with another's | Tampering (data integrity, not a security boundary) | The `PersonaId`-keyed schema fix IS the mitigation — this is the single most important correctness safeguard in this phase |

This phase has no network-facing surface, no new user input, and no auth/session changes — it is an offline calibration pipeline plus a read-only label-rendering change on an existing detail surface. The ASVS review here is deliberately thin because there is genuinely little attack surface to review.

## Sources

### Primary (HIGH confidence — read directly from the committed repository)
- `scripts/calibration-harness.mjs` (full file, 1659 lines) — harness structure, `selectBotMoveOnce` seam, ledger/aggregate schema, resume logic
- `scripts/lib/calibration-bot-cell-schedule.mjs` (full file) — two-pass locate→bracket→measure primitives
- `scripts/calibration_anchor_fit.py` (relevant sections, lines 1-60, 455-632, 700-870) — `fit_bot_cell_rating`, `fit_all_bot_cells`, `combine_preset_g_preset`, CLI structure
- `scripts/gen_bot_strength_curves.py` (full file, 334 lines) — PAVA `isotonic_fit`, `approx_blitz_points`, `invert_lookup`, codegen/`--check` pattern
- `reports/data/bot-strength-lookup.json` — verified live lookup values (human/light/deep components + derived lookups + ranges)
- `frontend/src/generated/botStrengthCurves.ts` — verified generated-file shape and header convention
- `frontend/src/lib/personas/personaRegistry.ts` (full file, 461 lines) — A1 placeholder documentation, `RUNG_BLEND` collision source, `PersonaId` type
- `frontend/src/lib/engine/botStyleBundles.ts` (full file) — `BotStyleParams` shape, 4 style bundles
- `frontend/src/lib/playStyle.ts` (full file) — `HUMAN_BLEND`/`LIGHT_BLEND`/`DEEP_BLEND` values
- `frontend/src/components/bots/PersonaCard.tsx` / `PersonaDetailSurface.tsx` (full files) — current label rendering
- `bin/preset-supervisor.sh` / `bin/run_bot_curves_sweep.sh` (full files) — overnight sweep + crash-recovery pattern
- `frontend/src/components/popovers/MetricStatPopover.tsx` / `frontend/src/components/charts/PercentileChip.tsx` — disclosure popover precedent
- `.github/workflows/ci.yml` (lines 40-68) — generated-file CI drift-check convention
- `.planning/phases/184-persona-calibration-strength-honesty/184-CONTEXT.md` — locked decisions and discretion areas
- `.planning/REQUIREMENTS.md` — CAL-04/CAL-05 definitions
- `.planning/STATE.md` — v2.6/v2.7 milestone history and phase sequencing context

### Secondary (MEDIUM confidence)
- None — no external documentation lookup was needed; this phase's entire technical surface is in-repo prior art.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; every reused component read directly from disk
- Architecture: HIGH — the harness seam, lookup table, fit function, and codegen pattern were all read verbatim; the persona-collision finding was independently derived and cross-checked against the live `bot-strength-lookup.json` values
- Pitfalls: HIGH for Pitfalls 1/2/3/5 (directly evidenced in code/docs); MEDIUM for Pitfall 4 (a plausible interaction, not independently reproduced this session)

**Research date:** 2026-07-22
**Valid until:** Effectively unbounded for the harness/fit-reuse patterns (stable, hardened Phase 173/180/181 code); the specific `bot-strength-lookup.json` values and `g_preset_combined` numbers are valid until the next re-run of `gen_bot_strength_curves.py` (D-11: any style/ladder change invalidates them — treat as re-verify-at-plan-time if Phase 180/181 outputs are regenerated before this phase executes).
