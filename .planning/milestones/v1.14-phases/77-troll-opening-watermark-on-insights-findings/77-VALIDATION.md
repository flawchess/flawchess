---
phase: 77
slug: troll-opening-watermark-on-insights-findings
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
---

# Phase 77 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Mirrors the Validation Architecture in `77-RESEARCH.md`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest@4.1.1 (frontend) |
| **Config file** | None — vitest auto-discovers; component tests use `// @vitest-environment jsdom` directive |
| **Quick run command** | `cd frontend && npm test -- --run trollOpenings.test.ts` |
| **Full suite command** | `cd frontend && npm test -- --run` |
| **Estimated runtime** | ~1s quick / ~30s full |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm test -- --run trollOpenings.test.ts` (or the most relevant component test if the task touched a component)
- **After every plan wave:** Run `cd frontend && npm test -- --run` + `cd frontend && npm run lint && npm run knip`
- **Before `/gsd-verify-work`:** Full suite green + `cd frontend && npm run build` succeeds (catches asset import + tsc errors) + manual visual verification at desktop and 375px mobile
- **Max feedback latency:** ~30 seconds for full suite

---

## Per-Task Verification Map

Decisions from `77-CONTEXT.md` are mapped to tests (no formal REQ-IDs for this phase).

| Decision | Behavior to verify | Test Type | Automated Command | File Exists | Status |
|----------|--------------------|-----------|-------------------|-------------|--------|
| D-08 | `deriveUserSideKey` golden inputs: starting position, post-1.e4, kings-only, all-empty rank, full FEN with side token, board-only FEN | unit | `cd frontend && npm test -- --run trollOpenings.test.ts` | ❌ Wave 0 | ⬜ pending |
| D-08 | `isTrollPosition` returns true when key in set, false otherwise; routes to correct side-set | unit | same as above | ❌ Wave 0 | ⬜ pending |
| D-02, D-03, D-04, D-05 | Watermark renders on `OpeningFindingCard` with correct testid, opacity 30%, `pointer-events: none`, both mobile + desktop | component | `cd frontend && npm test -- --run OpeningFindingCard.test.tsx` | ✅ extends existing | ⬜ pending |
| D-05 | Watermark renders for both `weakness` and `strength` classifications (always-on regardless of severity) | component | same as above | ✅ extends existing | ⬜ pending |
| D-04 | `Moves` and `Games` link buttons remain clickable when watermark is present | component | same as above | ✅ extends existing | ⬜ pending |
| D-06 | Move Explorer inline icon renders when `result_fen` is in troll set; absent otherwise | component | `cd frontend && npm test -- --run MoveExplorer.test.tsx` | ✅ extends existing | ⬜ pending |
| D-07 | Move Explorer icon has `hidden sm:inline-block` (or equivalent) class — assert class, not visibility (jsdom default is desktop-width) | component | same as above | ✅ extends existing | ⬜ pending |
| D-10 | Side-just-moved derived correctly from parent `position` side-to-move token (parent ` w ` → check white-side keys for the candidate that white plays) | component | same as above | ✅ extends existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/lib/trollOpenings.test.ts` — unit tests for `deriveUserSideKey` + `isTrollPosition` (covers D-08). Uses `vi.mock('@/data/trollOpenings', () => ({ WHITE_TROLL_KEYS: new Set([...]), BLACK_TROLL_KEYS: new Set([...]) }))` so it doesn't depend on the curated data module being final.
- [ ] No new framework install — vitest is already configured.
- [ ] No new shared fixtures — reuse existing `makeFinding` (in `OpeningFindingCard.test.tsx`) and `makeEntry` (in `MoveExplorer.test.tsx`).

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|-----------|-------------------|
| Curation list correctness | D-01 | Hand-pruning is a hard human checkpoint — only a human can decide whether the Englund Gambit is "fun but legit" vs. troll-tier | After running the curation script, surface the full candidate list to the user; require explicit approval before committing `frontend/src/data/trollOpenings.ts` |
| Mobile visual check (Insights card watermark) at 375px | D-03 | Layout fit + visual balance against severity border-left tint — not assertable in jsdom | Open DevTools responsive mode at 375px; navigate to Insights; verify watermark sits bottom-right behind text without clipping the prose/links column |
| Desktop visual check (Insights card watermark) | D-02 | Visual balance with the `MOBILE_BOARD_SIZE`/`DESKTOP_BOARD_SIZE` boards alongside | Load Insights at typical desktop viewport; confirm watermark reads as a subtle stamp |
| Mobile suppression of Move Explorer icon | D-07 | jsdom default viewport is desktop-width, so suppression must be manually verified | DevTools responsive mode at 375px; open Move Explorer; confirm troll icon is absent next to qualifying SAN rows |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies declared
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`trollOpenings.test.ts`)
- [ ] No watch-mode flags (all commands use `--run`)
- [ ] Feedback latency < 30s
- [ ] Curation hand-pruning checkpoint flagged as `autonomous: false` in the relevant plan task
- [ ] `nyquist_compliant: true` set in frontmatter when sign-off is granted

**Approval:** pending
