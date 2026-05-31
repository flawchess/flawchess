/**
 * Phase 94.1 Plan 11 — regression guard for the import-complete invalidation gap.
 *
 * Bug: percentile badges on /endgames only appeared after a hard refresh because
 * the import-complete handlers in App.tsx (`handleJobDone`) and Import.tsx
 * (active-poll interval, delete-all-games handler) invalidated `['games']`,
 * `['gameCount']`, `['userProfile']`, but NOT `['endgameOverview']`. The
 * `staleTime: 30_000` default in queryClient.ts then served the stale
 * pre-import response for 30s.
 *
 * Fix: every invalidation call-site that affects user-game state also
 * invalidates `['endgameOverview']`.
 *
 * Test strategy: a heavy full-component mount of <ImportPage /> or <App /> is
 * not justified to catch a missing string literal. A static source-file
 * assertion is the smallest viable regression guard: if a future refactor
 * removes the `['endgameOverview']` invalidation from any of these call
 * sites, this test fails fast.
 */

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const IMPORT_TSX = new URL('../Import.tsx', import.meta.url);
const APP_TSX = new URL('../../App.tsx', import.meta.url);

function load(url: URL): string {
  return readFileSync(url, 'utf8');
}

const ENDGAME_OVERVIEW_INVALIDATION =
  /queryClient\.invalidateQueries\(\s*\{\s*queryKey:\s*\['endgameOverview'\]\s*\}\s*\)/g;

describe('endgameOverview invalidation contract (Phase 94.1-11)', () => {
  it('Import.tsx invalidates endgameOverview in at least 2 call sites', () => {
    const src = load(IMPORT_TSX);
    const matches = src.match(ENDGAME_OVERVIEW_INVALIDATION) ?? [];
    // Active-poll interval (during import) + delete-all-games handler.
    expect(matches.length).toBeGreaterThanOrEqual(2);
  });

  it('App.tsx invalidates endgameOverview when an import job completes', () => {
    const src = load(APP_TSX);
    const matches = src.match(ENDGAME_OVERVIEW_INVALIDATION) ?? [];
    // handleJobDone in App.tsx is the canonical import-complete site.
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });
});
