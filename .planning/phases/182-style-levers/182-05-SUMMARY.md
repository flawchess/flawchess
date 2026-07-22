---
phase: 182-style-levers
plan: "05"
subsystem: frontend-engine
tags: [flawchess-engine, bot-style, style-levers, maia, headless-measurement]

# Dependency graph
requires:
  - phase: 182-02
    provides: "botDrawGate.ts contempt/resign-threshold/hysteresisFloor semantics + RESIGN_MIN_FULLMOVE/RESIGN_HYSTERESIS_TURNS defaults"
  - phase: 182-03
    provides: "styleLinesFor(style, side) curated per-style SAN-prefix sets + the Style union"
  - phase: 182-04
    provides: "BotStyleParams shape, classifyMoveFeatures, applyStylePriorReweighting, applyStyleScoreShaping, styleBookWeighting"
provides:
  - "ATTACKER_STYLE / TRICKSTER_STYLE / GRINDER_STYLE / WALL_STYLE — the 4 named style bundles as concrete BotStyleParams data"
  - "BOT_STYLE_BUNDLES: Record<Style, BotStyleParams> — the lookup Phase 183's persona registry will reference"
  - "scripts/style-lever-measurement.mjs — headless D-11 measurement script (prior_reweighting + score_shaping lanes) reusable for future re-tuning"
  - "reports/data/style-lever-measurement-*.tsv — committed tuning evidence"
affects: ["182-06-selectBotMove-wiring", "182-07-useBotGame-wiring", "183-persona-registry"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Headless Node measurement script family member (calibration-harness.mjs/gem-elo-calibration.mjs conventions): real onnxruntime-web Maia inference via node-engine-providers.mjs, live frontend imports via the @/ alias hook, mulberry32-seeded determinism"
    - "Expected-weighted-frequency metric (sum(weight_i * feature_i) / sum(weight_i)) instead of single-argmax-pick sampling — the closed-form expectation of what samplePolicy/sampleRankedLines would draw in the long run, avoiding a noisy/binary argmax-flip signal at small N"
    - "[ASSUMED] -> \"Tuned (D-12)\" doc-comment lifecycle for hand-tuned magnitudes, citing the measured shift or (for non-measured fields) the cross-style test-suite ordering invariant that confirms the final value"

key-files:
  created:
    - frontend/src/lib/engine/botStyleBundles.ts
    - frontend/src/lib/engine/__tests__/botStyleBundles.test.ts
    - scripts/style-lever-measurement.mjs
    - reports/data/style-lever-measurement-2026-07-21T22-10-35-424Z.tsv
  modified: []

key-decisions:
  - "STYLE-01/STYLE-03 requirements left Pending (not marked complete) despite this plan shipping the bundles those requirements describe — the requirement text ('each persona plays a style-specific book' / 'Human-rung personas get prior reweighting') describes RUNTIME behavior that only exists once Plans 06/07 wire BOT_STYLE_BUNDLES into selectBotMove.ts/useBotGame.ts; this plan only defines the data + proves the transforms shift feature frequency in isolation. Mirrors the established partial-delivery pattern from Plans 151-03/154-01/155-01/155-02 (see STATE.md Decisions log)."
  - "Wall's isExchange multiplier needed raising from the initial 1.5 to 4.0 (via an intermediate 3.0) — the measurement TSV showed 1.5 was too weak to overcome the redistribution pull of Wall's OTHER discounts (isPawnAdvance 0.9 / isPawnStorm 0.5-then-0.3 / isCheck 0.8) onto the large share of legal moves matching no feature at all; a companion isPawnStorm retune from 0.5 to 0.3 was needed to keep storm's own delta negative once the larger exchange boost started pulling relative weight off pawn-advance moves generally."
  - "The measurement script's score_shaping lane synthesizes a RankedLine[] fixture (practicalScore = raw Maia policy probability, childScoreSpread = a hand-picked tactical/quiet proxy keyed off classifyMoveFeatures) rather than running a real MCTS search — a full search is out of scope for a fast headless measurement pass per the plan's own read_first guidance ('applyStyleScoreShaping where a search snapshot is available or synthesized'); clearly documented in the script's module header as an approximation, not a real search statistic."
  - "The measurement metric is the expected weighted feature frequency under the (re)weighted distribution (sum(weight_i * feature_i) / sum(weight_i)), not a single argmax-move pick — an argmax-only measurement at the initial N=20 verification run showed mostly-zero deltas (Maia's opening-position policy is already sharply peaked, so most feature multipliers weren't large enough to flip the single most-likely move), while the expected-frequency metric is mathematically the closed-form long-run average of what samplePolicy's weightedPick would draw, giving a continuous, sensitive signal suited to iterative tuning."

patterns-established:
  - "Style bundle magnitude documentation: every BotStyleParams numeric field carries either a 'Tuned (D-12)' comment citing its measured TSV delta (for featureMultipliers, which the script directly tallies) or citing the cross-style ordering invariant a unit test asserts (for scoreBonus/varianceBonus/contempt/threshold/hysteresisFloor/bookBoost, which the TSV cannot individually tally) — no bare [ASSUMED] tag survives past Task 3 of a tuning plan."

requirements-completed: []  # STYLE-01/03 partial delivery only (see key-decisions); STYLE-02/04 were already Complete from Plans 02/04 and are unaffected by this plan

coverage:
  - id: D1
    description: "The 4 named style bundles (Attacker/Trickster/Grinder/Wall) ship as plain exported BotStyleParams data constants with no function fields, each pinning a curated book boost, feature multipliers, score bonus, signed contempt, and resign threshold/hysteresis"
    requirement: "STYLE-01"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/botStyleBundles.test.ts#BOT_STYLE_BUNDLES"
        status: pass
    human_judgment: false
  - id: D2
    description: "Grinder never resigns early (threshold far below the other 3 styles, high hysteresis) and has high-positive contempt; Wall has slightly-negative contempt; Attacker boosts checks/captures/pawn storms; Trickster carries its identity via variance preference + the book"
    requirement: "STYLE-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/botStyleBundles.test.ts#identity assertions (182-CONTEXT.md specifics)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The D-11 measurement script (scripts/style-lever-measurement.mjs) runs each style over N sampled positions, importing the LIVE applyStylePriorReweighting/applyStyleScoreShaping/classifyMoveFeatures/BOT_STYLE_BUNDLES via the @/ alias hook, and reports per-style move-feature-frequency shift vs the unstyled baseline into a committed reports/data/ TSV"
    requirement: "STYLE-03"
    verification:
      - kind: unit
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/style-lever-measurement.mjs --n 20 (writes reports/data/style-lever-measurement-*.tsv, echoes MEASUREMENT_TSV_OK)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Magnitudes are hand-tuned (D-12) until each style's identity-feature shift is visibly present without gross strength distortion; final values documented inline with their tuning rationale, no bare [ASSUMED] tag remains"
    requirement: "STYLE-04"
    verification:
      - kind: unit
        ref: "grep '\\[ASSUMED\\]' frontend/src/lib/engine/botStyleBundles.ts (zero matches) + reports/data/style-lever-measurement-2026-07-21T22-10-35-424Z.tsv"
        status: pass
    human_judgment: true
    rationale: "The 'visible shift without gross strength distortion' judgment call is a qualitative D-12 tuning target the user reviews the committed TSV against during UAT — verified programmatically that no [ASSUMED] tag remains and that headline identity features have the correct sign, but the final 'is this the right amount of flavor' call is the human's per the plan's own UAT framing."
  - id: D5
    description: "styleLinesFor selection inside each bundle stays color-correct — no White-only style book ever boosts Black-side lines"
    requirement: "STYLE-01"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/botStyleBundles.test.ts#references a non-empty curated book set for at least one color"
        status: pass
    human_judgment: false

# Metrics
duration: 55min
completed: 2026-07-21
status: complete
---

# Phase 182 Plan 05: Style Bundles + D-11 Measurement Script Summary

**Ships the 4 named style bundles (Attacker/Trickster/Grinder/Wall) as BotStyleParams data plus a headless Maia-backed measurement script that empirically tuned every magnitude until each style's identity features show a visible, correctly-signed shift vs baseline.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3
- **Files created:** 4 (botStyleBundles.ts, its test file, the measurement script, the committed evidence TSV)

## Accomplishments

- `frontend/src/lib/engine/botStyleBundles.ts`: `ATTACKER_STYLE`/`TRICKSTER_STYLE`/`GRINDER_STYLE`/`WALL_STYLE` as concrete `BotStyleParams` constants plus `BOT_STYLE_BUNDLES: Record<Style, BotStyleParams>`. Attacker boosts checks (1.8x)/captures (1.5x)/pawn storms (1.6x); Grinder boosts exchanges (1.8x), never resigns early (threshold 0.02, hysteresisFloor 10, far below the other 3 styles' 0.12-0.18/3-5 band) and carries the largest-magnitude positive contempt (0.15); Wall boosts exchanges (4.0x, tuned up from an initial 1.5x that measured negative) while discouraging pawn advances (0.9x) and storms (0.3x), with the only negative contempt (-0.08); Trickster carries its identity mainly through the highest `varianceBonus` (0.2) and its curated troll/swindle book, keeping prior-reweighting multipliers deliberately mild.
- `scripts/style-lever-measurement.mjs`: a headless Node measurement script in the `calibration-harness.mjs`/`gem-elo-calibration.mjs` family — real onnxruntime-web Maia inference at a representative Human-rung ELO (1000) over a mulberry32-seeded sample of the curated opening-book FEN corpus, measuring two independent levers: `prior_reweighting` (the closed-form expected feature frequency under `applyStylePriorReweighting`'s reweighted distribution) and `score_shaping` (the same technique over a synthesized `RankedLine[]` fixture run through `applyStyleScoreShaping` and the same softmax weighting `sampleRankedLines` uses). Emits a TSV of style x lever x feature baseline/styled/delta frequencies. Imports `applyStylePriorReweighting`/`applyStyleScoreShaping`/`classifyMoveFeatures`/`BOT_STYLE_BUNDLES` from the live frontend source via the `@/` alias hook — no reimplementation.
- Hand-tuned Wall's `isExchange` from 1.5 -> 3.0 -> 4.0 (with a companion `isPawnStorm` retune 0.5 -> 0.3) after the measurement showed the initial magnitude produced a NEGATIVE exchange-frequency delta — the redistribution pull of Wall's other discounts onto non-feature-matching moves diluted a 1.5x boost faster than it could compensate. Found and fixed a bug in the measurement script's own `synthesizedChildScoreSpread` heuristic during this iteration (see Deviations).
- Every `botStyleBundles.ts` magnitude that started `[ASSUMED]` now carries a `Tuned (D-12)` doc comment citing either its measured TSV delta or the cross-style test-suite ordering invariant that confirms it (zero bare `[ASSUMED]` tags remain).
- Committed `reports/data/style-lever-measurement-2026-07-21T22-10-35-424Z.tsv` (N=200, seed=1, elo=1000) as the tuning evidence: every style's headline identity feature shows a correctly-signed delta in the `prior_reweighting` lane (Attacker check/capture/storm all positive; Grinder exchange positive; Wall exchange positive, pawn-advance/storm negative).

## Task Commits

1. **Task 1: Define the 4 named style bundles as exported BotStyleParams constants** — `a647a2ee` (feat)
2. **Task 2: Author the D-11 style-lever measurement script** — `3581af4a` (feat)
3. **Task 3: Hand-tune bundle magnitudes against the measurement report (D-12)** — `082e6a44` (feat)

## Files Created

- `frontend/src/lib/engine/botStyleBundles.ts` — `ATTACKER_STYLE`/`TRICKSTER_STYLE`/`GRINDER_STYLE`/`WALL_STYLE`/`BOT_STYLE_BUNDLES`
- `frontend/src/lib/engine/__tests__/botStyleBundles.test.ts` — 24 tests: structural (no function fields, all-4-keys), identity (contempt sign, Attacker check/capture, Grinder exchange, Wall exchange+storm, never-resigns-early ordering, variance-preference ordering), and book-reference (non-empty for at least one color, bookBoost in [20,50])
- `scripts/style-lever-measurement.mjs` — the D-11 headless measurement script
- `reports/data/style-lever-measurement-2026-07-21T22-10-35-424Z.tsv` — the committed tuning evidence

## Verification

- `cd frontend && npx vitest run src/lib/engine/__tests__/botStyleBundles.test.ts` — 24/24 passing.
- `cd frontend && npx vitest run src/lib/engine/` — 255/255 passing across all 17 engine test files (no regression).
- `cd frontend && npx tsc -b` — zero errors.
- `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/style-lever-measurement.mjs --n 20` — writes a non-empty TSV to `reports/data/`; the plan's exact verify command (`... && ls reports/data/style-lever-measurement-*.tsv >/dev/null 2>&1 && echo MEASUREMENT_TSV_OK`) prints `MEASUREMENT_TSV_OK`.
- `npm run lint` / `npm run knip` — clean (0 errors; only 3 pre-existing unrelated `coverage/` generated-artifact warnings).
- `grep -n "function applyStylePriorReweighting\|function applyStyleScoreShaping\|function classifyMoveFeatures" scripts/style-lever-measurement.mjs` — no matches (prohibition: no reimplementation).

## Decisions Made

- STYLE-01/STYLE-03 requirements left `[ ]` Pending rather than marked complete — see key-decisions in frontmatter for the full rationale (this plan ships the data, Plans 06/07 wire it into actual gameplay, mirroring the established partial-delivery pattern elsewhere in this project's history).
- Switched the measurement metric from a single argmax-move pick to the expected weighted feature frequency (`sum(weight_i * feature_i) / sum(weight_i)`) after the initial argmax-based design showed mostly-zero deltas at N=20 — Maia's opening-position policy is already sharply peaked around one move, so most of the initial feature-multiplier magnitudes weren't large enough to flip the single top pick. The expected-frequency metric is the closed-form long-run average of what `samplePolicy`'s `weightedPick` would actually draw, giving a continuous, sensitive signal.
- The score_shaping lane synthesizes a `RankedLine[]` fixture (practicalScore from real Maia policy, childScoreSpread from a documented hand-picked proxy) rather than running a real MCTS search, per the plan's own explicit allowance ("applyStyleScoreShaping where a search snapshot is available or synthesized") — a full search is out of scope for a fast headless measurement pass.
- Wall's `isExchange` needed 4.0 (not the initially-assumed 1.5) to overcome the redistribution pull of its other discounts; paired with lowering `isPawnStorm` from 0.5 to 0.3 to hold storm's own delta negative at the new exchange magnitude.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed synthesizedChildScoreSpread's isCapture/isExchange precedence bug in the measurement script**
- **Found during:** Task 3 (hand-tuning against the measurement report)
- **Issue:** `classifyMoveFeatures` defines `isExchange = isCapture && (roughly-even trade)`, so every exchange move is ALSO a capture. The measurement script's `synthesizedChildScoreSpread` checked `isCheck || isCapture || isPawnStorm` before `isExchange`, so every exchange fell through to the "tactical" `HIGH_SPREAD_PROXY` branch instead of the intended "quiet" `LOW_SPREAD_PROXY` branch — the `isExchange`-specific branch was unreachable. This masked Grinder's exchange preference in the `score_shaping` lane (measured delta was negative before the fix).
- **Fix:** Reordered the checks so `isExchange` is tested first.
- **Files modified:** `scripts/style-lever-measurement.mjs`
- **Verification:** Re-ran the measurement at N=200; Grinder's `score_shaping` `isExchange` delta flipped from negative to `+0.0019` (correctly signed).
- **Committed in:** `082e6a44` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for the measurement script to correctly report the score_shaping lever's effect; no scope creep — the fix stayed inside the file the plan already scoped for Task 2/3.

## Issues Encountered

None beyond the auto-fixed bug above.

## User Setup Required

None — pure TypeScript/Node modules and a committed TSV, no external service configuration.

## Next Phase Readiness

- `BOT_STYLE_BUNDLES` is ready for Plan 06 (`selectBotMove.ts` wiring) and Plan 07 (`useBotGame.ts` wiring) to consume directly by `Style` key.
- `scripts/style-lever-measurement.mjs` is reusable if Plans 06/07's real-search wiring reveals the search-branch identity signal needs further retuning once `applyStyleScoreShaping` runs over REAL `RankedLine[]` output instead of the synthesized fixture this plan used.
- No blockers. `npx tsc -b` (zero errors) and `npx vitest run src/lib/engine/` (255/255) both green.

---
*Phase: 182-style-levers*
*Completed: 2026-07-21*

## Self-Check: PASSED

All claimed files found on disk; all 3 commits (`a647a2ee`, `3581af4a`, `082e6a44`) found in git log.
