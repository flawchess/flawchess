# Phase 184: Persona Calibration & Strength Honesty - Context

**Gathered:** 2026-07-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the 24 personas' provisional `~{rung}` labels with harness-measured calibrated values: extend the Phase-180 calibration harness to accept the Phase-182 style params, re-seat each persona's `botElo` via the Phase-181 lookup so its preset strength targets its rung, run ~2 operator-run overnight sweeps (~24 persona cells × ~4 anchors × ~24 games) on the Phase-173 internal anchor scale, fit per-persona offsets, and surface honest labels (800-floor acknowledgment, global 1800 ceiling) plus a measurement-disclosure popover. Covers CAL-04, CAL-05. Style tuning changes, ladder extension above 1800 (SEED-114), and new personas are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Label semantics (retarget + measure)
- **D-01: Two-step retarget-then-measure.** First re-seat each persona's `botElo` via the Phase-181 lookup (`reports/data/bot-strength-lookup.json` 100-step inversions, per the persona's own preset) so the underlying strength targets the rung (e.g. a Human rung 1400 gets `botElo` ~1900+, not 1400). Then harness-measure each persona cell WITH its style bundle active; the measured value (converted to approx blitz per Phase-181 conventions) becomes the displayed label. This replaces the 183 A1 placeholder (`botElo === rung`) entirely — both `botElo` and the label change.
- **D-02: One-shot measurement.** A single measurement round (~2 overnight runs, matching the SEED-098 budget). Whatever each persona measures is its label; the tilde format absorbs residual error. No correction pass is planned — if a persona lands far off its rung, that is the honest label.

### Ladder coherence
- **D-03: Labels round to nearest 50** (e.g. `~950`, `~1250`). Matches the ±50–100 CI scale without pseudo-precision; keeps 183 D-04's tilde format.
- **D-04: Weak monotonicity within each style column, enforced by CI-pooling.** If a higher rung measures below a lower rung within the same style, pool/nudge the violating neighbors to a shared label (PAVA-style, the same technique Phase 181 used on the preset curves). Ties are allowed — two adjacent rungs may both show `~1600`. Never display an inversion.
- **D-05: Cross-style divergence at the same rung is shown as measured.** attacker-1200 may read `~1150` while wall-1200 reads `~1250`; per-persona offsets are the point of CAL-04. The grid stays organized by rung; only the printed number differs.

### Honesty surfaces (CAL-05)
- **D-06: Bottom rung shows its measured/extrapolated value (~900) like every other persona**, with the floor acknowledgment living in an info popover on the detail surface (not a qualifier on the card). Grid label format stays uniform.
- **D-07: Global ~1800 cap.** No persona label ever exceeds `~1800` (Deep's measured ceiling), regardless of rung. A styled cell measuring above pools down to `~1800`.
- **D-08: Reusable measurement-disclosure popover on every persona's ELO label** in the detail surface (all 24): what the number is (measured in bot-vs-engine games on the internal anchor ladder, approximate blitz scale). Follows the PercentileChip-disclosure convention; the bottom rung's floor note (D-06) is a variant line of this same popover. Popover bodies may use `text-xs` per the frontend exception.

### Run & pipeline
- **D-09: Operator-run overnight sweeps with a committed runbook** (Phase 180 model). The phase ships: harness style-wiring, the 24-persona-cell schedule, and a runbook; the user runs the ~2 overnight sweeps under the resume-on-crash supervisor (`scripts/preset-supervisor.sh` pattern — the onnxruntime-wasm OOB crash ~5–6h into blend>0 runs is a known failure mode and ledger resume self-heals). A final plan fits offsets and updates labels from the ledger. The phase gates on this HUMAN-UAT step.
- **D-10: Calibrated values live in a generated TS file.** Fit script writes `reports/data` JSON → a generator produces `frontend/src/generated/personaCalibration.ts` (or similar) keyed by `PersonaId`, holding both the retargeted `botElo` and the display label, CI drift-checked — exactly the `botStrengthCurves.ts` pattern. `personaRegistry.ts` consumes it; reruns are mechanical, no hand-transcription.
- **D-11: Staleness is a documented policy, not a CI guard.** A prominent doc comment in `botStyleBundles.ts` and the generated calibration file: changing style params (or ladder extension) invalidates persona calibration — re-run the sweep. No hash-guard automation.

### Claude's Discretion
- Harness style-wiring details (how `BotStyleParams` flows into the harness's `selectBotMove` call; the harness currently does NOT pass `style` — this is a prerequisite to build).
- Persona-cell schedule design: anchor selection/windowing by measured `INTERNAL_RATING`, games-per-cell split, opening FEN sampling (harness starts mid-opening, so style opening books are structurally outside measurement — accepted, per 182).
- Exact fit approach for per-persona offsets (single-parameter pinned-anchor MLE per cell, reusing `fit_bot_cell_rating`, is the obvious candidate) and internal→blitz conversion reuse (pooled `G_preset` + `BLITZ_OFFSET_C`).
- Retarget mechanics at the edges: the 800 rung clamps to the lookup's lowest available `bot_elo`; how far to trust `beyond_ladder` extrapolated lookup rows.
- Generated-file name/location and generator language (Python vs Node), following the `gen_*` + CI-drift-check convention.
- Popover copy (follows feedback_popover_copy_minimalism, but the disclosure requirements of D-08 override minimalism for this surface, mirroring the percentile-chip precedent).
- What the registry's `rung` field means post-calibration (it stays the grid-position key; `botElo` and label are calibration outputs).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone & requirements
- `.planning/seeds/SEED-098-bot-personas-playstyle-layer.md` — calibration strategy (§"Calibration strategy": ~24 cells × ~4 anchors × ~24 games ≈ 2 overnight runs), strength-honesty constraints (§"Strength-honesty constraints"), per-persona offset rationale
- `.planning/REQUIREMENTS.md` — CAL-04, CAL-05 definitions
- `.planning/phases/183-persona-registry-bots-page/183-CONTEXT.md` — D-04 tilde format (kept, number swapped), registry decisions this phase amends
- `.planning/phases/182-style-levers/182-CONTEXT.md` — D-11 (strength deltas deferred to this phase), harness-compatibility note (mid-opening FENs put books outside calibration)

### Calibration machinery (Phase 173/180/181 output this phase drives)
- `scripts/calibration-harness.mjs` — the Phase-180 two-pass locate→bracket→measure cell loop + resumable ledger; its `selectBotMoveOnce` (~line 565) builds `BotSettings` WITHOUT `style` — the seam this phase must extend
- `scripts/lib/calibration-bot-cell-schedule.mjs` — the bot-cell scheduling module the persona-cell schedule extends/mirrors
- `scripts/preset-supervisor.sh` + `scripts/run_bot_curves_sweep.sh` — resume-on-crash supervisor pattern for long blend>0 sweeps (wasm OOB crash mode)
- `scripts/gen_bot_strength_curves.py` — Phase-181 fit/codegen pipeline (PAVA pooling, `G_preset` + `BLITZ_OFFSET_C` conversion, CI drift-check) to reuse/mirror
- `reports/data/bot-strength-lookup.json` — the 100-step blitz→bot_elo inversions per preset used for retargeting (D-01); `extrapolated_bot_elos` flags mark `beyond_ladder` rows
- `reports/data/anchor-ladder-internal-scale.json` — Phase-173 anchor `INTERNAL_RATING` scale for anchor windowing
- `frontend/src/generated/botStrengthCurves.ts` — the generated-TS + CI-drift-check convention D-10 follows

### Persona & style code (what gets recalibrated)
- `frontend/src/lib/personas/personaRegistry.ts` — the 24-slot registry; header A1 note documents the provisional `botElo === rung` this phase replaces; `botElo` and label become calibration-fed
- `frontend/src/lib/engine/botStyleBundles.ts` — the 4 style bundles measured per persona; gains the D-11 staleness note
- `frontend/src/lib/playStyle.ts` — `HUMAN_BLEND`/`LIGHT_BLEND`/`DEEP_BLEND` per-persona presets the harness cells pin
- `frontend/src/components/bots/PersonaCard.tsx` — renders `` `~${persona.rung}` `` today (line ~58); switches to the calibrated label
- `frontend/src/components/bots/PersonaDetailSurface.tsx` — detail surface gaining the D-08 disclosure popover

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `calibration-harness.mjs` two-pass cell loop + resumable per-game ledger: the persona sweep is "the same harness, 24 new cells with style params" — no new game-loop machinery.
- `fit_bot_cell_rating` (single-parameter pinned-anchor MLE from Phase 180): per-persona offset fitting is the same shape — one rating per cell against anchors of known `INTERNAL_RATING`.
- Phase-181 `gen_bot_strength_curves.py`: PAVA pooling code (reuse for D-04 monotonicity), internal→blitz conversion, and the JSON→generated-TS→CI-drift-check pipeline.
- `bot-strength-lookup.json`: purpose-built for D-01 retargeting — no new inversion math needed.
- Info-popover components (`MetricStatPopover` family, PercentileChip disclosure precedent): the D-08 popover follows this pattern; `text-xs` allowed in popover bodies.

### Established Patterns
- Generated frontend files from Python/Node sources with CI drift checks (`scripts/gen_*.py` → `frontend/src/generated/*`); re-run generator after editing the source registry.
- Operator-run overnight sweeps as HUMAN-UAT-gated phase steps with committed runbooks (Phase 180 pilot → operator approval → full sweep; Phase 181 confirmation-run runbook inside the prediction JSON).
- Tunables as named exported constants with tuning-rationale docstrings.
- Registry docstring-per-entry convention (`personaRegistry.ts`): calibration provenance should be traceable per persona (generated file keyed by `PersonaId` + registry doc pointer), never silent number edits.

### Integration Points
- `calibration-harness.mjs` `selectBotMoveOnce`: add optional style params to the `BotSettings` it passes to the live `selectBotMove` (styled cells) while unstyled runs stay byte-identical (Phase 182 D-03 absent-style invariant doubles as the harness regression guard).
- `personaRegistry.ts` ← `frontend/src/generated/personaCalibration.ts`: registry entries read retargeted `botElo` + display label from the generated file by `PersonaId`; `rung` stays the structural grid key.
- `PersonaCard.tsx` / `PersonaDetailSurface.tsx`: swap `~${rung}` for the calibrated label; add the D-08 popover in the detail surface (card stays clean).
- Snapshot/resume (`botGameSnapshot.ts` persona id): resumed games re-resolve persona config from the registry, so retargeted `botElo` flows automatically — verify no snapshot stores a stale raw `botElo` that would fight the recalibrated registry.

</code_context>

<specifics>
## Specific Ideas

- The Human preset's compression is the reason retargeting matters: `botElo` 1400 at blend 0 measures only ~1050–1100 approx blitz, so label-only calibration would collapse four Human rungs into ~920–~1060.
- Label examples under the decided format: `~950`, `~1250`, ties like two rungs both at `~1600`, bottom rung `~900`, ceiling `~1800`.
- The wasm OOB crash memory: blend>0 presets crash ~5–6h in (onnxruntime-web wasm heap, not system RAM); ledger append-mode resume self-heals; always run the sweep under the supervisor, never the bare driver.

</specifics>

<deferred>
## Deferred Ideas

- Ladder extension above ~1800 / large-animal personas >2000 — SEED-114 (dormant); D-07's global cap is the guard until then.
- Style-bundle retuning workflow (re-tune levers, then re-calibrate) — future work; this phase only documents the staleness policy (D-11).
- Measuring the strength effect of style opening books — structurally outside the harness (mid-opening FEN starts); accepted, not a gap to close here.
- Correction-pass re-measurement of far-off personas — explicitly not budgeted (D-02); revisit only if UAT shows labels wildly off.

### Reviewed Todos (not folded)
- `172-deferred-review-findings` — analysis-page gem-sweep review findings; unrelated (keyword-noise match, same verdict as Phases 182/183).
- `2026-03-11-bitboard-storage-for-partial-position-queries` — DB storage idea; unrelated.
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label` — chart label bug; unrelated to persona calibration.

</deferred>

---

*Phase: 184-Persona Calibration & Strength Honesty*
*Context gathered: 2026-07-22*
