---
id: SEED-167
status: planted
planted: 2026-09-13
planted_during: /gsd-execute-phase 222 (Train Bot-Narrated Onboarding & Verdicts), plan 06 phase close, per D-10 and the ROADMAP's explicit "record a follow-up seed" instruction
trigger_when: next Train or general-settings work; no urgency — the shared mute preference still works, it just has one fewer place to flip
scope: give the mute preference a second, Train-reachable home; no schema change, no new store
---

# SEED-167: Train's mute toggle was retired and needs a new home

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

## Proposed home

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
