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
}

export function PromotionModal({ open, onOpenChange }: PromotionModalProps) {
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

  // Reset form state whenever the modal closes
  useEffect(() => {
    if (!open) {
      setStep('confirm');
      setEmail('');
      setPassword('');
      setConfirmPassword('');
      setError(null);
      setIsSubmitting(false);
    }
  }, [open]);

  const totalGames =
    (profile?.chess_com_game_count ?? 0) + (profile?.lichess_game_count ?? 0);

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
            <DialogFooter>
              <Button
                onClick={() => setStep('form')}
                data-testid="btn-promote-continue"
              >
                Continue
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
