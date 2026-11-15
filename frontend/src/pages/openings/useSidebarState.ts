import { useState } from 'react';

export type SidebarPanel = 'filters' | 'bookmarks';

export type SidebarStateApi = {
  // Desktop sidebar
  sidebarOpen: SidebarPanel | null;
  setSidebarOpen: (panel: SidebarPanel | null) => void;
  // Mobile drawers
  filterDrawerOpen: boolean;
  setFilterDrawerOpen: (open: boolean) => void;
  bookmarkDrawerOpen: boolean;
  setBookmarkDrawerOpen: (open: boolean) => void;
};

/**
 * Owns the sidebar/drawer open state. The onboarding hint dots moved to the
 * server-side feature route (phase 255), so no localStorage state lives here.
 */
export function useSidebarState(): SidebarStateApi {
  const [sidebarOpen, setSidebarOpen] = useState<SidebarPanel | null>(null);
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const [bookmarkDrawerOpen, setBookmarkDrawerOpen] = useState(false);

  return {
    sidebarOpen,
    setSidebarOpen,
    filterDrawerOpen,
    setFilterDrawerOpen,
    bookmarkDrawerOpen,
    setBookmarkDrawerOpen,
  };
}
