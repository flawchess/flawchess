import { useState, useCallback, useEffect, useRef } from 'react';
import { Navigate, Outlet, Route, BrowserRouter as Router, Routes, useLocation } from 'react-router-dom';
import { Link } from 'react-router-dom';
import { QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { queryClient } from '@/lib/queryClient';
import { Toaster } from '@/components/ui/sonner';
import { Button } from '@/components/ui/button';

import { AuthProvider, useAuth } from '@/hooks/useAuth';
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

// ─── Nav header ───────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { to: '/import', label: 'Import' },
  { to: '/openings', label: 'Openings' },
  { to: '/global-stats', label: 'Global Stats' },
] as const;

function NavHeader() {
  const location = useLocation();
  const { logout } = useAuth();

  const isActive = (to: string) =>
    to === '/openings'
      ? location.pathname.startsWith('/openings')
      : location.pathname === to;

  return (
    <header className="border-b border-border bg-background px-6 py-3">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <div className="flex items-center gap-1">
          <span className="mr-3 text-lg font-bold tracking-tight text-foreground">Chessalytics</span>
          <nav aria-label="Main navigation">
            {NAV_ITEMS.map(({ to, label }) => (
              <Button
                key={to}
                asChild
                variant="ghost"
                size="sm"
                className={
                  isActive(to)
                    ? 'border-b-2 border-primary rounded-none font-medium'
                    : 'rounded-none text-muted-foreground'
                }
              >
                <Link to={to} data-testid={`nav-${label.toLowerCase().replace(/\s+/g, '-')}`}>{label}</Link>
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

// ─── Layout (protected pages) ─────────────────────────────────────────────────

function ProtectedLayout() {
  const { token } = useAuth();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return (
    <>
      <NavHeader />
      <Outlet />
    </>
  );
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
  if (restoredForTokenRef.current !== token) {
    restoredForTokenRef.current = token;
    hasRestoredRef.current = false;
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
          <Route path="/" element={<Navigate to="/openings" replace />} />
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
          <AppRoutes />
          <Toaster richColors />
        </AuthProvider>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
