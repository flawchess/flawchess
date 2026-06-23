---
title: Flaw attribution-tag definitions (tooltip-ready)
date: 2026-06-20
context: precise, tooltip-usable definitions for every severity tier + attribution tag. Documents the current live state.
source: app/services/flaws_service.py (all thresholds and tag names verified against source).
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
(e.g. chess.com games without per-move clocks) — its absence is not `unrushed`. See
[Structural rule: tempo is optional](#structural-rule-tempo-is-optional) below.

The trio is a two-level decision: *low on clock?* → `low-clock` (forced). Otherwise, *did
you move fast?* → `hasty` (self-inflicted haste) vs `unrushed` (took your time, still
erred). Three non-overlapping signals, each a different actionable story.

| Family | Name        | Definition |
|--------|-------------|------------|
| Tempo  | `low-clock` | You were short on time when you blundered or made the mistake: your remaining clock was under 5% of the base time (or under 30s when base time is unknown). |
| Tempo  | `hasty`     | You had a comfortable clock but still moved fast: the move took under 1% of the base time (or under 5s when base time is unknown). |
| Tempo  | `unrushed`  | You had time and didn't rush, yet the move was still a blunder or mistake. |

Priority when more than one could apply: `low-clock` > `hasty` > `unrushed`.

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

## Structural rule: tempo is optional

A flaw carries **at most one** tempo tag, and **none at all** when clock data is
unavailable. There is no fallback tag for missing clock data — "no time excuse"
(`unrushed`) and "we couldn't measure it" (no tag) are distinct.

Implications for code and UI:

- `_classify_tempo` returns `None` on missing clock/move-time instead of a fallback tag.
- `TempoTag` is `Literal["low-clock", "hasty", "unrushed"]`.
- The schema shape `tempo: dict[TempoTag, int]` sums to **≤** the mistake+blunder count.
- The Flaw-Stats panel's tempo stacked bar must show an **unmeasured remainder**
  (`total_mb_flaws − sum(tempo counts)`) so the segments still sum honestly — never
  normalize the three measured segments to 100%.

## Threshold reference (source of truth)

All values are from `app/services/flaws_service.py`. Expected-Score and clock-fraction
values are shown as percentages to match the rest of the doc; the Python constants store
them as `0–1` fractions (e.g. 75% → `0.7511`). The `*_ABS_SECONDS` values are literal
seconds.

| Constant | Value | Drives |
|----------|-------|--------|
| `INACCURACY_DROP` | 5% | Inaccuracy severity floor |
| `MISTAKE_DROP` | 10% | Mistake severity floor |
| `BLUNDER_DROP` | 15% | Blunder severity floor |
| `TIME_PRESSURE_CLOCK_FRACTION` | 5% | `low-clock` (relative) |
| `TIME_PRESSURE_CLOCK_ABS_SECONDS` | 30s | `low-clock` (fallback) |
| `HASTY_MOVE_FRACTION` | 1% | `hasty` (relative) |
| `HASTY_MOVE_ABS_SECONDS` | 5s | `hasty` (fallback) |
| `WINNING_LINE_ES` | 67.62% (`0.6762`) | `reversed` entry (clearly winning before, ≈ +2.0) |
| `LOSING_LINE_ES` | 32.38% (`0.3238`) | `reversed` exit (clearly losing after, ≈ −2.0) |
| `FROM_WINNING_ES` | 75.11% (`0.7511`) | `squandered` entry (winning, near-decisive before, ≈ +3.0) |
| `SQUANDERED_EXIT_ES` | 59.10% (`0.5910`) | `squandered` exit (back to a slight edge, ≈ +1.0) |

The four impact-ladder fractions are the sigmoid of the round eval they anchor to:
ES(+2.0)=0.6762, ES(−2.0)=0.3238, ES(+3.0)=0.7511, ES(+1.0)=0.5910.

Tags are computed **on the fly** and not persisted on the user's own flaws, so there is no
DB column behind any of them (the opponent-materialization path stores encoded equivalents
separately).
