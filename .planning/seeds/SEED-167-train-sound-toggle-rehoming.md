---
id: SEED-167
status: planted
planted: 2026-09-13
planted_during: /gsd-execute-phase 222 (Train Bot-Narrated Onboarding & Verdicts), plan 06 phase close, per D-10 and the ROADMAP's explicit "record a follow-up seed" instruction
trigger_when: BEFORE or WITH SEED-168 (bot voice + immersive bot game layout), which removes the LAST in-game mute button (Bots.tsx); until then no urgency, the shared preference still works from the Bots page
scope: give the mute preference one settings-page home that covers Train AND the bots game; no schema change, no new store
amended: 2026-09-15 by /gsd-explore (SEED-168) — widened from "a second, Train-reachable home" to "the only home"
---

# SEED-167: Train's mute toggle was retired and needs a new home (and the bots game's is next)

## What was removed

Phase 222 (plan 04, D-10) removed the Train solution screen's own mute toggle
(`board-btn-mute`, below the board) along with its four now-dead imports
(`Volume2`, `VolumeX`, `useMuted`, `setMuted`) from `TrainSolveScreen.tsx`.

## Why

The Solution/Analyze/Next action row moved from a below-board sibling row into
the narrated verdict bot's own chat bubble (D-10, the same plan). A mute
toggle is a fourth icon-only control; it did not fit that chat row, and a bot
bubble is the wrong visual register for a persistent settings affordance
anyway — it reads as part of the conversation, not chrome.

## The consequence to fix

`setMuted` now has exactly one call site in the whole frontend: `Bots.tsx`
(RESEARCH Finding L, `222-RESEARCH.md`). The mute preference itself is shared
and persisted (one flag, not per-page), so muting still works everywhere sound
plays — Train's reveal-line stepper, the free-play move sounds, the
solve/session result chimes all still honor it. What is gone is a **Train-side
control surface**: a user who mutes from the Bots page and then only ever
opens Train has no way back to unmuted without returning to Bots first. This
is a discoverability gap, not a functional regression — nothing is stuck
muted, the control for un-muting simply lives somewhere the affected user may
never visit again.

## 2026-09-15 amendment: the Bots page loses its toggle too

SEED-168 rebuilds the mobile bot game screen with a fixed bottom action bar of
exactly Resign / Back / Forward / Flip, and drops the sound toggle from the
desktop controls as well. Once that ships, `setMuted` has **zero** in-game call
sites: there is no way to mute or unmute anywhere. So this seed stops being a
discoverability gap and becomes a hard prerequisite of SEED-168. Ship the
settings-page switch before or in the same phase.

Decided home (2026-09-15): one "board sounds" switch on the general settings
page, not a per-page control and not an in-game gear sheet (an in-game sheet
was considered for the bots screen and rejected: one switch, no extra chrome).

## Proposed home (original, 2026-09-13)

A Train-scoped or general settings surface (e.g. an entry on `TrainScheduleSettings`,
or a small app-wide sound toggle if one gets built for other reasons) is the
natural next home. **Explicitly out of scope for Phase 222** per the ROADMAP's
own out-of-scope list — this seed exists so the gap is recorded rather than
silently accepted.

## Evidence

- RESEARCH Finding L (`222-RESEARCH.md`): `setMuted` call-site count and the
  shared/persisted nature of the preference, verified by grep across
  `frontend/src`.
- D-10 (`222-CONTEXT.md`): accepts the removal and requires this seed at
  phase close.

## Out of scope / decided against

- Do not promote this to a phase or add it to the ROADMAP — it is a small,
  low-urgency UX gap, not a project of its own.
- Do not reintroduce a per-page mute control on Train as a quick fix; the new
  home should be a real settings surface, not a repeat of the same
  chat-row-doesn't-fit problem.
