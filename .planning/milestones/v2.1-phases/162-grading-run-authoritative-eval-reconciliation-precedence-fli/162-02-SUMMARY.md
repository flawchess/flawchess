---
phase: 162-grading-run-authoritative-eval-reconciliation-precedence-fli
plan: 02
subsystem: ui
tags: [react, typescript, stockfish, chess-eval, sigmoid]

# Dependency graph
requires:
  - phase: 162-01
    provides: buildEvalLookup flipped to grading-first precedence, resolveReconciledBest(evalLookup, candidateUcis, mover, tieBreakUci)
provides:
  - unionSans extended with the free run's own top-2 root SANs, gated on a freeRunCommitted signal (D-02/D-09)
  - reconciledBestUci — the single canonical reconciled-argmax memo in Analysis.tsx, consumed by qualityBySan
  - qualityBySan's classifyMoveQuality pin re-sourced from reconciledBestUci instead of the raw free-run bestSan (D-03)
affects: [162-03, Analysis.tsx arrow/verdict/eval-bar/card wiring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "freeRunCommitted signal (pvLines non-empty AND not analyzing) gates a display consumer's contribution to a shared candidate union, avoiding a stale-position false-commit"
    - "A single reconciledBestUci memo per page, resolved once over the grading keyspace and threaded to every downstream consumer instead of each consumer re-deriving its own argmax pin"

key-files:
  created: []
  modified:
    - frontend/src/pages/Analysis.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx

key-decisions:
  - "freeRunCommitted declared as a plain const (not useMemo) — cheap boolean derivation, no need for memoization overhead"
  - "unionSans kept to a SINGLE Array.from(new Set(...)).sort() call across all three contributors (Maia/FC/free-run), per D-02's explicit no-second-sort constraint"
  - "reconciledBestUci iterates grading.gradeMap.keys() directly (Pitfall 3 keyspace) — NOT unionSans, which is a broader superset only used to seed the grading run's own search"
  - "Fixed a pre-existing test broken by 162-01's precedence flip (Rule 1): 'Reconciled eval provenance (SC1 precedence)' asserted the OLD free-run-first badge value (+3.1); inverted to assert the grading value (+0.8) now that buildEvalLookup resolves overlaps to the grading run"
  - "Mirror-image D-03 test verified indirectly via MaiaMoveQualityBar's positionVerdict prose (testid maia-position-verdict), not the MovesByRatingChart's recharts SVG — the chart requires a ResponsiveContainer mock + real container sizing Analysis.test.tsx doesn't provide, while positionVerdict's escape/bad-move roles cleanly distinguish the reconciled-best move from a demoted free-run bestSan without touching recharts"
  - "Extended the useMaiaEngine test mock with a settable maiaState.perElo (previously hardcoded to []) so the mirror-image test can exercise MaiaMoveQualityBar's totalMass>0 gate"

patterns-established:
  - "Test a reconciled-argmax label flip through the lowest-friction rendering surface that distinguishes best from non-best (positionVerdict's escape/bad roles), not necessarily the surface named in the plan prose (the chart), when the named surface has jsdom rendering costs the test file doesn't already pay"

requirements-completed: [D-02, D-03, D-09, D-10, D-11]

coverage:
  - id: D1
    description: "The free run's top-2 root SANs join the grading union only after the free run's bestmove commits for the current position (pvLines non-empty AND not analyzing)"
    requirement: D-02
    verification:
      - kind: integration
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#Grading run gating (Phase 158, SEED-087 SC2) > excludes the free run's top-2 root SANs from the grading union while it is still analyzing, and includes them once it has committed (Phase 162 D-02/D-09)"
        status: pass
    human_judgment: false
  - id: D2
    description: "freeRunCommitted signal gates the union extension using !engine.isAnalyzing; bestSan stays free-run-derived and unchanged as the union INPUT (D-11 anti-circularity)"
    requirement: D-09
    verification:
      - kind: integration
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#Grading run gating (Phase 158, SEED-087 SC2) > excludes the free run's top-2 root SANs from the grading union while it is still analyzing, and includes them once it has committed (Phase 162 D-02/D-09)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A single reconciledBestUci memo is computed once per render over the grading gradeMap keyspace, tie-broken toward the free-run bestSan, with no pinned-label state; a non-bestSan move with the strictly higher reconciled eval becomes the designated Best and the free-run bestSan is demoted"
    requirement: D-03
    verification:
      - kind: integration
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#Reconciled eval provenance (Phase 158, SEED-087) > mirror-image label case: a non-bestSan move with the strictly higher reconciled eval becomes the chart's Best, and the free-run bestSan is demoted (Phase 162 D-03)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engineEvalLookup.test.ts#resolveReconciledBest (Phase 162 D-03)"
        status: pass
    human_judgment: false
  - id: D4
    description: "qualityBySan's classifyMoveQuality call passes the reconciled argmax's SAN (or null when ungraded) instead of the raw free-run bestSan; no useState/useRef label-pin state introduced"
    requirement: D-10, D-11
    verification:
      - kind: other
        ref: "grep -n reconciledBestUci frontend/src/pages/Analysis.tsx (single memo, consumed by qualityBySan); grep confirms no best-SAN useState/useRef added"
        status: pass
    human_judgment: false

# Metrics
duration: 20min
completed: 2026-07-10
status: complete
---

# Phase 162 Plan 02: Grading-run-authoritative eval reconciliation — union extension + reconciled label pin Summary

**Extended the shared grading union with the free run's own top-2 root moves (gated on a bestmove-commit signal) and added the single canonical `reconciledBestUci` argmax memo that now drives the Moves-by-Rating chart's Best/Good labels, closing the mirror-image bug where a free-run pin could label a lower-eval move Best.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-07-10T10:20:00Z (approx)
- **Completed:** 2026-07-10T10:40:00Z (approx)
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `unionSans` now also contains the free run's top-2 root SANs (via `pvLines[0]`/`pvLines[1]`), but ONLY once the free run has committed a bestmove for the current position (`freeRunCommitted = pvLines.length > 0 && !isAnalyzing`) — closes the "no uncovered displayed move" gap: the grading union now covers everything the Stockfish card shows.
- `bestSan` stays unchanged and free-run-derived, preserved as the grading-union INPUT (D-11 anti-circularity — deriving it from the downstream reconciled argmax would be circular).
- New `reconciledBestUci` memo: the single canonical reconciled-argmax value, resolved once per render via `resolveReconciledBest` (from 162-01) over `grading.gradeMap`'s own SAN keyspace converted to UCI (Pitfall 3 — the SAME keyspace `qualityBySan` iterates, not the broader `unionSans`), tie-broken toward the free run's own `bestSan`.
- `qualityBySan`'s `classifyMoveQuality` call now pins the SAN form of `reconciledBestUci` instead of the raw free-run `bestSan` — the chart's "Best" label can no longer contradict the reconciled eval.
- No pinned-label state introduced (D-10): `reconciledBestUci` re-derives fresh from `evalLookup`/`grading.gradeMap`/`position`/`bestSan` on every render.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend unionSans with free-run top-2, gated on bestmove commit (D-02/D-09)** - `70091c7e` (feat)
2. **Task 2: Canonical reconciledBestUci memo + re-source qualityBySan labels (D-03/D-10/D-11)** - `88ee6dbb` (feat)

_Note: both tasks are `tdd="true"` — implementation and test changes for each task were verified together (`npx vitest run` confirmed green) before each atomic commit._

## Files Created/Modified
- `frontend/src/pages/Analysis.tsx` - `freeRunCommitted` const added; `unionSans` extended with the gated free-run top-2 contribution (single sort+dedup preserved); new `reconciledBestUci` memo; `qualityBySan`'s `classifyMoveQuality` pin re-sourced; `evalLookup` docstring corrected to grading-first precedence (Rule 1 deviation, see below)
- `frontend/src/pages/__tests__/Analysis.test.tsx` - new D-02/D-09 gating test; new D-03 mirror-image label test; fixed the stale SC1-precedence test (Rule 1); extended the `useMaiaEngine` mock with a settable `maiaState.perElo`

## Decisions Made
- `freeRunCommitted` is a plain `const`, not a `useMemo` — the boolean is cheap to derive on every render and adding memoization would be pure overhead.
- `unionSans` keeps exactly ONE `Array.from(new Set(...)).sort()` call across all three contributors (Maia/FC/free-run), per D-02's explicit "no second sort" constraint.
- `reconciledBestUci` iterates `grading.gradeMap.keys()` directly (Pitfall 3 keyspace), not the broader `unionSans` (which only seeds the grading run's own search and is not itself the reconciliation keyspace).
- The D-03 mirror-image test is verified through `MaiaMoveQualityBar`'s `positionVerdict` prose (`data-testid="maia-position-verdict"`) rather than the `MovesByRatingChart`'s recharts SVG output. The chart requires a `ResponsiveContainer` mock plus a fixed-size wrapper (as `MovesByRatingChart.test.tsx` does) to render any visible lines in jsdom — machinery `Analysis.test.tsx` doesn't already carry. `positionVerdict`'s `escape`/`bad` move roles cleanly and directly distinguish "the reconciled-best move" from "the demoted free-run bestSan" via distinct prose fragments ("is the accurate move" vs "is objectively looser") without touching recharts, and exercise the exact same `qualityBySan` → `classifyMoveQuality` wiring the chart itself reads.
- Extended the `useMaiaEngine` mock's `maiaState` with a settable `perElo` field (previously hardcoded to `[]` in the mock's return value) — needed so the mirror-image test can populate `MaiaMoveQualityBar`'s `totalMass > 0` gate and `selectCandidatesByMass`'s union pass-through.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a pre-existing test broken by 162-01's precedence flip**
- **Found during:** Task 1 (running the plan's required `npx vitest run src/pages/__tests__/Analysis.test.tsx` verification)
- **Issue:** `Analysis.test.tsx`'s "a move graded by both the free run and the grading run displays the free-run value (SC1 precedence)" test asserted the OLD free-run-first `buildEvalLookup` precedence (badge shows the free run's `+3.1`). Plan 162-01 already flipped `buildEvalLookup` to grading-first precedence (its own files_modified only touched `engineEvalLookup.ts`/`.test.ts`, not `Analysis.test.tsx`), so this test was failing on `main` before any of this plan's own changes — confirmed by reproducing the failure via `git stash` against the post-162-01, pre-162-02 tree.
- **Fix:** Renamed the test to "displays the grading value (Phase 162 D-01 grading-first precedence)" and inverted its assertions: the badge must now contain `objectively +0.8` (the grading value) and must NOT contain `objectively +3.1` (the stale free-run value).
- **Files modified:** `frontend/src/pages/__tests__/Analysis.test.tsx`
- **Verification:** `npx vitest run src/pages/__tests__/Analysis.test.tsx` — 17/17 pass (was 16/17 with 1 failure before the fix).
- **Committed in:** `70091c7e` (Task 1 commit)

**2. [Rule 1 - Bug] Corrected `evalLookup`'s stale docstring**
- **Found during:** Task 2 (reading the surrounding memo to add `reconciledBestUci` next to it)
- **Issue:** `evalLookup`'s inline comment in `Analysis.tsx` still described the pre-162-01 free-run-first precedence ("the free run's pvLines win by construction ... a move graded by both sources always shows the free-run value"), directly contradicting the actual (grading-first) behavior since 162-01 landed — misleading documentation adjacent to code this plan's Task 2 modifies.
- **Fix:** Rewrote the comment to describe grading-first precedence, matching `engineEvalLookup.ts`'s own already-corrected docstring from 162-01.
- **Files modified:** `frontend/src/pages/Analysis.tsx`
- **Verification:** No behavior change (comment-only); `npx tsc -b` clean, full suite green.
- **Committed in:** `88ee6dbb` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bug fixes to test/doc content left inconsistent by the prior wave's precedence flip)
**Impact on plan:** Both were necessary for the plan's own required verification gate (`Analysis.test.tsx` green) to pass; neither is scope creep — both are direct, narrow corrections of stale content this plan's own diff sits next to.

## Issues Encountered

Testing the D-03 "mirror-image" label case at the `Analysis.tsx` integration level required deciding which rendering surface to assert against. The plan's `<action>` prose names the Moves-by-Rating chart, but that chart is recharts-based and `Analysis.test.tsx` doesn't mock `ResponsiveContainer` (unlike the dedicated `MovesByRatingChart.test.tsx`), so it renders no visible lines/labels in jsdom without additional test-only wiring. Resolved by asserting through `MaiaMoveQualityBar`'s `positionVerdict` prose instead, which reads the identical `qualityBySan` map and cleanly names the reconciled-best move (`escape` role, "is the accurate move") separately from a demoted free-run bestSan (`bad` role, "is objectively looser") — proving the same wiring without adding recharts test machinery.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `reconciledBestUci` is ready for Wave 3 (162-03) to thread into the arrow (`engineArrows` SF branch), the agreement verdict's `stockfishLine`, `useGameOverlay`'s eval passthrough, and the Stockfish card's re-sorted lines — per 162-PATTERNS.md and 162-03-PLAN.md's explicit reuse instruction ("do NOT re-derive an argmax here").
- No blockers. `npx vitest run src/pages/__tests__/Analysis.test.tsx src/lib/engineEvalLookup.test.ts` (30/30 pass), `npm test -- --run` (full frontend suite, 1697/1697 pass), `npx tsc -b` clean, `npm run lint` clean (0 errors).

---
*Phase: 162-grading-run-authoritative-eval-reconciliation-precedence-fli*
*Completed: 2026-07-10*

## Self-Check: PASSED

- FOUND: frontend/src/pages/Analysis.tsx
- FOUND: frontend/src/pages/__tests__/Analysis.test.tsx
- FOUND: 70091c7e
- FOUND: 88ee6dbb
