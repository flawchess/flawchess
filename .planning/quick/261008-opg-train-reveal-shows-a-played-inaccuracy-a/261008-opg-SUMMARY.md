---
quick_id: 261008-opg
status: complete
commit: 44e037dd3
---

# Quick 261008-opg Summary: Train reveal shows a played inaccuracy as inaccuracy

- Removed `toDisplayQuality` (Phase 200 D-04/D-05 collapse). The played move's
  arrow (yellow), corner badge (?!), step highlight (shared yellow), "Your move"
  header icon, the game move, and free-play moves now show the real quality.
- "Also fine" alternatives keep the good badge and dark-green arrow (explicit
  mapping in `buildTrainRevealOverlay`; the existing alternative test still
  passes).
- Tests: replaced the 5 `toDisplayQuality` cases; the dedupe badge, step
  highlight and TrainReveal header tests now assert inaccuracy; new arrow +
  glyph color test. Mutation check: reverting the arrow color fails the new
  test.
- 85 test files / 1576 tests green across train, hooks, analysis; eslint,
  build, knip clean. No browser UAT (forcing a graded inaccuracy in dev is
  impractical); the component tests cover every render site.
