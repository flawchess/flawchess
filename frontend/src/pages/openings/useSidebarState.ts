import { useCallback, useState } from 'react';

export type SidebarPanel = 'filters' | 'bookmarks';

export type SidebarStateApi = {
  // Desktop sidebar
  sidebarOpen: SidebarPanel | null;
  setSidebarOpen: (panel: SidebarPanel | null) => void;
  // Mobile drawers
  filterSidebarOpen: boolean;
  setFilterSidebarOpen: (open: boolean) => void;
  bookmarkSidebarOpen: boolean;
  setBookmarkSidebarOpen: (open: boolean) => void;
  // Onboarding hints (persisted in localStorage)
  playedAsHintDismissed: boolean;
  filtersHintDismissed: boolean;
  setFiltersHintDismissed: (v: boolean) => void;
  dismissPlayedAsHint: () => void;
};

/**
 * Owns sidebar/drawer open state plus the localStorage-backed onboarding
 * hint dismissal flags. Behavior preserved exactly from OpeningsPage.
 */
export function useSidebarState(): SidebarStateApi {
  const [sidebarOpen, setSidebarOpen] = useState<SidebarPanel | null>(null);
  const [filterSidebarOpen, setFilterSidebarOpen] = useState(false);
  const [bookmarkSidebarOpen, setBookmarkSidebarOpen] = useState(false);

  const [playedAsHintDismissed, setPlayedAsHintDismissed] = useState(
    () => localStorage.getItem('played-as-hint-dismissed') === 'true',
  );
  const [filtersHintDismissed, setFiltersHintDismissedState] = useState(
    () => localStorage.getItem('filters-hint-dismissed') === 'true',
  );

  const dismissPlayedAsHint = useCallback(() => {
    setPlayedAsHintDismissed(true);
    localStorage.setItem('played-as-hint-dismissed', 'true');
  }, []);

  const setFiltersHintDismissed = useCallback((v: boolean) => {
    setFiltersHintDismissedState(v);
    if (v) {
      localStorage.setItem('filters-hint-dismissed', 'true');
    }
  }, []);

  return {
    sidebarOpen,
    setSidebarOpen,
    filterSidebarOpen,
    setFilterSidebarOpen,
    bookmarkSidebarOpen,
    setBookmarkSidebarOpen,
    playedAsHintDismissed,
    filtersHintDismissed,
    setFiltersHintDismissed,
    dismissPlayedAsHint,
  };
}
