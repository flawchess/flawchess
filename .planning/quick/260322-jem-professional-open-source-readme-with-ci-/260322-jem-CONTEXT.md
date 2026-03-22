# Quick Task 260322-jem: Professional open-source README — Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Task Boundary

Rewrite README.md to professional open-source quality. Add CI badge, screenshot gallery, self-hosting instructions, and verify open source essentials (LICENSE already exists).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

**README structure:** Keep existing sections but upgrade quality:
1. Logo + tagline + badges (CI badge added, existing tech badges kept)
2. One-paragraph pitch
3. Screenshot gallery — show 3-4 best screenshots inline (not all 6, avoid wall of images)
4. Features list (already good)
5. Quick Start (local dev — already exists, minor polish)
6. Self-Hosting (new section — Docker Compose production deployment)
7. Architecture (Zobrist — already good)
8. Contributing (expand slightly — mention issues-first workflow)
9. License + Links

**Screenshot presentation:** Inline images using GitHub relative paths (`frontend/public/screenshots/`). Pick the most impactful 3-4. Use a table or flex layout for side-by-side on desktop.

**Open source extras:** Skip CONTRIBUTING.md and issue templates for now — the README's Contributing section is sufficient for a solo-dev project. Can add later if community grows.

**Self-hosting section:** Document the production Docker Compose flow (`docker-compose.yml` with Caddy). Reference `.env.example`, list required env vars, and the 3-command deploy sequence.

**CI badge:** Use `https://github.com/flawchess/flawchess/actions/workflows/ci.yml/badge.svg` — standard GitHub Actions badge.

</decisions>

<specifics>
## Specific Ideas

- 6 screenshots available in `frontend/public/screenshots/`: board-and-move-explorer.png, filters.png, game-import.png, position-bookmarks.png, win-rate-over-time.png, chess-board-and-moves.png
- CI workflow file: `.github/workflows/ci.yml`, workflow name: "CI"
- `.env.example` already exists with good comments
- Production docker-compose.yml uses Caddy for auto-TLS
- Google OAuth is optional (app works with email/password auth)
- Sentry is optional (empty DSN disables it)

</specifics>
