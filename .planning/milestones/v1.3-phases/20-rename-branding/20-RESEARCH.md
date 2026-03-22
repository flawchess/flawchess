# Phase 20: Rename & Branding - Research

**Researched:** 2026-03-21
**Domain:** Project rename, branding assets, PWA manifest, git remote update
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- AI-generated logo with manual polish — but deferred: use **placeholder icons** for now
- User will provide final logos later; phase uses current chess knight icons or simple placeholders
- Icon-only in favicon/PWA icons; icon + "FlawChess" text in app header
- Logo concept direction: knight with magnifying glass (cute/comic) vs simple piece silhouette — to be decided when user provides assets
- Keep current dark theme palette (#0a0a0a background), no new accent color
- Required icon formats for user to supply later: icon-192.png (192x192), icon-512.png (512x512), favicon.ico or favicon.png (32x32), apple-touch-icon.png (180x180)
- GitHub org "flawchess" already exists
- Use GitHub's built-in repo transfer feature (preserves history, issues, auto-redirects old URL)
- Repo transfer is a **manual step** done by user after rename is complete — plan documents the steps but doesn't execute transfer
- Local project directory renamed from `chessalytics` to `flawchess` (manual step by user)
- Git remote updated to point to `flawchess/flawchess` after transfer
- **Database name**: rename from `chessalytics` to `flawchess` in .env and config
- **pyproject.toml**: rename project from `chessalytics` to `flawchess` (source stays in `app/`)
- **All source files**: find/replace "Chessalytics" → "FlawChess" and "chessalytics" → "flawchess" across ~18 tracked files
- **PWA manifest**: update name/short_name in vite.config.ts
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

### Deferred Ideas (OUT OF SCOPE)
- Final logo design and icon creation — user will provide assets separately
- README polish with screenshots — Phase 23 (needs live domain)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BRAND-01 | Project renamed from Chessalytics to FlawChess across all code, config, and documentation | Full file inventory below; 18 tracked source files identified + active planning docs |
| BRAND-02 | PWA manifest updated with FlawChess name, short_name, and new logo/icons | vite.config.ts VitePWA plugin is the single source of truth; placeholder icons already exist at correct paths |
| BRAND-03 | FlawChess logo designed and integrated (favicon, PWA icons, About page, README) | Favicon references index.html link tag; placeholder icons (icon-192.png, icon-512.png) remain; new apple-touch-icon.png needed |
| BRAND-04 | Git repo transferred to flawchess GitHub organization with remotes updated | Current remote: git@github.com:aimfeld/chessalytics.git; target: git@github.com:flawchess/flawchess.git; transfer is user manual step |
</phase_requirements>

## Summary

Phase 20 is a pure rename-and-branding phase: no new features, no schema migrations, no architectural changes. The work is precisely scoped to replacing the string "Chessalytics"/"chessalytics" with "FlawChess"/"flawchess" across source files, config, and active planning docs — then adding placeholder favicon/PWA assets and updating the git remote.

A complete audit of tracked files containing "chessalytics" or "Chessalytics" has been performed. There are 18 source/config/test files requiring changes (excluding the historical planning phase docs in `.planning/milestones/` and `.planning/quick/`, which are left as-is). The PWA manifest is inline inside `vite.config.ts` — a single location to update `name` and `short_name`. The favicon is referenced only in `frontend/index.html`. Placeholder icons already exist at `frontend/public/icons/icon-192.png` and `icon-512.png`; a 180x180 `apple-touch-icon.png` is not yet present and must be created or copied.

The git remote currently points to `git@github.com:aimfeld/chessalytics.git`. The GitHub org `flawchess` already exists. The repo transfer is a user-executed manual step; the plan should document the exact procedure but not automate it. After the user transfers the repo, the git remote is updated locally to `git@github.com:flawchess/flawchess.git`.

**Primary recommendation:** Work in two waves — Wave 1: all in-code string replacements and `frontend/dist/` rebuild; Wave 2: favicon/icon assets and git remote update instructions.

## Standard Stack

This phase does not introduce new libraries. All tooling is already installed.

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Python/uv | 3.13 / current | Run find/replace in Python files | Already in use |
| Vite + VitePWA | 5.x / 0.20.x | PWA manifest name/short_name | Single config location in vite.config.ts |
| git | system | Remote update after repo transfer | Standard VCS |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `npm run build` | — | Regenerate frontend/dist/ | After all source renames complete |
| `grep -ri chessalytics` | — | Verify no remaining references | Final success check |

## Architecture Patterns

### File Inventory — Complete Rename Targets

**Backend source files (exact paths):**
| File | What to Change |
|------|----------------|
| `pyproject.toml` | `name = "chessalytics"` → `name = "flawchess"` |
| `app/main.py` | `title="Chessalytics"` → `title="FlawChess"` |
| `app/core/config.py` | Default DATABASE_URL: `chessalytics` → `flawchess`; default TEST_DATABASE_URL: `chessalytics_test` → `flawchess_test` |
| `app/services/chesscom_client.py` | `USER_AGENT = "Chessalytics/1.0 (github.com/chessalytics)"` → `"FlawChess/1.0 (github.com/flawchess/flawchess)"` |
| `app/services/zobrist.py` | Module docstring: "Chessalytics" → "FlawChess" |
| `app/routers/auth.py` | No direct "Chessalytics" string — verify after search |

**Frontend source files:**
| File | What to Change |
|------|----------------|
| `frontend/index.html` | `<title>Chessalytics</title>` → `<title>FlawChess</title>`; favicon link stays at `/icons/icon-192.png` |
| `frontend/vite.config.ts` | `name: 'Chessalytics'`, `short_name: 'Chessalytics'` → `'FlawChess'` in VitePWA manifest |
| `frontend/src/App.tsx` | Desktop NavHeader: `"Chessalytics"` span → `"FlawChess"`; MobileHeader: `"Chessalytics"` span → `"FlawChess"` (both `NavHeader` and `MobileHeader` components) |
| `frontend/src/pages/Auth.tsx` | `<h1>Chessalytics</h1>` on login page → `<h1>FlawChess</h1>` |
| `frontend/src/components/install/InstallPromptBanner.tsx` | `<DrawerTitle>Install Chessalytics</DrawerTitle>` → `Install FlawChess` |
| `frontend/src/lib/zobrist.ts` | File comment: "Chessalytics" → "FlawChess" |

**Tests:**
| File | What to Change |
|------|----------------|
| `tests/conftest.py` | Comments referencing "chessalytics_test"; actual TEST_DATABASE_URL comes from settings so the real DB name change happens in `.env` and `app/core/config.py` |
| `tests/test_chesscom_client.py` | `assert "Chessalytics" in headers["User-Agent"]` → `assert "FlawChess" in headers["User-Agent"]` |

**Config / dotfiles:**
| File | What to Change |
|------|----------------|
| `.env.example` | `DATABASE_URL=...chessalytics` → `flawchess`; `TEST_DATABASE_URL=...chessalytics_test` → `flawchess_test` |
| `.env` (local, not tracked) | Same as `.env.example` — document as a manual step for the developer |
| `CLAUDE.md` | All "Chessalytics" references (project name, description) → "FlawChess" |
| `.claude/settings.local.json` | Path strings contain `/chessalytics/` — these are filesystem paths that change only when the user renames the local directory (manual step, not automated) |

**Active planning docs:**
| File | What to Change |
|------|----------------|
| `.planning/PROJECT.md` | "# Chessalytics" heading + description |
| `.planning/STATE.md` | "# Project State: FlawChess (formerly Chessalytics)" — already partially updated; remove "(formerly Chessalytics)" from heading |
| `.planning/REQUIREMENTS.md` | "# Requirements: FlawChess" — already updated (no change needed) |
| `.planning/ROADMAP.md` | Success criterion text referencing `.planning/phases/` path |
| `.planning/MILESTONES.md` | "# Milestones: Chessalytics" → "# Milestones: FlawChess" |

**Frontend dist (generated):**
- `frontend/dist/` — regenerated by `npm run build`; no manual edits needed

### PWA Icon Asset Requirements

The VitePWA manifest already references the correct icon paths. The placeholder icons at `frontend/public/icons/icon-192.png` and `icon-512.png` remain in place. A new placeholder is needed:

| Asset | Path | Size | Status |
|-------|------|------|--------|
| PWA icon small | `frontend/public/icons/icon-192.png` | 192x192 | Exists (placeholder) |
| PWA icon large | `frontend/public/icons/icon-512.png` | 512x512 | Exists (placeholder) |
| Favicon | Linked from `index.html` as `/icons/icon-192.png` | 192x192 | Reuses existing |
| Apple touch icon | `frontend/public/icons/apple-touch-icon.png` | 180x180 | **Missing — create from icon-192.png** |

The `index.html` references `apple-touch-icon` at `/icons/icon-192.png` — it works but is the wrong size for iOS best practice. BRAND-03 requires an `apple-touch-icon.png` at 180x180. The simplest approach for this phase: copy `icon-192.png` to `apple-touch-icon.png` and update the `<link rel="apple-touch-icon">` href in `index.html`. User replaces both when providing final assets.

### Git Remote Update Pattern

```bash
# After user transfers repo on GitHub:
git remote set-url origin git@github.com:flawchess/flawchess.git
git remote -v  # verify
```

The GitHub transfer preserves full git history, all issues, and sets up automatic redirects from `aimfeld/chessalytics` to `flawchess/flawchess` for 12 months.

### Grep Verification Pattern

```bash
# Run from project root — success criterion
grep -ri chessalytics . \
  --include="*.py" --include="*.ts" --include="*.tsx" --include="*.html" \
  --include="*.toml" --include="*.md" --include="*.json" --include="*.yaml" \
  --include="*.env*" \
  --exclude-dir=node_modules --exclude-dir=.git \
  --exclude-dir=".planning/milestones" --exclude-dir=".planning/quick" \
  --exclude-dir=".planning/research"
```

Per the CONTEXT.md decision: `.planning/phases/` completed phase directories are excluded from the success check. The exact exclusion scope is: `.planning/milestones/`, `.planning/quick/`, and `.planning/research/` (historical records). The active docs (`.planning/PROJECT.md`, `.planning/STATE.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/MILESTONES.md`) are in scope and must be clean.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Generating 180x180 icon | Custom image resize script | Copy icon-192.png as apple-touch-icon.png | Close enough for placeholder; user provides final |
| Verifying rename completeness | Custom scan script | `grep -ri chessalytics` with path exclusions | Direct, auditable, matches success criterion |
| PWA manifest | Custom HTML meta tags | VitePWA plugin inline manifest in vite.config.ts | Already established pattern in this project |

**Key insight:** This is a text replacement phase. The complexity is inventory completeness, not implementation. Don't over-engineer the process.

## Common Pitfalls

### Pitfall 1: Leaving "chessalytics" in the local .env file
**What goes wrong:** The `.env` file is git-ignored but still used by the running app. After renaming the database, local dev breaks if `.env` still points to the old `chessalytics` database.
**Why it happens:** `.env` is not tracked, easy to forget.
**How to avoid:** Include `.env` update as an explicit manual step task for the developer. The app/core/config.py default and .env.example are code-controlled; the local .env is a developer action.
**Warning signs:** `uv run pytest` fails with "database does not exist" after rename.

### Pitfall 2: Desktop and mobile header both show the app name
**What goes wrong:** CLAUDE.md says to check both desktop and mobile variants. `App.tsx` has two separate components: `NavHeader` (desktop, hidden on mobile) and `MobileHeader` (mobile, hidden on desktop). Both display "Chessalytics" and must both be updated.
**Why it happens:** The name appears in two places in the same file, easy to miss one.
**How to avoid:** Search for all occurrences in App.tsx, not just the first.
**Warning signs:** Mobile header still shows old name after desktop header is updated.

### Pitfall 3: .claude/settings.local.json path strings
**What goes wrong:** `.claude/settings.local.json` contains absolute filesystem paths (`/home/aimfeld/Projects/Python/chessalytics/...`). These are not "Chessalytics" branding references — they are filesystem paths that only change when the user renames the local directory.
**Why it happens:** The grep will find `/home/aimfeld/Projects/Python/chessalytics/` as a match.
**How to avoid:** Do NOT modify `.claude/settings.local.json` paths in code. They will update naturally when the user renames the directory (manual step). Document this as a post-rename user action.
**Warning signs:** Breaking Claude Code permission allowlists.

### Pitfall 4: Test database name in conftest.py comments vs actual DB name
**What goes wrong:** The `conftest.py` comments say "chessalytics_test" but the actual database URL comes from `settings.TEST_DATABASE_URL` which reads from `.env`. Changing only the comment without changing the settings/env means tests still point to the old database.
**Why it happens:** Comments look like config but aren't.
**How to avoid:** Change `app/core/config.py` default TEST_DATABASE_URL and `.env.example`. The comments in conftest.py can be updated to say "flawchess_test" for consistency.

### Pitfall 5: User-Agent string in test assertion
**What goes wrong:** `tests/test_chesscom_client.py` line 143 asserts `"Chessalytics" in headers["User-Agent"]`. After renaming `USER_AGENT` in `chesscom_client.py`, this test will fail unless updated simultaneously.
**Why it happens:** Test assertion mirrors a constant that's being renamed.
**How to avoid:** Update both `app/services/chesscom_client.py` and `tests/test_chesscom_client.py` in the same commit.
**Warning signs:** `uv run pytest tests/test_chesscom_client.py` fails after renaming USER_AGENT.

### Pitfall 6: frontend/dist/ contains stale old name
**What goes wrong:** `frontend/dist/` is a build artifact. If a `frontend/dist/index.html` exists with "Chessalytics" in it and it's tracked by git (check: it's listed in the grep output as `/frontend/dist/index.html`), the grep success check will fail even if all source files are clean.
**Why it happens:** Dist files are sometimes committed for simple deployment workflows.
**How to avoid:** Run `npm run build` after all source changes. The dist/ file will be regenerated with "FlawChess". Alternatively, check if dist/ is in .gitignore — if it is, it's irrelevant to the tracked-files grep check. Verify with `git check-ignore frontend/dist`.
**Warning signs:** grep finds `frontend/dist/index.html` in tracked files.

## Code Examples

### PWA Manifest Update (vite.config.ts)
```typescript
// Source: current vite.config.ts
VitePWA({
  registerType: 'autoUpdate',
  devOptions: { enabled: true },
  manifest: {
    name: 'FlawChess',          // was 'Chessalytics'
    short_name: 'FlawChess',    // was 'Chessalytics'
    description: 'Chess opening analysis by position',
    theme_color: '#0a0a0a',
    background_color: '#0a0a0a',
    display: 'standalone',
    start_url: '/',
    scope: '/',
    icons: [
      { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
      { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
    ],
  },
  // ...
})
```

### Apple Touch Icon Addition (index.html)
```html
<!-- Source: current frontend/index.html -->
<link rel="icon" type="image/png" href="/icons/icon-192.png" />
<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png" />  <!-- updated path -->
<meta name="theme-color" content="#0a0a0a" />
<title>FlawChess</title>
```

### User-Agent Update (chesscom_client.py)
```python
# Source: current app/services/chesscom_client.py
USER_AGENT = "FlawChess/1.0 (github.com/flawchess/flawchess)"
```

### Git Remote Update
```bash
# After GitHub repo transfer:
git remote set-url origin git@github.com:flawchess/flawchess.git
git remote -v
```

### GitHub Repo Transfer Steps (for plan documentation)
1. Go to https://github.com/aimfeld/chessalytics/settings
2. Scroll to "Danger Zone" → "Transfer ownership"
3. Enter the destination: `flawchess/flawchess`
4. Confirm with repository name
5. After transfer: run `git remote set-url origin git@github.com:flawchess/flawchess.git` locally

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Manual favicon files | VitePWA generates PWA manifest; favicon still manual in index.html | No change needed; both patterns coexist |
| Separate manifest.json | Inline manifest in vite.config.ts VitePWA plugin | Already established; one place to update |

**No deprecated patterns to address in this phase.**

## Open Questions

1. **Is `frontend/dist/` tracked by git?**
   - What we know: `frontend/dist/index.html` appeared in the grep scan of tracked files
   - What's unclear: Whether dist/ is committed or just unignored but present locally
   - Recommendation: Planner should add a task to `git check-ignore frontend/dist` and handle accordingly. If tracked: must rebuild and commit. If unignored but not tracked: irrelevant to success criterion.

2. **Local .env database rename coordination**
   - What we know: `.env` is not tracked; developer must manually rename the local PostgreSQL database from `chessalytics` to `flawchess`
   - What's unclear: Whether to rename the existing PostgreSQL database or create a fresh one
   - Recommendation: Plan should document the PostgreSQL rename command (`ALTER DATABASE chessalytics RENAME TO flawchess;`) as a manual developer step. The test database (`chessalytics_test` → `flawchess_test`) requires similar treatment.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_chesscom_client.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BRAND-01 | No "Chessalytics" string remains in tracked source files | smoke/grep | `grep -ri chessalytics . --include="*.py" --include="*.ts" --include="*.tsx" --include="*.html" --include="*.toml" --include="*.md" --include="*.json" --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=".planning/milestones" --exclude-dir=".planning/quick" --exclude-dir=".planning/research"` | N/A — shell command |
| BRAND-01 | User-Agent header uses "FlawChess" | unit | `uv run pytest tests/test_chesscom_client.py -x` | ✅ |
| BRAND-02 | PWA manifest shows "FlawChess" name/short_name | manual | Install PWA on phone; check app icon label | N/A — manual |
| BRAND-03 | Favicon and PWA icons present at expected paths | smoke | `ls frontend/public/icons/` | N/A — shell command |
| BRAND-04 | Git remote points to flawchess org | smoke | `git remote -v` | N/A — shell command |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_chesscom_client.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- None — existing test infrastructure covers all phase requirements. The User-Agent test in `test_chesscom_client.py` will be updated in-place (not a new file). No new test files are needed.

## Sources

### Primary (HIGH confidence)
- Direct file audit of `/home/aimfeld/Projects/Python/chessalytics` — complete grep inventory performed
- `frontend/vite.config.ts` — VitePWA manifest structure verified
- `frontend/index.html` — favicon and title verified
- `frontend/src/App.tsx` — both NavHeader and MobileHeader verified
- `app/core/config.py` — default database URL strings verified
- `tests/test_chesscom_client.py:143` — User-Agent assertion verified

### Secondary (MEDIUM confidence)
- GitHub repo transfer behavior (redirects, history preservation) — well-documented standard GitHub feature, consistent across multiple sources

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- File inventory: HIGH — complete grep audit performed on actual codebase
- Rename targets: HIGH — each file read and exact change locations identified
- PWA manifest: HIGH — vite.config.ts read directly
- Git remote update: HIGH — remote verified with `git remote -v`
- Apple touch icon gap: HIGH — file system audit confirmed missing

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable codebase; no external dependencies changing)
