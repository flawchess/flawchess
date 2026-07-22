---
phase: 184-persona-calibration-strength-honesty
plan: 01
subsystem: testing
tags: [calibration-harness, node, persona-registry, bot-style, fixture-check]

requires:
  - phase: 182-style-levers
    provides: BotStyleParams / BOT_STYLE_BUNDLES (Attacker/Trickster/Grinder/Wall), applyStylePriorReweighting/applyStyleScoreShaping
  - phase: 183-persona-registry-bots-page
    provides: PERSONA_REGISTRY (24-slot Record<PersonaId, Persona>), the provisional botElo===rung placeholder this phase's later plans replace
  - phase: 180-bot-strength-curves (v2.6)
    provides: calibration-bot-cell-schedule.mjs's pure anchor-selection primitives (internalRatingFor, pickLocateAnchors, locateEstimate, selectMeasureBracket, bracketBeyondLadder), the two-pass locate/measure cell loop in calibration-harness.mjs
  - phase: 181-strength-lookup-curves (v2.6)
    provides: BOT_STRENGTH_LOOKUP / BOT_STRENGTH_RANGES (frontend/src/generated/botStrengthCurves.ts) — the D-01 retargeting source
provides:
  - An optional `style` seam on calibration-harness.mjs's playGame/selectBotMoveOnce, proven byte-identical when absent (STYLE-05)
  - scripts/lib/calibration-persona-cell-schedule.mjs — PersonaId-keyed persona-cell schedule (ALL_PERSONA_CELLS, personaCellKey, retargetedBotEloFor, presetNameForBlend)
  - A fixture check proving the PersonaId-keyed schedule genuinely guards against the (botElo, blend) collision bug (Pitfall 1), verified via revert-and-confirm-fails
affects: [184-02-persona-calibration-sweep, 184-04-persona-labels-and-disclosure]

tech-stack:
  added: []
  patterns:
    - "Conditional spread for an optional pass-through field (`...(style !== undefined ? { style } : {})`) rather than a literal `key: undefined`, to keep an object shape byte-identical when the field is absent"
    - "Reuse pure anchor-selection primitives from a sibling scheduler module via import, never fork, when only the outer grouping key changes"
    - "Deterministic stub-provider fixture (fixed rng, hand-derived cumulative weights) to prove a real orchestration function's behavior change, instead of a probabilistic multi-game real-engine comparison"

key-files:
  created:
    - scripts/lib/calibration-persona-cell-schedule.mjs
    - scripts/lib/calibration-persona-cell-schedule.check.mjs
  modified:
    - scripts/calibration-harness.mjs
    - scripts/lib/calibration-determinism.check.mjs

key-decisions:
  - "presetNameForBlend reuses playStyle.ts's deriveActivePlayStylePreset (throwing on its null case) rather than re-deriving the 0/0.05/0.5 literals locally"
  - "The 'defined style bundle reaches selectBotMove' proof uses a deterministic stub-provider fixture (fixed rng=0.5, hand-derived cumulative weights over a real chess position) calling the real selectBotMove directly, mirroring calibration-parity.check.mjs's established convention, instead of a probabilistic full real-engine game comparison — faster and non-flaky"
  - "playCellAnchorGames also gained a `style` param (forwarded, undefined today) even though the plan's collision/schedule work targets a future sweep script, since the plan explicitly required every playGame caller to forward style"
  - "requirements-completed left empty: CAL-04 is shared across Plans 01/02/04 (frontmatter) — this plan delivers only the harness style seam + persona-cell schedule (the measurement machinery), not the actual sweep/fit/labels; marking CAL-04 complete here would be a partial-delivery false-positive"

patterns-established:
  - "Pattern: fail-loud pure scheduler module (throws on unmeasured/unrecognized input, never silently defaults), mirroring calibration-bot-cell-schedule.mjs's internalRatingFor discipline"

requirements-completed: []

coverage:
  - id: D1
    description: "playGame/selectBotMoveOnce thread an optional style param into selectBotMove's BotSettings only when defined, leaving unstyled BotSettings objects byte-identical to the pre-184 harness"
    requirement: "CAL-04"
    verification:
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-determinism.check.mjs (real Maia+Stockfish engines, 3 full games, exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A defined style bundle (ATTACKER_STYLE) reaches selectBotMove and deterministically changes its output via the prior-reweighting branch"
    requirement: "CAL-04"
    verification:
      - kind: unit
        ref: "scripts/lib/calibration-determinism.check.mjs — deterministic stub-provider assertion (STYLE_CHECK_FEN, fixed rng=0.5)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A new PersonaId-keyed persona-cell schedule (ALL_PERSONA_CELLS) produces exactly 24 distinct cells with D-01 retargeted botElo (Phase-181 lookup), never colliding on (botElo, blend)"
    requirement: "CAL-04"
    verification:
      - kind: unit
        ref: "scripts/lib/calibration-persona-cell-schedule.check.mjs (5 assertion groups, exit 0)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The collision-regression guard (rung-1800 personas sharing botElo=2300/blend=DEEP_BLEND still key to 4 distinct cells) is a genuine mutation-tested proof, not a symbol-presence check"
    requirement: "CAL-04"
    verification:
      - kind: unit
        ref: "scripts/lib/calibration-persona-cell-schedule.check.mjs assertion (2) — manually reverted personaCellKey to a (botElo, blend)-derived key, confirmed the check fails (1 !== 4), then restored"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-07-22
status: complete
---

# Phase 184 Plan 01: Harness Style Seam & Persona-Cell Schedule Summary

**Threaded an optional style param through the calibration harness's one `selectBotMove` call site (proven byte-identical when absent) and built a new PersonaId-keyed persona-cell schedule that keeps the 4 rung-1800 personas (and other retargeting collisions) independently measurable instead of silently merged.**

## Performance

- **Duration:** ~35 min (includes a ~6 min real-engine verification run: 3 full Maia+Stockfish games)
- **Completed:** 2026-07-22
- **Tasks:** 3
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments
- `playGame`/`selectBotMoveOnce` in `scripts/calibration-harness.mjs` accept an optional `style` (`BotStyleParams`) and forward it into `selectBotMove`'s `BotSettings.style` via a conditional spread — never a literal `style: undefined` key — so every existing (unstyled) bot-cell caller is provably unaffected.
- `scripts/lib/calibration-persona-cell-schedule.mjs`: a new pure, engine-free module that imports (never forks) the Phase-180 bot-cell scheduler's anchor-selection primitives, adding only persona-specific logic — `presetNameForBlend`, `retargetedBotEloFor` (D-01 retargeting via `BOT_STRENGTH_LOOKUP`, with an 800-rung floor clamp), `personaCellKey` (the Pitfall-1 fix), and the 24-entry `ALL_PERSONA_CELLS`.
- `scripts/lib/calibration-persona-cell-schedule.check.mjs`: a pure-logic fixture proving 24 distinct cells, correct retargeting (Human-1200 → 1900, 800-rung → clamped 1100), fail-loud `presetNameForBlend`, and — the load-bearing assertion — that the 4 rung-1800 personas (which genuinely collide on `botElo=2300`/`blend=DEEP_BLEND` after retargeting) still produce 4 distinct `personaCellKey` values.
- Extended `scripts/lib/calibration-determinism.check.mjs` with two new real-verified assertions: the STYLE-05 absent-style byte-identity invariant (via 3 full real-engine games), and a deterministic stub-provider proof that a defined style bundle reaches `selectBotMove` and flips its move choice.

## Task Commits

Each task was committed atomically:

1. **Task 1: Thread an optional style param through the harness move seam** - `becef489` (feat) — committed last (after the real-engine verification passed), even though implemented first
2. **Task 2: New persona-cell schedule module (PersonaId-keyed, retargeting-aware)** - `a299d9ee` (feat)
3. **Task 3: Pure-logic fixture check for the persona-cell schedule** - `8ef761ab` (test)

_Note: Task 1's commit landed after Tasks 2/3 in git history because its real-engine verification (3 full Maia+Stockfish games) ran in the background while Tasks 2/3's pure-logic work and verification completed first; all three tasks were implemented and verified independently before any commit._

## Files Created/Modified
- `scripts/calibration-harness.mjs` - `playGame` gains an optional `style` param, conditionally spread into `selectBotMove`'s settings; `playCellAnchorGames` forwards it (undefined today)
- `scripts/lib/calibration-determinism.check.mjs` - two new assertions: absent-style byte-identity (real engines) and defined-style-reaches-selectBotMove (deterministic stub)
- `scripts/lib/calibration-persona-cell-schedule.mjs` (new) - PersonaId-keyed persona-cell schedule, reusing the bot-cell scheduler's pure anchor primitives
- `scripts/lib/calibration-persona-cell-schedule.check.mjs` (new) - fixture check, including a manually-verified collision-regression proof

## Decisions Made
- `presetNameForBlend` reuses `playStyle.ts`'s `deriveActivePlayStylePreset` (wrapping its `null` case into a thrown error) instead of re-deriving the `0`/`0.05`/`0.5` → `human`/`light`/`deep` mapping locally — one source of truth for the blend-to-preset mapping.
- The "defined style bundle reaches selectBotMove" proof (Task 1 acceptance criterion) is implemented as a deterministic stub-provider fixture inside `calibration-determinism.check.mjs` — real `selectBotMove`, fixed `rng=0.5`, hand-derived cumulative weights over a real chess position (`1.e4 d5`, capture vs quiet-advance) — rather than a second/third full real-engine game relying on a real Maia policy distribution to probabilistically diverge. This mirrors the repo's own `calibration-parity.check.mjs` stub-provider convention and is both faster and non-flaky. The STYLE-05 absent-style invariant is still verified with real engines (3 full games), since that assertion needs the actual harness plumbing, not just `selectBotMove`'s own contract.
- `playCellAnchorGames` (the bot-cell sweep's `playGame` caller) also gained a `style` param, forwarded but unused by any existing call site — the plan explicitly required every `playGame` caller to forward `style`, in preparation for a future persona-sweep orchestration script.
- Left `requirements-completed` empty. `CAL-04` is shared across Plans 01/02/04 (per frontmatter); this plan delivers only the measurement machinery (harness style seam + persona-cell schedule), not the actual overnight sweep, fit, or calibrated labels. Marking it complete here would misrepresent partial delivery — Plan 02 (the actual sweep + fit) and Plan 04 (labels + disclosure) close it.

## Deviations from Plan

None — plan executed exactly as written. The two acceptance-criteria proof techniques (real-engine determinism check extension in Task 1, deterministic-stub style-reaches-selectBotMove assertion) were both explicitly anticipated by the plan's own action text ("assert via a stubbed/instrumented selectBotMove capturing the received BotSettings"); the chosen implementation captures the *effect* on `selectBotMove`'s output deterministically rather than instrumenting the function itself, since `selectBotMove` is a static ES-module import with no injection seam — this is Claude's Discretion within the plan's explicit allowance for harness style-wiring details.

## Issues Encountered
- The real-engine determinism check (3 full Maia+Stockfish games at the shipped bot budget) took ~6 minutes to complete — run in the background and monitored to completion rather than blocking synchronously. No functional issues; all assertions passed on the first real-engine run.

## Mutation-Test Verification (Pitfall 1 collision guard)

Per the project's "prove a gap fix by reverting it" convention: `personaCellKey` was temporarily mutated to derive a key from `(botElo, blend)` instead of `personaId` (looking up each persona's retargeted `botElo`/`blend` and keying by those instead of the id). Re-running `calibration-persona-cell-schedule.check.mjs` against this mutation failed exactly as expected — `1 !== 4` on the rung-1800 collision assertion — confirming the fixture genuinely guards against the regression, not just checking symbol presence. The mutation was then reverted and the check re-verified green before committing.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 02 can now build the actual overnight persona-calibration sweep orchestration (`bin/run_persona_calibration_sweep.sh` + `calibration_persona_fit.py`) directly on top of `ALL_PERSONA_CELLS` and the style-threaded `playGame`.
- No blockers. The style seam and schedule are both independently fixture-verified; the real-engine harness path (blend=1, full search) is confirmed unaffected by the change.

---
*Phase: 184-persona-calibration-strength-honesty*
*Completed: 2026-07-22*

## Self-Check: PASSED

All files and commits referenced in this summary were verified present on disk / in git history.
