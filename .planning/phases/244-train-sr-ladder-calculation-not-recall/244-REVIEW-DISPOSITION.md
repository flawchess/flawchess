---
phase: 244-train-sr-ladder-calculation-not-recall
review: 244-REVIEW.md
critical: 0
warning: 0
info: 3
open: 0
---

# Phase 244 — Code Review Disposition

| Finding | Severity | Disposition | Evidence |
|---------|----------|-------------|----------|
| IN-01 | info | fixed | `80843391c`: Door B comment no longer claims k=6 "would almost never fire" (its own math gives ~18% for p=0.5) |
| IN-02 | info | fixed | `80843391c`: migration case L (streak 1, SR fail + herring correct, no SR correct) stays unchanged; mutation (`streak >= 1 AND last_correct_at IS NOT NULL`, i.e. fall back to fail floor) fails the test. Calling `upgrade()` itself remains covered by the dev-DB alembic round trip in 244-01-SUMMARY |
| IN-03 | info | fixed | `80843391c`: "always comes" → "comes at least" CORRECT_RETRY_DAYS after the previous correct solve |
