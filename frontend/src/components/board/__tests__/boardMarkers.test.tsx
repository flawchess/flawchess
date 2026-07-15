// @vitest-environment jsdom
import { describe, it, expect, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import { SquareMarkerGroup, type SquareMarker } from '../boardMarkers';
import { MAIA_ACCENT, BOOK_MARKER_COLOR } from '@/lib/theme';

function renderMarker(marker: SquareMarker) {
  return render(
    <svg data-testid="board-svg">
      <SquareMarkerGroup marker={marker} sqSize={64} flipped={false} />
    </svg>,
  );
}

describe('SquareMarkerGroup', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders the violet gem badge with no severity text for a gem marker', () => {
    const { container } = renderMarker({ square: 'e4', gem: true });

    const circle = container.querySelector('circle');
    expect(circle).not.toBeNull();
    expect(circle?.getAttribute('fill')).toBe(MAIA_ACCENT);

    // Nested lucide Gem icon renders as an inner <svg>.
    const nestedIcon = container.querySelectorAll('svg');
    expect(nestedIcon.length).toBeGreaterThan(1);

    // No severity NAG glyph text emitted.
    const text = container.querySelector('text');
    expect(text).toBeNull();
    expect(container.textContent).not.toContain('??');
    expect(container.textContent).not.toContain('?!');
  });

  it('still renders the "??" severity glyph for a blunder marker (regression)', () => {
    const { container } = renderMarker({ square: 'e4', severity: 'blunder' });

    const text = container.querySelector('text');
    expect(text?.textContent).toBe('??');

    // No gem icon rendered.
    const nestedIcon = container.querySelectorAll('svg');
    expect(nestedIcon.length).toBe(1);
  });

  // Phase 172 (SEED-106 D-08): book marker on the board corner marker.
  it('renders the muted book badge with a BookOpen glyph for a book marker', () => {
    const { container } = renderMarker({ square: 'e4', book: true });

    const circle = container.querySelector('circle');
    expect(circle).not.toBeNull();
    expect(circle?.getAttribute('fill')).toBe(BOOK_MARKER_COLOR);

    // Nested lucide BookOpen icon renders as an inner <svg>.
    const nestedIcon = container.querySelectorAll('svg');
    expect(nestedIcon.length).toBeGreaterThan(1);

    // No severity NAG glyph text emitted.
    const text = container.querySelector('text');
    expect(text).toBeNull();
  });

  it('still renders the gem badge when both gem and book could apply (ordering regression)', () => {
    const { container } = renderMarker({ square: 'e4', gem: true, book: true });

    const circle = container.querySelector('circle');
    expect(circle).not.toBeNull();
    // Gem takes precedence over book — same as the shipped fill.
    expect(circle?.getAttribute('fill')).toBe(MAIA_ACCENT);
    expect(circle?.getAttribute('fill')).not.toBe(BOOK_MARKER_COLOR);
  });
});
