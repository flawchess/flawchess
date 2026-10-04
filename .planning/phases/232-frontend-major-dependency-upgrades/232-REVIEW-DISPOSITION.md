---
phase: 232
review: 232-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "`dataCollection.urlQueryParams` does not scrub `event.request.url`, so the password-reset JWT still reaches Sentry"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "`typescript` alias range was loosened from `~6.0.3` to `^6.0.2`, but typescript-eslint caps at `<6.1.0`"
  - id: IN-01
    severity: info
    disposition: open
    title: "The privacy-baseline test checks only the mocked init arguments, and the deny-list contents are only partly pinned"
  - id: IN-02
    severity: info
    disposition: open
    title: "vite-plugin-pwa 2.x makes `workbox-build` and `workbox-window` peer dependencies that `package.json` does not declare"
  - id: IN-03
    severity: info
    disposition: open
    title: "The deny terms are broad substrings, and `SENTRY_PII_KEY_DENYLIST` is a mutable `string[]`"
open: 3
total: 5
recorded: 2026-10-04T12:29:54.450Z
---

# Phase 232: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | 232-REVIEW-FIX.md |
| WR-02 | warning | fixed | 232-REVIEW-FIX.md |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
