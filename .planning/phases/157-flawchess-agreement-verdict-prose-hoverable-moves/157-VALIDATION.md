---
phase: 157
slug: flawchess-agreement-verdict-prose-hoverable-moves
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-07
---

# Phase 157 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.1.7 + Testing Library (`frontend/package.json`) |
| **Config file** | `frontend/vite.config.ts` (vitest config co-located; no separate `vitest.config.ts`) |
| **Quick run command** | `cd frontend && npx vitest run src/lib/flawChessVerdict.test.ts` |
| **Full suite command** | `cd frontend && npm test -- --run` (= `vitest run`) |
| **Estimated runtime** | ~10–30 seconds (targeted files); full suite ~1–2 min |

---

## Sampling Rate

- **After every task commit:** `cd frontend && npx vitest run src/lib/flawChessVerdict.test.ts src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx` (adjust to planner's chosen filenames)
- **After every plan wave:** `cd frontend && npm run lint && npm test -- --run`
- **Before `/gsd-verify-work`:** Full suite green AND `cd frontend && npx tsc -b` (or `npm run build`) — `noUncheckedIndexedAccess` errors on `rankedLines[0]`/`pvLines[0]` indexing do NOT surface via `npm run lint`/`npm test` alone (CLAUDE.md gotcha).
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 157-01-* | 01 | 1 | REVIEW-02 (D-04) | — | Same UCI move → `aligned` tier | unit | `npx vitest run src/lib/flawChessVerdict.test.ts` | ❌ W0 | ⬜ pending |
| 157-01-* | 01 | 1 | REVIEW-02 (D-05) | — | drop < BLUNDER_DROP → `safe`; drop ≥ BLUNDER_DROP → `sharp` | unit | `npx vitest run src/lib/flawChessVerdict.test.ts` | ❌ W0 | ⬜ pending |
| 157-01-* | 01 | 1 | REVIEW-02 (D-06) | — | Null objective eval (either side) → `null` result, no bogus tier | unit | `npx vitest run src/lib/flawChessVerdict.test.ts` | ❌ W0 | ⬜ pending |
| 157-02-* | 02 | 2 | REVIEW-02 (D-02/D-03) | — | `engineEnabled === false` → muted prompt, no comparison | component | `npx vitest run src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx` | ❌ W0 | ⬜ pending |
| 157-02-* | 02 | 2 | REVIEW-02 (D-09) | — | Hover span → `onHoverMovesChange` with one `{san, color}` in tier color | component | same file | ❌ W0 | ⬜ pending |
| 157-02-* | 02 | 2 | REVIEW-02 (D-10) | — | Popover shows engine-labeled two lines; SF-pick omits FC line when engine didn't rank that move | component | same file | ❌ W0 | ⬜ pending |
| 157-02-* | 02 | 2 | REVIEW-02 (D-11) | — | Click (popover open) → `onPlayMove(san)`; first click only reveals | component | same file (mirror `MaiaMoveQualityBar.test.tsx` pointerDown+click) | ❌ W0 | ⬜ pending |
| 157-02-* | 02 | 2 | REVIEW-01/SC4 | — | Verdict renders identically on `?game_id&ply` and free analysis | manual/UAT | N/A — single shared `flawChessCard` JSX | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky. Task IDs are placeholders — the planner assigns final IDs.*

---

## Wave 0 Requirements

- [ ] `frontend/src/lib/flawChessVerdict.test.ts` — tier classification (D-04/D-05/D-06), mirroring `positionVerdict.test.ts` fixture style with direct `RankedLine`/`PvLine` fixtures.
- [ ] `frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx` — hover/click/popover mechanics, mirroring `MaiaMoveQualityBar.test.tsx`'s `fireEvent.focus`/`fireEvent.pointerDown`+`fireEvent.click` patterns. NOTE: this new component has no MiniBoard hover preview, so it needs NO `matchMedia`/`ResizeObserver` stubs — use the simpler `MaiaMoveQualityBar.test.tsx` setup, NOT `FlawChessEngineLines.test.tsx`'s.
- [ ] No framework install needed — Vitest + Testing Library already configured and used by both mirror-target files.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Game-review parity (`?game_id&ply`) | REVIEW-01 / SC4 | Both surfaces share the single `flawChessCard` JSX (`Analysis.tsx` ~L1476–1515), so this is a parity *confirmation*, not new code — no automated seam to assert beyond the component test | Open `/analysis?game_id=<id>&ply=<n>` with Stockfish on; confirm the verdict prose + hover arrows + popover + click-to-play behave identically to free analysis |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter (planner/executor sets when Wave 0 tests exist)

**Approval:** pending
