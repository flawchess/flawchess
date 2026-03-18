# Phase 15: Enhanced Game Import Data - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Enrich the game import pipeline with clock data, termination reason, and time control improvements. Fix multi-username import sync bug, data isolation bug (user A's games visible to user B), and last_login not updating on Google SSO. Display termination reason and exact time control on game cards. No migration of existing data — tables will be emptied and reimported.

</domain>

<decisions>
## Implementation Decisions

### Clock data storage
- Store seconds remaining (from PGN `%clk` annotations) as a new column on `game_positions` table
- Store the raw clock value — time spent per move can be derived by consumers
- Use NULL when `%clk` not present (daily games, some older games)
- No UI display of clock data in this phase — store only for future use

### Termination reason
- Add TWO columns to `games` table:
  - `termination_raw` — platform's original string (e.g. chess.com's "checkmated", lichess's "mate")
  - `termination` — normalized bucket from ~6 categories: checkmate, resignation, timeout, draw, abandoned, unknown
- "Draw" bucket covers: stalemate, repetition, 50-move rule, insufficient material, agreement
- Display normalized termination on game cards (e.g. "Checkmate", "Timeout")

### Time control bucketing fix
- Fix 180+0 misclassification (currently bucket = bullet because <=180s)
- Claude decides exact boundary adjustment (strict `<` vs threshold shift) based on chess.com/lichess conventions
- Game cards show both exact time control AND bucket: e.g. "Blitz · 10+5" or "10+5 (Blitz)"
- `time_control_str` already stored — just needs to be included in API response and displayed

### Multi-username import fix
- Fix `get_latest_for_user_platform()` to filter by `(user_id, platform, username)` not just `(user_id, platform)`
- Each username gets its own sync boundary — importing "bob" after "alice" fetches bob's full history
- Keep games from both usernames — no deletion when switching usernames

### Bug fixes
- **Data isolation**: User A's games visible when logged in as user B (same browser, different accounts). Likely a caching or user_id filtering issue — investigate and fix.
- **last_login on Google SSO**: last_login updates on email/password login but NOT on Google SSO. Missing hook in the OAuth login flow — needs to be added.

### Claude's Discretion
- Exact time control bucket boundaries (as long as 180+0 = blitz)
- Clock column data type (REAL vs INTEGER seconds)
- Exact game card layout for termination and time control display
- Termination reason mapping table details per platform
- Data isolation bug root cause and fix approach

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Import pipeline
- `app/services/import_service.py` — Import orchestrator, incremental sync logic (the username bug is here)
- `app/services/normalization.py` — Game normalization, `parse_time_control()` function, platform-specific mappers
- `app/services/chesscom_client.py` — chess.com API client, PGN fetching
- `app/services/lichess_client.py` — lichess API client, NDJSON streaming
- `app/services/zobrist.py` — `hashes_for_game()` — where clock extraction from PGN should be added

### Models & schemas
- `app/models/game.py` — Game model (add termination columns here)
- `app/models/game_position.py` — GamePosition model (add clock column here)
- `app/models/import_job.py` — ImportJob model (username field already exists)
- `app/repositories/import_job_repository.py` — `get_latest_for_user_platform()` — the sync bug
- `app/schemas/analysis.py` — GameRecord schema (add termination + time_control_str to response)

### Frontend
- `frontend/src/components/results/GameCard.tsx` — Game card display (add termination + exact TC)
- `frontend/src/types/api.ts` — GameRecord type (must match backend schema changes)

### Auth
- `app/models/user.py` — User model with last_login column
- FastAPI-Users OAuth configuration — where SSO login hook needs last_login update

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `parse_time_control()` in normalization.py: handles "600+0" format and daily games — needs boundary fix only
- `hashes_for_game()` in zobrist.py: already iterates every PGN move — natural place to extract `%clk`
- `GameCard.tsx`: existing card layout with result badge, players, opening, TC bucket — extend with termination + exact TC
- ImportJob model already has `username` field — just not used in sync query

### Established Patterns
- Normalization functions per platform: `normalize_chesscom_game()` and `normalize_lichess_game()` — add termination extraction here
- Bulk insert with `ON CONFLICT DO NOTHING` — clock data follows same pattern
- GameRecord schema mirrors frontend type — both must be updated in sync
- DB wipe accepted — no Alembic migration gymnastics needed

### Integration Points
- `game_positions` bulk insert in import_service.py: add clock_seconds to the insert
- Analysis API GameRecord response: add `termination`, `time_control_str` fields
- GameCard.tsx: display new fields from enriched API response
- FastAPI-Users OAuth backend: hook for last_login update on SSO login

</code_context>

<specifics>
## Specific Ideas

- Time control display format: "Blitz · 10+5" or similar showing both bucket and exact control
- Termination shown as small text/badge alongside the W/D/L result on game cards
- 180+0 should classify as blitz (matching chess.com/lichess conventions)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-enhanced-game-import-data*
*Context gathered: 2026-03-18*
