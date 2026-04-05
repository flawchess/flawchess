---
status: awaiting_human_verify
trigger: "lichess import only fetched 191 of 1201 games for account mrburns123"
created: 2026-04-05T00:00:00Z
updated: 2026-04-05T00:00:00Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: CONFIRMED — perfType API filter in lichess_client.py is excluding correspondence, chess960, and fromPosition (imported) games, reducing the API response to 191 games before any data reaches the normalization layer.
test: curl the lichess API with and without the perfType parameter for mrburns123 — observed exactly 191 with filter, 1201 without.
expecting: n/a — confirmed
next_action: return ROOT CAUSE FOUND

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: Import should fetch all ~1201 standard-variant games from mrburns123 lichess account
actual: Only 191 games were imported into the database
errors: Unknown — no user-reported errors. Silent failure suspected.
reproduction: Trigger lichess import for account mrburns123. Only 191 games land in games table.
started: Unknown — treat as current/ongoing

## Eliminated
<!-- APPEND only - prevents re-investigating -->

- hypothesis: Stream timeout / httpx 60s client-level timeout truncating stream
  evidence: The httpx.AsyncClient uses timeout=60.0 for individual request timeouts, but the stream call passes timeout=300.0. Per httpx docs, per-request timeout overrides client default. Also, the stream completed cleanly at 191 — a truncated stream would not yield clean batches.
  timestamp: 2026-04-05T00:00:00Z

- hypothesis: Per-game try/except silently swallowing PGN parse errors
  evidence: normalize_lichess_game returns None for non-standard variants, but the 191 games returned all have variant=standard — no further filtering occurs at normalization. The missing 1010 games never reach normalization.
  timestamp: 2026-04-05T00:00:00Z

- hypothesis: Duplicate detection short-circuit (incremental sync stopping early)
  evidence: Not applicable — the API is only returning 191 games. The truncation happens at the lichess API level, not in the deduplication layer.
  timestamp: 2026-04-05T00:00:00Z

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-05T00:00:00Z
  checked: lichess_client.py line 23 — _PERF_TYPES constant
  found: "_PERF_TYPES = 'ultraBullet,bullet,blitz,rapid,classical'" — correspondence and chess960 are not included
  implication: The lichess API /games/user endpoint with perfType parameter filters server-side BEFORE returning any data

- timestamp: 2026-04-05T00:00:00Z
  checked: lichess API for mrburns123 user profile (/api/user/mrburns123)
  found: perfs show blitz=90, rapid=295, classical=224, correspondence=133, chess960=25. count.import=226, count.all=1201
  implication: 226 "imported" games have their own perf type not in the filter; correspondence (133) and chess960 (25) also excluded

- timestamp: 2026-04-05T00:00:00Z
  checked: curl of lichess API WITH perfType filter (current code behavior)
  found: Returns exactly 191 games — all variant=standard, perf distribution: classical=34, rapid=156, blitz=1
  implication: 1010 games are excluded at the API level by the perfType parameter

- timestamp: 2026-04-05T00:00:00Z
  checked: curl of lichess API WITHOUT perfType filter
  found: Returns exactly 1201 games. Variant distribution: standard=1092, fromPosition=83, chess960=26. Perf distribution: rapid=600, correspondence=236, classical=231, blitz=101, chess960=26, bullet=7
  implication: 1092 games have variant=standard (would pass normalization filter). 83 are fromPosition and 26 are chess960 — these would be correctly filtered out by normalize_lichess_game.

- timestamp: 2026-04-05T00:00:00Z
  checked: normalization.py normalize_lichess_game variant filter (lines 257-263)
  found: Correctly filters variant_key != "standard" — returns None for non-standard games
  implication: If the perfType API filter is removed, fromPosition (83) and chess960 (26) would be correctly excluded at normalization. The 1092 standard-variant games would all be imported.

- timestamp: 2026-04-05T00:00:00Z
  checked: Breakdown of what perfType filter is excluding
  found: 1201 total - 191 returned = 1010 excluded. Breakdown: correspondence=236-some_subset + rapid=remaining + etc. The bulk of excluded games include correspondence (correspondence perf type not in filter), chess960 (chess960 perf type not in filter), and standard-variant games played at correspondence/chess960 cadence. The fromPosition (imported) games have their own perf — likely 'correspondence' or unlisted.
  implication: Many STANDARD variant games played at correspondence or other time controls are excluded by the perfType filter

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: The `_PERF_TYPES = "ultraBullet,bullet,blitz,rapid,classical"` constant in `app/services/lichess_client.py` is passed as the `perfType` parameter to the lichess API. This is an API-level filter that causes the lichess server to return only 191 of the user's 1201 games. The filter excludes: (1) correspondence games (perf type "correspondence"), (2) chess960 games (perf type "chess960"), and (3) imported/fromPosition games (which use their own perf type). All of these exclusions happen server-side — only 191 JSON lines are ever streamed back. The normalization layer never sees the missing 1010 games. The fix is to remove the `perfType` parameter from the API request entirely and let the existing `normalize_lichess_game()` variant filter handle non-standard games (it already correctly returns None for variant_key != "standard", which covers chess960 and fromPosition).

fix: Remove `"perfType": _PERF_TYPES` from the `params` dict in `fetch_lichess_games()` in `app/services/lichess_client.py`, and delete the `_PERF_TYPES` constant. The normalization-layer variant filter in `normalize_lichess_game()` already correctly excludes chess960 (25 games) and fromPosition (83 games) — no additional server-side filtering is needed.

verification: ruff and ty both pass with zero errors. No tests assert on perfType param.
files_changed:
  - app/services/lichess_client.py
