import { Navigate, Outlet, Route, BrowserRouter as Router, Routes, useLocation } from 'react-router-dom';
import { Link } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from '@/components/ui/sonner';
import { Button } from '@/components/ui/button';

import { AuthProvider, useAuth } from '@/hooks/useAuth';
import { AuthPage } from '@/pages/Auth';
import { DashboardPage } from '@/pages/Dashboard';
import { OAuthCallbackPage } from '@/pages/OAuthCallbackPage';
import { OpeningsPage } from '@/pages/Openings';
import { RatingPage } from '@/pages/Rating';
import { GlobalStatsPage } from '@/pages/GlobalStats';

// ─── Query client ─────────────────────────────────────────────────────────────

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

// ─── Nav header ───────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { to: '/', label: 'Games' },
  { to: '/openings', label: 'Openings' },
  { to: '/rating', label: 'Rating' },
  { to: '/global-stats', label: 'Global Stats' },
] as const;

function NavHeader() {
  const location = useLocation();
  const { logout } = useAuth();

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
                  location.pathname === to
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
  return (
    <Routes>
      <Route path="/login" element={<AuthPage />} />
      {/* Google OAuth callback — reads token from URL fragment */}
      <Route path="/auth/callback" element={<OAuthCallbackPage />} />
      {/* Protected layout wraps all authenticated pages */}
      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/openings" element={<OpeningsPage />} />
        <Route path="/rating" element={<RatingPage />} />
        <Route path="/global-stats" element={<GlobalStatsPage />} />
      </Route>
      {/* Catch-all redirects to dashboard (auth guard handles the rest) */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
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
