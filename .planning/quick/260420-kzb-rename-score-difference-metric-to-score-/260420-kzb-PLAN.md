---
id: 260420-kzb
description: Rename Score % Difference metric to Score Gap in EndgamePerformanceSection
date: 2026-04-20
status: in-progress
---

# Quick Task 260420-kzb: Rename "Score % Difference" → "Score Gap"

## Problem

The metric label `"Score % Difference"` on the Endgames tab is clunky (% as a noun, "Difference" is vague) and the timeline subtitle on L330 of `EndgamePerformanceSection.tsx` — *"Has your endgame edge versus your non-endgame play improved over time?"* — is confusingly phrased.

A natural-language name like "Endgame Edge" would collide with the existing **Endgame Skill** and **Endgame ELO** metrics (both absolute), whereas this metric is *relative* (endgame minus non-endgame).

## Solution

Rename to **"Score Gap"** with full context in the timeline heading where the chart stands alone:

- Table header + mobile card: `Score Gap`
- Timeline section title: `Endgame vs Non-Endgame Score Gap over Time`
- Timeline subtitle (L330): `Is your endgame improving faster than the rest of your game?`
- InfoPopover bodies, aria-labels, y-axis label, tooltip row: updated to match.
- Internal code: `ScoreDiffTimelineChart` → `ScoreGapTimelineChart`, `SCORE_DIFF_*` → `SCORE_GAP_*`, local `diff*` identifiers → `gap*`.

## Scope

**Files modified:**
- `frontend/src/components/charts/EndgamePerformanceSection.tsx` — all label sites + internal rename
- `frontend/src/pages/Endgames.tsx` — import + JSX tag for renamed component (L20, L283)
- `frontend/src/types/endgames.ts` — two stale comments mentioning "score-difference" and "Score % Difference" (backend field `score_difference` on the interface stays)

**Out of scope:**
- Backend schema field `score_difference` on `ScoreGapTimelinePoint` / `ScoreGapMaterialResponse` — rename would touch backend + DB response shape + tests. Not worth the blast radius for a copy change.
- `EndgameScoreGapSection.tsx` — uses a separate "Diff" concept (material-stratified, opponent-relative). Unaffected.
- `MiniBulletChart.tsx` — reused by multiple sections; its internal "score-diff" comment is generic.
- testids `score-gap-difference` / `score-gap-difference-mobile` on the table bullet chart — already use `gap`, stable, kept.

## Tasks

1. **Apply rename in `EndgamePerformanceSection.tsx`** — user-facing labels, ariaLabels, testids (`score-diff-*` → `score-gap-*`), component name, constant names, local identifiers.
2. **Update import + JSX in `Endgames.tsx`** — `ScoreDiffTimelineChart` → `ScoreGapTimelineChart`.
3. **Update stale comments in `types/endgames.ts`** — preserve backend field names, only fix comment text.
4. **Verify** — `npm run lint`, `npm run build`, `npm run knip`. Start dev server and spot-check the Endgames tab in a browser.

## must_haves

- Every user-visible occurrence of "Score % Difference" / "Score diff" / "Score difference" in `EndgamePerformanceSection.tsx` and `Endgames.tsx` is replaced with "Score Gap" (with the full "Endgame vs Non-Endgame Score Gap" on the timeline heading).
- Line 330's subtitle reads: "Is your endgame improving faster than the rest of your game?"
- Frontend still builds and lints cleanly.
- Backend schema field `score_difference` is untouched.
