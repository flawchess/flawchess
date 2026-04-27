# Open Research Questions

Open questions surfaced during exploration that need data or investigation before they
can be settled. Append new entries at the bottom; mark resolved entries with **Resolved:**
and a one-line answer + link to where the answer lives.

---

## Q-001: Effective independent test count for opening insights, post-dedupe

**Asked:** 2026-04-28 (during `/gsd-explore` on opening-insight statistical framing)

**Context:** The Phase 70/71 opening-insights classifier scans every `(entry_hash, candidate_san)` transition with `N >= 20` across plies 3..16, then collapses results via `_dedupe_within_section` (deepest-opening wins per `resulting_full_hash`) and `_dedupe_continuations` (drop downstream chains). The remaining surface is what users see.

If we ever apply multiple-comparisons correction (BH-FDR or similar — see SEED-007), we need to know roughly how many *effectively independent* tests survive dedupe per user. This sets the corrected per-test alpha needed to keep overall FDR ≤ 10%.

Anecdotally Adrian estimated 5-30 lines per typical user. We want a real distribution.

**How to answer:** One SQL query against `flawchess-prod-db` (read-only, via `mcp__flawchess-prod-db__query`):

1. For each user with ≥1000 games, replicate the `query_opening_transitions` aggregate (HAVING `N >= 20` AND `(L/N > 0.55 OR W/N > 0.55)`) for both colors under default filters (no time-control restriction, no recency cutoff, opponent_strength=any).
2. Approximate dedupe by counting distinct `resulting_full_hash` values surviving the HAVING clause (cheap proxy — the actual `_dedupe_continuations` chain-collapse is harder to express in SQL, so the count is an overcount, but a useful upper bound).
3. Report: median, p90, p99 of surviving tuple count per user, broken out by total game count (1k / 3k / 10k+).

**Why deferred:** Today the surface is positioned as "candidate hint, not diagnosis", so per-test FDR isn't load-bearing. The question becomes load-bearing when SEED-007 fires (LLM narration over opening findings, or feedback shows over-claiming).

**Resolved:** _(open)_
