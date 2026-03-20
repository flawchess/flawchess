---
phase: quick
plan: 260320-ouo
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/ui/info-popover.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/pages/GlobalStats.tsx
  - frontend/src/components/stats/GlobalStatsCharts.tsx
  - frontend/src/components/charts/WDLBarChart.tsx
  - frontend/src/components/charts/WinRateChart.tsx
  - frontend/src/components/move-explorer/MoveExplorer.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "Info icon tooltips stay visible on mobile tap until user taps elsewhere"
    - "Info icon tooltips still work on desktop (click to open, click outside to close)"
  artifacts:
    - path: "frontend/src/components/ui/info-popover.tsx"
      provides: "Reusable click-based info icon component using Radix Popover"
  key_links:
    - from: "All info icon usage sites"
      to: "frontend/src/components/ui/info-popover.tsx"
      via: "import InfoPopover"
      pattern: "<InfoPopover"
---

<objective>
Fix mobile tooltip info icons that flash and close immediately on tap.

Purpose: Radix UI Tooltip is hover-based. On mobile, a tap fires hover+focus+click in rapid succession, opening and immediately closing the tooltip. The fix is to replace all info icon tooltips with a click-based Popover component that works reliably on both mobile and desktop.

Output: A reusable `InfoPopover` component and all info icon sites migrated to use it.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/ui/tooltip.tsx
@frontend/src/pages/Openings.tsx
@frontend/src/pages/GlobalStats.tsx
@frontend/src/components/stats/GlobalStatsCharts.tsx
@frontend/src/components/charts/WDLBarChart.tsx
@frontend/src/components/charts/WinRateChart.tsx
@frontend/src/components/move-explorer/MoveExplorer.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create InfoPopover component</name>
  <files>frontend/src/components/ui/info-popover.tsx</files>
  <action>
    Create a reusable `InfoPopover` component using Radix Popover (from `radix-ui` package, same as Tooltip import pattern: `import { Popover as PopoverPrimitive } from "radix-ui"`).

    Props:
    - `children: React.ReactNode` — the popover content text
    - `ariaLabel: string` — for the trigger button
    - `testId: string` — data-testid for the trigger button
    - `side?: "top" | "bottom" | "left" | "right"` — defaults to "top"

    The component renders:
    - `PopoverPrimitive.Root` (uncontrolled, click-to-toggle by default)
    - `PopoverPrimitive.Trigger` with `asChild`, wrapping a `<button>` with the Info icon (lucide-react `Info`, `h-3.5 w-3.5`), same styling as current tooltips: `text-muted-foreground hover:text-foreground`
    - `PopoverPrimitive.Portal` > `PopoverPrimitive.Content` with matching visual styling from the existing TooltipContent (dark background, rounded, text-xs/text-sm, max-w-xs, z-50). Use `sideOffset={4}`.
    - Include `PopoverPrimitive.Arrow` styled similarly to the tooltip arrow.
    - Add animation classes matching tooltip: `data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95`.

    Export as named export: `export { InfoPopover }`.

    Popover closes automatically when clicking outside — no custom logic needed.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit 2>&1 | head -30</automated>
  </verify>
  <done>InfoPopover component exists, compiles without errors, uses Radix Popover for click-based interaction.</done>
</task>

<task type="auto">
  <name>Task 2: Replace all info icon tooltips with InfoPopover</name>
  <files>
    frontend/src/pages/Openings.tsx
    frontend/src/pages/GlobalStats.tsx
    frontend/src/components/stats/GlobalStatsCharts.tsx
    frontend/src/components/charts/WDLBarChart.tsx
    frontend/src/components/charts/WinRateChart.tsx
    frontend/src/components/move-explorer/MoveExplorer.tsx
  </files>
  <action>
    In each file, replace every info icon tooltip pattern:
    ```tsx
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button type="button" className="..." aria-label="..." data-testid="...">
            <Info className="h-3.5 w-3.5" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs text-sm">
          {text}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
    ```

    With:
    ```tsx
    <InfoPopover ariaLabel="..." testId="...">
      {text}
    </InfoPopover>
    ```

    Specific replacements by file:

    **Openings.tsx** — 3 info tooltips: chessboard-info, piece-filter-info, position-bookmarks-info. Remove unused Tooltip/TooltipProvider/TooltipContent/TooltipTrigger imports and the `Info` import if no longer used. Add `import { InfoPopover } from '@/components/ui/info-popover'`.

    **GlobalStats.tsx** — 2 info tooltips: rating-chess-com-info, rating-lichess-info. Same import cleanup.

    **GlobalStatsCharts.tsx** — The `ChartTitle` component uses tooltip. Replace with InfoPopover. Update the `ChartTitle` function and its callers. Remove unused tooltip/Info imports.

    **WDLBarChart.tsx** — 1 info tooltip: wdl-bar-chart-info. Same pattern.

    **WinRateChart.tsx** — 1 info tooltip: win-rate-chart-info. Same pattern.

    **MoveExplorer.tsx** — 2 info tooltips: move-arrows-info and the flip-board tooltip. For the flip-board button (ArrowLeftRight icon), this is NOT an info tooltip — it's a different tooltip on a functional button. Leave that one as a Tooltip OR convert it too if it has the same mobile issue. Actually, convert it to use the same Popover approach but inline (not InfoPopover since it has a different trigger). Better: leave the flip-board tooltip as-is since it's a hover tooltip on a functional button, not an info icon. Only replace the move-arrows-info tooltip.

    After all replacements, verify no file imports both Tooltip components AND InfoPopover unless the file still uses Tooltip for non-info purposes. Clean up unused imports.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit 2>&1 | head -30 && npm run build 2>&1 | tail -10</automated>
  </verify>
  <done>All info icon tooltips replaced with InfoPopover. No TypeScript errors. Build succeeds. Tapping info icons on mobile opens a persistent popover that closes on outside tap.</done>
</task>

</tasks>

<verification>
- `cd frontend && npm run build` succeeds with no errors
- `cd frontend && npx tsc --noEmit` passes
- No remaining `<Tooltip>` wrapping `<Info` icon pattern in the codebase (grep confirms)
- Manual test on mobile: tap any info icon, popover appears and stays visible until tapping elsewhere
</verification>

<success_criteria>
- Info icon popovers open on tap (mobile) and click (desktop), stay visible until dismissed
- No tooltip flash-and-close behavior on mobile
- All existing info tooltips migrated to InfoPopover
- Build and type-check pass
</success_criteria>

<output>
After completion, create `.planning/quick/260320-ouo-fix-mobile-tooltip-info-icons-flashing-a/260320-ouo-SUMMARY.md`
</output>
