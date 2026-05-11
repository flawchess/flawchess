---
phase: 83
plan: 04
status: complete
completed: 2026-05-11
---

# 83-04 SUMMARY — entry_expected_score benchmark calibration

## Outcome

- New cohort zone band locked into Python registry and code-generated to the frontend.
- All `verify` checks pass; codegen is idempotent (CI drift gate green).

## Locked band

```python
"entry_expected_score": ZoneSpec(
    typical_lower=0.45,
    typical_upper=0.55,
    direction="higher_is_better",
)
```

Operator chose **[0.45, 0.55]** over the strict pooled IQR **[0.4629, 0.5536]**. Rationale:
- Round numbers (easy to communicate, debug, and override).
- Very close to pooled IQR (delta < 0.01 on both sides).
- Visual parity with `endgame_score` (§0 final-score) ZoneSpec which uses the identical [0.45, 0.55] band — the new bullet sits adjacent to the §0 tile on the Endgame Start vs End section, and matching bands give a single consistent "neutral chess fairness" reference across both rows.

Per memory `feedback_zone_band_judgement.md`: band alignment with the neighbouring tile preferred over asymmetric +1pp drift from strict IQR.

## Collapse verdict

| Axis | max \|d\| | Pair | Verdict |
|------|---------:|------|---------|
| TC   | 0.218    | bullet vs rapid | review |
| ELO  | 0.224    | 800 vs 2000     | review |

Both axes < 0.5 → **single global zone** justified. Per-ELO stratification deferred per CONTEXT.md "Deferred Ideas". Re-evaluate if a future snapshot's ELO d ≥ 0.5.

## Sanity checks

- Equal-footing filter: pooled mean = 0.5094 (+0.94 pp from 50% baseline). Within ±1 pp tolerance ✓ (§0 reads +1.2 pp on the same population — equal-footing filter is working consistently).
- Pooled IQR width = 0.0907 (≈ 9 pp). No editorial tightening needed (contrast with Phase 82 entry_eval_pawns where ±0.75 was tightened to ±0.50 because pawn-unit IQR was 1.31 wide).

## Files modified

- `.claude/skills/benchmarks/SKILL.md` — new Section 7 with canonical CTE (selected_users / endgame_game_ids / entry_rows / rows / per_user / per_user_excl_sparse) for entry_expected_score
- `reports/benchmarks-2026-05-11.md` — Section 5 with 5×4 cell table, TC + ELO marginals, pooled overall, recommendations, collapse verdict, heatmap, "Currently set in code" filled in
- `app/services/endgame_zones.py` — new `entry_expected_score` ZoneSpec, MetricId Literal entry
- `scripts/gen_endgame_zones_ts.py` — emits ENTRY_EXPECTED_SCORE_NEUTRAL_MIN/MAX + entryExpectedScoreZoneColor; theme import hoisted to top of generated file
- `frontend/src/generated/endgameZones.ts` — regenerated (idempotent: second `python scripts/gen_endgame_zones_ts.py` produces zero diff)
- `tests/services/test_endgame_zones.py` — TestRegistrySanity updated to include `entry_expected_score`

## Canonical SKILL.md CTE shape (Section 7)

Per-game `expected_score` from the first endgame-class ply (`ROW_NUMBER() OVER (PARTITION BY game_id ORDER BY ply ASC) = 1`):

```sql
CASE
  WHEN entry_eval_mate IS NOT NULL AND (entry_eval_mate * color_sign) > 0 THEN 1.0
  WHEN entry_eval_mate IS NOT NULL AND (entry_eval_mate * color_sign) < 0 THEN 0.0
  WHEN entry_eval_cp IS NOT NULL AND abs(entry_eval_cp) < 2000
       THEN 1.0 / (1.0 + exp(-0.00368208 * (entry_eval_cp * color_sign)))
  ELSE NULL
END
```

Per-user aggregation: `avg(expected_score)` over endgame-reaching games, ≥20 game floor, equal-footing-filtered, `bic.status='completed'`, `(2400, classical)` sparse cell excluded from marginals/pooled stats.

## Verification

| Check | Result |
|-------|--------|
| `uv run pytest tests/services/test_endgame_zones.py` | 41 passed |
| `uv run ty check app/services/endgame_zones.py tests/services/test_endgame_zones.py` | clean |
| `uv run ruff check app/services/endgame_zones.py tests/services/test_endgame_zones.py scripts/gen_endgame_zones_ts.py` | clean |
| `uv run python scripts/gen_endgame_zones_ts.py` (run twice) | byte-for-byte identical (idempotent) |
| `grep -c '"entry_expected_score"' app/services/endgame_zones.py` | 2 (Literal + ZoneSpec entry) |
| `grep -c "entryExpectedScoreZoneColor\|ENTRY_EXPECTED_SCORE_NEUTRAL_MIN\|ENTRY_EXPECTED_SCORE_NEUTRAL_MAX" frontend/src/generated/endgameZones.ts` | 5 |
| `test -f reports/benchmarks-2026-05-11.md` | exists |
| `grep -c "Section 7\|Stockfish-baseline expected score at endgame entry" .claude/skills/benchmarks/SKILL.md` | ≥1 |
| `grep -c "bic.status" .claude/skills/benchmarks/SKILL.md` | 12 |

## Commits

- `fc202cbe` docs(83-04): add entry_expected_score benchmark calibration (SKILL.md Section 7 + report)
- `88c461f6` feat(83-04): register entry_expected_score zone band [0.45, 0.55] (Python + codegen + tests)

## Plan 3 + Plan 5 unblocked

- Plan 3 (83-03 frontend tile 1 grid): can import `entryExpectedScoreZoneColor`, `ENTRY_EXPECTED_SCORE_NEUTRAL_MIN`, `ENTRY_EXPECTED_SCORE_NEUTRAL_MAX` from `@/generated/endgameZones`.
- Plan 5 (83-05 LLM prompt awareness): can call `assign_zone("entry_expected_score", value)` from `app.services.endgame_zones`.
