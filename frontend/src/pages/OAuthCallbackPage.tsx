import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import { useAuth } from '@/hooks/useAuth';

/**
 * Handles the Google OAuth redirect callback.
 *
 * After Google authenticates the user, the backend redirects to:
 *   /auth/callback#token=<JWT>
 *
 * This page reads the token from the URL fragment, updates auth state
 * (both localStorage and React context), and navigates to the dashboard.
 */
export function OAuthCallbackPage() {
  const navigate = useNavigate();
  const { loginWithToken } = useAuth();

  useEffect(() => {
    const hash = window.location.hash;
    const params = new URLSearchParams(hash.slice(1)); // strip leading #
    const token = params.get('token');

    if (token) {
      loginWithToken(token);
      toast.success('Signed in with Google');
      navigate('/', { replace: true });
    } else {
      toast.error('Google sign-in failed. Please try again.');
      navigate('/login', { replace: true });
    }
  }, [navigate, loginWithToken]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="text-center text-muted-foreground">
        <p>Completing sign-in...</p>
      </div>
    </div>
  );
}
