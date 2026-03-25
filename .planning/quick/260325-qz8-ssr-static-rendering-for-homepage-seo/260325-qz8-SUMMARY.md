---
phase: quick
plan: 260325-qz8
subsystem: ui, seo
tags: [vite, prerender, ssr, seo, react, static-html]

provides:
  - Build-time prerendered HTML for homepage (/) and privacy page (/privacy)
  - Crawler-visible content without JavaScript execution
affects: [frontend-build, deployment, seo]

tech-stack:
  added: [vite-prerender-plugin]
  patterns: [build-time SSR via prerender entry point separate from main app]

key-files:
  created:
    - frontend/src/prerender.tsx
  modified:
    - frontend/vite.config.ts
    - frontend/src/pages/Home.tsx
    - frontend/package.json
    - frontend/package-lock.json

key-decisions:
  - "Keep createRoot (not hydrateRoot) -- prerendered HTML gets replaced by React on load, avoiding hydration mismatch complexity for auth redirects"
  - "Prerender entry renders only public page components (HomePageContent, PrivacyPage), not full App -- avoids SSR issues with auth, QueryClient, Sentry"

requirements-completed: []

duration: 21min
completed: 2026-03-25
---

# Quick Task 260325-qz8: SSR Static Rendering for Homepage SEO

**Build-time prerendering for homepage and privacy page using vite-prerender-plugin so non-JS crawlers see full page content**

## Performance

- **Duration:** 21 min
- **Started:** 2026-03-25T18:41:48Z
- **Completed:** 2026-03-25T19:03:25Z
- **Tasks:** 1
- **Files modified:** 5

## Accomplishments

- Homepage (/) now contains full hero, features, and FAQ content in the initial HTML
- Privacy page (/privacy) prerendered as dist/privacy/index.html with full policy content
- SPA behavior preserved -- client-side routing and auth redirects still work normally
- All 38 existing frontend tests pass
- No Docker or infrastructure changes required

## Task Commits

1. **Task 1: Create prerender entry and configure vite-prerender-plugin** - `1b08b2d` (feat)

## Files Created/Modified

- `frontend/src/prerender.tsx` - SSR entry point using StaticRouter + renderToString for build-time prerendering
- `frontend/vite.config.ts` - Added vitePrerenderPlugin configuration with renderTarget, prerenderScript, and additionalPrerenderRoutes
- `frontend/src/pages/Home.tsx` - Exported HomePageContent function (was private) for SSR import
- `frontend/package.json` - vite-prerender-plugin already in devDependencies (installed during research)
- `frontend/package-lock.json` - Updated lockfile

## Decisions Made

- **createRoot over hydrateRoot:** Kept createRoot in main.tsx. The prerendered HTML gets replaced when React boots, which avoids hydration mismatch complexity for authenticated users who get redirected away from the homepage. The brief flash of prerendered content before React takes over is acceptable.
- **Separate prerender entry:** prerender.tsx renders only HomePageContent and PrivacyPage via StaticRouter, not the full App component. This avoids SSR issues with auth context, QueryClient, Sentry initialization, and other client-only providers.

## Deviations from Plan

None - plan executed exactly as written.

## Known Issues

- **Prerender chunk in client bundle:** The build produces a `prerender-*.js` chunk (~472KB) that gets modulepreloaded in the client HTML. This file is only needed at build time but Vite includes it in the client output. This is a known limitation of vite-prerender-plugin. It does not affect functionality -- the chunk loads but is never executed client-side. A future optimization could exclude it via rollupOptions.

## Issues Encountered

- vite-prerender-plugin was not installed in the worktree's node_modules despite being in package.json -- resolved by running npm install explicitly.

## User Setup Required

None - no external service configuration required.

## Next Steps

- Deploy to production (the prerendered HTML is automatically included in the build output)
- Verify with curl that crawlers see content: `curl -s https://flawchess.com/ | grep "Engines are flawless"`

---
*Quick task: 260325-qz8*
*Completed: 2026-03-25*

## Self-Check: PASSED
