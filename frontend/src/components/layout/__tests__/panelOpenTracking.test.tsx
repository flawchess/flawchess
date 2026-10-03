// @vitest-environment jsdom
import { useState } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { SidebarLayout, type SidebarPanelConfig } from '@/components/layout/SidebarLayout';
import { TooltipProvider } from '@/components/ui/tooltip';
import { MobileFilterDrawer } from '@/components/filters/MobileFilterDrawer';
import type { SidebarPanelId } from '@/lib/analytics';

// jsdom shims required by vaul's Drawer (MobileFilterDrawer) and the sidebar.
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
(globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
  ResizeObserverStub;

const PANELS: SidebarPanelConfig[] = [
  { id: 'filters', label: 'Filters', icon: <span>f</span>, content: <div>filters body</div> },
  { id: 'tags', label: 'Tags', icon: <span>t</span>, content: <div>tags body</div> },
];

function SidebarHarness() {
  const [active, setActive] = useState<string | null>(null);
  return (
    <TooltipProvider>
      <SidebarLayout panels={PANELS} activePanel={active} onActivePanelChange={setActive}>
        <div>main</div>
      </SidebarLayout>
    </TooltipProvider>
  );
}

function DrawerHarness({ open, panel }: { open: boolean; panel: SidebarPanelId }) {
  return (
    <TooltipProvider>
    <MobileFilterDrawer
      open={open}
      onOpenChange={() => {}}
      panel={panel}
      title="Tags"
      contentTestId="drawer-test-content"
      closeTestId="drawer-test-close"
    >
      <div>body</div>
    </MobileFilterDrawer>
    </TooltipProvider>
  );
}

describe('panel-open tracking', () => {
  const track = vi.fn();

  beforeEach(() => {
    track.mockClear();
    window.umami = { track, identify: vi.fn() };
    window.history.pushState({}, '', '/library/games');
  });

  afterEach(() => {
    cleanup();
    delete window.umami;
    window.history.pushState({}, '', '/');
  });

  describe('SidebarLayout', () => {
    it('fires one panel-open on the opening click and nothing on close', () => {
      render(<SidebarHarness />);
      expect(track).not.toHaveBeenCalled();

      fireEvent.click(screen.getByTestId('sidebar-strip-btn-filters'));
      expect(track).toHaveBeenCalledTimes(1);
      expect(track).toHaveBeenCalledWith('panel-open', { page: 'library', target: 'filters' });

      fireEvent.click(screen.getByTestId('sidebar-strip-btn-filters'));
      expect(track).toHaveBeenCalledTimes(1);
    });

    it('fires panel-open tags when switching panels, nothing on outside-click close', () => {
      render(<SidebarHarness />);
      fireEvent.click(screen.getByTestId('sidebar-strip-btn-filters'));
      track.mockClear();

      fireEvent.click(screen.getByTestId('sidebar-strip-btn-tags'));
      expect(track).toHaveBeenCalledTimes(1);
      expect(track).toHaveBeenCalledWith('panel-open', { page: 'library', target: 'tags' });

      track.mockClear();
      fireEvent.mouseDown(document.body);
      expect(track).not.toHaveBeenCalled();
    });
  });

  describe('MobileFilterDrawer', () => {
    it('fires once on the false-to-true transition, not on re-render, again on reopen', () => {
      const { rerender } = render(<DrawerHarness open={false} panel="tags" />);
      expect(track).not.toHaveBeenCalled();

      rerender(<DrawerHarness open={true} panel="tags" />);
      expect(track).toHaveBeenCalledTimes(1);
      expect(track).toHaveBeenCalledWith('panel-open', { page: 'library', target: 'tags' });

      rerender(<DrawerHarness open={true} panel="tags" />);
      expect(track).toHaveBeenCalledTimes(1);

      rerender(<DrawerHarness open={false} panel="tags" />);
      expect(track).toHaveBeenCalledTimes(1);

      rerender(<DrawerHarness open={true} panel="tags" />);
      expect(track).toHaveBeenCalledTimes(2);
    });

    it('fires nothing when mounted already open (D-03)', () => {
      render(<DrawerHarness open={true} panel="filters" />);
      expect(track).not.toHaveBeenCalled();
    });
  });
});
