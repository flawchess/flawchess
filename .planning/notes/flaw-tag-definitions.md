---
title: Flaw attribution-tag definitions (tooltip-ready)
date: 2026-06-08 (impact thresholds recalibrated 2026-06-09)
context: precise, tooltip-usable definitions for every severity tier + attribution tag.
source: app/services/flaws_service.py. Severity/tempo/opportunity/phase thresholds verified against source. Impact thresholds (`reversed`/`squandered`) recalibrated to round-eval anchors on 2026-06-09 (see Impact section); the flaws_service.py constant + test + tooltip update is a pending /gsd-quick, so code still holds the prior values (70/30, 85/60) until it lands.
related: flaw-tag-naming.md (the authoritative naming taxonomy this builds on)
---

# Flaw attribution-tag definitions

Every user mistake or blunder in an analyzed game is classified into one **severity** tier
plus a set of orthogonal **attribution tags** across four families. Tags are additive
*across families*: a single flaw can carry one from each family (phase is always present;
tempo is present only when clock data exists; opportunity and impact are conditional).
Within a family there is **at most one** tag.

All scores below use **Expected Score** on a `0–100%` scale (100% = certain win, 50% =
even, 0% = certain loss), derived from the Stockfish eval via the Lichess winning-chances
sigmoid in `eval_utils.py`. "Expected Score drop" = Expected Score before the move minus
Expected Score after, measured in percentage points.

The sigmoid is flatter than gut feel, so the corresponding engine evals look large.
Rough map on the absolute scale: Expected Score 50% ≈ 0.0, 59% ≈ +1.0, 68% ≈ +2.0,
75% ≈ +3.0, 85% ≈ +4.7 (symmetric below 50%). The impact thresholds are deliberately
anchored to round Stockfish evals (±1.0 / ±2.0 / +3.0). Eval equivalents below are
approximate and given so players can think in Stockfish terms.

## Severity

Inaccuracies are detected for counts but are **not** surfaced as flaw cards — only
mistakes and blunders appear in the list. Severity uses the *drop* in Expected Score, not
an absolute eval. Near an even position those drops are roughly a 5-point drop ≈ 0.5 pawn,
10 ≈ 1.0 pawn, 15 ≈ 1.6 pawns of eval lost; the same Expected Score drop is a larger eval
swing when the position is already one-sided.

| Family   | Name         | Definition |
|----------|--------------|------------|
| Severity | `inaccuracy` | A minor slip: your move dropped your Expected Score by at least 5 but less than 10 percentage points (count-only, not shown as a card). |
| Severity | `mistake`    | Your move dropped your Expected Score by at least 10 but less than 15 percentage points. |
| Severity | `blunder`    | Your move dropped your Expected Score by at least 15 percentage points. |

## Tempo — how the clock shaped the move

At most one tempo tag per flaw. Thresholds are relative to the game's base time when
known (a 5s move is hasty in classical but normal in bullet); absolute fallbacks
apply when base time is unknown. **No tempo tag is shown when clock data is unavailable**
(e.g. chess.com games without per-move clocks) — its absence is not `unrushed`.

The trio is a two-level decision: *low on clock?* → `low-clock` (forced). Otherwise, *did
you move fast?* → `hasty` (self-inflicted haste) vs `unrushed` (took your time, still
erred). Three non-overlapping signals, each a different actionable story.

| Family | Name        | Definition |
|--------|-------------|------------|
| Tempo  | `low-clock` | You were short on time when you blundered or made the mistake: your remaining clock was under 5% of the base time (or under 30s when base time is unknown). |
| Tempo  | `hasty`     | You had a comfortable clock but still moved fast: the move took under 1% of the base time (or under 5s when base time is unknown). |
| Tempo  | `unrushed`  | You had time and didn't rush, yet the move was still a blunder or mistake. |

## Opportunity — how the blunder or mistake related to the opponent's play

Both require the full both-color analysis pass.

| Family      | Name           | Definition |
|-------------|----------------|------------|
| Opportunity | `miss`         | Your blunder or mistake came immediately after the opponent's own mistake or blunder: they handed you something and you didn't take it (or made it worse) on the very next move. |
| Opportunity | `lucky`        | A blunder the opponent failed to punish: their immediate reply was itself a mistake or blunder, so your Expected Score recovered. (Blunders only. End-of-game with no reply counts only if you didn't go on to lose.) |

## Impact — how far the blunder or mistake swung the game

**At most one impact tag, evaluated top-down as a severity ladder** (`reversed` →
`squandered`); the more severe applicable tag wins, the other is suppressed.
**Outcome-independent**: impact depends only on the Expected Score before and after the
move, never on how the game actually ended. Both tags are *swings* defined by where you
started and where you landed.

Impact tags are highlight markers for *dramatic* swings, not an exhaustive label of every
flaw. A clearly-winning-but-not-near-decisive advantage that drops only to slightly worse
(e.g. 70% → 45%) carries no impact tag; its size is already captured by severity
(`blunder`).

By construction every `squandered` (and every `reversed`) is also at least a `blunder`:
the smallest qualifying squandered swing is 75% → 59%, a 16-point drop, just past the
15-point blunder floor. Impact tags never fire on a sub-blunder move.

**Recalibrated 2026-06-09 (pending implementation).** The impact thresholds were loosened
from their original values (`reversed` 70/30, `squandered` 85/60) to round-eval anchors
(`reversed` 68/32 ≈ ±2.0, `squandered` 75/59 ≈ +3.0/+1.0). Rationale: the planned
[[SEED-040-flaw-stats-opponent-comparison]] you-vs-opponent surface computes
`reversed`/`squandered` as a **Wilson difference-of-proportions** with a benchmark IQR
zone, which needs a denser event count than a single population baseline. Benchmark-DB
measurement: the change ~3× the squandered rate (per-user share with ≥10 instances
34% → 68%) while keeping `reversed` roughly flat (+21%, already healthy) — the
`squandered` *entry* is the load-bearing lever. Tags stay meaningful (still a
blunder-sized throw of a winning game), but "overwhelming" becomes "winning, near-decisive."

| Family | Name            | Definition |
|--------|-----------------|------------|
| Impact | `reversed`      | You turned a winning game into a losing one: your Expected Score before the move was at least 68% (clearly winning, eval roughly +2.0 or better) and dropped to 32% or below (clearly losing, roughly −2.0). |
| Impact | `squandered`    | You erased a winning, near-decisive advantage back to roughly even: your Expected Score before the move was at least 75% (eval roughly +3.0 or better) and dropped to 59% or below, but not far enough to be `reversed`. |

## Phase — where in the game it happened

Exactly one phase tag per flaw, taken from the position's stored game phase (defaults to
middlegame when the phase is unknown).

| Family | Name           | Definition |
|--------|----------------|------------|
| Phase  | `opening`      | The blunder or mistake occurred in the opening phase of the game. |
| Phase  | `middlegame`   | The blunder or mistake occurred in the middlegame. |
| Phase  | `endgame`      | The blunder or mistake occurred in the endgame phase of the game. |

## Threshold reference (source of truth)

All values are from `app/services/flaws_service.py`, except the impact rows marked `*`,
which are the recalibrated 2026-06-09 targets pending implementation (the code still holds
the prior values). Expected-Score and clock-fraction values are shown as percentages to
match the rest of the doc; the Python constants store them as `0–1` fractions (e.g.
85% → `0.85`). The `*_ABS_SECONDS` values are literal seconds.

| Constant | Value | Drives |
|----------|-------|--------|
| `INACCURACY_DROP` | 5% | Inaccuracy severity floor |
| `MISTAKE_DROP` | 10% | Mistake severity floor |
| `BLUNDER_DROP` | 15% | Blunder severity floor |
| `TIME_PRESSURE_CLOCK_FRACTION` | 5% | `low-clock` (relative) |
| `TIME_PRESSURE_CLOCK_ABS_SECONDS` | 30s | `low-clock` (fallback) |
| `HASTY_MOVE_FRACTION` | 1% | `hasty` (relative) |
| `HASTY_MOVE_ABS_SECONDS` | 5s | `hasty` (fallback) |
| `WINNING_LINE_ES` | 68%* | `reversed` entry (clearly winning before, ≈ +2.0) |
| `LOSING_LINE_ES` | 32%* | `reversed` exit (clearly losing after, ≈ −2.0) |
| `FROM_WINNING_ES` | 75%* | `squandered` entry (winning, near-decisive before, ≈ +3.0) |
| `SQUANDERED_EXIT_ES` | 59%* | `squandered` exit (back to a slight edge, ≈ +1.0) |

`*` Recalibrated target values (2026-06-09, round-eval anchors). The flaws_service.py
constants still hold the prior values (`WINNING_LINE_ES` 70%, `LOSING_LINE_ES` 30%,
`FROM_WINNING_ES` 85%, `SQUANDERED_EXIT_ES` 60%) until the implementation /gsd-quick lands.
The exact stored fractions are the sigmoid of the round eval: ES(+2.0)=0.6762,
ES(−2.0)=0.3238, ES(+3.0)=0.7511, ES(+1.0)=0.5910.

Tags are computed **on the fly** and not persisted, so there is no DB column behind any of
them.
