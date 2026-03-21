import { useState, useCallback, useEffect, useRef } from 'react';
import { Navigate, Outlet, Route, BrowserRouter as Router, Routes, useLocation } from 'react-router-dom';
import * as Sentry from "@sentry/react";
import { Link } from 'react-router-dom';
import { QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { queryClient } from '@/lib/queryClient';
import { Toaster } from '@/components/ui/sonner';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { DownloadIcon, BookOpenIcon, BarChart3Icon, MenuIcon, LogOutIcon } from 'lucide-react';
import {
  Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose,
} from '@/components/ui/drawer';

import { AuthProvider, useAuth } from '@/hooks/useAuth';
import { InstallPromptBanner } from '@/components/install/InstallPromptBanner';
import { useUserProfile } from '@/hooks/useUserProfile';
import { AuthPage } from '@/pages/Auth';
import { ImportPage } from '@/pages/Import';
import { OAuthCallbackPage } from '@/pages/OAuthCallbackPage';
import { OpeningsPage } from '@/pages/Openings';
import { GlobalStatsPage } from '@/pages/GlobalStats';
import { useImportPolling, useActiveJobs } from '@/hooks/useImport';

// ─── Non-visual job completion watcher ────────────────────────────────────────

function ImportJobWatcher({ jobId, onDone }: { jobId: string; onDone: (jobId: string) => void }) {
  const { data } = useImportPolling(jobId);

  useEffect(() => {
    if (data?.status === 'completed' || data?.status === 'failed') {
      onDone(jobId);
    }
  }, [data?.status, jobId, onDone]);

  return null;
}

// ─── Nav items ────────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { to: '/import', label: 'Import', Icon: DownloadIcon },
  { to: '/openings', label: 'Openings', Icon: BookOpenIcon },
  { to: '/global-stats', label: 'Statistics', Icon: BarChart3Icon },
] as const;

const BOTTOM_NAV_ITEMS = [
  { to: '/import', label: 'Import', Icon: DownloadIcon },
  { to: '/openings', label: 'Openings', Icon: BookOpenIcon },
  { to: '/global-stats', label: 'Statistics', Icon: BarChart3Icon },
] as const;

const ROUTE_TITLES: Record<string, string> = {
  '/import': 'Import',
  '/openings': 'Openings',
  '/global-stats': 'Statistics',
};

// ─── Active route helper ───────────────────────────────────────────────────────

function isActive(to: string, pathname: string): boolean {
  return to === '/openings'
    ? pathname.startsWith('/openings')
    : pathname === to;
}

// ─── Nav header (desktop) ─────────────────────────────────────────────────────

function NavHeader() {
  const location = useLocation();
  const { logout } = useAuth();

  return (
    <header className="hidden sm:block border-b border-border bg-background px-6 overflow-hidden">
      <div className="mx-auto flex max-w-7xl items-center justify-between py-1">
        <div className="flex items-center gap-1">
          <img src="/icons/logo-128.png" alt="" className="h-11 w-11 self-end -mb-1" aria-hidden="true" />
          <span className="mr-3 text-lg tracking-tight text-foreground font-brand">FlawChess</span>
          <nav aria-label="Main navigation">
            {NAV_ITEMS.map(({ to, label, Icon }) => (
              <Button
                key={to}
                asChild
                variant="ghost"
                size="sm"
                className={
                  isActive(to, location.pathname)
                    ? 'border-b-2 border-primary rounded-none font-medium'
                    : 'rounded-none text-muted-foreground'
                }
              >
                <Link to={to} data-testid={`nav-${label.toLowerCase().replace(/\s+/g, '-')}`}>
                  <Icon className="mr-1.5 h-4 w-4" aria-hidden="true" />
                  {label}
                </Link>
              </Button>
            ))}
          </nav>
        </div>
        <Button variant="ghost" size="sm" onClick={logout} data-testid="nav-logout">
          Logout
        </Button>
      </div>
    </header>
  );
}

// ─── Mobile header ────────────────────────────────────────────────────────────

function MobileHeader() {
  const location = useLocation();
  const pageTitle = Object.entries(ROUTE_TITLES).find(
    ([path]) => location.pathname.startsWith(path),
  )?.[1] ?? '';

  return (
    <header
      data-testid="mobile-header"
      className="block sm:hidden pt-safe flex items-center justify-between px-4 py-1 border-b border-border bg-background overflow-hidden"
    >
      <span
        data-testid="mobile-header-brand"
        className="flex items-center gap-1.5 text-xl tracking-tight text-foreground font-brand"
      >
        <img src="/icons/logo-128.png" alt="" className="h-11 w-11 self-end -mb-1" aria-hidden="true" />
        FlawChess
      </span>
      <span
        data-testid="mobile-header-page-title"
        className="text-sm text-muted-foreground"
      >
        {pageTitle}
      </span>
    </header>
  );
}

// ─── Mobile bottom bar ────────────────────────────────────────────────────────

function MobileBottomBar({ onMoreClick }: { onMoreClick: () => void }) {
  const location = useLocation();

  return (
    <nav
      aria-label="Mobile navigation"
      data-testid="mobile-bottom-bar"
      className="fixed bottom-0 inset-x-0 flex sm:hidden z-40 bg-background border-t border-border pb-safe"
    >
      {BOTTOM_NAV_ITEMS.map(({ to, label, Icon }) => (
        <Link
          key={to}
          to={to}
          data-testid={`mobile-nav-${label.toLowerCase().replace(/\s+/g, '-')}`}
          className={cn(
            'flex flex-1 flex-col items-center gap-1 py-2',
            isActive(to, location.pathname) ? 'text-primary' : 'text-muted-foreground',
          )}
        >
          <Icon className="h-5 w-5" aria-hidden="true" />
          <span className="text-xs">{label}</span>
        </Link>
      ))}
      <button
        onClick={onMoreClick}
        data-testid="mobile-nav-more"
        aria-label="More navigation options"
        className="flex flex-1 flex-col items-center gap-1 py-2 text-muted-foreground"
      >
        <MenuIcon className="h-5 w-5" aria-hidden="true" />
        <span className="text-xs">More</span>
      </button>
    </nav>
  );
}

// ─── Mobile more drawer ───────────────────────────────────────────────────────

function MobileMoreDrawer({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const location = useLocation();
  const { logout } = useAuth();
  const { data: profile } = useUserProfile();

  return (
    <Drawer open={open} onOpenChange={onOpenChange} direction="bottom">
      <DrawerContent data-testid="mobile-more-drawer">
        <DrawerHeader>
          <DrawerTitle className="text-sm font-medium text-foreground">
            {profile?.email ?? 'Account'}
          </DrawerTitle>
        </DrawerHeader>
        <div className="px-4 pb-4">
          <nav className="flex flex-col gap-1">
            {NAV_ITEMS.map(({ to, label }) => (
              <DrawerClose key={to} asChild>
                <Link
                  to={to}
                  data-testid={`drawer-nav-${label.toLowerCase().replace(/\s+/g, '-')}`}
                  className={cn(
                    'rounded-md px-3 py-2 text-base',
                    isActive(to, location.pathname) ? 'text-primary font-medium' : 'text-foreground',
                  )}
                >
                  {label}
                </Link>
              </DrawerClose>
            ))}
          </nav>
          <div className="my-2 border-t border-border" />
          <DrawerClose asChild>
            <button
              onClick={logout}
              data-testid="drawer-logout"
              className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-base text-destructive"
            >
              <LogOutIcon className="h-4 w-4" />
              Logout
            </button>
          </DrawerClose>
        </div>
      </DrawerContent>
    </Drawer>
  );
}

// ─── Layout (protected pages) ─────────────────────────────────────────────────

function ProtectedLayout() {
  const { token } = useAuth();
  const location = useLocation();
  const [moreOpen, setMoreOpen] = useState(false);
  const isOpeningsRoute = location.pathname.startsWith('/openings');

  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return (
    <>
      <NavHeader />
      {!isOpeningsRoute && <MobileHeader />}
      <main className="pb-16 sm:pb-0">
        <Outlet />
      </main>
      <MobileBottomBar onMoreClick={() => setMoreOpen(true)} />
      <MobileMoreDrawer open={moreOpen} onOpenChange={setMoreOpen} />
      <InstallPromptBanner />
    </>
  );
}

// ─── Home redirect (0 games → import, otherwise → openings) ──────────────────

function HomeRedirect() {
  const { data: profile, isLoading } = useUserProfile();

  if (isLoading) return null;

  const totalGames = (profile?.chess_com_game_count ?? 0) + (profile?.lichess_game_count ?? 0);
  return <Navigate to={totalGames === 0 ? '/import' : '/openings'} replace />;
}

// ─── Router ───────────────────────────────────────────────────────────────────

function AppRoutes() {
  const [activeJobIds, setActiveJobIds] = useState<string[]>([]);
  const [completedJobIds, setCompletedJobIds] = useState<Set<string>>(new Set());
  const queryClient = useQueryClient();
  const { token } = useAuth();

  // Restore active jobs from server on mount (and after re-login when token changes)
  const hasRestoredRef = useRef(false);
  // Track which token restoration has been performed for — reset guard on re-login
  const restoredForTokenRef = useRef<string | null>(null);
  // eslint-disable-next-line react-hooks/refs -- intentional: reset restoration guard on token change
  if (restoredForTokenRef.current !== token) {
    restoredForTokenRef.current = token; // eslint-disable-line react-hooks/refs
    hasRestoredRef.current = false; // eslint-disable-line react-hooks/refs
  }

  const activeJobsQuery = useActiveJobs(!!token);
  useEffect(() => {
    if (hasRestoredRef.current) return;
    if (!activeJobsQuery.data) return;
    hasRestoredRef.current = true;
    const serverJobIds = activeJobsQuery.data.map((j) => j.job_id);
    setActiveJobIds((ids) => {
      const existing = new Set(ids);
      const newIds = serverJobIds.filter((id) => !existing.has(id));
      if (newIds.length === 0) return ids;
      return [...ids, ...newIds];
    });
  }, [activeJobsQuery.data]);

  const handleImportStarted = useCallback((jobId: string) => {
    setActiveJobIds((ids) => [...ids, jobId]);
  }, []);

  // Called when a job finishes (completed or failed) — invalidate queries but keep in list
  const handleJobDone = useCallback((jobId: string) => {
    setCompletedJobIds((prev) => {
      if (prev.has(jobId)) return prev;
      const next = new Set(prev);
      next.add(jobId);
      return next;
    });
    queryClient.invalidateQueries({ queryKey: ['games'] });
    queryClient.invalidateQueries({ queryKey: ['gameCount'] });
    queryClient.invalidateQueries({ queryKey: ['userProfile'] });
  }, [queryClient]);

  // Called when user dismisses a completed progress bar
  const handleJobDismissed = useCallback((jobId: string) => {
    setActiveJobIds((ids) => ids.filter((id) => id !== jobId));
    setCompletedJobIds((prev) => {
      const next = new Set(prev);
      next.delete(jobId);
      return next;
    });
  }, []);

  // Only watch jobs that haven't completed yet
  const watchableJobIds = activeJobIds.filter((id) => !completedJobIds.has(id));

  return (
    <>
      <Routes>
        <Route path="/login" element={<AuthPage />} />
        {/* Google OAuth callback — reads token from URL fragment */}
        <Route path="/auth/callback" element={<OAuthCallbackPage />} />
        {/* Protected layout wraps all authenticated pages */}
        <Route element={<ProtectedLayout />}>
          <Route path="/" element={<HomeRedirect />} />
          <Route path="/import" element={<ImportPage onImportStarted={handleImportStarted} activeJobIds={activeJobIds} onJobDismissed={handleJobDismissed} />} />
          <Route path="/openings/*" element={<OpeningsPage />} />
          <Route path="/rating" element={<Navigate to="/global-stats" replace />} />
          <Route path="/global-stats" element={<GlobalStatsPage />} />
        </Route>
        {/* Catch-all redirects to openings */}
        <Route path="*" element={<Navigate to="/openings" replace />} />
      </Routes>
      {watchableJobIds.map((id) => (
        <ImportJobWatcher key={id} jobId={id} onDone={handleJobDone} />
      ))}
    </>
  );
}

// ─── App ──────────────────────────────────────────────────────────────────────

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <AuthProvider>
          <Sentry.ErrorBoundary
            fallback={
              <div className="flex flex-col items-center justify-center min-h-screen gap-4">
                <p className="text-lg font-medium text-destructive">Something went wrong.</p>
                <button
                  onClick={() => window.location.reload()}
                  className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
                  data-testid="btn-error-reload"
                >
                  Reload page
                </button>
              </div>
            }
          >
            <AppRoutes />
            <Toaster richColors />
          </Sentry.ErrorBoundary>
        </AuthProvider>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
