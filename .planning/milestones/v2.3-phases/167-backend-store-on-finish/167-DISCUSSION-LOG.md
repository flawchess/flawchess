# Phase 167: Backend Store-on-Finish - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-11
**Phase:** 167-backend-store-on-finish
**Areas discussed:** Analytics exclusion + is_computer_game, Player-rating conversion, Persistence reuse seam, Endpoint contract + UUID + guest auth (all delegated to Claude)

---

## Gray areas presented

| Area | Description | Selected |
|------|-------------|----------|
| Analytics exclusion + is_computer_game | Where to exclude 'flawchess' (query_utils vs per-site); is_computer_game flag | |
| Player-rating conversion: server vs client | Server-authoritative from user_rating_anchors vs client-supplied; rating_source values | |
| Persistence reuse seam | Reuse `_flush_batch` (1-item batch) vs slimmer single-game persist | |
| Endpoint contract + UUID + guest auth | POST body, client-minted UUID idempotency, guest auth via existing User rows | |

**User's choice:** "You decide" — delegated all four areas to Claude.
**Notes:** User selected "You decide" on the multiSelect. Given the extensive
locked decisions (ROADMAP SC1–SC5, STORE-01…07, SEED-091 #1/#5) and a thorough
codebase scout, Claude made grounded calls for every area rather than deep-diving
interactively. See CONTEXT.md D-01…D-17.

---

## Claude's Discretion

All four areas were delegated. Key calls made:
- **Analytics exclusion** — implement in `apply_game_filters` (D-02); flagged that
  SEED-091's "exclusion for free" is factually wrong (routers default `platform=None`
  → all platforms). `is_computer_game=True`, `rated=False` (D-04).
- **Rating conversion** — server-authoritative via `fetch_anchors_for_user`, NULL
  when no anchor; `rating_source ∈ {lichess, chesscom, blended} | NULL` (D-05…D-08).
- **Persistence seam** — reuse `_flush_batch` with a 1-item batch, endpoint owns its
  transaction; idempotency via the existing unique constraint (D-09…D-11).
- **Endpoint** — `POST /bots/games`, standard authed dep (covers guests), server
  parses PGN, `[%clk]` gate rejects with 422 (D-12…D-15).
- Side-table shape + `Platform` Literal extension locked (D-16/D-17); exact
  names/module placement left to the planner.

## Deferred Ideas

- Post-launch curve fitting (CALX-01 / SEED-091 #3) — later milestone.
- Frontend flawchess filter chip / Bots-vs-Library surfacing UX — Phase 171.
