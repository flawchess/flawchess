---
phase: 163
slug: gem-moves-maia-findability-move-badges-on-analysis-seed-092
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-10
---

# Phase 163 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest (existing, `frontend/package.json` `"test": "vitest run"`) |
| **Config file** | `frontend/vitest.config.ts` (existing) |
| **Quick run command** | `npx vitest run src/lib/__tests__/gemMove.test.ts` (from `frontend/`) |
| **Full suite command** | `npm test -- --run` (from `frontend/`) |
| **Estimated runtime** | ~60 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `npx vitest run src/lib/__tests__/gemMove.test.ts src/pages/__tests__/Analysis.test.tsx`
- **After every plan wave:** Run `npm test -- --run` + `npx tsc -b` + `npm run lint` + `npm run knip`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 163-01-01 | 01 | 1 | D-01 lost-position gem qualifies | — | N/A | unit | `npx vitest run src/lib/__tests__/gemMove.test.ts` | ❌ W0 | ⬜ pending |
| 163-01-01 | 01 | 1 | D-02 no opening-guard exclusion | — | N/A | unit | same file | ❌ W0 | ⬜ pending |
| 163-04-03 | 04 | 3 | D-03 ELO-rung re-evaluation | — | N/A | unit + integration | `gemMove.test.ts` + `Analysis.test.tsx` | ❌ W0 / ✅ | ⬜ pending |
| 163-01-01 | 01 | 1 | D-04 both colors | — | N/A | unit | `gemMove.test.ts` | ❌ W0 | ⬜ pending |
| 163-04-03 | 04 | 3 | D-05 mainline + explored/PV nodes | — | N/A | integration | `Analysis.test.tsx` | ✅ | ⬜ pending |
| 163-04-03 | 04 | 3 | D-06 sticky per-node cache | — | N/A | integration | `Analysis.test.tsx` | ✅ | ⬜ pending |
| 163-01-01 | 01 | 1 | D-07 `GEM_MAIA_MAX_PROB` = 0.03, imported not inlined | — | N/A | unit | `gemMove.test.ts` | ❌ W0 | ⬜ pending |
| 163-01-02 | 01 | 1 | D-07/Pitfall-4 `bucketKeyForQuality` explicit `'gem'` case | — | N/A | unit | `npx vitest run src/lib/__tests__/moveQuality.test.ts` | ✅ | ⬜ pending |
| 163-02-01 | 02 | 1 | Gem glyph single-source record + `GemIcon` | — | N/A | unit | `npx vitest run src/components/board/__tests__/boardMarkers.test.tsx` | ❌ W0 | ⬜ pending |
| 163-02-02 | 02 | 1 | `SquareMarker` gem board variant | — | N/A | unit | same file | ❌ W0 | ⬜ pending |
| 163-03-01 | 03 | 2 | Chart gem curve + Pitfall-5 `'best'` audit | — | N/A | unit | `npm test -- --run` (chart tests) | ✅ | ⬜ pending |
| 163-03-02 | 03 | 2 | Popover gem copy (`isGem`) | — | N/A | unit | `npm test -- --run` (popover tests) | ✅ | ⬜ pending |
| 163-01-01 | 01 | 1 | Free-lunch guard 1 (ES saturation) | — | N/A | unit | `gemMove.test.ts` | ❌ W0 | ⬜ pending |
| 163-01-01 | 01 | 1 | Free-lunch guard 2 (forced recapture fails C1) | — | N/A | unit | `gemMove.test.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/lib/__tests__/gemMove.test.ts` — new file: `classifyGem` + `GEM_MAIA_MAX_PROB` constant assertion + both free-lunch guards
- [ ] Extend `frontend/src/lib/__tests__/moveQuality.test.ts` — gem-override behavior and `bucketKeyForQuality` `'gem'` case
- [ ] Extend `frontend/src/pages/__tests__/Analysis.test.tsx` — `gemByNode` sticky-cache integration, squareMarkers gem-variant assembly
- [ ] `frontend/src/components/board/__tests__/boardMarkers.test.tsx` — extend if it exists, else create — icon-content `SquareMarker` variant
- Framework install: none — Vitest already configured.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Board-corner gem marker placement, chart curve color, popover copy | visual surfacing | jsdom cannot fully validate SVG/circle geometry rendering (Phase 162 precedent: arrow-provenance test needed a `clientWidth` spy workaround) | Live-browser UAT on /analysis: navigate to a known gem ply, verify violet Gem icon on board corner + move list, MovesByRatingChart curve + tooltip, popover copy |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-10 (plan-checker VERIFICATION PASSED; task map finalized against 163-01..04 plans)
