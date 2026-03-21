# Phase 20: Rename & Branding - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish the FlawChess brand — rename all code/config/docs from Chessalytics to FlawChess, use placeholder icons (user provides final logos later), update PWA manifest, and prepare for GitHub repo transfer. No new features, no deployment, no README polish (Phase 23).

</domain>

<decisions>
## Implementation Decisions

### Logo & Visual Identity
- AI-generated logo with manual polish — but deferred: use **placeholder icons** for now
- User will provide final logos later; phase uses current chess knight icons or simple placeholders
- Icon-only in favicon/PWA icons; icon + "FlawChess" text in app header
- Logo concept direction: knight with magnifying glass (cute/comic) vs simple piece silhouette — to be decided when user provides assets
- Keep current dark theme palette (#0a0a0a background), no new accent color
- Required icon formats for user to supply later:
  - icon-192.png (192x192) — PWA icon
  - icon-512.png (512x512) — PWA splash/install
  - favicon.ico or favicon.png (32x32) — browser tab
  - apple-touch-icon.png (180x180) — iOS home screen

### Repo Transfer Mechanics
- GitHub org "flawchess" already exists
- Use GitHub's built-in repo transfer feature (preserves history, issues, auto-redirects old URL)
- Repo transfer is a **manual step** done by user after rename is complete — plan documents the steps but doesn't execute transfer
- Local project directory renamed from `chessalytics` to `flawchess` (manual step by user)
- Git remote updated to point to `flawchess/flawchess` after transfer

### Rename Scope
- **Database name**: rename from `chessalytics` to `flawchess` in .env and config
- **pyproject.toml**: rename project from `chessalytics` to `flawchess` (source stays in `app/`)
- **All source files**: find/replace "Chessalytics" → "FlawChess" and "chessalytics" → "flawchess" across ~18 tracked files (Python, TypeScript, HTML, config)
- **PWA manifest**: update name/short_name in vite.config.ts from "Chessalytics" to "FlawChess"
- **index.html**: update `<title>` to "FlawChess"
- **CLAUDE.md**: update all references to reflect FlawChess
- **.planning/ active docs**: rename in PROJECT.md, STATE.md, REQUIREMENTS.md, ROADMAP.md
- **.planning/ completed phase docs**: leave as historical record (not renamed)
- **Success criterion grep check**: `grep -ri chessalytics` excludes `.planning/phases/` completed phase directories
- **.env.example**: update database URL and any project references

### Claude's Discretion
- Exact ordering of rename operations
- Whether to update `frontend/dist/` (likely just rebuild)
- Handling any edge cases in alembic migration files referencing the old name

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Branding requirements
- `.planning/REQUIREMENTS.md` — BRAND-01 through BRAND-04 define rename and branding scope

### Rename targets
- `pyproject.toml` — Python project name
- `frontend/vite.config.ts` — PWA manifest with name/short_name
- `frontend/index.html` — Page title
- `app/core/config.py` — Backend config referencing project name
- `.env.example` — Database URL and config defaults
- `CLAUDE.md` — Project guidance for Claude Code

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Current PWA icons at `frontend/public/icons/` (icon-192.png, icon-512.png) — will be kept as placeholders until user provides final logos
- PWA manifest is inline in `frontend/vite.config.ts` (VitePWA plugin config) — single place to update name/icons

### Established Patterns
- Config uses Pydantic BaseSettings in `app/core/config.py` — DB name comes from environment variable
- `.env` file holds DATABASE_URL with embedded database name

### Integration Points
- `frontend/src/App.tsx` — may display app name in header/nav
- `frontend/src/components/install/InstallPromptBanner.tsx` — references app name in install prompt
- `frontend/src/pages/Auth.tsx` — may show app name on login page
- `app/main.py` — FastAPI app title/description

</code_context>

<specifics>
## Specific Ideas

- User wants to explore both logo directions later: knight with magnifying glass (conceptual, cute/comic) vs simple piece silhouette (clean, lichess-style)
- Visual style is open to Claude's recommendation — user is flexible
- Placeholder icons are fine for this phase; real branding comes when user provides assets

</specifics>

<deferred>
## Deferred Ideas

- Final logo design and icon creation — user will provide assets separately
- README polish with screenshots — Phase 23 (needs live domain)

</deferred>

---

*Phase: 20-rename-branding*
*Context gathered: 2026-03-21*
