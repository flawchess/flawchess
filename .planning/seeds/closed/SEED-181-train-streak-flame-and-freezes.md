---
id: SEED-181
status: dormant
planted: 2026-10-02
planted_during: no open milestone (after v2.19), during Phase 227 (SEED-171); standalone /gsd-explore session on the Train landing
trigger_when: next Train UI polish / Train landing phase, or when picking up Train retention work
scope: medium (frontend-only UI phase, no backend change, no migration; SVG + animation work wants a UI-SPEC and browser UAT)
---

# SEED-181: Train streak flame + freeze buffer redesign

## Why This Matters

The Streak card renders the 0-7 `shield_level` buffer as flames and the
streak count as an amber trophy pill. The trophy was a workaround: 193 UAT
round 2 found "three lit flames next to a 3" read as "the flames ARE the
streak", so the streak itself could never use the flame, the most natural
streak symbol there is.

Moving the buffer to a cold visual family (freezes) separates the two
concepts by temperature, not only by layout, and frees the flame for the
streak. The mechanic is literally a freeze: in
`../../../app/services/train_scheduler.py` `_judge_one_day`, a missed scheduled day
costs one unit and the streak is held (neither grows nor resets) until the
units run out. "Streak freeze" is also a convention users already know.

Diff-driven animations make the landing a reward moment instead of a static
stat card, without becoming wallpaper (they only play when something changed).

## Design (decided 2026-10-02)

1. **Streak flame.** Inline SVG, three nested paths: red outer, orange middle,
   yellow core. `session_streak_count` sits inside the wide lower bowl and
   must fit 3 digits (365+). Streak 0 = grey unlit outline flame. Replaces
   `StreakBadge` in `TrainStreakCard.tsx` (and `TRAIN_STREAK_BADGE_*` tokens).
2. **Freezes.** The 7-slot meter renders snowflakes in icy blue (filled vs
   grey outline, shape difference kept for greyscale). Row label "Flames" ->
   "Freezes". `SHIELD_EXPLAINER` rewritten, e.g. "Every completed session
   earns a freeze (7 max). Each missed scheduled day uses one; when you have
   none left, your streak resets to 0." The `shield_level` API field and the
   `train-shield-*` testids keep their names. `TRAIN_SHIELD_FLAME_COLORS` in
   `lib/theme.ts` is replaced by a freeze color token.
3. **Animations, only when something changed.** Store last-seen
   `{streak, freezes}` in localStorage (try/catch every access), diff against
   `GET /train/progress` on landing mount:

   | Diff since last seen | Animation |
   |---|---|
   | streak up | Flame ignites: core flares, number ticks up from the old value |
   | streak same, freezes down | Spent snowflake(s) crack and fade in sequence; brief frost sweep over the flame, which stays lit (streak held) |
   | streak same, freezes up (off-day session) | New snowflake pops in; no flame animation |
   | streak reset to 0 | Simple extinguish (changed at review 2026-10-02, was a quiet reset): the old lit flame gutters into its base, then the grey outline and 0 fade in |
   | no stored value (first visit / new device) | No animation; just store |

   `prefers-reduced-motion` renders static. Replay on a second device is
   accepted; no server-side "last seen" (over-engineering for a cosmetic).
4. **Where it plays.** The Train landing only. The score screen's Done button
   already returns there (SEED-122), so a session-day tick shows right after
   Done; missed days settle lazily on the next visit via `tick_days`, so
   freeze-used also lands there.
5. **Mobile layout.** Hero block at the top: big flame beside a full-width
   Start session button (today the streak is a small card row and the CTA a
   small pill). The Train schedule card collapses to a one-line summary
   ("Mo-Su · 6 puzzles · 16:00 reminder") that expands on tap; it is set-once
   config that dominates phone height.

## Sketch decisions (2026-10-02)

- Flame: **Concentric** (sketch 005 A): one silhouette at 100/76/56% scale, red/orange/yellow,
  number in the bowl; 64px at card size was the legibility floor for 2-3 digits.
- Freeze icon: **plain stroke snowflake** (lucide `Snowflake`), icy blue filled vs grey outline.
- Layout: **flame beside the CTA** (sketch 006 A): hero card with ~92px flame left, right column =
  streak caption + freeze meter + full-width Start. Puzzle pool as two stat tiles. Schedule
  collapsed to a summary row; selected day toggles filled brand brown.

## When to Surface

**Trigger:** next Train UI polish / Train landing phase, or Train retention work.

## Scope Estimate

**Medium.** Frontend only. Touches `TrainStreakCard.tsx`, `TrainStartScreen.tsx`
(hero), `TrainScheduleSettings.tsx` (collapse), `lib/theme.ts`, a new flame SVG
component + a small last-seen/diff hook, and the existing card tests (copy and
label assertions change). Run `/gsd-ui-phase` before planning.

## Breadcrumbs

- `../../../frontend/src/components/train/TrainStreakCard.tsx` (StreakBadge, ShieldMeter, SHIELD_EXPLAINER, 193 UAT history in the header comment)
- `../../../frontend/src/components/train/__tests__/TrainStreakCard.test.tsx`
- `../../../frontend/src/components/train/TrainStartScreen.tsx` (LANDING_CARD_GRID_CLASS, Start CTA)
- `../../../frontend/src/components/train/TrainScheduleSettings.tsx`
- `../../../frontend/src/lib/theme.ts` (`TRAIN_SHIELD_FLAME_COLORS`, `TRAIN_STREAK_BADGE_BG/FG`)
- `../../../frontend/src/types/train.ts` (`TrainProgressResponse`)
- `../../../app/services/train_scheduler.py` (`_judge_one_day`, `tick_days`)
- Mockups: `../../sketches/005-streak-flame-and-freezes` (winner: A Concentric + Snowflake) and `.planning/sketches/006-train-landing-hero/` (winner: A Flame beside the CTA); `flame.js` there holds the SVG paths and keyframes

## Notes

Deferred, not in scope: a Mo-Su week strip replacing "This week N of M"
(done / frozen / missed / scheduled / today). It needs backend per-day
outcome history; only a snapshot is persisted today.
