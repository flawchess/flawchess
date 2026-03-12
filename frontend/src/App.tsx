import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from '@/components/ui/sonner';

import { AuthProvider, useAuth } from '@/hooks/useAuth';
import { AuthPage } from '@/pages/Auth';
import { DashboardPage } from '@/pages/Dashboard';
import { OAuthCallbackPage } from '@/pages/OAuthCallbackPage';

// ─── Query client ─────────────────────────────────────────────────────────────

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

// ─── Protected route ──────────────────────────────────────────────────────────

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

// ─── Router ───────────────────────────────────────────────────────────────────

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage />} />
      {/* Google OAuth callback — reads token from URL fragment */}
      <Route path="/auth/callback" element={<OAuthCallbackPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
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
