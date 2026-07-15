---
status: resolved
trigger: "On a phone viewport, the /bots setup screen takes too much vertical space. The Start button is pushed below the fold / underneath the fixed bottom navigation bar."
created: 2026-07-14
updated: 2026-07-14
---

## Current Focus

hypothesis: BOTH — (a) SetupScreen skips the app's `pb-20` mobile bottom-nav clearance pattern (occlusion), and (b) its section stack is ~632px tall, exceeding a real phone's usable viewport (below-fold).
test: static layout arithmetic from Tailwind classes + comparison against every other page's clearance
expecting: confirmed
next_action: report diagnosis (read-only, no fix)

## Symptoms

expected: On 390x844, Start CTA reachable without scrolling; never obscured behind the fixed bottom nav.
actual: Start button pushed below fold / under the fixed bottom nav.
errors: none (visual/layout)
reproduction: Open /bots setup on a real phone (Safari, or the installed PWA)
started: Phase 171

## Eliminated

- hypothesis: Bots renders in the analysis-route shell (h-[100dvh] locked, no bottom nav)
  evidence: App.tsx:472 `isAnalysisRoute = pathname.startsWith('/analysis')` — /bots falls into the default branch (App.tsx:559-575) which renders MobileHeader + `<main className="pb-16 sm:pb-0">` + MobileBottomBar.

## Evidence

- checked: App.tsx:567 — the app-level `<main className="pb-16 sm:pb-0">`
  found: reserves exactly 4rem (64px) on mobile; NOT safe-area-aware.
  implication: matches MobileBottomBar's nominal 4rem, but the nav is `pb-safe` (App.tsx:323), so in standalone PWA the nav is 4rem + env(safe-area-inset-bottom) (~34px on iPhone) = ~98px. main's 64px does not cover it.

- checked: every other page's bottom clearance
  found: Endgames.tsx:812 `pb-20 md:pb-6`, Analysis.tsx:2660 `pb-20 md:pb-6`, GamesTab.tsx:385 `pb-20`, FlawsTab.tsx:362 `pb-20`.
  implication: the ESTABLISHED PATTERN is page content adding `pb-20` (80px) ON TOP of main's `pb-16` = 144px total mobile clearance. Bots.tsx:355 and SetupScreen.tsx:216 both use bare `p-4` (16px) — the only pages in the app that skip it. They mask the app-level safe-area shortfall; /bots does not.

- checked: SetupScreen.tsx section heights (mobile, <sm)
  found: ~632px total (see diagnosis table): 2x `min-h-11` Sliders (44px each), 5x `h-11` chip rows (44px each, CHIP_BASE_CLASS), 3x TC sub-headers (24px each), 4x `gap-4`.
  implication: + MobileHeader (~51px) = 683px before any clearance. Real Safari innerHeight on a 390x844 iPhone is ~664-745px (URL bar), so the Start CTA lands at/below the fold.

- checked: FeedbackButton.tsx:36 — `fixed right-4 bottom-[4.5rem] z-20`
  found: the FAB sits 72px above the viewport bottom, i.e. inside the 80px band left below the Start CTA.
  implication: even where the Start button is not behind the nav, the FAB overlays the right end of the full-width CTA. Fixed by the same `pb-20`.

## Resolution

root_cause: SetupScreen's container reserves only `p-4` (16px) below the Start CTA and omits the app-wide `pb-20` mobile bottom-nav clearance that every other page applies, while the setup stack itself costs ~632px on a phone — so the CTA is BOTH below the fold on a real phone viewport AND (in the safe-area/PWA shell, where main's flat `pb-16` under-reserves vs the nav's 4rem+inset) occluded behind the nav.
fix: (not applied — diagnose-only)
verification: (n/a)
files_changed: []
