---
phase: quick
plan: 260327-jfd
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/pages/Endgames.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "User sees a Beta label on the Endgames Statistics tab indicating the feature is under development"
  artifacts:
    - path: "frontend/src/pages/Endgames.tsx"
      provides: "Beta badge next to Statistics tab trigger text"
  key_links: []
---

<objective>
Add a "Beta" badge to the Endgames Statistics tab to indicate endgame statistics are still under active development and subject to change.

Purpose: Set user expectations that endgame metrics/classifications may change.
Output: Visual beta indicator on the Statistics tab.
</objective>

<context>
@frontend/src/pages/Endgames.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add Beta badge to Endgames Statistics tab</name>
  <files>frontend/src/pages/Endgames.tsx</files>
  <action>
Add a small "Beta" badge inline with the "Statistics" text in the TabsTrigger for both desktop and mobile variants.

Use a `<span>` with Tailwind classes for a subtle pill-style badge:
- `text-[10px] font-semibold uppercase tracking-wide`
- `bg-amber-500/15 text-amber-600 dark:text-amber-400`
- `px-1.5 py-0.5 rounded-full ml-1.5`

Place it after the "Statistics" text inside both TabsTrigger elements (desktop data-testid="tab-statistics" and mobile data-testid="tab-statistics-mobile").

Add `data-testid="badge-beta"` to the badge span.

Do NOT add the badge to the Games tab — only Statistics.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npm run build</automated>
  </verify>
  <done>Both desktop and mobile Statistics tabs show a "Beta" pill badge. Build succeeds.</done>
</task>

</tasks>

<verification>
- `npm run build` passes
- Visual: Statistics tab shows "Beta" badge, Games tab does not
</verification>

<success_criteria>
Beta badge visible on Statistics tab in both desktop and mobile layouts.
</success_criteria>

<output>
Quick task complete — no SUMMARY needed.
</output>
