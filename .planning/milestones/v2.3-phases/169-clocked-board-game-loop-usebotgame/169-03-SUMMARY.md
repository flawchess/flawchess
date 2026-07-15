---
phase: 169-clocked-board-game-loop-usebotgame
plan: 03
subsystem: ui
tags: [audio, howler-alternative, html-audio-element, localstorage, use-sync-external-store, agpl, lila-sfx]

# Dependency graph
requires:
  - phase: 169 (plan 01/02, same phase)
    provides: chessClock.ts (LOW_TIME_THRESHOLD_MS) and botGamePgn.ts constants that this plan's sibling modules use, no direct dependency from sounds.ts itself
provides:
  - Vendored AGPLv3+ lila `sfx` sound assets under frontend/public/sound/
  - sounds.ts audio module (playSound, useMuted, setMuted, unlockAudio, SoundEvent, MUTE_KEY)
  - README "## Sound Assets" attribution section
affects: [169-04 (useBotGame fires playSound events + unlockAudio on first gesture), 169-05 (GameControls mute toggle via useMuted/setMuted)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "useSyncExternalStore + localStorage listener Set, mirroring useUserFlag.ts's shape but with real two-way toggle semantics and a flat non-email-scoped key"
    - "Module-level Audio instance cache (Map<SoundEvent, HTMLAudioElement>) to support the iOS autoplay-unlock workaround (same element instance must be unlocked, not a fresh one per play)"

key-files:
  created:
    - frontend/public/sound/Move.mp3
    - frontend/public/sound/Capture.mp3
    - frontend/public/sound/Check.mp3
    - frontend/public/sound/Checkmate.mp3
    - frontend/public/sound/Victory.mp3
    - frontend/public/sound/Defeat.mp3
    - frontend/public/sound/Draw.mp3
    - frontend/public/sound/LowTime.mp3
    - frontend/public/sound/GenericNotify.mp3
    - frontend/src/lib/sounds.ts
    - frontend/src/lib/__tests__/sounds.test.ts
  modified:
    - README.md

key-decisions:
  - "Vendored lila's public/sound/sfx directory (Enigmahack, AGPLv3+), not the non-free 'standard' set D-08 originally named (RESEARCH Pitfall 1 correction)"
  - "Checkmate.mp3 is a real byte-copy of Check.mp3's audio, mirroring an upstream symlink that raw.githubusercontent.com serves as literal target-path text rather than resolved binary content for non-API raw fetches"
  - "SoundEvent's single 'game-end' member maps to Checkmate.mp3 as the representative clip (Claude's discretion) — Victory/Defeat/Draw remain vendored unused by sounds.ts today for a future surface wanting win/loss/draw-specific sounds"
  - "Test isolation via vi.resetModules() + dynamic import per test case (not a single shared module import), since sounds.ts caches Audio instances and listeners at module scope and would otherwise bleed a prior test's mocked Audio constructor into the next test"

patterns-established:
  - "Guest-usable, default-ON, real-toggle localStorage preference: flat non-email-scoped key + useSyncExternalStore, distinct from useUserFlag's one-shot per-user flag pattern"

requirements-completed: [PLAY-08]

coverage:
  - id: D1
    description: "Move/capture/check/game-end sounds vendored (AGPLv3+ lila sfx, license-corrected from D-08's non-free 'standard' set) and playable on demand via playSound(event)"
    requirement: "PLAY-08"
    verification:
      - kind: unit
        ref: "src/lib/__tests__/sounds.test.ts#defaults to unmuted when the storage key is absent, and playSound calls Audio.play with the Move asset"
        status: pass
      - kind: unit
        ref: "src/lib/__tests__/sounds.test.ts#dispatches the %s asset (%s) [capture/check/game-end]"
        status: pass
    human_judgment: false
  - id: D2
    description: "Two D-09 extra events (low-time warning, draw-declined blip) exist as distinct SoundEvent members with their own assets"
    requirement: "PLAY-08"
    verification:
      - kind: unit
        ref: "src/lib/__tests__/sounds.test.ts#dispatches the %s asset (%s) [low-time/draw-declined]"
        status: pass
    human_judgment: false
  - id: D3
    description: "Sounds default ON; boolean mute toggle persists to localStorage across reloads and works for guests (flat, non-email-scoped key)"
    requirement: "PLAY-08"
    verification:
      - kind: unit
        ref: "src/lib/__tests__/sounds.test.ts#defaults to unmuted when the storage key is absent..."
        status: pass
      - kind: unit
        ref: "src/lib/__tests__/sounds.test.ts#is a no-op after setMuted(true), and audible again after setMuted(false)"
        status: pass
      - kind: unit
        ref: "src/lib/__tests__/sounds.test.ts#persists the mute preference to localStorage under MUTE_KEY and notifies useMuted subscribers"
        status: pass
    human_judgment: false
  - id: D4
    description: "iOS audio-unlock workaround (unlockAudio plays+immediately pauses each preloaded clip) so bot-initiated sounds fire after the first user gesture"
    requirement: "PLAY-08"
    verification:
      - kind: unit
        ref: "src/lib/__tests__/sounds.test.ts#unlockAudio calls play then pause on each preloaded clip"
        status: pass
    human_judgment: true
    rationale: "The unit test proves the play-then-pause call sequence on a mocked Audio constructor, but whether this genuinely unlocks audible playback on real iOS Safari (the actual Pitfall 4 concern) can only be confirmed on a real device during Phase 169's end-of-phase UAT once plan 04/06 wire the game loop that calls unlockAudio from a real first gesture."
duration: 20min
completed: 2026-07-12
status: complete
---

# Phase 169 Plan 03: Sound Assets + sounds.ts Audio Module Summary

**Vendored AGPLv3+ lila `sfx` sound clips plus a standalone `sounds.ts` module (HTMLAudioElement playback, guest-usable persisted mute, iOS unlock) covering PLAY-08 and D-09's two extra events.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-07-12T21:28:00Z
- **Completed:** 2026-07-12T21:34:00Z
- **Tasks:** 2
- **Files modified:** 11 (9 vendored audio assets + sounds.ts + sounds.test.ts + README.md)

## Accomplishments
- Vendored 9 real AGPLv3+ MP3 clips (Move, Capture, Check, Checkmate, Victory, Defeat, Draw, LowTime, GenericNotify) from lila's `public/sound/sfx` directory — the license-correct substitute for D-08's originally-named non-free "standard" set
- Added README "## Sound Assets" section crediting Enigmahack + AGPLv3+, mirroring the existing "## Engine Binaries" precedent
- Built `sounds.ts`: `SoundEvent` union, `playSound`, `useMuted`/`setMuted` (default-ON, guest-usable, real toggle semantics), `unlockAudio` (iOS autoplay-unlock workaround)
- 10 passing unit tests covering default-unmuted state, per-event asset dispatch, mute no-op/audible round-trip, localStorage persistence + subscriber notification, unlock play-then-pause ordering, and a localStorage-failure degradation path

## Task Commits

1. **Task 1: Vendor the license-correct lila sfx sound set + README attribution (D-08 corrected)** — `619c8818` (feat)
2. **Task 2: sounds.ts audio module — event playback, mute persistence, iOS unlock (PLAY-08, D-09/D-10)** — `2da84daf` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `frontend/public/sound/Move.mp3`, `Capture.mp3`, `Check.mp3`, `Checkmate.mp3`, `Victory.mp3`, `Defeat.mp3`, `Draw.mp3`, `LowTime.mp3`, `GenericNotify.mp3` — vendored AGPLv3+ lila sfx clips
- `frontend/src/lib/sounds.ts` — the audio module: `SoundEvent`, `MUTE_KEY`, `playSound`, `useMuted`, `setMuted`, `unlockAudio`
- `frontend/src/lib/__tests__/sounds.test.ts` — 10 unit tests
- `README.md` — new "## Sound Assets" section

## Decisions Made
- Vendored `sfx` (not "standard") per RESEARCH.md Pitfall 1's license correction — verified the 9 downloaded files are real audio via `file`, not placeholder text.
- `Checkmate.mp3` reconstructed as a byte-identical copy of `Check.mp3` because lila's own `sfx/Checkmate.mp3` is a git symlink to `Check.mp3`, and `raw.githubusercontent.com` serves symlinks as their literal target-path text (9 bytes: `"Check.mp3"`) rather than resolving to the binary content for a plain (non-API) raw fetch. Verified by fetching and inspecting the byte content before correcting.
- `SoundEvent`'s single `'game-end'` member (per the plan's literal signature) is mapped to `Checkmate.mp3` — the plan's own `SOUND_FILES` design only has one game-end slot despite three other game-end-flavored clips (Victory/Defeat/Draw) being vendored; those remain available under `public/sound/` for a future surface that wants win/loss/draw-specific sounds, but expanding `SoundEvent` to discriminate them was out of this plan's scope (would be a Rule 4 architectural change to the frozen type signature the plan specifies).
- Test isolation required `vi.resetModules()` + dynamic `import('../sounds')` per test case, not a single top-level import — `sounds.ts`'s module-scoped `audioCache` Map and `listeners` Set would otherwise carry a prior test's mocked `Audio` constructor into subsequent tests, silently reusing stale mock instances.

## Deviations from Plan

None - plan executed exactly as written. The two decisions above (Checkmate.mp3 reconstruction, game-end asset mapping) were resolved within the plan's own explicit scope/signature (`game-end→a game-end clip`), not deviations requiring a rule classification.

## Issues Encountered
- `raw.githubusercontent.com` does not resolve git symlinks for binary raw fetches — discovered when `Checkmate.mp3` downloaded as a 9-byte text file (`"Check.mp3"`) instead of audio. Resolved by copying the already-downloaded `Check.mp3`'s real audio bytes, which is faithful to the upstream symlink relationship (both point to the same sound in lila's own repo).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `sounds.ts`'s `playSound`/`useMuted`/`setMuted`/`unlockAudio` are ready for Plan 04 (`useBotGame` fires events on move/capture/check/game-end/low-time/draw-declined transitions, calls `unlockAudio()` from the first user gesture) and Plan 05 (`GameControls` renders the mute toggle).
- The `unlockAudio` play-then-pause sequence is unit-tested against a mocked `Audio` constructor but not yet verified on a real iOS Safari device — flagged as `human_judgment: true` in the coverage block; real-device verification should happen once Plan 04/06 wire the actual first-gesture call site, as part of end-of-phase UAT.
- No blockers for Plan 04.

---
*Phase: 169-clocked-board-game-loop-usebotgame*
*Completed: 2026-07-12*

## Self-Check: PASSED

- All 7 key files (9 vendored audio assets sampled via 5, sounds.ts, sounds.test.ts) verified present on disk.
- All 3 commit hashes (619c8818, 2da84daf, c105ba70) verified present in git log.
