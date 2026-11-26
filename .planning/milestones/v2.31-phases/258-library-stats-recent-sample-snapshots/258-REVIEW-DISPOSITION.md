---
phase: 258
source: 258-REVIEW.md
updated: 2026-11-21
---

# Phase 258 Review Disposition

| Finding | Severity | Disposition | Note |
|---------|----------|-------------|------|
| WR-01 | warning | fixed | Pin-validity option on the TC selection store; hook test covers the Recency round-trip (commit below) |
| WR-02 | warning | fixed | Gap closure 258-05: the quiet message reads the same `otherFiltersActive` as the basis line; hint reworded by owner decision (re-review confirmed) |
| IN-01 | info | open | `count_analyzed_by_tc` keeps `require_tactic_blobs` / tactic args with no production caller |
| IN-02 | info | open | `games_cap` returned and typed, not read by the frontend |
| IN-03 | info | open | Bare `str` in `fetch_recent_window_rows`; `Mapping[str, Any]` filter kwargs |
| IN-04 | info | open | "Explicit recency" decided in two places in `library_service.py` |
| IN-05 | info | open | Two router tests seed before the `try`; one frontend test asserts less than its name |
| IN-06 | info | open | Two stale comments |
| IN-07 | info | open | `played_at IS NOT NULL` predicate never changes a production result |
| IN-08 | info | open | The quiet message hard-codes `recencyFiltered = false`; the backend invariant behind it (no quiet TC under an explicit date bound) has no test |
