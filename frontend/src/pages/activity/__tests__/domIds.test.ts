// Seam test: render.js addresses the page shell purely by DOM id, and the two
// files are plain strings to the type checker. A renamed or missing id would
// silently blank a chart, so assert every id render.js addresses exists in
// ActivityPage.tsx.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const renderSource = readFileSync(new URL('../render.js', import.meta.url), 'utf8');
const pageSource = readFileSync(new URL('../ActivityPage.tsx', import.meta.url), 'utf8');

// A quoted string starting with `#` and an id token: $("#x"), emptyNote("#x"), legend("#x"), ...
const RENDER_ID_PATTERN = /["'`]#([A-Za-z][\w-]*)/g;
const PAGE_ID_PATTERN = /\bid="([^"]+)"/g;

function collect(source: string, pattern: RegExp): Set<string> {
  return new Set([...source.matchAll(pattern)].map((m) => m[1] as string));
}

const BLUNDER_CHECK_HOSTS = [
  'c-bc-sessions',
  't-bc-sessions',
  'bc-sessions-legend',
  'c-bc-windows',
  'c-bc-score',
  'bc-outcome-legend',
  'c-bc-outcomes',
];

describe('activity page DOM ids', () => {
  const renderIds = collect(renderSource, RENDER_ID_PATTERN);
  const pageIds = collect(pageSource, PAGE_ID_PATTERN);

  it('every id render.js addresses exists in ActivityPage.tsx', () => {
    const missing = [...renderIds].filter((id) => !pageIds.has(id));
    expect(missing).toEqual([]);
  });

  it('render.js addresses every Blunder Check host', () => {
    for (const id of BLUNDER_CHECK_HOSTS) {
      expect(renderIds.has(id), id).toBe(true);
    }
  });
});
