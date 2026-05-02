---
phase: 77-troll-opening-watermark-on-insights-findings
verified: 2026-04-29T00:55:00Z
status: human_needed
score: 22/22 must-haves verified (code-side)
human_verification:
  - test: "Render an OpeningFindingCard whose entry_fen+color is in the curated set on desktop and at 375px mobile (Insights → Openings → finding for Bongcloud/Grob/etc.)"
    expected: "Troll-face watermark visible in bottom-right corner of the card at ~30% opacity. On 375px mobile, the watermark must not visually obscure the Moves/Games link button text/icons (REVIEW WR-02)."
    why_human: "Pixel-level visual placement, contrast, and overlap require human inspection. CONTEXT.md D-03 explicitly mandates 375px re-verification; 77-03-SUMMARY.md does not record one."
  - test: "Open Move Explorer on desktop with a position whose candidate move leads to a troll opening (e.g. start position → e4 should NOT trigger; from a position where Ke2 is legal it should)."
    expected: "Small troll-face icon appears next to the qualifying SAN, fully opaque, sized like other inline glyphs. On 375px mobile, the icon is suppressed."
    why_human: "Visual register (fully opaque vs the 30% card watermark), inline alignment with SAN cell, and mobile suppression all need eyes on it."
  - test: "Click the Moves and Games link buttons on a troll-watermarked OpeningFindingCard"
    expected: "Both navigate as before — watermark does not steal pointer events even though it overlaps."
    why_human: "Automated tests cover this with fireEvent on Moves only; D-04 risk is real-DOM hit-testing on top of the absolute layer."
---

# Phase 77: Troll-opening watermark on Insights findings — Verification Report

**Phase Goal:** Render `troll-face.svg` as a 30%-opacity bottom-right watermark on `OpeningFindingCard` (mobile + desktop) AND a small inline icon next to qualifying SAN rows in `MoveExplorer` (desktop only) when the user-side position matches a curated troll-opening set.

**Verified:** 2026-04-29
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                              | Status     | Evidence                                                                                                           |
| --- | ------------------------------------------------------------------------------------------------------------------ | ---------- | ------------------------------------------------------------------------------------------------------------------ |
| 1   | `troll-face.svg` exists at canonical kebab-case path; gitignored `temp/` copy is untracked                         | ✓ VERIFIED | `frontend/src/assets/troll-face.svg` (26842 B). `temp/` matches `.gitignore:5` (`/temp`); `git ls-files` empty.    |
| 2   | `TROLL_WATERMARK_OPACITY = 0.30` exported from `theme.ts`                                                          | ✓ VERIFIED | `frontend/src/lib/theme.ts:83`                                                                                     |
| 3   | `deriveUserSideKey(fen, side)` pure helper exported with required FEN canonicalization                             | ✓ VERIFIED | `frontend/src/lib/trollOpenings.ts:11-20`; 7 golden-input tests in `trollOpenings.test.ts` pass                    |
| 4   | `isTrollPosition(fen, side)` consults correct side-set, returns false on malformed FEN (BL-01 fix)                  | ✓ VERIFIED | `frontend/src/lib/trollOpenings.ts:49-57` wraps call in try/catch (commit `85b4a32`); regression test added         |
| 5   | Curation script `curate-troll-openings.ts` exists, embeds `deriveUserSideKey`, prints candidates, no auto-write     | ✓ VERIFIED | `frontend/scripts/curate-troll-openings.ts`; `.cache/.gitignore` ignores `*.pgn`                                    |
| 6   | `frontend/src/data/trollOpenings.ts` exports `WHITE_TROLL_KEYS` (12) + `BLACK_TROLL_KEYS` (3) as `ReadonlySet<string>` | ✓ VERIFIED | 12 white keys (Bongcloud, Hammerschlag, Halloween, Sodium, Drunken Knight, Crab, Double Duck, Creepy Crawly, Reagan, Napoleon, Grob, Barnes); 3 black keys (Drunken Knight Variation, Borg, Fred). Bongcloud canary key present. |
| 7   | Curated set is strict Bongcloud-tier (excludes Englund/Latvian/From's/Schliemann/Damiano)                          | ✓ VERIFIED | None of the excluded openings appear in the data file.                                                              |
| 8   | OpeningFindingCard renders watermark `<img>` when `isTrollPosition(entry_fen, color)` is true                       | ✓ VERIFIED | `OpeningFindingCard.tsx:61, 180-186`; `data-testid='opening-finding-card-${idx}-troll-watermark'`                   |
| 9   | Watermark covers BOTH mobile and desktop branches via single sibling                                                | ✓ VERIFIED | Test "renders exactly once across both mobile and desktop branches" passes; `getAllByTestId` length == 1            |
| 10  | Watermark has `pointer-events-none` (D-04)                                                                         | ✓ VERIFIED | className contains `pointer-events-none`; click pass-through test asserts `onFindingClick` fires                   |
| 11  | Watermark fires regardless of classification × severity (D-05)                                                     | ✓ VERIFIED | Two tests assert weakness/major and strength/minor both render watermark                                            |
| 12  | Watermark uses `TROLL_WATERMARK_OPACITY` (no hard-coded opacity)                                                   | ✓ VERIFIED | `style={{ opacity: TROLL_WATERMARK_OPACITY }}` (`OpeningFindingCard.tsx:185`)                                       |
| 13  | Watermark absent when position not in troll set                                                                    | ✓ VERIFIED | Negative test passes; `screen.queryByTestId(...)` returns null                                                      |
| 14  | MoveExplorer derives `sideJustMoved` from `position.split(' ')[1]`                                                 | ✓ VERIFIED | `MoveExplorer.tsx:78-87`                                                                                            |
| 15  | `sideJustMoved` is passed to MoveRow as a prop                                                                     | ✓ VERIFIED | `MoveExplorer.tsx:234, 246, 259`                                                                                    |
| 16  | MoveRow renders inline troll icon when `isTrollPosition(entry.result_fen, sideJustMoved)` is true                  | ✓ VERIFIED | `MoveExplorer.tsx:268, 332-341`; `data-testid='move-list-row-${move_san}-troll-icon'`                               |
| 17  | Icon class is `hidden sm:inline-block h-3.5 w-3.5` (D-07 mobile suppression)                                       | ✓ VERIFIED | `MoveExplorer.tsx:340`                                                                                              |
| 18  | Side-routing: black-to-move parent only consults `BLACK_TROLL_KEYS`                                                | ✓ VERIFIED | "routes to BLACK_TROLL_KEYS when parent position is black-to-move (D-10)" test passes                              |
| 19  | Decorative idiom on both surfaces (`alt=""` + `aria-hidden="true"`)                                                | ✓ VERIFIED | Both render `<img alt="" aria-hidden="true">`; tests assert attributes                                              |
| 20  | Insights-side matching uses `entry_fen` + `finding.color` (D-10 Insights side)                                     | ✓ VERIFIED | `OpeningFindingCard.tsx:61` `isTrollPosition(finding.entry_fen, finding.color)`                                     |
| 21  | Move-Explorer-side matching uses `entry.result_fen` + `sideJustMoved` (D-10 Explorer side)                         | ✓ VERIFIED | `MoveExplorer.tsx:268` `isTrollPosition(entry.result_fen, sideJustMoved)`                                           |
| 22  | All test suites green; tsc and knip clean                                                                          | ✓ VERIFIED | `npm test -- --run`: 192/192 pass. `npx tsc --noEmit -p tsconfig.app.json`: exit 0. `npm run knip`: exit 0.        |

**Score:** 22/22 truths verified (code-side).

### Required Artifacts

| Artifact                                                                  | Expected                                              | Status     |
| ------------------------------------------------------------------------- | ----------------------------------------------------- | ---------- |
| `frontend/src/assets/troll-face.svg`                                      | Decorative SVG, kebab-case                            | ✓ VERIFIED |
| `frontend/src/lib/theme.ts`                                               | Exports `TROLL_WATERMARK_OPACITY = 0.30`              | ✓ VERIFIED |
| `frontend/src/lib/trollOpenings.ts`                                       | `deriveUserSideKey` + render-safe `isTrollPosition`   | ✓ VERIFIED |
| `frontend/src/lib/trollOpenings.test.ts`                                  | Golden-input unit tests (10 cases + BL-01 regression) | ✓ VERIFIED |
| `frontend/scripts/curate-troll-openings.ts`                               | Reproducible curation script                          | ✓ VERIFIED |
| `frontend/src/data/trollOpenings.ts`                                      | `ReadonlySet<string>` ×2, strict-tier curated         | ✓ VERIFIED |
| `frontend/src/components/insights/OpeningFindingCard.tsx`                 | Watermark wired, `relative` on outer div              | ✓ VERIFIED |
| `frontend/src/components/insights/OpeningFindingCard.test.tsx`            | Phase 77 describe block (9 tests)                     | ✓ VERIFIED |
| `frontend/src/components/move-explorer/MoveExplorer.tsx`                  | `sideJustMoved` derivation + inline icon in MoveRow   | ✓ VERIFIED |
| `frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx`   | Phase 77 describe block (6 tests)                     | ✓ VERIFIED |

### Key Link Verification

| From                       | To                                | Via                                                         | Status |
| -------------------------- | --------------------------------- | ----------------------------------------------------------- | ------ |
| `lib/trollOpenings.ts`     | `data/trollOpenings.ts`           | named imports `WHITE_TROLL_KEYS, BLACK_TROLL_KEYS`          | WIRED  |
| `lib/trollOpenings.ts`     | `types/api.ts`                    | `import type { Color }`                                     | WIRED  |
| `OpeningFindingCard.tsx`   | `lib/trollOpenings.ts`            | `import { isTrollPosition }`                                | WIRED  |
| `OpeningFindingCard.tsx`   | `assets/troll-face.svg`           | `import trollFaceUrl from '@/assets/troll-face.svg'`        | WIRED  |
| `OpeningFindingCard.tsx`   | `lib/theme.ts`                    | `import { TROLL_WATERMARK_OPACITY }`                        | WIRED  |
| `MoveExplorer.tsx`         | `lib/trollOpenings.ts`            | `import { isTrollPosition }`                                | WIRED  |
| `MoveExplorer.tsx`         | `assets/troll-face.svg`           | `import trollFaceUrl ...`                                   | WIRED  |
| MoveExplorer (parent)      | MoveRow (child)                   | `sideJustMoved` prop derived from `position.split(' ')[1]`  | WIRED  |
| `curate-troll-openings.ts` | `lichess.org/study/cEDAMVBB.pgn`  | fetch with cache at `frontend/scripts/.cache/cEDAMVBB.pgn`  | WIRED  |

### Data-Flow Trace (Level 4)

| Artifact                  | Data Variable          | Source                                              | Real Data | Status     |
| ------------------------- | ---------------------- | --------------------------------------------------- | --------- | ---------- |
| `OpeningFindingCard.tsx`  | `showTroll`            | `isTrollPosition(finding.entry_fen, finding.color)` | Yes       | ✓ FLOWING  |
| `MoveExplorer.tsx`        | `sideJustMoved`        | `position.split(' ')[1]` (parent prop)              | Yes       | ✓ FLOWING  |
| `MoveExplorer.tsx` (Row)  | `showTroll`            | `isTrollPosition(entry.result_fen, sideJustMoved)`  | Yes       | ✓ FLOWING  |
| `data/trollOpenings.ts`   | Set members            | Hand-pruned from cEDAMVBB.pgn + 4 manual entries    | Yes       | ✓ FLOWING  |

### Behavioral Spot-Checks

| Behavior                          | Command                                                                                | Result          | Status |
| --------------------------------- | -------------------------------------------------------------------------------------- | --------------- | ------ |
| Full frontend test suite green    | `cd frontend && npm test -- --run`                                                     | 192/192 pass    | ✓ PASS |
| TypeScript compile                | `cd frontend && npx tsc --noEmit -p tsconfig.app.json`                                 | exit 0          | ✓ PASS |
| Knip dead-export check            | `cd frontend && npm run knip`                                                          | exit 0          | ✓ PASS |
| Bongcloud canary in curated set   | `grep '8/8/8/8/4P3/8/PPPPKPPP/RNBQ1BNR' frontend/src/data/trollOpenings.ts`            | match           | ✓ PASS |
| `temp/Troll-Face.svg` not tracked | `git ls-files temp/Troll-Face.svg`                                                     | empty (ignored) | ✓ PASS |

### Requirements Coverage

D-NN are decision IDs from `77-CONTEXT.md`, not REQ-IDs in `REQUIREMENTS.md`. All 11 are verifiable:

| Decision | Description                                                                  | Source Plan | Status                |
| -------- | ---------------------------------------------------------------------------- | ----------- | --------------------- |
| D-01     | Strict (Bongcloud-tier) curation only                                        | 77-02       | ✓ SATISFIED           |
| D-02     | Bottom-right anchor, ~60-80px, 30% opacity locked                            | 77-03       | ✓ SATISFIED           |
| D-03     | Mobile parity (same anchor + opacity + sizing)                               | 77-03       | ✓ SATISFIED (code); needs human at 375px (WR-02) |
| D-04     | `pointer-events: none` so links remain clickable                             | 77-03       | ✓ SATISFIED           |
| D-05     | Always-on regardless of classification × severity                            | 77-03       | ✓ SATISFIED           |
| D-06     | Inline icon in MoveExplorer when `result_fen` matches for side-just-moved    | 77-04       | ✓ SATISFIED           |
| D-07     | Desktop only via `hidden sm:inline-block`                                    | 77-04       | ✓ SATISFIED (class); needs human at 375px |
| D-08     | Frontend FEN-derived side-only key, `Set<string>` lookup                     | 77-01       | ✓ SATISFIED           |
| D-09     | Pre-compute keys offline via reproducible Node/TS script                     | 77-02       | ✓ SATISFIED           |
| D-10     | Insights uses `entry_fen` + `finding.color`; Explorer uses `result_fen` + side-just-moved | 77-03 + 77-04 | ✓ SATISFIED |
| D-11     | Asset moved to `frontend/src/assets/troll-face.svg`, kebab-case              | 77-01       | ✓ SATISFIED (`/temp` is gitignored) |

### Anti-Patterns Found

| File                                | Severity   | Impact                                                                                           |
| ----------------------------------- | ---------- | ------------------------------------------------------------------------------------------------ |
| `MoveExplorer.tsx:78-87`            | ⚠️ Warning | REVIEW WR-05: `sideJustMoved` `useMemo` ordering is load-bearing for the friendly error message; if a future hook is inserted between this and `moveMap`, the wrong error wins. Documented and tested but fragile. Not blocking. |
| `MoveExplorer.tsx:81-85`            | ⚠️ Warning | REVIEW BL-01 (partial fix): the position-prop `throw` is still reachable. Helper `isTrollPosition` is now defensive (commit `85b4a32`), but the parent `useMemo` still throws if `position` lacks a side-to-move token. In practice the parent always feeds a full FEN (chess.js parses it for board rendering); risk is narrow but not eliminated. Not blocking. |
| `OpeningFindingCard.tsx:184`        | ℹ️ Info    | REVIEW WR-02: 64px mobile watermark may overlap Moves/Games link row at 375px. `pointer-events-none` keeps clicks working but contrast on the link text could be impacted. Needs eyes-on at 375px. |
| `frontend/knip.json`                | ℹ️ Info    | REVIEW WR-03: ignoring `src/data/trollOpenings.ts` masks future dead exports. Knip currently exits 0 either way; if the entry is no longer needed, it should be removed. Not blocking. |
| `curate-troll-openings.ts`          | ℹ️ Info    | REVIEW WR-04: `frontend/scripts/` is not included in any tsconfig; `noUncheckedIndexedAccess` enforcement is by author discipline, not by the type-checker. Not blocking — script is committed and runs cleanly under `tsx`. |

No blocker anti-patterns. The render-time crash risk that REVIEW BL-01 flagged is mitigated for the helper (try/catch wraps `deriveUserSideKey`); the residual parent-throw risk is an isolated UX-degradation, not a goal-blocker.

### Human Verification Required

See `human_verification:` in frontmatter — three items:
1. **375px mobile watermark visual check** (D-03 + REVIEW WR-02): confirm watermark does not visually obscure mobile link row.
2. **Move Explorer mobile suppression + desktop placement** (D-06/D-07): confirm icon appears next to qualifying SAN on desktop, hidden on mobile.
3. **Click pass-through under real DOM** (D-04): confirm Moves/Games buttons still navigate when watermark overlaps them.

### Gaps Summary

No code-side gaps. The phase goal is achieved at the implementation level:

- All 22 observable truths VERIFIED.
- All artifacts exist, are substantive, are wired, and propagate real data through the render chain.
- Both surfaces' tests assert presence/absence, side routing, decorative attributes, and mobile suppression behavior.
- BL-01 (the only original BLOCKER) was fixed in commit `85b4a32` — `isTrollPosition` no longer crashes on malformed FEN, and a regression test pins the behavior.
- Curated data set is strict Bongcloud-tier (12 white + 3 black keys; excludes legitimate-but-fun gambits per D-01).
- All four lower-severity REVIEW warnings remain as documented quality-of-implementation notes; none block the phase goal.

The remaining verifications (375px visual placement, click pass-through under real DOM, mobile suppression) are not testable in jsdom and are routed to the human reviewer per the standard escalation gate.

---

_Verified: 2026-04-29_
_Verifier: Claude (gsd-verifier)_
