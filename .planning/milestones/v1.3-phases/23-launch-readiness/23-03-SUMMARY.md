---
phase: 23-launch-readiness
plan: "03"
subsystem: frontend
tags: [privacy, seo, meta-tags, legal, robots, sitemap]
dependency_graph:
  requires: ["23-01"]
  provides: [privacy-page, seo-meta-tags, robots-txt, sitemap-xml]
  affects: [frontend/index.html, frontend/src/App.tsx]
tech_stack:
  added: []
  patterns: [react-useEffect-title, public-static-files]
key_files:
  created:
    - frontend/src/pages/Privacy.tsx
    - frontend/public/robots.txt
    - frontend/public/sitemap.xml
  modified:
    - frontend/index.html
    - frontend/src/App.tsx
decisions:
  - Static meta tags in index.html — no head management library (D-09 compliant)
  - document.title managed via useEffect in PrivacyPage — no react-helmet dependency
  - robots.txt and sitemap.xml in public/ — served automatically as static files by Vite build and Caddy
metrics:
  duration: "1m 17s"
  completed: "2026-03-22"
  tasks_completed: 2
  files_modified: 5
---

# Phase 23 Plan 03: Privacy Policy + SEO Summary

Privacy policy page at /privacy and SEO fundamentals (title, Open Graph tags, Twitter cards, robots.txt, sitemap.xml).

## What Was Built

### Task 1: Privacy policy page

Created `frontend/src/pages/Privacy.tsx` with:
- `PrivacyPage` component using `PublicHeader` (same as homepage)
- Four required sections: What we collect, Who we share it with (Sentry + Hetzner), Your rights (deletion via email), Open source (GitHub link)
- Contact section at `data-testid="privacy-contact"`
- Page-level `data-testid="privacy-page"` on `<main>`
- `useEffect` sets `document.title = 'Privacy Policy | FlawChess'` on mount and restores default on unmount
- Page footer with copyright and link back to homepage

Updated `frontend/src/App.tsx`:
- Removed inline `PrivacyPage` placeholder function
- Added real import: `import { PrivacyPage } from '@/pages/Privacy'`

### Task 2: SEO meta tags, robots.txt, sitemap.xml

Updated `frontend/index.html`:
- Title: `FlawChess — Chess Opening Analysis`
- Meta description with value proposition
- Full Open Graph tag set (og:title, og:description, og:image, og:url, og:type)
- Twitter/X card tags (summary_large_image)

Created `frontend/public/robots.txt`:
- Allows `/` and `/privacy`, disallows authenticated routes (`/import`, `/openings`, `/global-stats`, `/api/`)
- Sitemap pointer: `Sitemap: https://flawchess.com/sitemap.xml`

Created `frontend/public/sitemap.xml`:
- W3C sitemap namespace (`http://www.sitemaps.org/schemas/sitemap/0.9`)
- Lists `/` and `/privacy`

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1 | 95dd272 | frontend/src/pages/Privacy.tsx, frontend/src/App.tsx |
| 2 | db1236f | frontend/index.html, frontend/public/robots.txt, frontend/public/sitemap.xml |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

- `og:image` references `https://flawchess.com/og-image.jpg` — this asset does not exist yet. The plan notes this is a manual asset the user will provide (D-11). The meta tag is correct and will work once the image file is created and deployed.

## Self-Check: PASSED
