import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/api/client';
import { Button } from '@/components/ui/button';

// Admin-only: Sentry error path test.
// Tests four error paths: event handler, TanStack Query, React render, and backend.
// Moved from frontend/src/pages/GlobalStats.tsx in Phase 62 (D-19).
export function SentryTestButtons() {
  const [shouldCrash, setShouldCrash] = useState(false);
  const [tqEnabled, setTqEnabled] = useState(false);

  // TanStack Query error — fires only when enabled
  useQuery({
    queryKey: ['sentry-test-tq-error'],
    queryFn: async () => { throw new Error('[Sentry Test] TanStack Query error'); },
    enabled: tqEnabled,
    retry: false,
  });

  // React render error — triggers ErrorBoundary + Sentry
  if (shouldCrash) {
    throw new Error('[Sentry Test] React render error');
  }

  return (
    <div
      className="charcoal-texture rounded-md p-4 space-y-2"
      data-testid="sentry-test-section"
    >
      <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
        Sentry Error Test (temporary)
      </p>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="destructive"
          data-testid="btn-sentry-test-event"
          onClick={() => { throw new Error('[Sentry Test] Event handler error'); }}
        >
          Event handler error
        </Button>
        <Button
          size="sm"
          variant="destructive"
          data-testid="btn-sentry-test-tq"
          onClick={() => setTqEnabled(true)}
        >
          TanStack Query error
        </Button>
        <Button
          size="sm"
          variant="destructive"
          data-testid="btn-sentry-test-render"
          onClick={() => setShouldCrash(true)}
        >
          React render error
        </Button>
        <Button
          size="sm"
          variant="destructive"
          data-testid="btn-sentry-test-backend"
          onClick={() => apiClient.post('/users/sentry-test-error')}
        >
          Backend error
        </Button>
      </div>
    </div>
  );
}
