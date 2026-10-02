---
quick_id: 261002-8xb
status: complete
source: SEED-179
commit: e9b466552
date: 2026-10-02
---

# Quick 261002-8xb: Train puzzles-per-session slider (3-30, step 3)

Executed inline in a dedicated worktree (`../flawchess-q179`, branch
`quick/seed-179-session-size-slider` off local `main`) so phase 226 in the main
checkout was untouched. No planner/executor subagents: frontend-only, ~3 files.

## What changed

- `TrainScheduleSettings.tsx`: `PUZZLES_PER_SESSION_PRESETS` + Radix `ToggleGroup`
  replaced by a new `PuzzlesPerSessionControl` (single-thumb `Slider`, min 3,
  max 30, step 3, live value right-aligned in the label row). Exports
  `PUZZLES_PER_SESSION_MIN/MAX/STEP`. Always controlled (thumb parks at the min
  while loading) to avoid a Radix uncontrolled-to-controlled switch. Extracted
  into its own component so `TrainScheduleSettings` stays within the cognitive
  complexity cap.
- Tests: loading disables the slider; populated shows 12; two `ArrowRight`
  presses issue one debounced `updateSettings` with 18; `End` saves the max;
  guest still sees the slider. Mutation check: setting the step to 1 fails the
  ArrowRight test.
- `frontend/src/vitest.setup.ts`: guarded no-op `ResizeObserver` stub. jsdom has
  none and the Slider broke every test that mounts the card
  (`TrainStartScreen.test.tsx` and others).
- `CHANGELOG.md` `[Unreleased]` → Changed: one user-facing bullet.

No backend change: the CHECK and `Field(ge=1, le=50)` stay at 50.

## Verification

- `npm run lint` clean, `npm run lint:cognitive` no finding for the file,
  `npm run build` OK, `npm run knip` clean.
- `npm test -- --run`: 278 files, 4443 tests passed.
- Not done: browser visual check of the slider on the Train card.
