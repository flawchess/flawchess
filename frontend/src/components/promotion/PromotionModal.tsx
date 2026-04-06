import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import * as Sentry from '@sentry/react';
import axios from 'axios';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/ui/alert';
import { useAuth } from '@/hooks/useAuth';
import { useUserProfile } from '@/hooks/useUserProfile';
import { apiClient } from '@/api/client';
import type { GuestPromoteResponse } from '@/types/api';

// Matches the minimum password length enforced by the existing RegisterForm
const MIN_PASSWORD_LENGTH = 8;

// Step type for the two-step promotion flow
type PromotionStep = 'confirm' | 'form';

interface PromotionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  hasActiveImport: boolean;
}

export function PromotionModal({ open, onOpenChange, hasActiveImport }: PromotionModalProps) {
  const { loginWithToken } = useAuth();
  const { data: profile } = useUserProfile();
  const location = useLocation();
  const navigate = useNavigate();

  const [step, setStep] = useState<PromotionStep>('confirm');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [googleAvailable, setGoogleAvailable] = useState<boolean | null>(null);

  // Check Google OAuth availability when modal opens
  useEffect(() => {
    if (open) {
      apiClient
        .get<{ available: boolean }>('/auth/google/available')
        .then((res) => setGoogleAvailable(res.data.available))
        // Expected to fail in dev environments without Google OAuth configured
        .catch(() => setGoogleAvailable(false));
    }
  }, [open]);

  // Reset form state whenever the modal closes
  useEffect(() => {
    if (!open) {
      setStep('confirm');
      setEmail('');
      setPassword('');
      setConfirmPassword('');
      setError(null);
      setIsSubmitting(false);
      setGoogleAvailable(null);
    }
  }, [open]);

  const totalGames =
    (profile?.chess_com_game_count ?? 0) + (profile?.lichess_game_count ?? 0);

  const handleGoogleSignIn = async () => {
    setIsSubmitting(true);
    try {
      const response = await apiClient.get<{ authorization_url: string }>(
        '/auth/google/authorize-promote',
      );
      window.location.href = response.data.authorization_url;
      // No setIsSubmitting(false) — page navigates away
    } catch (err) {
      setError('Could not start Google sign-in. Please try again.');
      Sentry.captureException(err, { tags: { source: 'guest-promotion-google' } });
      setIsSubmitting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);

    // Client-side validation
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters`);
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await apiClient.post<GuestPromoteResponse>(
        '/auth/guest/promote/email',
        { email, password },
      );
      // Atomically replace the guest token and clear the query cache so
      // useUserProfile refetches and returns is_guest: false, causing the
      // GuestBanner to disappear.
      loginWithToken(response.data.access_token);
      // Stay on the current page — the modal overlays the page where the user
      // triggered promotion.
      navigate(location.pathname, { replace: true });
      onOpenChange(false);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        // EMAIL_ALREADY_REGISTERED — expected conflict, not a Sentry-worthy bug
        setError(
          'This email is already registered. Please log in with your existing account instead.',
        );
      } else {
        setError('Something went wrong. Please try again.');
        Sentry.captureException(err, { tags: { source: 'guest-promotion' } });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="promote-modal">
        {step === 'confirm' ? (
          <>
            <DialogHeader>
              <DialogTitle>Save your progress</DialogTitle>
            </DialogHeader>
            <p className="text-sm text-muted-foreground">
              Signing up will permanently preserve:
            </p>
            <ul className="list-disc list-inside text-sm space-y-1">
              <li data-testid="promote-game-count">
                {totalGames} {totalGames === 1 ? 'game' : 'games'} imported
              </li>
              <li>Your opening bookmarks</li>
            </ul>
            {error && (
              <Alert variant="error" data-testid="promote-error">
                <p>{error}</p>
              </Alert>
            )}
            <DialogFooter className="flex-col gap-2 sm:flex-col">
              {googleAvailable === true && (
                <>
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    onClick={handleGoogleSignIn}
                    disabled={isSubmitting || hasActiveImport}
                    title={hasActiveImport ? 'An import is running — wait for it to finish' : undefined}
                    data-testid="btn-promote-google"
                  >
                    <GoogleIcon />
                    {isSubmitting ? 'Redirecting...' : 'Continue with Google'}
                  </Button>
                  <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                      <span className="w-full border-t border-border" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                      <span className="bg-card px-2 text-muted-foreground">or</span>
                    </div>
                  </div>
                </>
              )}
              <Button
                onClick={() => setStep('form')}
                data-testid="btn-promote-continue"
                className="w-full"
              >
                Continue with email
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Create your account</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-3">
              <div className="space-y-1">
                <Label htmlFor="promote-email">Email</Label>
                <Input
                  id="promote-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  data-testid="promote-email"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="promote-password">Password</Label>
                <Input
                  id="promote-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                  data-testid="promote-password"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="promote-confirm-password">Confirm password</Label>
                <Input
                  id="promote-confirm-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                  data-testid="promote-confirm-password"
                />
              </div>
              {error && (
                <Alert variant="error" data-testid="promote-error">
                  <p>{error}</p>
                </Alert>
              )}
              <DialogFooter>
                <Button
                  type="submit"
                  disabled={isSubmitting}
                  data-testid="btn-promote-submit"
                >
                  {isSubmitting ? 'Creating account...' : 'Create Account'}
                </Button>
              </DialogFooter>
            </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function GoogleIcon() {
  return (
    <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        fill="#EA4335"
      />
    </svg>
  );
}
