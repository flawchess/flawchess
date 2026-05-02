# Conversion / Recovery Validation — 2026-05-02

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: 2026-05-02T09:30:52Z
- **Population**: 1,896 completed users / 1,260,266 rated non-computer games (sparse cell `(2400, classical)` excluded)
- **Sparse-cell exclusion**: `(2400, classical)` excluded from all aggregations
- **Persistence approximation**: SQL uses `entry_ply + 4` with same-class join; backend uses `array_agg` contiguity (small systematic difference, does not move headline numbers)
- **Currently set in code** (per `app/services/endgame_service.py` / `app/repositories/endgame_repository.py`): `_MATERIAL_ADVANTAGE_THRESHOLD` = 100, persistence = 4 plies, `ENDGAME_PLY_THRESHOLD` = 6
- **Agreement definitions**: proxy uses material imbalance with 4-ply persistence (entry **and** entry+4 both ≥ +100 / ≤ −100); eval uses entry-only (eval already factors compensation, no persistence needed)

## 1. Conversion, Parity & Recovery (Endgame Metrics)

Whole-game first-endgame entry. One row per game; the game's earliest qualifying endgame class (≥6 plies) is the entry sequence. Mirrors the live Endgame Metrics gauges.

### 1.1 Stockfish eval coverage

| Metric                                | Games   | Coverage |
|---------------------------------------|---------|----------|
| Total qualifying games                | 706,742 | —        |
| With `entry_eval` (entry ply)         | 158,302 | 22.4%    |
| With `entry_eval` and `after_eval`    | 150,976 | 21.4%    |

### 1.2 Proxy ↔ Stockfish agreement

Filtered to rows with both entry and after evals (n = 150,976).

| Class      | Sequences (proxy) | Agreement % | Avg eval @ entry (cp) | Missed by proxy |
|------------|-------------------|-------------|-----------------------|-----------------|
| Conversion | 43,340            | 81.5%       | +356.0                | 18,517          |
| Parity     | 68,319            | 51.5%       | +6.3                  | —               |
| Recovery   | 39,317            | 81.5%       | −358.8                | 17,476          |

Notes:
- Conversion and recovery proxy precision is symmetric at 81.5%; the average entry eval on those rows (~ ±360 cp) is well above the 100 cp threshold, so the proxy is firing on substantial material advantages.
- Parity rows are heterogeneous by design: 48.5% are reclassified by Stockfish as conversion or recovery, mostly cases where one side has positional / king-safety / tempo compensation that material imbalance cannot see.
- "Missed by proxy" totals (18,517 conv + 17,476 recov = ~36k) account for roughly 24% of the eval-available subset and are largely the same population the parity row is mismatching against.

## 2. Conversion & Recovery by Endgame Type

Per-class spans. A single game contributes one row per endgame class it traverses (≥6 plies in the class).

### 2.1 Stockfish eval coverage (per class)

| Endgame type | Total spans | With both evals | Coverage |
|--------------|-------------|-----------------|----------|
| rook         | 120,705     | 25,271          | 20.9%    |
| minor_piece  | 92,820      | 22,344          | 24.1%    |
| pawn         | 48,400      | 10,208          | 21.1%    |
| queen        | 44,464      | 4,539           | 10.2%    |
| mixed        | 675,396     | 143,065         | 21.2%    |
| pawnless     | 7,566       | 529             | 7.0%     |

Queen and pawnless coverage are noticeably lower than the other classes; treat their agreement numbers in 2.2 as having wider confidence intervals.

### 2.2 Proxy ↔ Stockfish agreement (per class)

#### Conversion

| Metric              | rook   | minor_piece | pawn   | queen  | mixed   | pawnless |
|---------------------|--------|-------------|--------|--------|---------|----------|
| Spans (proxy=conv)  | 7,811  | 6,941       | 2,710  | 1,309  | 41,533  | 246      |
| Agreement %         | 78.2%  | 80.2%       | 84.0%  | 71.5%  | 81.7%   | 31.3%    |
| Avg eval @ entry    | +392.7 | +435.6      | +860.3 | +730.9 | +358.8  | +213.3   |
| Missed by proxy     | 1,722  | 1,618       | 1,423  | 256    | 17,887  | 0        |

#### Recovery

| Metric              | rook   | minor_piece | pawn   | queen  | mixed   | pawnless |
|---------------------|--------|-------------|--------|--------|---------|----------|
| Spans (proxy=recov) | 7,023  | 6,045       | 2,502  | 1,228  | 37,738  | 218      |
| Agreement %         | 76.1%  | 79.2%       | 81.4%  | 72.0%  | 81.6%   | 33.9%    |
| Avg eval @ entry    | −376.2 | −417.1      | −808.5 | −628.9 | −361.3  | −278.0   |
| Missed by proxy     | 1,569  | 1,390       | 1,222  | 248    | 16,958  | 3        |

Notes:
- Conversion and recovery agreement are within ~3 pp across classes (rook through mixed), indicating the proxy is class-symmetric at the populations that matter.
- Pawn endgames carry the largest avg eval at entry (~ ±830 cp): material imbalance there usually means an extra pawn or two on a near-empty board, which Stockfish strongly endorses.
- Queen endgames sit at 71-72%, a few points below the others. Likely a compensation effect: at queen-only material, perpetual / fortress / king-safety patterns can flip Stockfish's verdict despite a material edge.
- Pawnless agreement collapses to ~32% on tiny populations (246 conv / 218 recov spans, 7% eval coverage). A material imbalance in a pawnless endgame is almost always KQ vs KR, KR vs KB, or similar — Stockfish frequently calls these draws or much smaller advantages than the raw material count suggests, which the material-imbalance proxy cannot reproduce. The class also surfaces in the report's smallest cells, so treat the headline as illustrative.

## 3. Verdict

**PASS** — the t=100 cp + 4-ply-persistence proxy is fit-for-purpose for the live UI. No action recommended.

- **Whole-game gauges (Section 1) clear the PASS bar.** Conversion and recovery proxy precision are both 81.5% (≥ 80% rubric threshold). The proxy's average entry eval on those rows (~ ±360 cp) sits well above the 100 cp threshold, confirming the proxy fires on substantive material edges, not borderline noise.
- **All five UI-visible endgame types clear ≥ 70%.** rook, minor_piece, pawn, mixed all sit in the 76-84% band; queen lands at 71.5% / 72.0% — the slimmest margin but still over. Queen's compensation patterns (perpetuals, fortresses, king-safety) are the structural reason and are visible to Stockfish but not to material count.
- **Pawnless (~32% / ~34% on n ≈ 230 spans) is informational only.** Pawnless is hidden from the Endgames page (`frontend/src/pages/Endgames.tsx` `HIDDEN_ENDGAME_CLASSES`) and dropped from LLM insights (`app/services/insights_llm.py:572`, `:1573`), so its low agreement does not reach users. It is reported here for completeness; the underlying cause (KQvKR / KRvKB positions where Stockfish calls a draw despite a material edge) is a structural limit of any material-imbalance proxy, not a calibration issue.
- **Parity heterogeneity (51.5% agreement) is structural, not a bug.** Proxy parity is "no ±100 cp material edge with 4-ply persistence"; eval parity is "entry eval within ±99 cp." Anything where one side has positional / king-safety / tempo compensation (or fleeting material that doesn't persist 4 plies) lands in proxy parity but eval conversion/recovery. No action — the gauges are already split into three buckets that absorb this.

No threshold or persistence change recommended. Re-run after any change to `_MATERIAL_ADVANTAGE_THRESHOLD`, the persistence ply count, or `ENDGAME_PLY_THRESHOLD`.
