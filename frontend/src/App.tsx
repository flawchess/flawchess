import { useState, useCallback, useEffect, useRef } from 'react';
import { Navigate, Outlet, Route, BrowserRouter as Router, Routes, useLocation } from 'react-router-dom';
import * as Sentry from "@sentry/react";
import { Link } from 'react-router-dom';
import { QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { queryClient } from '@/lib/queryClient';
import { Toaster } from '@/components/ui/sonner';
import { toast } from 'sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { DownloadIcon, BookOpenIcon, BarChart3Icon, MenuIcon, LogOutIcon, TrophyIcon, DoorOpen, Shield } from 'lucide-react';
import {
  Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose,
} from '@/components/ui/drawer';

import { apiClient } from '@/api/client';
import { AuthProvider, useAuth } from '@/hooks/useAuth';
import { InstallPromptBanner } from '@/components/install/InstallPromptBanner';
import { ImpersonationPill } from '@/components/admin/ImpersonationPill';
import { useUserProfile } from '@/hooks/useUserProfile';
import { AuthPage } from '@/pages/Auth';
import { HomePage } from '@/pages/Home';
import { ImportPage } from '@/pages/Import';
import { OAuthCallbackPage } from '@/pages/OAuthCallbackPage';
import { OpeningsPage } from '@/pages/Openings';
import { EndgamesPage } from '@/pages/Endgames';
import { GlobalStatsPage } from '@/pages/GlobalStats';
import { AdminPage } from '@/pages/Admin';
import { PrivacyPage } from '@/pages/Privacy';
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
  { to: '/endgames', label: 'Endgames', Icon: TrophyIcon },
  { to: '/global-stats', label: 'Global Stats', Icon: BarChart3Icon },
] as const;

const BOTTOM_NAV_ITEMS = [
  { to: '/import', label: 'Import', Icon: DownloadIcon },
  { to: '/openings', label: 'Openings', Icon: BookOpenIcon },
  { to: '/endgames', label: 'Endgames', Icon: TrophyIcon },
  { to: '/global-stats', label: 'Global Stats', Icon: BarChart3Icon },
] as const;

// D-16: Admin nav item appended at render time when profile.is_superuser === true.
// Kept out of the `as const` NAV_ITEMS tuple so the conditional spread below does
// not widen the type; declared here so both NavHeader and MobileMoreDrawer share
// the same object literal and icon.
const ADMIN_NAV_ITEM = { to: '/admin', label: 'Admin', Icon: Shield } as const;

const ROUTE_TITLES: Record<string, string> = {
  '/import': 'Import',
  '/openings': 'Openings',
  '/endgames': 'Endgames',
  '/global-stats': 'Global Stats',
  '/admin': 'Admin',
};

// ─── Active route helper ───────────────────────────────────────────────────────

function isActive(to: string, pathname: string): boolean {
  if (to === '/openings') return pathname.startsWith('/openings');
  if (to === '/endgames') return pathname.startsWith('/endgames');
  return pathname === to;
}

// ─── Nav header (desktop) ─────────────────────────────────────────────────────

function NavHeader() {
  const location = useLocation();
  const { logout } = useAuth();
  const { data: profile } = useUserProfile();
  const noGames = profile != null && profile.chess_com_game_count + profile.lichess_game_count === 0;
  // D-16: Admin tab rightmost for superusers, absent otherwise.
  const navItems = profile?.is_superuser ? [...NAV_ITEMS, ADMIN_NAV_ITEM] : NAV_ITEMS;

  return (
    <header className="hidden sm:block bg-background border-b border-border px-6 overflow-hidden">
      <div className="mx-auto flex max-w-7xl items-stretch justify-between">
        <div className="flex items-center">
          <Link to="/openings" className="flex items-center gap-1 mr-3" data-testid="nav-home">
            <img src="/icons/logo-128.png" alt="" className="h-11 w-11 self-end -mb-1" aria-hidden="true" />
            <span className="text-lg tracking-tight text-foreground font-brand">FlawChess</span>
          </Link>
          <nav aria-label="Main navigation" className="flex items-stretch h-full">
            {navItems.map(({ to, label, Icon }) => (
              <Link
                key={to}
                to={to}
                data-testid={`nav-${label.toLowerCase().replace(/\s+/g, '-')}`}
                className={cn(
                  'relative flex items-center gap-1.5 px-3 text-sm transition-colors',
                  isActive(to, location.pathname)
                    ? 'font-medium bg-white/10 text-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {label}
                {to === '/import' && noGames && (
                  <span
                    className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
                    data-testid="import-notification-dot"
                  >
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
                  </span>
                )}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-2">
          {profile?.is_guest && (
            <Badge
              className="bg-amber-500/15 text-amber-500 border-amber-500/30 text-xs"
              data-testid="nav-guest-badge"
              aria-label="Guest session"
            >
              <DoorOpen className="h-3 w-3 mr-1" />
              Guest
            </Badge>
          )}
          {profile?.impersonation && (
            <ImpersonationPill impersonation={profile.impersonation} />
          )}
          <Button variant="ghost" size="sm" onClick={logout} data-testid="nav-logout">
            Logout
          </Button>
        </div>
      </div>
    </header>
  );
}

// ─── Mobile header ────────────────────────────────────────────────────────────

function MobileHeader() {
  const location = useLocation();
  const { data: profile } = useUserProfile();
  const pageTitle = Object.entries(ROUTE_TITLES).find(
    ([path]) => location.pathname.startsWith(path),
  )?.[1] ?? '';

  return (
    <header
      data-testid="mobile-header"
      className="block sm:hidden pt-safe flex items-center justify-between px-4 py-1 bg-background border-b border-border overflow-hidden"
    >
      <Link
        to="/openings"
        data-testid="nav-home-mobile"
        className="flex items-center gap-1.5 text-xl tracking-tight text-foreground font-brand"
      >
        <img src="/icons/logo-128.png" alt="" className="h-11 w-11 self-end -mb-1" aria-hidden="true" />
        FlawChess
      </Link>
      <div className="flex items-center gap-2 min-w-0">
        {profile?.impersonation && (
          <ImpersonationPill
            impersonation={profile.impersonation}
            emailMaxWidthClass="max-w-[8rem]"
          />
        )}
        <span
          data-testid="mobile-header-page-title"
          className="text-sm text-muted-foreground"
        >
          {pageTitle}
        </span>
      </div>
    </header>
  );
}

// ─── Mobile bottom bar ────────────────────────────────────────────────────────

function MobileBottomBar({ onMoreClick }: { onMoreClick: () => void }) {
  const location = useLocation();
  const { data: profile } = useUserProfile();
  const noGames = profile != null && profile.chess_com_game_count + profile.lichess_game_count === 0;

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
            'relative flex flex-1 flex-col items-center gap-1 py-2',
            isActive(to, location.pathname) ? 'text-primary' : 'text-muted-foreground',
          )}
        >
          <Icon className="h-5 w-5" aria-hidden="true" />
          <span className="text-xs">{label}</span>
          {to === '/import' && noGames && (
            <span
              className="absolute top-1.5 right-[30%] flex h-2 w-2"
              data-testid="import-notification-dot-mobile"
            >
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
            </span>
          )}
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
  // D-17: Admin entry surfaced in the More drawer (not the bottom bar) for superusers.
  const navItems = profile?.is_superuser ? [...NAV_ITEMS, ADMIN_NAV_ITEM] : NAV_ITEMS;

  return (
    <Drawer open={open} onOpenChange={onOpenChange} direction="bottom">
      <DrawerContent data-testid="mobile-more-drawer">
        <DrawerHeader>
          <DrawerTitle className="text-sm font-medium text-foreground">
            {profile?.is_guest ? 'Guest session' : (profile?.email ?? 'Account')}
          </DrawerTitle>
        </DrawerHeader>
        <div className="px-4 pb-4">
          <nav className="flex flex-col gap-1">
            {navItems.map(({ to, label }) => (
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
  const { token, refreshAuthToken } = useAuth();
  const { data: profile } = useUserProfile();
  const location = useLocation();
  const [moreOpen, setMoreOpen] = useState(false);
  const isOpeningsRoute = location.pathname.startsWith('/openings');
  const refreshedRef = useRef(false);

  // Show deferred toast from OAuth callback — checked here because ProtectedLayout
  // is the stable destination after the redirect chain (callback → / → /openings).
  useEffect(() => {
    const msg = sessionStorage.getItem('pending_toast');
    if (msg) {
      sessionStorage.removeItem('pending_toast');
      toast.success(msg);
    }
  }, []);

  // GUEST-05: Refresh guest JWT on each visit, resetting the 30-day expiry.
  // Uses refreshAuthToken (not loginWithToken) to avoid clearing the query cache
  // on the same user — otherwise useUserProfile refetches mid-keystroke on the
  // Import page and the focused username input loses focus after the first char.
  useEffect(() => {
    if (profile?.is_guest && !refreshedRef.current) {
      refreshedRef.current = true;
      apiClient.post<{ access_token: string }>('/auth/guest/refresh')
        .then((res) => refreshAuthToken(res.data.access_token))
        .catch(() => { /* token still valid, refresh is best-effort */ });
    }
  }, [profile?.is_guest, refreshAuthToken]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return (
    <>
      <NavHeader />
      {!isOpeningsRoute && (
        <>
          <MobileHeader />
        </>
      )}
      <main className="pb-16 sm:pb-0">
        <Outlet />
      </main>
      <MobileBottomBar onMoreClick={() => setMoreOpen(true)} />
      <MobileMoreDrawer open={moreOpen} onOpenChange={setMoreOpen} />
      <InstallPromptBanner />
    </>
  );
}

// ─── Superuser route guard ────────────────────────────────────────────────────

/**
 * Redirects non-superusers to /openings (D-18). Profile query loading flicker
 * falls through to an explicit loading state so we do not briefly show /admin
 * to someone whose profile has not resolved yet.
 */
function SuperuserRoute({ children }: { children: React.ReactNode }) {
  const { data: profile, isLoading } = useUserProfile();
  if (isLoading) {
    return <div className="p-6 text-muted-foreground" data-testid="superuser-route-loading">Loading...</div>;
  }
  if (!profile?.is_superuser) {
    return <Navigate to="/openings" replace />;
  }
  return <>{children}</>;
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
    // Phase 62: an admin who impersonates swaps their token — their in-flight job
    // ids belong to the admin, not the target. Drop them so we do not poll 404s.
    setActiveJobIds([]);
    setCompletedJobIds(new Set());
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
        {/* Public routes */}
        <Route path="/" element={<HomePage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/login" element={<AuthPage />} />
        {/* Google OAuth callback — reads token from URL fragment */}
        <Route path="/auth/callback" element={<OAuthCallbackPage />} />
        {/* Protected layout wraps all authenticated pages */}
        <Route element={<ProtectedLayout />}>
          <Route path="/import" element={<ImportPage onImportStarted={handleImportStarted} activeJobIds={activeJobIds} onJobDismissed={handleJobDismissed} />} />
          <Route path="/openings/*" element={<OpeningsPage />} />
          <Route path="/endgames/*" element={<EndgamesPage />} />
          <Route path="/rating" element={<Navigate to="/global-stats" replace />} />
          <Route path="/global-stats" element={<GlobalStatsPage />} />
          <Route path="/admin" element={<SuperuserRoute><AdminPage /></SuperuserRoute>} />
        </Route>
        {/* Catch-all redirects to homepage */}
        <Route path="*" element={<Navigate to="/" replace />} />
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
          <TooltipProvider>
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
          </TooltipProvider>
        </AuthProvider>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
