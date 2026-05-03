# Endgame entry eval — twin-tile design (notes from 2026-05-03 exploration)

Source conversation: Adrian + Claude, 2026-05-03 (post-v1.15 ship). Captured here so the
forthcoming `/gsd-discuss-phase 81` has the full context without re-deriving it.

## Decision

Add "Average eval at endgame entry" to the **Endgame Overall Performance** section of the
Endgames page. Present it as a twin-tile pairing alongside the existing Score Gap, lifted
out of the WDL table into its own dedicated visual block.

## Why this metric

It answers a different question than conv/parity/recovery: **do you reach the endgame
already ahead, even, or behind?** Conv/parity/recov measure what you do *with* the position
you arrive at; entry eval measures the position itself. Together with Score Gap they
decompose endgame outcomes into two stages:

- **Where you start** = avg eval at endgame entry (pre-endgame contribution)
- **What you do with it** = endgame vs non-endgame score gap (endgame skill)

A user with `+0.4 entry / +5% gap` is "ahead and stays ahead." `+0.4 entry / −5% gap` is
"ahead but squanders it." `−0.3 entry / +8% gap` is "starts behind, claws back."

## Population baseline (from benchmark DB, 2026-05-03)

Reference: `.claude/skills/benchmarks/SKILL.md` §2 ("Eval distribution at endgame entry"
and "Population bucket prevalence" subsections; data also surfaced in
`reports/benchmarks-2026-05-03.md`).

- **Game-weighted population mean:** +4 cp under equal-footing (~0 pawns). Confirms the
  "test against 0" framing — there's no systematic population offset to correct for.
- **Per-game SD:** 418 cp. Median 0; IQR `[−300, +312]`; p05/p95 `[−681, +684]`.
- **Distribution shape:** strong central peak (~25% within ±100 cp), mild secondary
  shoulders around ±400-500 (likely "piece hung in middlegame" cohort), symmetric tails.
  Trimodal-ish, NOT bimodal.

**Sample-size implications** (test mean ≠ 0, α=0.05, 80% power, σ = 418 cp):

| effect Δ | n endgame games |
|---:|---:|
| +50 cp | ~1,100 |
| +100 cp | ~280 |
| +200 cp | ~70 |

Most users will have 100-500 endgame games per filter view; the sig test reliably catches
≳+150 cp and says "no signal" for genuine but smaller effects. UI copy must phrase the
null as **"we can't tell"** not **"no advantage."**

## Why we did NOT pair with clock-diff narrative

Cross-user Pearson correlation between per-user mean entry eval and per-user mean clock-diff
% (2026-05-03 analysis, equal-footing, ≥30 endgame games/user, mate excluded):

| TC | n users | r |
|---|---:|---:|
| bullet | 494 | −0.43 |
| blitz | 494 | −0.33 |
| rapid | 482 | −0.00 |
| classical | 212 | +0.06 |
| pooled | 1,682 | −0.13 |

The "you paid for it with time" trade-off **holds in bullet/blitz, vanishes in
rapid/classical**. A globally applied trade-off framing would tell a false causal story to
half the users. Decision: clock-diff stays in its existing Time Pressure section as an
independent fact; entry eval lives in Overall Performance with its own honest framing.

## Visual design — Option C (twin tile)

### Desktop layout

```
┌─ Endgame entry quality vs endgame skill ─────────────────────────────────┐
│  ┌──────────────────────────────────┬──────────────────────────────────┐ │
│  │  Where you start              ⓘ  │  What you do with it          ⓘ │ │
│  │  Avg eval at endgame entry       │  Endgame vs non-endgame score   │ │
│  │                                  │                                  │ │
│  │   −2.0       0       +2.0 pawns  │   −20%      0       +20%        │ │
│  │   ─────────[░░░]──●──────────    │   ────────[░░░]─●────────       │ │
│  │                                  │                                  │ │
│  │   +0.4 pawns ahead               │   +5% endgame stronger          │ │
│  │   n=247 · p<0.05                 │   n=520 · p<0.05                │ │
│  └──────────────────────────────────┴──────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

Mobile: stacked vertically, entry eval first (chronological order: setup → execution).

### Tile anatomy (consistent across both)

1. **Title**: punchy header ("Where you start") + technical sub-header ("Avg eval at
   endgame entry") + info-popover icon.
2. **Bullet chart**: axis labels at ends + center, neutral band shaded, dot for value.
   Reuses existing `MiniBulletChart`. No new component.
3. **Value line**: signed magnitude + plain-English direction ("+0.4 pawns ahead"). Color
   matches sig-test verdict (green / red / neutral gray).
4. **Stats line**: `n=… · p<0.05` (or `n=… · not enough signal` when not sig). Always
   shown, smaller, muted.

### Sig-test rules (apply to BOTH tiles for consistency)

- One-sample t-test against 0
- Minimum n=30 to compute; below that → empty bullet chart + "Not enough data yet"
- Three-state color: sig > 0 → green; sig < 0 → red; not sig → neutral gray
- Score Gap currently has no sig test — adding it for consistency. Score Gap has lower
  per-game noise so virtually all users with ≥100 games will hit sig; the neutral state
  fires only for very small samples (which is when the existing always-colored display is
  actually misleading).

### WDL table changes

Drop the `Score Gap` column entirely. WDL table becomes 4-column (Endgame, Games,
Win/Draw/Loss, Score). The mobile Score Gap card also goes away — replaced by the twin
tiles below the cards.

### Concept-explainer accordion

Add an "Avg eval at endgame entry" paragraph between Recovery and "Conversion / Recovery
rate" notes:

> **Avg eval at endgame entry:** the Stockfish evaluation in pawns at the start of your
> endgame phase, averaged across all your endgame games and shown from your perspective.
> Positive means you tend to reach endgames already ahead; negative means already behind.
> Mate scores are excluded. Among players matched against opponents of similar strength,
> the population average is approximately 0 — so values clearly above or below 0 indicate
> that you systematically out-prepare or get out-prepared in the middlegame.

### Empty / sparse states

- `n < 30` → empty bullet chart + "Not enough data yet"
- `n=0` (no endgame games) → hide both tiles entirely

## Backend additions implied

`EndgamePerformanceResponse` gains three fields:

- `entry_eval_mean_pawns: float`
- `entry_eval_n: int` (games with non-NULL `eval_cp`, mate excluded)
- `entry_eval_p_value: float | None` (None when n < 30)

Same for Score Gap (sig-test fields) for symmetry.

Aggregation reuses the existing `first_endgame` ply walk that conv/parity/recov already
do — single extra column in that query path, not a new pipeline.

## Open questions for discuss-phase

1. **Tile order** — entry on left (chronological) vs score gap on left (current → new
   read order). Default vote: chronological.
2. **Section heading wording** — *"Endgame entry quality vs endgame skill"* is descriptive
   but long. Alternatives: *"Setup vs execution"*, *"Reaching the endgame vs playing it"*,
   or keep the umbrella *"Endgame Overall Performance"* and let tile sub-headers carry it.
3. **Pawn axis range** — proposed ±2.0. Population p25/p75 is `[−300, +312]` cp ≈ ±3.0
   pawns *per game*; per-user means concentrate much tighter (most in `[−0.5, +0.5]` under
   equal-footing). ±2.0 fits typical user data with headroom; ±3.0 makes most dots cluster
   center. Default vote: ±2.0.
4. **Population-baseline tick at 0** — probably skip; neutral band already implies "0 is
   normal."
5. **Sig-test on Score Gap** — confirm we want this, or keep Score Gap visually identical
   to today and only sig-test the new tile.
6. **Mobile tile order when stacked** — entry first (chronological) vs gap first (more
   familiar, "where the existing data lives").

## Out of scope for this phase

- Per-user across-game eval × clock-diff correlation as a displayed metric. Interesting
  cross-section but doesn't belong in Overall Performance; would warrant its own
  exploration if at all.
- Per-TC stratification of entry eval. Decided not to split — population baseline is
  TC-invariant under equal-footing.
- Distribution histogram view of the user's per-game evals. More informative than a single
  number but heavier on the page; could be a future "click to expand" detail.
