---
title: Flaw attribution-tag definitions (tooltip-ready)
date: 2026-06-07
context: precise, tooltip-usable definitions for every severity tier + attribution tag. Includes the 2026-06-07 /gsd-explore redesign of the impact family (outcome-independent ladder) and the tempo renames (impatient→hasty, considered→unrushed) — these LEAD the shipped Phase 106 code (see "Implementation status").
source: app/services/flaws_service.py (severity/tempo/opportunity thresholds verified against source; the new impact ladder is a proposed design, not yet in code)
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
Rough map on the absolute scale: Expected Score 50% ≈ 0.00, 60% ≈ +1.1, 70% ≈ +2.3,
85% ≈ +4.7 (symmetric below 50%). Eval equivalents below are approximate and given so
players can think in Stockfish terms.

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
| Tempo  | `low-clock` | You were short on time when you blundered or made the mistake: your remaining clock was under 5% of the base time (or under 30s when base time is unknown). A forced time problem. |
| Tempo  | `hasty`     | You had a comfortable clock but still moved fast: the move took under 1% of the base time (or under 5s when base time is unknown). Self-inflicted haste. |
| Tempo  | `unrushed`  | You had time and didn't rush, yet the move was still a blunder or mistake. No time excuse — purely a matter of judgement. |

## Opportunity — how the blunder or mistake related to the opponent's play

Both require the full both-color analysis pass.

| Family      | Name           | Definition |
|-------------|----------------|------------|
| Opportunity | `miss`         | Your blunder or mistake came immediately after the opponent's own mistake or blunder: they handed you something and you didn't take it (or made it worse) on the very next move. Mirrors chess.com's Miss classification (the Ø glyph). |
| Opportunity | `lucky-escape` | A blunder the opponent failed to punish: their immediate reply was itself a mistake or blunder, so your Expected Score recovered. (Blunders only. End-of-game with no reply counts only if you didn't go on to lose.) The one good-news tag. |

## Impact — how far the blunder or mistake swung the game

**At most one impact tag, evaluated top-down as a severity ladder** (`reversed` →
`squandered`); the more severe applicable tag wins, the other is suppressed.
**Outcome-independent**: impact depends only on the Expected Score before and after the
move, never on how the game actually ended. (This replaces the old `result-changing` tag,
which keyed off the final result and could fire on a game you *won* — see "Deprecated /
renamed".) Both tags are *swings* defined by where you started and where you landed; a tag
for merely *being* in a winning position when you slipped was considered and dropped (see
"Deprecated / renamed").

Impact tags are highlight markers for *dramatic* swings, not an exhaustive label of every
flaw. A clear-but-not-overwhelming advantage that drops only to slightly worse (e.g. 78%
→ 45%) carries no impact tag; its size is already captured by severity (`blunder`).

| Family | Name            | Definition |
|--------|-----------------|------------|
| Impact | `reversed`      | You turned a winning game into a losing one: your Expected Score before the move was at least 70% (clearly winning, eval roughly +2.3 or better) and dropped to 30% or below (clearly losing, roughly −2.3). A full reversal across equality. |
| Impact | `squandered`    | You erased an overwhelming advantage back to roughly even: your Expected Score before the move was at least 85% (eval roughly +4.7 or better) and dropped to 60% or below, but not far enough to be `reversed`. The win is gone, the game is still playable. |

## Phase — where in the game it happened

Exactly one phase tag per flaw, taken from the position's stored game phase (defaults to
middlegame when the phase is unknown).

| Family | Name           | Definition |
|--------|----------------|------------|
| Phase  | `opening`      | The blunder or mistake occurred in the opening phase of the game. |
| Phase  | `middlegame`   | The blunder or mistake occurred in the middlegame (also the default when the phase can't be determined). |
| Phase  | `endgame`      | The blunder or mistake occurred in the endgame phase of the game. |

## Deprecated / renamed tags

This session (2026-06-07) renamed the tempo residual pair and replaced the entire impact
family. Older renames (Phase 106) are recorded in `flaw-tag-naming.md`.

| Family | Deprecated name   | Replacement               | Why |
|--------|-------------------|---------------------------|-----|
| Tempo  | `impatient`       | `hasty`                   | `impatient` editorialised about character; `hasty` describes the move and is native chess phrasing. (`hasty` was the pre-106 name; this reverts it.) |
| Tempo  | `considered`      | `unrushed`                | On a blunder card `considered` read as a contradiction ("considered, yet blundered?"). `unrushed` is the clean complement to `hasty` and stays clock-framed (cause-of-error naming is reserved for the future tactic family). |
| Impact | `while-ahead` (briefly renamed `while-winning`) | *removed* | A pure *state* tag (you were ≥85% when you slipped), not a swing — it had only an entry threshold with nothing to cross, fired on a large fraction of winning-position blunders, and duplicated what `blunder` severity already says. The "lapse while winning" pattern lives better in aggregate (endgame conversion rates), not on individual cards. |
| Impact | `result-changing` | `reversed` + `squandered` | `result-changing` depended on the final result and could fire on a *won* game (the result didn't change), overclaiming causality. Split into two outcome-independent swing tags. |

## Threshold reference (source of truth)

Severity / tempo / opportunity values are from `app/services/flaws_service.py`. The impact
ladder is the **proposed** design from this session and is **not yet in code** (see
"Implementation status"). Expected-Score and clock-fraction values are shown as
percentages to match the rest of the doc; the Python constants store them as `0–1`
fractions (e.g. 85% → `0.85`). The `*_ABS_SECONDS` values are literal seconds.
`[ASSUMED]` = tunable initial default, no schema change needed to adjust.

| Constant | Value | Drives | Status |
|----------|-------|--------|--------|
| `INACCURACY_DROP` | 5% | Inaccuracy severity floor | shipped |
| `MISTAKE_DROP` | 10% | Mistake severity floor | shipped |
| `BLUNDER_DROP` | 15% | Blunder severity floor | shipped |
| `TIME_PRESSURE_CLOCK_FRACTION` | 5% | `low-clock` (relative) | shipped |
| `TIME_PRESSURE_CLOCK_ABS_SECONDS` | 30s | `low-clock` (fallback) | shipped |
| `HASTY_MOVE_FRACTION` | 1% | `hasty` (relative) | shipped |
| `HASTY_MOVE_ABS_SECONDS` | 5s | `hasty` (fallback) | shipped |
| `FROM_WINNING_ES` | 85% | `squandered` entry | shipped (was `while-ahead`; that tag is now removed, the constant is reused) |
| `WINNING_LINE_ES` | 70% | `reversed` entry (clearly winning before) | proposed (repurposes old `RESULT_WIN_THRESHOLD`) |
| `LOSING_LINE_ES` | 30% | `reversed` exit (clearly losing after) | proposed (new) |
| `SQUANDERED_EXIT_ES` | 60% | `squandered` exit (back to roughly even) | proposed (new) |
| ~~`RESULT_WIN_THRESHOLD`~~ | 70% | (removed — outcome-dependent `result-changing`) | deprecated |
| ~~`RESULT_DRAW_THRESHOLD`~~ | 40% | (removed — outcome-dependent `result-changing`) | deprecated |

## Implementation status

Severity, tempo (under their old names `impatient` / `considered`), opportunity, and phase
are shipped in Phase 106 code. **Not yet implemented**, pending a backend pass:

- Tempo renames `impatient` → `hasty`, `considered` → `unrushed` (`TempoTag` Literal,
  `_classify_tempo`, tests, docstrings).
- Impact family rebuild: drop `while-ahead` / `result-changing`, add the
  `reversed` / `squandered` two-rung ladder (`FlawTag` Literal, the impact classifier, the
  new constants above, `_build_tags` single-tag ladder selection, tests).

Like the rest of the taxonomy, tags are computed **on the fly** and not persisted, so there
is **no DB migration** — the change is pure code + docs.
