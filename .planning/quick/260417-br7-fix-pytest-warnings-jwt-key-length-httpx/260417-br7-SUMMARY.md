---
quick_id: 260417-br7
description: Fix pytest warnings (JWT key length + httpx cookies)
date: 2026-04-17
status: complete
---

# Quick Task 260417-br7: Summary

## Outcome

Removed all pytest warning noise. `uv run pytest` now reports `775 passed in 7.05s` with zero warnings.

## Changes

### `tests/conftest.py`
Added a 51-byte `SECRET_KEY` env var override next to the existing `SENTRY_DSN` stub, before `app.core.config` is imported. Eliminates `InsecureKeyLengthWarning` (PyJWT) across all JWT-emitting tests (~75+ warnings). The production default `"change-me-in-production"` is 23 bytes — below RFC 7518 §3.2 minimum for HS256.

### `tests/test_oauth_csrf.py` (3 sites)
Moved `cookies={_CSRF_COOKIE: ...}` from `client.get()` into `httpx.AsyncClient(...)` constructor. Each client is created per-test and used for a single request, so the scope is unchanged.

### `tests/test_guest_google_promotion.py` (4 sites)
Same pattern. Clients here are shared across multiple requests (guest-create, register, callback), but no other endpoint validates the `flawchess_oauth_csrf` cookie, so promotion to the constructor is a no-op for those calls.

## Verification

```
$ uv run pytest 2>&1 | grep -cE "(Warning|warning)"
0

$ uv run pytest
============================= 775 passed in 7.05s ==============================
```

## Decisions

- **Fix, not suppress.** Both warnings were trivial to fix at the source. No `filterwarnings` added to pyproject.toml.
- **Cookie placement: constructor, not `client.cookies.set()`.** Constructor is more declarative and keeps test setup visually compact. The "pollution" of unrelated requests with a harmless CSRF cookie is acceptable since no other endpoint reads it.
- **Test SECRET_KEY is a fixed literal, not random.** Tests that generate and validate JWTs within a single process don't need secret rotation; a stable value keeps assertions reproducible if any test ever compares signed tokens.
