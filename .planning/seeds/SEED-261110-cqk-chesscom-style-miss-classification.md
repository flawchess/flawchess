---
id: SEED-261110-cqk
status: dormant
planted: 2026-11-10
planted_during: post-Phase 248 chat (comparing game_flaws.is_miss against chess.com Game Review)
trigger_when: a phase touches move-quality glyphs (MoveQualityIcon / severityGlyph / boardMarkers) or the flaw tag taxonomy, or the owner asks for a chess.com-style "Miss" badge
scope: medium (one phase: backend classifier + stored column/backfill + glyph + filter wiring)
---

# SEED-261110-cqk: chess.com-style Miss classification (✕ glyph)

## Why This Matters

Users coming from chess.com expect a **Miss** badge (red circle, white ✕): "the opponent handed you something and you didn't take it". We already have `game_flaws.is_miss`, but it is a pure timing rule ("this M/B immediately follows an opponent M/B", `flaws_service._is_miss`). Compared with chess.com on real games it is far too broad to drive a glyph: putting ✕ on every `is_miss` row would relabel ~35% of all blunders (dev DB: 35.0% of blunders, 22.2% of mistakes carry `is_miss`).

Keep `is_miss` as the existing "miss" filter tag. This seed is a **separate, tighter classification** that drives the glyph.

## Evidence (2026-11-10, owner's chess.com games, prod user 28)

Method: chess.com Game Review (Analysis tab, annotation SVG `<g id=...>`; chess.com's internal id for Miss is `incorrect`) vs prod `game_positions.eval_cp` + `game_flaws` for 9 games. Both players' moves are compared.

**Ply convention gotcha:** `game_flaws.ply` / `game_positions.ply` is the 0-based half-move index (white moves are EVEN), and the row's `eval_cp` is the eval AFTER that row's move. chess.com ply = our ply + 1.

| Result | Count |
|---|---|
| chess.com Misses | 12 |
| … that carry our `is_miss` | 9 (recall 75%) |
| Our `is_miss` rows | 25 |
| … that are chess.com Misses | 9 (precision 36%) |

Our false positives (16) fall into three patterns:

1. **Mover was already lost (4):** the opponent's "error" took them from lost to more lost (e.g. −8 → mate). chess.com: inaccuracy or fine.
2. **Mover still crushing (5):** mate-in-N → +6.5 and similar. chess.com: fine or inaccuracy. (This is also a severity disagreement: we call these M/B.)
3. **Chains (3):** in an error → error → error run, chess.com labels only the first reply a Miss. The next move is a plain blunder or mistake. A Miss never follows a Miss.

The rest are severity disagreements (chess.com said inaccuracy) or one-offs.

Our false negatives (3):
- 2 rows are not flaws for us at all: about a 1-pawn drop while ahead after an opponent mistake (+1.65 → +0.60, +1.89 → +0.78). chess.com Miss isn't gated on mistake severity.
- 1 blunder isn't tagged because the opponent's previous move was only an inaccuracy (`_is_miss` requires M/B).

Raw sample (our ply, mover-POV eval before → after, chess.com label):

| game_id | ply | eval | ours | chess.com |
|---|---|---|---|---|
| 3237990 | 12 | +2.17 → −1.67 | B, miss | **Miss** |
| 3237990 | 13 | +1.67 → −2.25 | B, miss | Blunder (after a Miss) |
| 3237991 | 52 | +1.65 → +0.60 | none | **Miss** |
| 3237991 | 58 | +7.85 → +4.15 | M, miss | **Miss** |
| 3237991 | 83–86 | mate shuffles at ±9 | M, miss ×4 | inaccuracy / fine |
| 3237992 | 24 | +1.89 → +0.78 | none | **Miss** |
| 3237992 | 31 | +0.44 → −0.69 | M, miss | Inaccuracy |
| 3237992 | 34 | +1.23 → −2.70 | B (no miss) | **Miss** |
| 3238004 | 42 | −0.36 → −3.83 | B, miss | Mistake |
| 3238004 | 43 | +3.83 → +0.59 | B, miss | **Miss** |
| 3238004 | 44 | −0.59 → −2.97 | B, miss | Blunder (after a Miss) |
| 3252403 | 31 | +0.90 → −1.32 | B, miss | **Miss** |
| 3252403 | 46 | +2.77 → −0.03 | B, miss | Blunder |
| 3252403 | 47 | +0.03 → −3.16 | B, miss | **Miss** |
| 3252403 | 51 | 0.00 → −1.40 | M, miss | **Miss** |
| 3252404 | 58 | M4 → +7.41 | M, miss | **Miss** |
| 3252404 | 91 / 92 | −7.29 → mated / M13 → +6.44 | M / B, miss | fine / inaccuracy |
| 3252405 | 30 / 48 | M7 → +6.52 / M4 → +8.09 | B / M, miss | fine |
| 3252405 | 49 | −8.09 → mated | M, miss | Inaccuracy |
| 3252405 | 50 | M7 → +3.70 | B, miss | **Miss** |
| 3252405 | 51 | −3.70 → −12.72 | B, miss | Mistake (after a Miss) |
| 3252406 | 8 | +1.49 → −0.39 | B, miss | **Miss** |
| 3252407 | 34 | +4.62 → +2.89 | M, miss | Inaccuracy |

chess.com game URLs: `platform_url` on these `games` rows.

## Rule that fits the samples

A move is a **Miss** when all of these hold:

1. **Opponent erred on the previous ply, and that move wasn't itself a Miss** (anti-chaining; this is recursive, so classify in ply order). chess.com also accepts an inaccuracy as the gift: one Miss followed an opponent inaccuracy.
2. **The gift left the mover at least equal:** the mover's best-move expected score at their turn is ≥ 0.5. This separates 3238004/42 (−0.36, chess.com: Mistake) from 3252403/47 and /51 (≈0.00, chess.com: Miss). The margin is thin.
3. **The move gave a meaningful part of it back,** without leaving the mover still crushing (score after the move stays below ~0.9). This excludes the mate-shuffle rows.

Re-scored on the same sample: about **70% precision / 58% recall** (vs 36% / 75% today).

**Exact parity is not reachable:** chess.com uses its own engine and evals. 3252403/46 and /47 have near-identical shapes in our evals yet are labelled Blunder vs Miss, and the M4/M7 rows split Miss vs fine inconsistently. Tune for "feels right", not parity.

## Open Decisions

- **Severity floor.** `game_flaws` is M+B only (inaccuracies never stored), so the 2 inaccuracy-sized chess.com Misses can't be represented without a schema change. Recommendation: accept the M+B floor for v1.
- **Inaccuracy as the gift.** Loosening criterion 1 from M/B to "≥ INACCURACY_DROP" catches 3237992/34 but adds false positives. Decide on a larger sample.
- **Glyph precedence.** On chess.com, Miss replaces the severity glyph. Proposal: ✕ replaces "?"/"??" on the board marker and in the move list, and the severity stays in the tooltip ("Miss (blunder)").
- **Storage.** Either add a new boolean `is_chesscom_miss` (or rename the concept, e.g. `is_missed_chance`) with a backfill from stored evals (no engine needed, since criteria 1–3 read `game_positions.eval_cp` + `missed_pv_lines[0]`), or compute it at query time.
- **Validation sample.** Re-run the comparison on 30+ games across several users and rating bands before locking thresholds. Use the same scrape method.

## Breadcrumbs

- Current rule: `app/services/flaws_service.py` `_is_miss` (~L923), called from `_build_tags`. Thresholds `INACCURACY_DROP`/`MISTAKE_DROP`/`BLUNDER_DROP` are at L47–49.
- Columns: `app/models/game_flaw.py` (`is_miss`, `missed_pv_lines` with `b`/`bm`/`s`/`sm` best/second evals).
- Glyphs: `frontend/src/lib/severityGlyph.ts` (single source for board markers and badges), `frontend/src/components/icons/MoveQualityIcon.tsx`, `SeverityGlyphIcon.tsx`.
- Tag copy: `frontend/src/lib/tagDefinitions.ts` ('miss'), `frontend/src/lib/tagVisuals.ts`.
- Related: [[project_game_flaws_both_players_scope]] (both players stored), the `eval_cp` ply conventions memory.
