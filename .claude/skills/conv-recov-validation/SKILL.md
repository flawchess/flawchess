---
name: conv-recov-validation
description: Validate the FlawChess conversion/recovery proxy (material imbalance ≥100 cp with 4-ply persistence) against Stockfish engine eval as ground truth, on the benchmark DB. Produces a focused two-section report mirroring the Endgames page UI: (1) whole-game Endgame Metrics agreement and (2) per-endgame-type span agreement. Each section reports eval coverage and a proxy ↔ Stockfish agreement table. Use this skill whenever the user asks about validating the conversion/recovery thresholds, validating the 4-ply persistence rule, comparing material imbalance vs Stockfish eval, "is t=100 still the right threshold", "does persistence actually help", "how close is our proxy to engine ground truth", or wants an updated proxy validation report. Trigger on phrases like "conv/recov validation", "conversion recovery validation", "validate threshold", "validate persistence", "material vs stockfish", "material vs eval", "proxy validation", "100 centipawn threshold", "4-ply persistence", "endgame threshold report", "engine eval validation". Writes a timestamped markdown report to reports/conv-recov-validation-YYYY-MM-DD.md.
---

# Conversion / Recovery Validation

Validate that the **t=100 centipawn + 4-ply persistence** material-imbalance proxy (live in `_compute_score_gap_material` / `_endgame_skill_from_bucket_rows`) agrees with Stockfish engine evaluation on the benchmark DB.

The report has exactly two sections, mirroring the Endgames page:

1. **Conversion, Parity & Recovery** — whole-game Endgame Metrics. One row per game; the game's *first* qualifying endgame class is the entry sequence.
2. **Conversion & Recovery by Endgame Type** — per-class spans. A single game can contribute multiple rows (one per endgame class it traverses).

Both sections have the same shape: an eval coverage subsection, then a proxy ↔ Stockfish agreement subsection.

## Out of scope

- Threshold sweeps (t=50/150/300). t=100 was chosen for coverage; this skill validates it, not re-derives it.
- Persistence-window comparison (5-ply / 6-ply). Settled in the legacy report.
- Per-user distribution / gauge zone calibration. Lives in the `benchmarks` skill.

## Target

- **Benchmark DB only** (`mcp__flawchess-benchmark-db__query`). Stockfish ground truth requires `eval_cp`, which only the benchmark DB has at meaningful coverage.
- Docker on `localhost:5433`. If `docker compose -p flawchess-benchmark ps` shows nothing, run `bin/benchmark_db.sh start` first.
- One statement per MCP call (no `;`-separated multi-statements).

## Methodology lifted from the `benchmarks` skill

Read `.claude/skills/benchmarks/SKILL.md` if you need the full justification.

### Canonical `selected_users` CTE — non-optional

The `bic.status='completed'` filter is mandatory — `benchmark_selected_users` is the candidate *pool*, and skipping the filter pulls in zero-game users.

```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.rating_bucket, bsu.tc_bucket
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
)
```

Then JOIN `selected_users su ON su.user_id = g.user_id` and filter `g.time_control_bucket::text = su.tc_bucket`. The `::text` cast is required (enum vs varchar).

### Sparse-cell exclusion

The `(rating_bucket=2400, tc_bucket='classical')` cell is structurally undersampled (~12 completed users) and **must be excluded** from every aggregation:

```sql
WHERE NOT (su.rating_bucket = 2400 AND su.tc_bucket = 'classical')
```

### Base game filters

`g.rated AND NOT g.is_computer_game`. Do not apply `opponent_strength` or `recency` — population stats are unconstrained by per-user UI filters.

### Persistence approximation

The 4-ply persistence check uses `position at entry_ply + 4` (same `endgame_class`). The live backend uses an `array_agg` contiguity check that is slightly stricter — small systematic difference that doesn't move the headline numbers. Surface this caveat in the report header.

### Eval columns

`game_positions.eval_cp` (smallint, white-perspective). Apply `eval_cp * color_sign` for user-perspective. `eval_mate` exists but mate-only positions are a small minority and usually have `eval_cp` too — this report filters on `eval_cp IS NOT NULL`.

## Live-threshold grep

Before running, grep these constants from `app/services/endgame_service.py` and record literal values in the report header:

| Constant | Variable to look for |
|---|---|
| Material threshold | `_MATERIAL_ADVANTAGE_THRESHOLD` (expect 100) |
| Persistence ply | search for `+ 4` near the material check |
| Endgame ply minimum | `ENDGAME_PLY_THRESHOLD` (expect 6) |

Use the Grep tool, not bash.

## Agreement definitions

User-perspective. `imb` = `material_imbalance * color_sign`, `eval` = `eval_cp * color_sign`.

**Proxy classification** (uses both entry and entry+4):
- Conversion: `entry_imb >= 100 AND after_imb >= 100`
- Recovery: `entry_imb <= -100 AND after_imb <= -100`
- Parity: NOT conversion AND NOT recovery

**Eval classification** (entry only — eval already factors compensation, no persistence needed):
- Conversion: `entry_eval >= 100`
- Recovery: `entry_eval <= -100`
- Parity: `entry_eval BETWEEN -99 AND 99`

**Agreement %** = among rows where proxy = X, fraction where eval = X.

**Missed by proxy** = rows where eval classifies as conversion or recovery but proxy didn't fire (proxy = parity or proxy = the *opposite* class). Reported on the eval-available subset. Parity rows do not have a meaningful "missed by proxy" count — leave the cell blank.

## Section 1 — Conversion, Parity & Recovery (Endgame Metrics)

**Whole-game first-endgame.** One row per game. The game's earliest qualifying endgame class (≥6 plies) is the entry sequence. Mirrors the live Endgame Metrics gauges.

### Section 1 CTE backbone

```sql
WITH selected_users AS ( /* canonical */ ),
class_span AS (
  SELECT game_id, endgame_class, min(ply) AS entry_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id, endgame_class
  HAVING count(*) >= 6
),
first_endgame AS (
  SELECT DISTINCT ON (game_id) game_id, endgame_class, entry_ply
  FROM class_span
  ORDER BY game_id, entry_ply
),
entries AS (
  SELECT
    g.id AS game_id,
    CASE WHEN g.user_color='white' THEN 1 ELSE -1 END AS color_sign,
    ep.material_imbalance AS entry_imb_raw,
    ep.eval_cp            AS entry_eval_raw,
    ap.material_imbalance AS after_imb_raw,
    ap.eval_cp            AS after_eval_raw
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN first_endgame fe  ON fe.game_id = g.id
  JOIN game_positions ep ON ep.game_id = g.id AND ep.ply = fe.entry_ply
  LEFT JOIN game_positions ap
    ON ap.game_id = g.id AND ap.ply = fe.entry_ply + 4
   AND ap.endgame_class = fe.endgame_class
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    AND NOT (su.rating_bucket = 2400 AND su.tc_bucket = 'classical')
)
```

Wrap user-perspective in the SELECT (or in a final view CTE):
`entry_imb = entry_imb_raw * color_sign`, etc.

### 1.1 Stockfish eval coverage

Report:
- Total qualifying games
- Games with `entry_eval IS NOT NULL`
- Games with `entry_eval IS NOT NULL AND after_eval IS NOT NULL`
- Coverage % for both

### 1.2 Proxy ↔ Stockfish agreement

Filter to rows with `entry_eval IS NOT NULL AND after_eval IS NOT NULL` (so proxy and eval are compared on the same population). Output:

| Class       | Sequences | Agreement % | Avg eval @ entry (cp) | Missed by proxy |
|-------------|-----------|-------------|-----------------------|-----------------|
| Conversion  | n         | %           | mean (signed)         | n               |
| Parity      | n         | %           | mean (signed)         | —               |
| Recovery    | n         | %           | mean (signed)         | n               |

- "Sequences" = rows classified as that class **by the proxy**.
- "Agreement %" = fraction of those proxy-X rows where eval also = X.
- "Avg eval @ entry" = mean of `entry_eval` (signed, user-perspective) over the proxy-X rows.
- "Missed by proxy" = on the *full* eval-available subset, count rows where eval = X but proxy ≠ X. Conversion and recovery only.

## Section 2 — Conversion & Recovery by Endgame Type

**Per-class spans.** Same as Section 1 but the `entries` CTE joins `class_span` directly (not `first_endgame`), so a game contributes one row per endgame class it traverses.

### Section 2 CTE backbone

Same as Section 1 except replace `JOIN first_endgame fe ON fe.game_id = g.id` with `JOIN class_span cs ON cs.game_id = g.id` and use `cs.entry_ply` / `cs.endgame_class` throughout.

### 2.1 Stockfish eval coverage (per class)

Per `endgame_class` ∈ {rook, minor_piece, pawn, queen, mixed, pawnless}:
- Total spans
- Spans with `entry_eval IS NOT NULL`
- Spans with both `entry_eval` and `after_eval` non-null
- Coverage %

### 2.2 Proxy ↔ Stockfish agreement (per class)

Two tables, conversion and recovery, columns by endgame class. Same four metrics as 1.2: sequences, agreement %, avg eval @ entry, missed by proxy.

```
Conversion:
| Metric            | rook | minor_piece | pawn | queen | mixed | pawnless |
| Spans (proxy=conv)| ...  |             |      |       |       |          |
| Agreement %       | ...  |             |      |       |       |          |
| Avg eval @ entry  | ...  |             |      |       |       |          |
| Missed by proxy   | ...  |             |      |       |       |          |

Recovery:
(same shape)
```

Parity row is omitted in Section 2 — the per-type breakdown is about asymmetry between conv and recov.

## Section 3 — Verdict

A short call on whether the live proxy is fit-for-purpose, derived mechanically from the Section 1 and Section 2 numbers. No new queries — synthesis only.

### Pawnless is hidden from the UI — ignore it in the rubric

`frontend/src/pages/Endgames.tsx` defines `HIDDEN_ENDGAME_CLASSES = new Set(['pawnless'])`, and the LLM-insights pipeline drops pawnless findings (`app/services/insights_llm.py` ~ line 572 and ~ line 1573). Pawnless conv/recov is **never user-visible** in the live product — it appears in this validation report only because the SQL aggregates every class for completeness.

For the verdict, treat pawnless agreement as informational only. It does not affect PASS / PASS WITH CAVEATS / REVISIT. Mention the pawnless number in the verdict body so future readers can see why we don't surface it, but do not let it drive the headline.

### Decision rubric

Apply these thresholds to the agreement numbers already computed (pawnless excluded from every gate):

- **PASS** — both whole-game conv and recov agreement ≥ 80%, and every UI-visible per-class agreement (rook, minor_piece, pawn, queen, mixed) ≥ 70%. Proxy is fit for live UI; no action needed.
- **PASS WITH CAVEATS** — whole-game ≥ 75%, but at least one UI-visible per-class agreement falls between 60-70%. Proxy is fit for the aggregate gauges; that class warrants a footnote in the UI or LLM prompt.
- **REVISIT** — whole-game agreement < 75% on either conv or recov, OR two or more UI-visible classes (rook/minor_piece/pawn/queen/mixed) below 70%. Threshold or persistence rule should be reconsidered.

### Verdict section content

Write a `## 3. Verdict` section to the report with:

1. One-line headline (PASS / PASS WITH CAVEATS / REVISIT) with the rubric tag.
2. 2-4 bullets covering: aggregate pass/fail, per-class outliers, the parity caveat (proxy parity ≠ eval parity is structural, not a bug), and any recommended UI / LLM-prompt footnotes.
3. No action items beyond what the rubric directly implies. If the verdict is PASS, do not invent follow-ups.

## Report file layout

Write to `reports/conv-recov-validation-YYYY-MM-DD.md` (UTC date). Layout:

```markdown
# Conversion / Recovery Validation — <DATE>

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: <ISO timestamp>
- **Population**: <N_users> completed users / <N_games> rated non-computer games
- **Sparse-cell exclusion**: `(2400, classical)` excluded from all aggregations
- **Persistence approximation**: SQL uses `entry_ply + 4` with same-class join; backend uses array_agg contiguity (small systematic difference)
- **Currently set in code** (per `app/services/endgame_service.py`): `_MATERIAL_ADVANTAGE_THRESHOLD` = <value>, persistence = <value> plies, `ENDGAME_PLY_THRESHOLD` = <value>
- **Agreement definitions**: proxy uses material imbalance with 4-ply persistence; eval uses entry-only (eval already factors compensation, no persistence needed)

## 1. Conversion, Parity & Recovery (Endgame Metrics)

Whole-game first-endgame entry. One row per game.

### 1.1 Stockfish eval coverage
... (totals + coverage %)

### 1.2 Proxy ↔ Stockfish agreement
... (4-column table: Sequences / Agreement % / Avg eval / Missed by proxy)

## 2. Conversion & Recovery by Endgame Type

Per-class spans. Multiple rows per game possible.

### 2.1 Stockfish eval coverage (per class)
... (per-class totals + coverage %)

### 2.2 Proxy ↔ Stockfish agreement (per class)
... (two tables, conv + recov, columns by endgame class)

## 3. Verdict
... (one-line headline + 2-4 bullets, derived from the rubric in Section 3)
```

## Re-running

If today's file already exists and the user asks for a section subset, replace only those sections; preserve the header. If the user asks for a fresh snapshot, write to today's file; never mutate prior dates.

## Workflow

1. **Pre-flight**: confirm benchmark DB is up (`docker compose -p flawchess-benchmark ps`); start with `bin/benchmark_db.sh start` if needed.
2. **Live-threshold grep**: record current values from `app/services/endgame_service.py`.
3. **Run Section 1** — two MCP queries (coverage + agreement). Write Section 1 to the report.
4. **Run Section 2** — two MCP queries (coverage + agreement). Write Section 2 to the report.
5. **Apply the Section 3 rubric** to the numbers from Sections 1 and 2 (no new queries) and write the verdict to the report.
6. **Done.** No per-user distribution, no threshold sweep. The agreement numbers and the verdict are the deliverable.
