import { useEffect, useRef, type ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';

/** Collapsed sidebar strip width in pixels */
const STRIP_WIDTH = 48;
/** Open sidebar panel width in pixels */
const PANEL_WIDTH = 380;

export interface SidebarPanelConfig {
  id: string;
  label: string;
  icon: ReactNode;
  content: ReactNode;
  /** Extra content rendered next to the panel heading (e.g. info popover) */
  headerExtra?: ReactNode;
  notificationDot?: ReactNode;
}

interface SidebarLayoutProps {
  panels: SidebarPanelConfig[];
  /** Currently active panel id, or null if collapsed */
  activePanel: string | null;
  /** Called when user clicks a strip icon — receives the new panel state (toggled) */
  onActivePanelChange: (panel: string | null) => void;
  /**
   * Content placed next to the strip in a shared height container (e.g. board column).
   * The strip height matches this content via CSS flexbox — no JS measurement needed.
   * When the panel is open and taller than sideContent, the strip grows to match.
   * If not provided, the strip stretches to fill the main content area height.
   */
  sideContent?: ReactNode;
  /** Extra content rendered in the strip below the panel icons (e.g. color toggle) */
  stripExtra?: ReactNode;
  /**
   * Tailwind breakpoint at which the desktop layout activates. Pages with a wide
   * board column (Openings) need "lg" so the main content column doesn't get
   * squeezed too narrow at md (768px).
   */
  breakpoint?: 'md' | 'lg';
  children: ReactNode;
}

export function SidebarLayout({ panels, activePanel, onActivePanelChange, sideContent, stripExtra, breakpoint = 'md', children }: SidebarLayoutProps) {
  const activePanelConfig = panels.find(p => p.id === activePanel);
  const panelRef = useRef<HTMLDivElement>(null);
  const stripRef = useRef<HTMLDivElement>(null);
  const sideContainerRef = useRef<HTMLDivElement>(null);
  const hasSideContent = sideContent !== undefined;

  // When panel content is taller than the side container (board column),
  // grow the container so the strip extends to match the panel height.
  useEffect(() => {
    const container = sideContainerRef.current;
    const panel = panelRef.current;
    if (!container || !panel || !activePanel || !hasSideContent) {
      if (container) container.style.minHeight = '';
      return;
    }
    const observer = new ResizeObserver(entries => {
      const entry = entries[0];
      if (entry) {
        container.style.minHeight = `${entry.contentRect.height}px`;
      }
    });
    observer.observe(panel);
    return () => { observer.disconnect(); container.style.minHeight = ''; };
  }, [activePanel, hasSideContent]);

  // For Endgames/Stats (no sideContent): sync panel min-height to strip height
  useEffect(() => {
    if (hasSideContent || !panelRef.current || !stripRef.current || !activePanel) return;
    panelRef.current.style.minHeight = `${stripRef.current.offsetHeight}px`;
  }, [hasSideContent, activePanel]);

  // Close panel when clicking outside strip and panel
  // Skip clicks on Radix portals (Select dropdowns, popovers) opened from the sidebar
  useEffect(() => {
    if (!activePanel) return;
    const handleMouseDown = (e: MouseEvent) => {
      const target = e.target as Element;
      if (
        panelRef.current?.contains(target) ||
        stripRef.current?.contains(target) ||
        sideContainerRef.current?.contains(target) ||
        target.closest?.('[data-radix-popper-content-wrapper]') ||
        target.closest?.('[data-radix-select-viewport]')
      ) return;
      onActivePanelChange(null);
    };
    document.addEventListener('mousedown', handleMouseDown);
    return () => document.removeEventListener('mousedown', handleMouseDown);
  }, [activePanel, onActivePanelChange]);

  const handleStripClick = (panelId: string) => {
    onActivePanelChange(activePanel === panelId ? null : panelId);
  };

  const stripIcons = panels.map(panel => (
    <Tooltip key={panel.id} content={panel.label} side="right">
      <Button
        variant={activePanel === panel.id ? 'brand-outline' : 'ghost'}
        size="icon"
        className="relative"
        onClick={() => handleStripClick(panel.id)}
        aria-label={activePanel === panel.id ? `Close ${panel.label.toLowerCase()}` : `Open ${panel.label.toLowerCase()}`}
        data-testid={`sidebar-strip-btn-${panel.id}`}
      >
        {panel.icon}
        {panel.notificationDot}
      </Button>
    </Tooltip>
  ));

  const panelContent = activePanelConfig && (
    <div
      ref={panelRef}
      className="flex flex-col bg-background/80 backdrop-blur-md border border-border rounded-r-md overflow-y-auto absolute z-40 min-h-full max-h-[calc(100vh-6rem)]"
      style={{ width: PANEL_WIDTH, left: STRIP_WIDTH, top: 0 }}
      data-testid="sidebar-panel"
    >
      <div className="px-3 pt-3 pb-1 flex items-center gap-1">
        <h3 className="text-sm font-semibold" data-testid={`sidebar-panel-${activePanelConfig.id}`}>
          {activePanelConfig.label}
        </h3>
        {activePanelConfig.headerExtra}
      </div>
      {activePanelConfig.content}
    </div>
  );

  // Tailwind JIT requires complete class strings — branch on the prop rather than interpolating.
  const wrapperClass = breakpoint === 'lg'
    ? `hidden lg:flex lg:flex-row lg:min-h-0 lg:flex-1 lg:relative ${hasSideContent ? 'lg:items-start' : 'lg:items-stretch'}`
    : `hidden md:flex md:flex-row md:min-h-0 md:flex-1 md:relative ${hasSideContent ? 'md:items-start' : 'md:items-stretch'}`;

  return (
    <div className={wrapperClass}>
      {hasSideContent ? (
        /* Strip + sideContent share a container — strip height matches sideContent via CSS */
        <div ref={sideContainerRef} className="flex flex-row self-start relative">
          <div
            ref={stripRef}
            className="flex flex-col items-center py-3 gap-2 bg-sidebar-bg charcoal-texture border-r border-border rounded-l-md self-stretch"
            style={{ width: STRIP_WIDTH, flexShrink: 0 }}
            data-testid="sidebar-strip"
          >
            {stripIcons}
            {stripExtra}
          </div>
          {panelContent}
          <div className="ml-6">{sideContent}</div>
        </div>
      ) : (
        /* No sideContent — strip stretches to main content height */
        <>
          <div
            ref={stripRef}
            className="flex flex-col items-center py-3 gap-2 bg-sidebar-bg charcoal-texture border-r border-border rounded-l-md self-stretch relative"
            style={{ width: STRIP_WIDTH, flexShrink: 0 }}
            data-testid="sidebar-strip"
          >
            {stripIcons}
            {stripExtra}
          </div>
          {panelContent}
        </>
      )}

      {/* Main content area */}
      <div className="flex-1 min-w-0 ml-6">
        {children}
      </div>
    </div>
  );
}
