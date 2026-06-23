---
phase: quick-260620-mjh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/filters/FlawFilterControl.tsx
  - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
  - frontend/src/pages/library/__tests__/FlawsTab.test.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "Tactic controls (Severity, Orientation, Depth, Tactic motif) are visible by default when showTacticFilter is true"
    - "The Context tag families (Timing/Opportunity/Impact/Game Phase) are collapsed by default behind a 'More: Context' toggle"
    - "Clicking the Context toggle expands and collapses the family groups"
    - "The collapsed Context header shows a count badge ('Context · N') when N>0 Context tags are selected, just 'Context' when 0"
    - "The Context collapse renders on both Games tab (showTacticFilter=false) and Flaws tab (showTacticFilter=true)"
  artifacts:
    - path: "frontend/src/components/filters/FlawFilterControl.tsx"
      provides: "Redesigned layout: visible tactic controls first, collapsed Context section"
      contains: "filter-flaw-context-toggle"
  key_links:
    - from: "FlawFilterControl.tsx contextOpen state"
      to: "FAMILY_SECTIONS conditional render"
      via: "{contextOpen && (...)} gates the family-group block"
      pattern: "contextOpen"
---

<objective>
Redesign `FlawFilterControl.tsx` so the more-important tactic controls are visible by
default and the secondary "Context" tag families collapse behind a "More" toggle.

Purpose: The current panel buries the primary tactic controls (Orientation, Depth, Tactic
motif) at the bottom under four always-visible Context tag families, making the panel
overwhelming. This reorders to surface tactics and hides Context by default while keeping
active-but-hidden selections visible via a count badge.

Output: Updated `FlawFilterControl.tsx` with a hand-rolled collapsible Context section
(mirroring the existing FilterPanel "More" pattern), plus updated tests.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@frontend/src/components/filters/FlawFilterControl.tsx
@frontend/src/components/filters/FilterPanel.tsx
@frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
@frontend/src/pages/library/__tests__/FlawsTab.test.tsx

Key facts already established from reading the code:
- `FlawFilterControl` is a single shared component owning its own layout. Both the desktop
  sidebar and the mobile drawer render the same component (FlawsTab.tsx lines 291 & 518,
  GamesTab.tsx lines 311 & 485). There is NO duplicated inline markup to change — editing
  the component once covers every call site. The FlawsTab test uses `getAllByTestId`
  because two instances mount simultaneously.
- The existing collapse pattern to mirror lives in `FilterPanel.tsx` (~lines 226, 465-528):
  `const [moreOpen, setMoreOpen] = useState(false)`, a semantic `<button>` with
  `onClick={() => setMoreOpen((v) => !v)}`, `aria-expanded={moreOpen}`,
  `<ChevronDown className={cn('h-3.5 w-3.5 transition-transform', moreOpen && 'rotate-180')} />`,
  and `{moreOpen && (...)}`. Use this exact shape. Do NOT add a Radix/shadcn Collapsible.
- The Context families are the `FAMILY_SECTIONS` array (Timing/Opportunity/Impact/Game Phase).
  Their tags: `low-clock, hasty, unrushed, miss, lucky, reversed, squandered, opening,
  middlegame, endgame`.
- `ChevronDown` comes from `lucide-react` (already the import source for the existing icons
  in this file). `cn` is imported from `@/lib/utils`.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Reorder layout and collapse Context families behind a "More" toggle</name>
  <files>frontend/src/components/filters/FlawFilterControl.tsx</files>
  <behavior>
    - When showTacticFilter=true: Severity, Orientation, Depth, and Tactic motif render
      visibly and in that order, BEFORE the Context section.
    - The Context section (FAMILY_SECTIONS block) is wrapped in a collapsible that is
      collapsed by default — its family groups are NOT in the DOM until expanded.
    - The Context toggle button has data-testid="filter-flaw-context-toggle",
      aria-expanded reflecting open state, and aria-controls pointing at the content region.
    - Clicking the toggle reveals the family groups; clicking again hides them.
    - Header text is "Context" when 0 Context tags selected, "Context · N" when N>0
      Context tags (counted from the `tags` prop against all FAMILY_SECTIONS tags) selected.
    - The Context section renders regardless of showTacticFilter (it must appear on the
      Games tab where showTacticFilter=false: visible Severity, then collapsed Context).
    - Filter Logic explainer remains last.
  </behavior>
  <action>
Restructure the JSX returned by `FlawFilterControl` to the new top-to-bottom order:
Severity → Orientation (showTacticFilter) → Depth (showTacticFilter) → Tactic motif
(showTacticFilter) → collapsed Context section (always) → Filter Logic explainer.

Concretely:
1. Add `import { ChevronDown } from 'lucide-react'` to the existing lucide-react import
   block (or merge into the existing destructured import — do not add a second import line
   from the same module).
2. Add `import { useState } from 'react'` at the top.
3. Inside the component body add `const [contextOpen, setContextOpen] = useState(false);`.
4. Derive the selected-Context count: build a flat set of all Context tags from
   FAMILY_SECTIONS (flatMap over `section.tags`), then count how many of the current
   `tags` prop values are in that set. Extract the flat tag list into a module-level
   const named CONTEXT_TAGS (computed from FAMILY_SECTIONS via flatMap) so it is not
   rebuilt per render. Name the count `selectedContextCount`.
5. Move the existing `FAMILY_SECTIONS.map(...)` block so it no longer renders directly.
   Instead place it AFTER the Tactic motif block, wrapped in a collapsible that mirrors
   FilterPanel.tsx's "More" pattern: a wrapper `<div className="pt-3 border-t border-border/40">`,
   a semantic `<button type="button">` toggle, then `{contextOpen && (...)}` containing the
   family groups inside a `<div id="..." className="mt-2 flex flex-col gap-3">`.
6. The toggle button:
   - `data-testid="filter-flaw-context-toggle"`
   - `aria-expanded={contextOpen}`
   - `aria-controls="flaw-filter-context-content"` (and give the content div that id)
   - `onClick={() => setContextOpen((v) => !v)}`
   - className mirroring the FilterPanel toggle:
     `'flex w-full items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors'`
   - Contents: the rotating ChevronDown
     (`<ChevronDown className={cn('h-3.5 w-3.5 transition-transform', contextOpen && 'rotate-180')} />`)
     followed by the header label.
   - Header label: render `Context` plus, only when `selectedContextCount > 0`, ` · {selectedContextCount}`.
     Keep it text-sm (the toggle className already sets text-sm; do NOT introduce text-xs).
7. The existing standalone `<div className="border-t border-border/40" />` divider that sat
   between Severity and the old family block should be removed (the new Context wrapper
   carries its own `pt-3 border-t`). Keep Severity's own section unchanged.
8. Do NOT change `showTacticFilter` gating on Orientation/Depth/Tactic-motif — they stay
   gated exactly as today. The Context section is NOT gated by showTacticFilter.
9. Update the component's leading JSDoc "Renders:" comment to describe the new order
   (visible tactic controls, then a collapsed "Context" section).

Keep functions small (CLAUDE.md): if the toggle header grows non-trivial, it is fine to
keep it inline JSX — do not over-extract. Use only theme/semantic utility classes already
present in this file and FilterPanel; do not hard-code semantic colors.
  </action>
  <verify>
    <automated>cd frontend && npx tsc -b 2>&1 | tail -5; grep -c "filter-flaw-context-toggle" src/components/filters/FlawFilterControl.tsx</automated>
  </verify>
  <done>
    FlawFilterControl.tsx compiles (tsc -b clean). The Context toggle button exists with
    data-testid="filter-flaw-context-toggle", aria-expanded, and aria-controls. The
    FAMILY_SECTIONS block renders only inside `{contextOpen && (...)}`. The visible order is
    Severity → Orientation → Depth → Tactic motif → collapsed Context → Filter Logic.
    Header shows "Context · N" only when N Context tags are selected, else "Context".
  </done>
</task>

<task type="auto">
  <name>Task 2: Update tests for collapsed Context + add collapse/count-badge coverage</name>
  <files>frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx, frontend/src/pages/library/__tests__/FlawsTab.test.tsx</files>
  <action>
The Context tag families now start collapsed, so existing tests that assert a Context tag
button is in the DOM without expanding will fail. Fix them and add new coverage.

In `frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx`:
1. The "tag family groups" describe block tests (renders all 4 family groups, renders 7
   non-phase tag buttons, renders 3 phase tag buttons, toggling tags, aria-pressed) and the
   "canonical tag names" + "accessibility/family groups" tests all query Context family/tag
   testids that are now hidden by default. Before each such assertion, expand the section
   first via `fireEvent.click(screen.getByTestId('filter-flaw-context-toggle'))`. The
   cleanest approach: add a small local helper `renderExpanded(props)` that renders and then
   clicks the toggle, and use it in every test that needs Context tags/families visible.
   (The "tag buttons have aria-label" and "family groups have correct role" accessibility
   tests also need expansion.)
2. Add a new describe block `context collapse (Quick 260620-mjh)` with tests:
   - Context family groups are hidden by default: `screen.queryByTestId('filter-flaw-family-tempo')`
     is null before clicking the toggle.
   - The toggle exists with aria-expanded="false" by default and "true" after one click.
   - After clicking the toggle, `filter-flaw-family-tempo` (and e.g. `filter-flaw-tag-miss`)
     become present.
   - Count badge: with `tags={['miss', 'opening']}` the toggle's textContent contains
     "Context · 2"; with `tags={[]}` it contains "Context" and NOT "· ".
   - The Context section is present even when `showTacticFilter` is false (Games-tab case):
     `filter-flaw-context-toggle` exists with `showTacticFilter` unset.
3. Verify the existing "tactic motif" and "severity" describe blocks still pass unchanged —
   those controls are visible by default and are not affected by the collapse.

In `frontend/src/pages/library/__tests__/FlawsTab.test.tsx`:
4. The test "reflects store state with tags in the FlawFilterControl (tag button selected)"
   (~line 520) asserts `filter-flaw-tag-miss` is rendered. `miss` is a Context tag, now
   hidden by default. Expand the Context section before the assertion: there are multiple
   FlawFilterControl instances mounted, so use
   `screen.getAllByTestId('filter-flaw-context-toggle')` and click each (or click all via
   `.forEach(fireEvent.click)`) before calling `getAllByTestId('filter-flaw-tag-miss')`.
   Ensure `fireEvent` is imported in that test file (add to the testing-library import if
   missing).
  </action>
  <verify>
    <automated>cd frontend && npm test -- --run src/components/filters/__tests__/FlawFilterControl.test.tsx src/pages/library/__tests__/FlawsTab.test.tsx 2>&1 | tail -20</automated>
  </verify>
  <done>
    Both test files pass. New context-collapse describe block covers: hidden-by-default,
    aria-expanded toggle, expand-reveals-tags, count badge ("Context · N" vs "Context"), and
    Context-present-when-showTacticFilter-false. The FlawsTab "miss tag selected" test
    expands the Context section before asserting.
  </done>
</task>

<task type="auto">
  <name>Task 3: Full frontend gate (lint, knip, tests, type check)</name>
  <files>frontend/src/components/filters/FlawFilterControl.tsx</files>
  <action>
Run the full frontend pre-merge gate from CLAUDE.md and resolve any output. Run, in order:
`npm run lint`, `npm run knip` (no new dead exports/unused deps — this change adds no new
exports, but ChevronDown/useState must actually be used so no unused-import lint errors),
`npm test -- --run` (full frontend suite), and `npx tsc -b` (full type check, since this
touches a component's render). Fix anything that fails. If only formatting/lint autofixes
changed files, that is acceptable (frontend uses ESLint only — never run prettier).
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npm run knip && npx tsc -b && npm test -- --run 2>&1 | tail -25</automated>
  </verify>
  <done>
    `npm run lint`, `npm run knip`, `npx tsc -b`, and `npm test -- --run` all pass with zero
    errors. No new knip violations. No unused imports.
  </done>
</task>

</tasks>

<verification>
- The redesigned panel renders, top to bottom: Severity → Orientation → Depth → Tactic
  motif (the last three gated by showTacticFilter) → collapsed "More: Context" section
  (always) → Filter Logic explainer.
- Context family groups are collapsed by default and expand via the
  `filter-flaw-context-toggle` button.
- Count badge "Context · N" shows when N>0 Context tags selected, "Context" otherwise.
- `cd frontend && npm run lint && npm run knip && npx tsc -b && npm test -- --run` all pass.
</verification>

<success_criteria>
- Tactic controls visible by default; Context families collapsed behind a hand-rolled
  toggle mirroring FilterPanel's "More" pattern (no Radix Collapsible).
- Count badge reflects selected hidden Context tags.
- Collapse works on both Games (showTacticFilter=false) and Flaws (true) tabs via the single
  shared component.
- CLAUDE.md frontend rules honored: data-testid + aria-expanded + aria-controls on the
  toggle, text-sm floor, semantic button, theme classes only, small functions.
- Full frontend gate green.
</success_criteria>

<output>
Create `.planning/quick/260620-mjh-redesign-flawfiltercontrol-make-tactics-/260620-mjh-SUMMARY.md` when done
</output>
