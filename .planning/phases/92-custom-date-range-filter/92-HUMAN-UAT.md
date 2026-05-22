# Phase 92: Custom Date Range Filter — Human UAT Script

**Phase:** 92-custom-date-range-filter
**Written:** 2026-05-22
**Purpose:** Visual and behavioral verification of the custom date range filter feature. Automation cannot cover calendar UI rendering, popover/drawer animations, or mobile layout — this script is the acceptance gate for those surfaces.

## Setup

### Prerequisites

Confirm the dev environment is running before starting:

```bash
# Dev database
docker compose -f docker-compose.dev.yml -p flawchess-dev ps
# Expect: flawchess-dev-postgres-1 running

# Backend + frontend (if not already up)
bin/run_local.sh
```

Confirm at least one imported user with >= 50 games spanning multiple months exists in the dev DB. If the dev DB only has fresh test users (no games), sign in with a real account or import games via the UI before running this script.

**Per Adrian's memory ("No dev DB reset in plans"):** Do NOT run `bin/reset_db.sh`. All scenarios are designed to work against the existing dev DB.

---

### Scenario 1: Preset parity (the 95% case)

**Goal:** Verify the 8 existing presets still return the same WDL totals as before the Phase 92 wire-format change. The preset → dates conversion on the frontend must be equivalent to the previous recency-cutoff logic on the backend.

**Steps:**

1. Open `http://localhost:5173` (Openings page) in the browser.
2. For each of the 8 presets in the Recency Select:
   - All time
   - Past week
   - Past month
   - 3 months
   - 6 months
   - 1 year
   - 3 years
   - 5 years
3. Pick the preset, observe the WDL total in the position stats or stat card.
4. Compare against a pre-Phase-92 baseline (prior git checkout, screenshot, or expected value you recorded before this phase).

**Expected result:**
- "All time" must match exactly (both phases return all games).
- Date-bounded presets may differ by at most the games played within the UTC/local-day boundary window (at most ~24 h of games at the boundary may shift in or out per D-16 / RESEARCH.md §Pitfall 2). This small discrepancy is an accepted trade-off.

**Sign-off:** [ ] Scenario 1 passed / describe issues below

---

### Scenario 2: Desktop Custom range

**Goal:** Verify the two-step Select -> Popover flow on a desktop-width viewport.

**Steps:**

1. Open the Openings page at desktop width (>= 768 px; Chrome default is fine).
2. Open the filter sidebar if not already visible.
3. Click the Recency Select. Observe 9 items including "Custom range..." at the bottom.
4. Click "Custom range...". **Expected:** the dropdown closes and a Popover opens anchored to the same trigger element. No layout jump or flicker. A two-month range Calendar is visible inside the popover.
5. Pick a `from` date on the left calendar month. Observe the calendar highlights the start of the range.
6. Pick a `to` date on the right calendar month (must be >= from). **Expected:** the Popover closes automatically (D-05 auto-close on full range). The Select trigger now shows the resolved range label, e.g. `"Mar 1, 2026 - Apr 1, 2026"`.
7. Verify the WDL stats update to reflect only games in that window.
8. Verify the trigger label stays readable and does not overflow the Select trigger width.

**Expected result:** Popover opens/closes cleanly with no layout jump. Trigger label renders the date range. WDL updates.

**Sign-off:** [ ] Scenario 2 passed / describe issues below

---

### Scenario 3: Mobile Custom range

**Goal:** Verify the nested Vaul Drawer on mobile widths.

**Steps:**

1. In Chrome DevTools, toggle mobile emulation (or resize to < 768 px width).
2. Open the Openings page. Open the filter Drawer via the filter icon.
3. Inside the FilterPanel Drawer, click the Recency control -> "Custom range...".
4. **Expected:** a nested bottom sheet (Drawer.NestedRoot) slides up from the bottom. The outer FilterPanel Drawer should still be partially visible behind it. A single-month Calendar is visible inside the nested sheet. An "Apply" button is present at the bottom of the sheet.
5. Pick a `from` date. Observe the calendar range start highlight.
6. Pick a `to` date.
7. Tap "Apply". **Expected:** the nested Drawer closes, the FilterPanel Drawer remains open. The Recency trigger inside the FilterPanel Drawer shows the resolved range label.
8. **Backdrop dismiss test:** open "Custom range..." again. Pick only a `from` date (do NOT tap Apply). Tap the backdrop behind the nested Drawer (the dark overlay). **Expected:** the nested Drawer closes WITHOUT committing the partial range. The trigger label should show the previously applied range (or the default preset), not "From MMM d, yyyy...".

**Expected result:** Nested Drawer opens/closes correctly. Apply commits. Backdrop dismiss cancels (D-08).

**Sign-off:** [ ] Scenario 3 passed / describe issues below

---

### Scenario 4: Switch back to preset

**Goal:** Verify that switching from a custom range back to a preset clears the custom range state.

**Steps:**

1. With a custom range active (trigger shows date range label), open the Recency Select.
2. Pick any preset, e.g. "Past month".
3. **Expected:** the trigger label immediately updates to "Past month" (the preset name). The WDL stats update to the past-month window. A subsequent open of "Custom range..." should start fresh (no lingering prior range pre-populated).
4. Click "Custom range..." again. Confirm the Calendar opens with no pre-selected range highlighted.

**Expected result:** Preset pick clears the custom range. Trigger returns to preset label.

**Sign-off:** [ ] Scenario 4 passed / describe issues below

---

### Scenario 5: Insights gating regression check

**Goal:** Confirm the insights LLM endpoint correctly gates on the custom date filter (RESEARCH.md §Pitfall 3, T-92-06-01).

**Steps:**

1. Set Recency to "All time". Navigate to Endgames. Click "Get Insights" (or wait for auto-load). Verify the insights report generates (or loads from cache) without errors.
2. Now set a custom date range (any range narrower than "All time"). Navigate back to Endgames.
3. Click "Get Insights" (or observe the auto-load result).
4. **Expected:** the insights endpoint returns a blocking message. The UI should display a message containing "Clear Custom date range filter". The Insights button should not trigger the LLM.
5. Repeat with any non-all-time preset (e.g. "Past month"). Same blocking behavior expected.
6. Clear the filter back to "All time". Verify insights generation works again.

**Expected result:** Insights blocked when any date filter is active. Message includes "Clear Custom date range filter".

**Sign-off:** [ ] Scenario 5 passed / describe issues below

---

### Scenario 6: Reload behavior

**Goal:** Confirm that page reload resets filters to defaults (no persistence regression).

**Steps:**

1. Set a custom date range. Verify the trigger shows the range label and WDL is filtered.
2. Hard-reload the page (Ctrl+R / Cmd+R).
3. **Expected:** filters reset to `DEFAULT_FILTERS` (All time, all platforms, etc.). The Recency Select shows its default label ("All time" or whatever the default is). No error states or stale-cache issues visible. WDL reflects unfiltered data.
4. Also verify no console errors appear related to stale TanStack Query cache keys or unknown filter states.

**Expected result:** Reload clears all filters cleanly. No errors.

**Sign-off:** [ ] Scenario 6 passed / describe issues below

---

## Sign-off Checklist

When done, mark each scenario as passed or describe any issues found:

| # | Scenario | Result |
|---|----------|--------|
| 1 | Preset parity (8 presets, WDL totals match baseline) | [ ] passed / issues: |
| 2 | Desktop Custom range (Popover, auto-close, trigger label) | [ ] passed / issues: |
| 3 | Mobile Custom range (nested Drawer, Apply, backdrop dismiss) | [ ] passed / issues: |
| 4 | Switch back to preset (custom range cleared) | [ ] passed / issues: |
| 5 | Insights gating ("Clear Custom date range filter" message) | [ ] passed / issues: |
| 6 | Reload behavior (filters reset, no errors) | [ ] passed / issues: |

Type "approved" when all scenarios pass, or describe any failed scenarios for follow-up.
