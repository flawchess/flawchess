import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

/**
 * Handles the Google OAuth redirect callback.
 *
 * After Google authenticates the user, the backend redirects to:
 *   /auth/callback#token=<JWT>
 *
 * This page reads the token from the URL fragment, stores it in
 * localStorage, and navigates to the dashboard.
 */
export function OAuthCallbackPage() {
  const navigate = useNavigate();

  useEffect(() => {
    const hash = window.location.hash;
    const params = new URLSearchParams(hash.slice(1)); // strip leading #
    const token = params.get('token');

    if (token) {
      localStorage.setItem('auth_token', token);
      toast.success('Signed in with Google');
      navigate('/', { replace: true });
    } else {
      toast.error('Google sign-in failed. Please try again.');
      navigate('/login', { replace: true });
    }
  }, [navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="text-center text-muted-foreground">
        <p>Completing sign-in...</p>
      </div>
    </div>
  );
}
