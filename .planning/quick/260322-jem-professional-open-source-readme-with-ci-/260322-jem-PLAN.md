---
phase: quick
plan: 260322-jem
type: execute
wave: 1
depends_on: []
files_modified:
  - README.md
autonomous: true
requirements: [README-rewrite]

must_haves:
  truths:
    - "README displays CI badge linked to GitHub Actions workflow"
    - "README shows 3-4 inline screenshots of the application"
    - "README contains Self-Hosting section with Docker Compose deployment instructions"
    - "README has polished Contributing and Quick Start sections"
  artifacts:
    - path: "README.md"
      provides: "Professional open-source project README"
      contains: "actions/workflows/ci.yml/badge.svg"
  key_links:
    - from: "README.md"
      to: "frontend/public/screenshots/"
      via: "relative image paths"
      pattern: "frontend/public/screenshots/.*\\.png"
---

<objective>
Rewrite README.md to professional open-source quality with CI badge, screenshot gallery, self-hosting instructions, and polished existing sections.

Purpose: The README is the first thing visitors see on GitHub. A polished README with screenshots and clear setup instructions drives adoption and contributions.
Output: Single rewritten README.md
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@README.md
@.env.example
@docker-compose.yml
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rewrite README.md</name>
  <files>README.md</files>
  <action>
Rewrite README.md with the following structure. Keep the existing logo/tagline header.

1. **Badge row** — Add CI badge as FIRST badge before the existing ones:
   `[![CI](https://github.com/flawchess/flawchess/actions/workflows/ci.yml/badge.svg)](https://github.com/flawchess/flawchess/actions/workflows/ci.yml)`
   Keep existing License, Python, React, FastAPI, PostgreSQL badges.

2. **What is FlawChess?** — Keep existing paragraph, it's good.

3. **Screenshots** — Replace "Screenshots coming soon" with 3-4 inline images using relative paths. Pick the best shots:
   - `board-and-move-explorer.png` (hero — main analysis view with move explorer)
   - `win-rate-over-time.png` (time series chart — shows analytical depth)
   - `filters.png` (powerful filtering — differentiator)
   - `position-bookmarks.png` (bookmarks — unique feature)

   Use a simple layout: each screenshot as a block image with a brief caption in bold or italic below it. Do NOT use HTML tables — just standard markdown images. Example format:
   ```
   **Board & Move Explorer** — Navigate positions and see next-move frequency with W/D/L stats
   ![Board and Move Explorer](frontend/public/screenshots/board-and-move-explorer.png)
   ```

4. **Features** — Keep existing list as-is (already good).

5. **Tech Stack** — Keep existing table as-is.

6. **Local Development** — Keep existing Setup/Tests/Linting sections. Minor polish:
   - Change section title from "Local Development" to "Getting Started" for friendlier tone
   - Add a note that Google OAuth and Sentry are optional (app works without them)

7. **Self-Hosting** (NEW section after Getting Started) — Production deployment via Docker Compose:
   - Prerequisites: VPS with Docker, a domain name pointing to the server
   - Steps:
     1. Clone the repo
     2. Copy `.env.example` to `.env`, fill in production values (list the required vars: ENVIRONMENT=production, POSTGRES_PASSWORD, SECRET_KEY, DATABASE_URL pointing to `db:5432`, BACKEND_URL, FRONTEND_URL)
     3. `docker compose up -d`
   - Note that Caddy handles automatic TLS certificate provisioning
   - Note that Alembic migrations run automatically on backend startup
   - Note that Google OAuth and Sentry DSN are optional

8. **Architecture: Zobrist Hash Position Matching** — Keep existing section as-is.

9. **Contributing** — Expand slightly: mention opening an issue first, note that the project uses Ruff for Python and ESLint for TypeScript. Keep it concise — no CONTRIBUTING.md needed.

10. **License** — Keep as-is.

11. **Links** — Keep as-is.

Important: Use standard centered HTML for the header section (logo, tagline, badges) as the original does. Use standard markdown for everything else. Keep the total length reasonable (under 200 lines).
  </action>
  <verify>
    <automated>grep -q "badge.svg" README.md && grep -q "frontend/public/screenshots/" README.md && grep -c "screenshots/" README.md | grep -q "[3-9]" && grep -qi "self-hosting" README.md && echo "PASS" || echo "FAIL"</automated>
  </verify>
  <done>README.md contains CI badge, 3-4 inline screenshots, Self-Hosting section, and polished content throughout</done>
</task>

</tasks>

<verification>
- CI badge image URL present and linked to workflow
- At least 3 screenshot image paths present
- Self-Hosting section with Docker Compose instructions
- No "coming soon" placeholder text remains
- All existing sections (Features, Tech Stack, Architecture, License) preserved
</verification>

<success_criteria>
README.md is professional open-source quality: badges, screenshots, clear setup for both local dev and self-hosting, architecture explanation, and contributing guidelines.
</success_criteria>

<output>
After completion, create `.planning/quick/260322-jem-professional-open-source-readme-with-ci-/260322-jem-SUMMARY.md`
</output>
