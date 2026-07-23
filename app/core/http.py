"""Shared HTTP client constants for outbound platform API calls."""

# Identifying User-Agent for all outbound platform API requests. chess.com has
# always required one; lichess started enforcing it around 2026-07-22 — requests
# with generic client UAs (python-httpx/curl) get a fake 404 {"error":"Not found"}
# from /api/games/user, which our client misread as "user not found".
USER_AGENT = "FlawChess/1.0 (github.com/flawchess/flawchess)"
