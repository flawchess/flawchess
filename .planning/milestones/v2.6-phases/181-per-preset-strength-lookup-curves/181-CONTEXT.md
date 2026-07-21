# Phase 181: Per-preset strength lookup curves - Context

**Gathered:** 2026-07-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn the landed Phase-180 sweep output (`reports/data/bot-curves-internal-scale.json`: 15
measured cells across Human/Light/Deep with per-cell `rating_vs_maia` / `rating_vs_sf` /
`g_preset` and per-preset pooled `G`: Human ≈ +41, Light ≈ +186, Deep ≈ +247) into the shipping
strength artifact:

1. Monotone fit `internal_rating = f_preset(bot_elo)` per preset over the ~5 measured points.
2. Convert to approximate human blitz ELO via `internal − G_preset + C` (C = +40 ± 100, shared
   named constant).
3. Invert into per-preset `target_blitz_elo → bot_elo` lookups in 100-ELO steps with honest
   per-preset ranges (the measured floor/ceiling IS the slider range).
4. Ship the artifact as a lookup JSON plus a **generated TS module** in
   `frontend/src/generated/` (via the existing `scripts/gen_*.py` pattern), including the
   canonical approximate-ELO disclaimer string.
5. Write a **prediction file** for 2–3 confirmation cells per preset; the confirmation run
   itself is an operator-run HUMAN-UAT step (mirrors Phase 180 D-01 split delivery).

Single source of truth for all future labeled bot strength claims (custom bot builder, preset
cards, SEED-098 personas). **No UI, API, schema, or shipped-bot (`selectBotMove`) change.**

**Out of scope:**
- Any UI/slider wiring on `/bots` (builder, preset cards, personas — future phases).
- New strength measurement beyond the confirmation cells (no low-end floor probing, no
  ladder extension above 1900 — SEED-114).
- Re-running or modifying the Phase-180 sweep/fit pipeline upstream of its JSON output.
</domain>

<decisions>
## Implementation Decisions

### Rating basis & offset math
- **D-01:** Fit `f_preset` on the **`rating_vs_maia`** points, then subtract the **per-preset
  pooled `G_preset`** (`per_preset[blend].g_preset_combined`: ≈41 / 186 / 247) and add `C`.
  Matches the SEED-104 formula literally; pooling G over 5 cells smooths the noisy per-cell
  style gap (per-cell G swings 61–313 for Light). Do NOT use per-cell G or `rating_vs_sf`
  directly, and do not average the two families.
- **D-02:** **Components + derived** artifact: the lookup JSON stores the internal fit values,
  `G_preset`, and `C` separately AND the derived blitz lookup. `C` is a named constant in the
  generator script, so retuning C (e.g. ±100 → ±50 after future human data) is a one-line
  change + regenerate — no refit.
- **D-03:** Uncertainty is one **blanket ± band per preset** (dominated by C's ±100 plus
  typical fit CI), stored as a constant. No per-entry CI in the lookup (false precision), but
  a numeric band must exist (not just the word "approximate").

### Artifact shape & boundary
- **D-04:** Deliverable = lookup JSON in `reports/data/` **AND** a generated TS module in
  `frontend/src/generated/` via the `gen_*.py` → committed-file → CI-drift-check pattern.
  No consumer imports it yet: add a **knip exception** until the first consumer phase lands.
  No UI wiring in this phase.
- **D-05:** **New gen script** (`scripts/gen_bot_strength_curves*.py`) reads
  `reports/data/bot-curves-internal-scale.json` (the Phase-180 fit output stays frozen
  upstream), does monotone fit + offset conversion + inversion, and emits both the lookup JSON
  and the generated TS. Do NOT extend `calibration_anchor_fit.py` with artifact stages — clean
  seam between measurement and shipping artifact.
- **D-06:** The **canonical user-facing approximate-ELO disclaimer string is written in this
  phase**, shipped as an exported constant in the generated TS module (and mirrored in the
  JSON), so every future surface imports the same copy.

### Plateaus & honest ranges
- **D-07:** **Isotonic (monotone) fit; lowest-`bot_elo`-wins inversion.** A target ELO landing
  on a flat segment maps to the LOWEST `bot_elo` reaching that strength; each preset's ceiling
  is its plateau value. Never claim a higher setting buys strength it doesn't (Deep's measured
  plateau ≈1950–2100 internal → roughly ~1850–1900 approx-blitz ceiling, NOT the seed's hoped
  ~2600). No smoothed/spline slope invented inside measured plateaus.
- **D-08:** **Keep the `beyond_ladder` Human cells (bot_elo 700, 1100) in the fit and lookup,
  flagged as extrapolated** in the artifact, so Human's floor reaches down to ~900 approx-blitz
  (the product wants genuinely weak bots). Researcher must verify why bot_elo 1100 carries the
  flag at all (the validated Maia-3 band is 1100–2000; 1100 being flagged looks like a boundary
  or flag-logic quirk).
- **D-09:** **Accept the measured Light/Deep floors as the slider floors** (~1450–1580
  approx-blitz at bot_elo 1100 — higher than hoped). No extra low-end measurement in this
  phase; note the narrower-than-hoped style-choice overlap zone (~1450–1900) in the findings.
- **D-10:** **Round range endpoints inward** to 100-ELO steps: floor rounded UP to the next
  100, ceiling rounded DOWN. Only offer targets fully inside the measured curve.

### Confirmation-cell protocol
- **D-11:** **Split delivery (mirrors 180 D-01):** the phase completes when the gen pipeline,
  artifact, and a **written prediction file** (confirmation cells + expected internal ratings +
  their pass bands) land. The confirmation run is an **operator-run HUMAN-UAT** step; the
  findings note closes the loop afterward.
- **D-12:** Confirmation cells are **off-grid predictions**: invert at chosen target ELOs and
  run the PREDICTED `bot_elo` values (generally between measured grid points — a true test of
  the shipped inversion). Include one target near each range endpoint plus one mid-range,
  2–3 per preset; planner picks exact values.
- **D-13:** **Pass criterion:** the cell's measured internal rating (vs-Maia, same basis as
  the fit) falls within the fit's interpolated **95% CI** at that `bot_elo`, as computed by the
  gen pipeline and recorded in the prediction file.
- **D-14:** **On failure: refit + regenerate.** Fold the confirmation games into the fit
  dataset, re-run the gen pipeline, regenerate the lookup + TS artifact, and document the shift
  in the findings note. No hand-tuning, no band-widening to paper over a miss.

### Claude's Discretion
- Exact confirmation-cell target values (D-12), the isotonic-fit implementation details
  (scipy vs hand-rolled PAVA — note `calibration_anchor_fit.py` is stdlib-only), TS module /
  JSON naming, and the prediction-file format are planner/researcher calls.
- The blanket band value per preset (D-03) is derived from C's ±100 + observed fit CI widths —
  researcher proposes the exact numbers.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source seed & measured data (the inputs)
- `.planning/seeds/SEED-104-iso-strength-inversion-table.md` — the phase spec: offset model
  `human_blitz = internal − G_preset + C`, C = +40 ± 100 rationale, Option-A honest ranges,
  method steps, consumer architecture. Authoritative.
- `reports/data/bot-curves-internal-scale.json` — the landed Phase-180 sweep output this phase
  consumes: 15 cells (`rating_vs_maia`/`rating_vs_sf`/CIs/`g_preset`/`beyond_ladder`) +
  `per_preset[blend].g_preset_combined`. THE input; treat as frozen.
- `scripts/lib/calibration-internal-scale.mjs` — the `INTERNAL_RATING` anchor table (GENERATED;
  `maia1500 == 1500` pin — the scale's zero-point).

### Phase-180 foundation (methodology + machinery for confirmation cells)
- `.planning/phases/180-three-preset-bot-strength-curves/180-CONTEXT.md` — upstream decisions
  (D-01 split delivery precedent, D-06 fit artifact shape, locked blend values {0, 0.05, 0.5}).
- `.planning/notes/2026-07-15-anchor-ladder-self-calibration-findings.md` — internal-scale
  methodology, ~2.8x compression verdict, Finding 4 (cross-family style residuals; sf0/maia700
  style-outlier caveat).
- `scripts/calibration-harness.mjs` — the harness the operator confirmation run uses
  (internal-scale two-pass cell loop, `--resume`, raw-ledger).
- `scripts/calibration_anchor_fit.py` — the Bradley-Terry/Elo fitter that produced the input
  JSON (`fit_bot_cell_rating` + `g_preset`); reference for CI conventions, NOT to be extended.
- `reports/data/preset-supervisor.sh` — resume-on-crash supervisor for long runs (wasm OOB
  crash ~5–6h in on blend>0 presets; ledger resume self-heals).

### Repo patterns to follow
- `scripts/gen_endgame_zones_ts.py` / `scripts/gen_flaw_thresholds_ts.py` — the established
  `gen_*.py` → `frontend/src/generated/*` pattern (CI fails on drift) the new gen script must
  follow.
- `frontend/src/lib/maiaEncoding.ts` — Maia-3 validated ELO band (1100–2000) referenced by the
  `beyond_ladder` flag (D-08 verification).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `reports/data/bot-curves-internal-scale.json` already carries everything the gen script
  needs: per-cell ratings both families, CIs, per-cell G, `beyond_ladder` flags, and pooled
  per-preset G. No new measurement needed to build the artifact.
- `scripts/gen_*.py` pattern: generator writes a committed TS file; CI drift check ensures the
  artifact can't silently diverge from its Python source.
- `scripts/calibration-harness.mjs` + `reports/data/preset-supervisor.sh`: the operator
  confirmation run is a plain harness invocation at the predicted `bot_elo`/blend cells — no
  new run machinery expected.
- `calibration_anchor_fit.py` is stdlib-only Python; if the isotonic fit follows suit
  (hand-rolled PAVA is ~20 lines), the gen script needs no new dependencies.

### Established Patterns
- Split delivery for long engine runs (180 D-01): interactive phase ends at proven machinery +
  prediction file; overnight runs are operator-run HUMAN-UAT.
- Findings note as the human-readable deliverable (`2026-07-15-anchor-ladder-...` is the
  template); the confirmation-run findings note closes this phase's loop.
- Named constants for every tunable (C, band values, step size) — no magic numbers.
- knip runs in CI: the generated TS module needs an explicit exception until its first
  consumer phase lands (D-04).

### Integration Points
- Downstream consumers (future phases): custom bot builder preset toggle + per-preset slider,
  preset cards, SEED-098 personas — all read the generated TS module. Nothing imports it yet.
- The raw uncalibrated `bot_elo` + `blend` slider surface makes no strength promise and does
  NOT consume these curves (SEED-104's explicit boundary).

</code_context>

<specifics>
## Specific Ideas

- The identity `rating_vs_maia − per-cell G = rating_vs_sf` means D-01's choice (pooled G) is
  exactly what distinguishes it from "use vs_sf" — the printed ELO differs by
  (per-cell G − pooled G) per cell. This is deliberate: pooled G is the de-noised estimate.
- Measured curve realities to carry into the findings note: Light is non-monotone
  (bot_elo 1100 → 1639 vs 1300 → 1513 internal vs-Maia), Deep dips at 2600 (2064 < 2118 at
  2300) and plateaus ≈1950–2100 internal; Human tops out ≈1474 internal at bot_elo 2300.
- "Deep is a ceiling, not a different feel" (from 180): don't market Deep as "deeper" —
  Light/Deep differ only in sampling temperature.

</specifics>

<deferred>
## Deferred Ideas

- **Ceiling extension above ~1900 approx-blitz** — Deep's measured plateau is far below the
  seed's hoped ~2600; already captured as `SEED-114-stronger-bots-above-1900-ladder-extension`.
- **Probing Light/Deep floors below bot_elo 1100** — explicitly not pursued (D-09 accepts
  measured floors); could become a seed if the narrow overlap zone hurts the product later.
- **Custom bot builder / preset cards / SEED-098 personas** — the consumer surfaces; future
  phases reading this phase's generated TS module.

### Reviewed Todos (not folded)
- `172-deferred-review-findings` (pending todo) — frontend gem-sweep review warnings from
  Phase 172; keyword match only, unrelated to calibration lookup curves.
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label` — frontend Tailwind class fix,
  unrelated.

</deferred>

---

*Phase: 181-per-preset-strength-lookup-curves*
*Context gathered: 2026-07-21*
