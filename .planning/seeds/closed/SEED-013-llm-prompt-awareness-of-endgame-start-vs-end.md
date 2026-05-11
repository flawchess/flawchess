---
id: SEED-013
status: closed
planted: 2026-05-10
closed: 2026-05-11
planted_during: /gsd-explore session after Phase 81 ("Endgame Start vs End — twin-tile section above the WDL table") shipped
trigger_when: ready to start a follow-up phase (Phase 82) on Endgame Insights LLM coverage; the two new tiles are in production but the LLM narration is unaware of them
scope: phase (single, ~5 plans) — /benchmarks extension + zone bake-in + findings emission + prompt update + (optional) tile-rule amendment
closed_by: superseded — entry_eval / endgame_score were wired into the LLM prompt directly (see commit eebcc7cd bumping `_PROMPT_VERSION` to `endgame_v24` and recent endgame_insights.md updates). Per feedback_llm_significance_signal, the planned `verdict` field was rejected in favor of tightening cohort bands; follow-up work now lives in SEED-014 / SEED-015.
---

# SEED-013: LLM prompt awareness of "Where you start" / "What you do with it" (Phase 81 follow-up)

## Why This Matters

Phase 81 added two tiles above the Endgame WDL table:

- **"Where you start"** — `entry_eval_mean_pawns`, signed Stockfish eval at endgame entry, sig-tested against 0
- **"What you do with it"** — absolute `endgame_score` (W=1/D=0.5/L=0), Wilson-tested against 50%

The phase was scoped as **purely additive UI** (decisions D-01..D-19 in `.planning/phases/81-endgame-start-vs-end-twin-tile-section-above-the-wdl-table/81-CONTEXT.md`). The LLM narration path was deliberately out of scope. As a result:

- `app/services/insights_service.py` emits **no findings** for either metric.
- `app/prompts/endgame_insights.md` has **no glossary entries** and no `### Subsection: endgame_start_vs_end` block.
- Grep for `entry_eval_mean_pawns`, `endgame_score_p_value`, "where you start", "what you do" across `app/services/insights_*.py` and `app/prompts/` returns **zero** matches.

The motivating example: user 28 in production has `entry_eval = +0.46 pawns (p = 0.000)` and `endgame_score = 46.6% (p = 0.000)`. With p<0.001 on both, this is a striking pattern — they arrive at endgames slightly ahead but score below break-even from there. The LLM-narrated "Endgame Insights" section currently cannot mention any of this because the data never reaches the prompt. The pattern is also likely paired with the time-pressure section (poor clock management converting "ahead" into "below 50%"), which the LLM **could** narrate as a causal story if it had the upstream data.

This is the natural follow-up to Phase 81: same conceptual surface, same data, but wire it through the insights pipeline so the LLM can narrate it alongside Conversion / Parity / Recovery and the score-gap timeline.

## When to Surface

Trigger any of:

1. The user asks "why does the LLM not mention the new tiles?" or notices the gap (already happened — see /gsd-explore session 2026-05-10).
2. A user reports a striking entry-eval / endgame-score pattern that the LLM ignored.
3. Roadmap planning for the Endgame Insights v2 milestone — this slots cleanly after Phase 81.
4. Before any further endgame-narration tweaks (otherwise we keep iterating on a prompt that is missing 1/3 of the visible Endgame Overall Performance section).

## Phase 82 Scope (six plans)

### Plan 1 — Extend `/benchmarks` SKILL.md with two new sections

Add `### N. Endgame entry eval (per-user)` and `### N+1. Endgame score (per-user)` to `.claude/skills/benchmarks/SKILL.md`, mirroring the existing pattern (Sections 1, 2a–d, 4a–b):

- Canonical CTE per the skill (lichess_username join, `bic.status='completed'`, `g.time_control_bucket::text = bsu.tc_bucket`, equal-footing filter `abs(opp_rating - user_rating) <= 100`, sparse-cell exclusion).
- **Entry eval**: per-user mean of signed `eval_cp` at the first endgame ply, mate excluded, `|eval_cp| < 2000` excluded (matches production filter `has_continuous_in_domain_eval`), per-game dedup at the bucket-rows grain (mirrors `app/repositories/endgame_repository.py` lines 793–841 and `app/services/endgame_service.py` lines 1670–1712).
- **Endgame score**: per-user `(W + 0.5*D) / total` over endgame games (≥6 plies in `endgame_class IS NOT NULL`).
- Sample floor: ≥20 endgame-entry-eval games per user for the eval metric; ≥20 endgame games per user for the score metric.
- Cell tables (5×4, sparse cell footnoted), TC marginal, ELO marginal, pooled, Cohen's d collapse verdicts, recommendations table.

### Plan 2 — Run /benchmarks; produce timestamped report

Run the extended skill, write `reports/benchmarks-YYYY-MM-DD.md` with the two new sections appended in their canonical position (between Section 2 "Conversion / Parity / Recovery" and Section 3 "Evals at game phase transitions" feels right — it fits the "endgame overall performance" family). The exploratory query in this seed (see "Provisional findings" below) is **not** a substitute — formal Cohen's d, full cell tables, and locked-in band recommendations come from running /benchmarks.

### Plan 3 — Bake bands into `endgame_zones.py` (Python) + regenerate `endgameZones.ts` (TS)

Add two new zone registries to `app/services/endgame_zones.py`:

- `ENDGAME_ENTRY_EVAL_ZONES` — almost certainly a single global zone (provisional collapse verdicts: TC review d≈0.21, ELO review d≈0.25). Exact `lo`/`hi` from /benchmarks pooled p25/p75 (provisionally `[-0.5, +0.8]` pawns; symmetrize or keep asymmetric based on the report's `|p25|` vs `|p75|` rounding rule).
- `ENDGAME_SCORE_ZONES` — provisionally needs **per-ELO** stratification (ELO max d≈0.88, same family as the existing `ENDGAME_SKILL_ZONES` which is also per-ELO). Verify with formal Cohen's d before locking; if /benchmarks confirms, mirror the `PER_ELO_GAUGE_ZONES` dispatch pattern.

After updating the Python registry, run `uv run python scripts/gen_endgame_zones_ts.py` to refresh `frontend/src/generated/endgameZones.ts` (CI fails on drift — see `CLAUDE.md` "Scripts" section).

### Plan 4 — Findings emission in `insights_service.py`

Add a new subsection `endgame_start_vs_end` and two finding generators:

- `_findings_endgame_entry_eval(window, response)` — emits one `SubsectionFinding` per window with `metric="entry_eval_pawns"`, value = `entry_eval_mean_pawns`, `zone=` from `ENDGAME_ENTRY_EVAL_ZONES`, plus a new `verdict=above_null|null|below_null` field driven by `entry_eval_p_value < 0.05` and the sign of the value. n gate: `entry_eval_n >= 10` (matches D-11 wire-format gate).
- `_findings_endgame_score(window, response)` — same shape, value = `endgame_wdl.win_pct/100 + 0.5*draw_pct/100`, sig test against 50% via `endgame_score_p_value`. ELO-aware zone dispatch if Plan 3 lands per-ELO bands.

The `verdict` field is **new** — it carries the sig-test outcome that `zone` (cohort-band) cannot capture. The pair `(zone=typical, verdict=above_null)` with high n is exactly the user-28 pattern: cohort says "ordinary", sig test says "very confident this is non-zero". The LLM combines them.

Wire both into `_compute_section_findings` with `subsection_id = "endgame_start_vs_end"`. Order: entry_eval first, endgame_score second (chronological: setup → execution, matches the UI mobile stacking order from D-17).

### Plan 5 — Prompt update in `app/prompts/endgame_insights.md`

- Add glossary entries for `entry_eval_pawns` and `endgame_start_vs_end_score` (or rename for the prompt — `endgame_score` would collide with the existing score_timeline `endgame_score` metric; pick a unique key, e.g. `eg_absolute_score`). Each entry: definition, units, sign convention, the cohort band's typical range (cited from the new /benchmarks report), and the sig-vs-null `verdict` semantics.
- Add a new `### Subsection: endgame_start_vs_end` block explaining the two-metric pair as a "setup → execution" diagnostic. Crucial: tell the LLM that `verdict=above_null` / `verdict=below_null` with `zone=typical` means "high-confidence small effect — pair with cross-section signals (time pressure, opponent strength) for the causal story". Without this guidance the LLM will skip these findings as cohort-typical.
- Bump `_PROMPT_VERSION` in `app/services/insights_llm.py` to a new tag (e.g. `endgame_v23`) with a one-line changelog entry following the existing pattern.

### Plan 6 — Phase 81 D-09 tile-rule amendment (optional, small UI follow-up)

Phase 81 D-09 locked tile color as `sig positive → green / null → neutral / sig negative → red`. With cohort bands now available, the cleaner rule is `(value in green/red band) AND p < 0.05`:

- Effect size + confidence both required.
- UI tile and LLM `zone` field stay coherent.
- Borderline cases (user 28: +0.46 inside typical, p<0.001) correctly read as **neutral on the tile**, while the LLM still narrates them via the `verdict` field.

Estimate: ~1 plan (frontend `EndgameStartVsEnd` component or wherever the tile color logic lives + theme constants pull). Could ship as part of Phase 82 or as a separate quick follow-up. If split, mark it as a /gsd-quick task — the change is genuinely trivial once the bands are in `endgameZones.ts`.

## Provisional Findings (from 2026-05-10 /gsd-explore exploratory query)

**Methodology**: canonical CTE per `/benchmarks` SKILL.md (lichess_username join — **NOT** `benchmark_user_id`, which only catches ~30% of completed users), `bic.status='completed'`, sparse `(2400, classical)` excluded, equal-footing `|opp_rating - user_rating| <= 100`, mate excluded, `|eval_cp| < 2000`, `g.rated AND NOT g.is_computer_game`, `g.time_control_bucket::text = bsu.tc_bucket`. Sample floor: per-user `entry_eval_n >= 20` and `endgame_n >= 20`.

**Pooled distributions (n≈1,750 users)**:

| metric | mean | SD | p05 | p10 | p25 | p50 | p75 | p90 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| entry_eval (pawns) | +0.13 | 1.19 | -1.83 | -1.28 | **-0.52** | +0.13 | **+0.78** | +1.49 | +2.08 |
| endgame_score | 0.5123 | 0.079 | 0.393 | 0.420 | **0.463** | 0.509 | **0.558** | 0.611 | 0.644 |

Means align with the live report's §3 residual benchmark-user skill edge (`+4.15` cp at MG entry → ~`+0.04` pawns; entry_eval at EG entry sits a touch higher as expected). The endgame_score population mean of 51.2% (slightly above 50%) confirms the D-08 fixed null is correctly placed.

**Marginals — provisional collapse verdicts (eyeball Cohen's d, formal calc deferred to /benchmarks)**:

| metric | TC max d | ELO max d | Verdict |
|---|---:|---:|---|
| entry_eval | ~0.21 (bullet vs rapid) | ~0.25 (800 vs 2000) | review / review → single global zone |
| endgame_score | ~0.25 | **~0.88 (800 vs 2400)** | review / **keep separate** → per-ELO bands |

The endgame_score ELO ramp is monotonic (800: 0.480 → 2400: 0.546, +6.6pp) and mirrors the live `ENDGAME_SKILL_ZONES` family (max d=0.78, "keep separate"). Plan 3's per-ELO `ENDGAME_SCORE_ZONES` is almost certainly the right call — confirm with formal Cohen's d in Plan 2.

**User-28 placement against provisional bands**:

| | value | vs typical band (provisional) | vs fixed null |
|---|---:|---|---|
| entry eval | +0.46 | inside typical (between p50=+0.13 and p75=+0.78) | sig positive (p<0.001) |
| endgame score | 46.6% | borderline — just inside p25=46.3% (per-ELO band may move this) | sig negative vs 50% (p<0.001) |

This is exactly the "cohort-typical + high-confidence-non-null" pattern that the new `verdict` field is designed to surface. With `zone=` alone the LLM would skip both findings. With `verdict=` it has license to narrate them.

## Methodology Lessons (capture before they evaporate)

- **The canonical join is `lichess_username`, not `benchmark_user_id`.** The skill's CTE template uses `bic.lichess_username = bsu.lichess_username` because `bic.benchmark_user_id` is sparsely populated (~30% coverage in the current benchmark DB state). Joining via `benchmark_user_id` silently undercounts users by ~3×. A spike query that bypasses the canonical CTE will produce wrong distributions and wrong population means. **Always copy the canonical CTE verbatim** — do not paraphrase the join.
- **The equal-footing filter is mandatory.** Without `abs(opp_rating - user_rating) <= 100`, the population mean drifts toward whatever rating-asymmetry the dump happens to have. The benchmark report applies this filter universally to §1, §2, §4, §5, §6.
- **The production eval filter is `mate excluded AND |eval_cp| < 2000`.** Both bounds matter — without the `|cp| < 2000` clip a single mate-in-12 game (eval ≈ -2900) shifts a per-user mean by ~0.3 pawns at n=10.
- **When testing zone semantics on a new metric, start with the pooled IQR.** Running the per-cell breakdown without a pooled sanity check first is how the broken join above went undetected for two messages.

## Open Decisions (defer until Phase 82 starts)

- Whether to use `Sequence[str]` or a `Literal` discriminator for the new `verdict` field on `SubsectionFinding`. Lean `Literal["above_null", "null", "below_null"]` for ty compliance.
- Tile-color rule amendment (Plan 6) — ship in same phase or split as /gsd-quick? Lean split, since Plan 6 is a frontend-only, ~30-line change once `endgameZones.ts` carries the bands.
- Naming: `endgame_score` collides with the existing `score_timeline` metric `endgame_score`. Pick a non-clashing key for findings emission and the prompt glossary (e.g. `eg_absolute_score`, `endgame_overall_score`, or qualify by subsection in the prompt). Verify by grepping `endgame_score` in `insights_llm.py` and `endgame_insights.md` before settling.
- Whether to extend the `endgame-concepts` accordion in `frontend/src/pages/Endgames.tsx` with a third paragraph clarifying the difference between "tile says neutral" and "LLM mentions the metric anyway" — likely yes if Plan 6 ships, since users will ask.

## Estimated Effort

5 plans (or 6 if Plan 6 lands in-phase). Plans 1–2 are in /benchmarks territory (~half a day each), Plan 3 is mechanical (~2 hours), Plans 4–5 are the substantive work (~half a day each), Plan 6 is trivial (~1 hour). Comparable in shape to Phase 81 itself.

## Cross-references

- Phase 81 artifacts: `.planning/phases/81-endgame-start-vs-end-twin-tile-section-above-the-wdl-table/` (especially `81-CONTEXT.md` for D-01..D-19, `81-VERIFICATION.md` for the shipped state)
- /benchmarks skill: `.claude/skills/benchmarks/SKILL.md`
- Latest benchmark report: `reports/benchmarks-2026-05-04.md`
- Schema fields added in Phase 81: `app/schemas/endgames.py:124-140`
- Zones registry: `app/services/endgame_zones.py` (Python) → `frontend/src/generated/endgameZones.ts` (auto-generated)
- Existing prompt: `app/prompts/endgame_insights.md`, prompt-version pin in `app/services/insights_llm.py:66`
- Related seeds: SEED-002 (benchmark-db population baselines — predecessor that established this whole pattern), SEED-006 (benchmark population zone recalibration — sister activity)
