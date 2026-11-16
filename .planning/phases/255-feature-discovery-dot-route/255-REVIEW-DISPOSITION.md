---
phase: 255-feature-discovery-dot-route
review: 255-REVIEW.md
updated: 2026-11-15
findings: 9
fixed: 4
open: 5
---

# Phase 255 Review Disposition

| ID | Severity | Finding | Disposition | Evidence |
|----|----------|---------|-------------|----------|
| WR-01 | warning | Failed `done` POST never retried in the session | fixed | a571af85c, recorder test (h) |
| WR-02 | warning | Route write drops an in-flight profile refetch | fixed | de1f2eaea, recorder tests (i), (j), (k) |
| WR-03 | warning | Stamp-signature reset defeats the sent-key guard | fixed | 674854515, recorder tests (l), (m) |
| WR-04 | warning | Recorder test (d) cannot fail | fixed | d925e7fb4, mutation-checked |
| IN-01 | info | `feature_route.current` never cleared when its step resolves | open | classified harmless by the reviewer |
| IN-02 | info | CURRENT trusts the client's candidate | open | |
| IN-03 | info | `_CorruptRouteStateError` is never raised (dead code) | open | |
| IN-04 | info | Stale comments and docstrings (`useUserFlag.ts`, key format, router docstring) | open | |
| IN-05 | info | Two backend tests weaker than their names | open | |

Fix details: 255-REVIEW-FIX.md. The WR-01/WR-03 fix uses a 10 s resend cooldown
(`ROUTE_WRITE_RESEND_COOLDOWN_MS`) instead of the review's send cap; owner decisions on it are listed
in the fix report.
