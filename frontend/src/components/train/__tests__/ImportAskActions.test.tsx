// @vitest-environment jsdom
/**
 * ImportAskActions.test.tsx — quick task 260926-8p5.
 *
 * The zero-game Train import CTA: an internal link to /library/import whose
 * attribution goes through `trackEvent` (never a `data-umami-event`
 * attribute, which would turn the client-side navigation into a reload).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

const mockTrackEvent = vi.fn();
vi.mock('@/lib/analytics', () => ({
  trackEvent: (...args: unknown[]) => mockTrackEvent(...args),
}));

import { ImportAskActions } from '@/components/train/ImportAskActions';

afterEach(() => {
  cleanup();
  mockTrackEvent.mockReset();
});

describe('ImportAskActions', () => {
  it('links to the import page with a per-source testid', () => {
    render(
      <MemoryRouter>
        <ImportAskActions source="train-landing" />
      </MemoryRouter>,
    );
    const link = screen.getByTestId('btn-import-games-train-landing');
    expect(link.textContent).toBe('Import games');
    expect(link.getAttribute('href')).toBe('/library/import');
    expect(link.hasAttribute('data-umami-event')).toBe(false);
  });

  it('tracks the click with its source', () => {
    render(
      <MemoryRouter>
        <ImportAskActions source="train-score" />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByTestId('btn-import-games-train-score'));
    expect(mockTrackEvent).toHaveBeenCalledWith('import-cta', { source: 'train-score' });
  });
});
