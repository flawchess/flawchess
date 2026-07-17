---
quick_id: 260717-lr9
title: "Preset-only 3-tier play-style control: Human / Light / Deep"
date: 2026-07-17
status: complete
commit: c6b4c7a4
---

# Quick Task 260717-lr9 — Summary

## What shipped

Replaced the Bots setup-screen play-style **slider + Human/Engine chips** with a
**preset-only three-button segmented control**:

| Preset | blend | Summary copy |
|--------|-------|--------------|
| Human | 0 | Human — instinct, no calculation |
| Light (**default**) | 0.05 | Light — calculates a little |
| Deep | 0.5 | Deep — calculates hard |

Names describe **calculation depth, not a rating** — the bot engine isn't
ELO-calibrated yet, so no copy makes a strength promise (calibrated sparring is
the north star, tracked as SEED-112).

## Changes

- **`frontend/src/lib/playStyle.ts`** — removed the slider constants
  (`PLAY_STYLE_MIN/MAX/STEP`) and the transitional `ENGINE_PRESET_BLEND`; added
  `LIGHT_BLEND` (0.05), `DEEP_BLEND` (0.5), and `BLEND_MAX` (1). `BLEND_MAX` is
  the **validation ceiling, not a preset** — the accepted range stays `[0, 1]`
  so a legacy stored blob from the retired Engine preset (blend 1.0) still
  *validates* rather than tripping the WR-01 "out-of-range → silently discard
  finished game" path. `deriveActivePlayStylePreset` is now 3-way
  (`'human' | 'light' | 'deep' | null`); `formatPlayStyleSummary` returns
  behavior prose with no blend number / `%` / ELO; default flips to Light.
- **`frontend/src/components/bots/PlayStyleControl.tsx`** — rewritten as a
  `grid-cols-3` segmented control (no `Slider`), driven by a `PRESETS` table
  with `aria-pressed` + kebab `data-testid` per button
  (`setup-play-style-preset-{human,light,deep}`). Info-popover copy rewritten to
  make no rating claim.
- **`frontend/src/lib/botSetupSettings.ts`** — default blend now Light via
  `PLAY_STYLE_DEFAULT_BLEND`; validation uses `BLEND_MAX` (range unchanged at
  `[0, 1]`).
- Tests updated across `playStyle.test.ts`, `PlayStyleControl.test.tsx`,
  `SetupScreen.test.tsx`, `botSetupSettings.test.ts`.
- Adjacent setup-screen copy tightened (user-driven): play-style popover wording
  and the `EloSelector` tooltip ("The Maia engine selects moves at this
  rating…").
- `CHANGELOG.md` — `### Changed` bullet under `[Unreleased]`.

## Verification

- Full frontend gate green: `knip` clean, `tsc -b` clean, `eslint src` clean,
  `npm test -- --run` → **2298 passed / 171 files**.
- A one-off `openings.test.ts` failure mid-run was a flake (SAN-parity
  whole-corpus replay, ~7s) — passed on the clean full-suite re-run.

## Notes / superseded

- Supersedes the earlier in-session change that set the "Engine" preset to
  blend 0.05 (transitional `ENGINE_PRESET_BLEND`) — that constant is removed.
- Legacy persisted `blend: 1.0` (old Engine preset) validates but matches no
  preset, so the control shows nothing pressed until the user clicks a preset.
  Acceptable for a pre-release feature; not migrated.

## Follow-ups

- **SEED-112** (calibrated FlawChess strength presets) still to be captured —
  the exploration's north star: once the engine is ELO-calibrated, collapse the
  ELO selector + blend into one predictable strength dial.
