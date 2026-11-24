// @vitest-environment jsdom
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { RouterProvider, createBrowserRouter } from 'react-router';

vi.mock('@/components/settings/LeaderboardPrivacyCard', () => ({ LeaderboardPrivacyCard: () => null }));

import { AnalysisMoreMenu } from '../AnalysisMoreMenu';

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver = ResizeObserverStub;
  Element.prototype.setPointerCapture = vi.fn();
  Element.prototype.releasePointerCapture = vi.fn();
  Element.prototype.hasPointerCapture = vi.fn(() => false);
});

let track: ReturnType<typeof vi.fn>;
const onFlip = vi.fn();
const onOpenPasteModal = vi.fn();
let dispose: (() => void) | null = null;

/** A real browser router: Leave reads the entry index the router keeps in history.state. */
function renderMenu() {
  const router = createBrowserRouter([
    {
      path: '/analysis',
      element: (
        <AnalysisMoreMenu onFlip={onFlip} onOpenPasteModal={onOpenPasteModal} fen="fen" getPgn={() => 'pgn'} />
      ),
    },
    { path: '/library', element: <div data-testid="library-page" /> },
    { path: '/train', element: <div data-testid="train-page" /> },
  ]);
  dispose = () => router.dispose();
  render(<RouterProvider router={router} />);
  return router;
}

/** Radix DropdownMenu opens on pointerdown or Enter, never on a bare click. */
function openMenu(): void {
  fireEvent.keyDown(screen.getByTestId('analysis-btn-more'), { key: 'Enter' });
}

beforeEach(() => {
  track = vi.fn();
  window.umami = { track, identify: vi.fn() };
  window.history.replaceState(null, '', '/analysis');
});

afterEach(() => {
  cleanup();
  dispose?.();
  dispose = null;
  vi.clearAllMocks();
  delete window.umami;
  window.history.replaceState(null, '', '/');
});

describe('AnalysisMoreMenu', () => {
  it('lists Leave first and Flip last (nearest the thumb)', () => {
    renderMenu();
    expect(track).not.toHaveBeenCalled();
    openMenu();
    expect(screen.getAllByRole('menuitem').map((item) => item.getAttribute('data-testid'))).toEqual([
      'analysis-menu-leave',
      'analysis-menu-import',
      'analysis-menu-copy-pgn',
      'analysis-menu-copy-fen',
      'analysis-menu-settings',
      'analysis-menu-flip',
    ]);
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('panel-open', { page: 'analysis', target: 'analysis-more' });
  });

  it('Flip flips once and keeps the board-tool flip event', () => {
    renderMenu();
    openMenu();
    track.mockClear();
    fireEvent.click(screen.getByTestId('analysis-menu-flip'));
    expect(onFlip).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('board-tool', { page: 'analysis', target: 'flip' });
  });

  it('Settings opens the sheet in place and keeps the panel-open settings event', async () => {
    const router = renderMenu();
    openMenu();
    track.mockClear();
    fireEvent.click(screen.getByTestId('analysis-menu-settings'));
    expect(await screen.findByTestId('settings-sheet')).toBeTruthy();
    expect(router.state.location.pathname).toBe('/analysis');
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('panel-open', { page: 'analysis', target: 'settings' });
  });

  it('Import opens the paste modal', () => {
    renderMenu();
    openMenu();
    fireEvent.click(screen.getByTestId('analysis-menu-import'));
    expect(onOpenPasteModal).toHaveBeenCalledTimes(1);
  });

  it('Leave goes back to the previous in-app page', async () => {
    window.history.replaceState(null, '', '/train');
    const router = renderMenu();
    await act(() => router.navigate('/analysis'));
    openMenu();
    fireEvent.click(screen.getByTestId('analysis-menu-leave'));
    expect(await screen.findByTestId('train-page')).toBeTruthy();
  });

  it('Leave falls back to the library when /analysis is the first entry, even after a replace', async () => {
    const router = renderMenu();
    await act(() => router.navigate('/analysis?game_id=1', { replace: true }));
    openMenu();
    fireEvent.click(screen.getByTestId('analysis-menu-leave'));
    await waitFor(() => expect(screen.getByTestId('library-page')).toBeTruthy());
  });
});
