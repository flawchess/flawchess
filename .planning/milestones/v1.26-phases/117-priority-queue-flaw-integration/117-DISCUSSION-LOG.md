# Phase 117: Priority Queue + Flaw Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-13
**Phase:** 117-Priority Queue + Flaw Integration
**Areas discussed:** PV persistence policy, Within-tier ordering, 117↔118 enqueue boundary, Flaw flow-through, PV/best_move backfill policy

---

## PV persistence policy

### Storage split + best-move encoding
| Option | Description | Selected |
|--------|-------------|----------|
| best_move-all, UCI text | best_move for every position as UCI (~+240 MB), full PV flaw-adjacent only | ✓ |
| best_move-all, int2 encoded | Same split, 2-byte int encoding (~+80 MB), opaque | |
| Only flaw-adjacent PV | Drop best_move-for-all; keep D-7 as-is | |

**User's choice:** UCI (after asking how UCI differs from SAN and whether UCI is better here).
**Notes:** Confirmed UCI over SAN — engine-native, board-arrow-friendly (from/to squares),
SEED-039 classifier consumes UCI, cheap PV serialization. `move_san` stays SAN for move lists.

### Flaw-PV scope
| Option | Description | Selected |
|--------|-------------|----------|
| After flawed move only | PV of the position after each flawed move (SEED-039 refutation) | ✓ |
| Flaw ply + next ply | Also the flawed move's own pre-move PV | |

**User's choice:** After flawed move only (asked for an explanation of what SEED-039 needs first).
**Notes:** Motif tagging reads the motif off the refutation line after the blunder; the
pre-move "better move" is already covered by best_move-for-all at the flaw ply.

### PV length cap
| Option | Description | Selected |
|--------|-------------|----------|
| Cap at ~12 plies | First ~12 PV plies, enough for motif ID | ✓ |
| Store full PV | No cap | |

**User's choice:** Cap at ~12 plies.

---

## Within-tier ordering

| Option | Description | Selected |
|--------|-------------|----------|
| TC-weighted, longer first | classical > rapid > blitz > bullet, then recency | ✓ |
| Pure recency (D-4 as-is) | Most-recent-first, TC ignored | |
| Longer-first + drop bullet | TC-weighted AND exclude bullet from auto/backlog (amends QUEUE-05) | |

**User's choice:** TC-weighted, longer first.
**Notes:** All TCs still covered eventually (QUEUE-05 intact); bullet just analyzed last.

---

## 117↔118 enqueue boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Mechanism + internal trigger | Full queue + tier-3 live; tier-1 via service fn + internal trigger to verify ~10s fan-out | ✓ |
| Pull real request API forward | Also ship the authenticated request endpoint in 117 | |
| Mechanism + tests only | No live enqueue path; QUEUE-03 verified only via tests | |

**User's choice:** Mechanism + internal trigger.
**Notes:** User button + auto-window enqueue + coverage UX deferred to Phase 118.

---

## Flaw flow-through

### Analyzed signal vs oracle columns
| Option | Description | Selected |
|--------|-------------|----------|
| Separate signals | full_evals_completed_at = engine marker; keep is_analyzed lichess-only | ✓ (with refinement) |
| Unify is_analyzed | classify writes counts for all; move D-116-04/WR-02 to a provenance column | |
| You decide | Defer to planning | |

**User's choice:** Separate signals — **with the refinement** "make sure the oracle columns
in the games table are filled; explain the planned approach."
**Notes:** Resolved to: add `lichess_evals_at` provenance column (set at import for lichess
%evals); repoint D-116-04 + WR-02 onto it; `classify_game_flaws` fills the oracle count
columns for engine games; `is_analyzed` becomes "has flaws (any source)";
one-time backfill of `lichess_evals_at` for existing `white_blunders IS NOT NULL` games.
User confirmed "Yes, lock it."

### Cache refresh
| Option | Description | Selected |
|--------|-------------|----------|
| Per-user, debounced | Mark dirty on completion, invalidate once per window / on next request | ✓ |
| Invalidate per game | Per-game-completion invalidation | |
| Rely on TTL | Natural expiry | |

**User's choice:** Per-user, debounced.

---

## PV/best_move backfill policy

User surfaced (post-discussion) that pre-117-analyzed games lack best_move/PV.

| Option | Description | Selected |
|--------|-------------|----------|
| Demand-driven + forward | Forward capture; pre-117 games backfilled only on re-touch (explicit request / 118 auto-window); parallel PV marker | ✓ |
| Full backfill re-enqueue | Mark all pre-117-analyzed games for a lowest-tier re-pass; re-pays search on the whole analyzed population | |
| Forward-only, no re-touch | Only 117+ games; permanent hole for pre-117-analyzed games | |

**User's choice:** Demand-driven + forward (D-117-12).
**Notes:** best_move/PV are search outputs not stored pre-117 → recoverable only by
re-search. Two pre-117 populations affected (116-engine-analyzed + lichess-analyzed).
Needs a second completion dimension (e.g. full_pv_completed_at) so re-touch sees
"eval-complete, PV-missing" without re-clearing the eval marker.

---

## Claude's Discretion

- Final column types/encodings (`best_move` varchar(5) UCI; `pv` Text UCI; `lichess_evals_at` timestamp).
- Jobs/lease table schema + lease/report mechanics (TTL, status states, requeue), constrained by SEED-012 D-8.
- Job/lease granularity (game-unit tiers 2/3; tier-1 position-batch fan-out per D-4 addendum).
- Round-robin fairness state implementation.
- `classify_game_flaws` idempotency mechanics.
- Internal tier-1 trigger shape; debounce window + exact flaw-dependent cache set.

## Deferred Ideas

- Phase 118: "analyze more" button, auto-window enqueue, coverage indicators, in-flight status, guest account-promotion UX.
- Full multi-source `eval_source` provenance column for client workers (SEED-012 D-8 phase 2).
- Pool-priority tier-aware EnginePool scheduling (116-CONTEXT deferred).
- Reviewed-not-folded todos: phase-70 amendments, bitboard storage, benchmark rebuild/skill (keyword false-positives).
