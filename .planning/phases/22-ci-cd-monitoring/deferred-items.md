# Deferred Items — Phase 22 CI/CD & Monitoring

## Pre-existing ESLint Errors (out of scope for plan 22-02)

Found during Task 2 lint verification. These errors existed before 22-02 changes — none are caused by the Sentry integration.

### src/App.tsx — useRef access during render (react-hooks/refs)
- Lines 273-275: `restoredForTokenRef.current` read and written during render body
- Fix: move into `useEffect` or restructure with `useState`

### src/components/filters/FilterPanel.tsx (line 22)
- react-refresh/only-export-components: file exports both components and constants

### src/components/position-bookmarks/SuggestionsModal.tsx
- Line 26: `suggestions` dependency causes useEffect to re-run unnecessarily (wrap in useMemo)
- Line 44: `setState` called synchronously inside effect body (react-hooks/set-state-in-effect)

### src/components/ui/badge.tsx, button.tsx, tabs.tsx, toggle.tsx
- react-refresh/only-export-components: shadcn UI files export variant constants alongside components

### frontend/dev-dist/workbox-*.js
- @typescript-eslint/ban-types, no-unsafe-member-access, etc. in generated workbox service worker file
- Fix: add dev-dist to .eslintignore
