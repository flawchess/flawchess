import { useNavigate } from 'react-router';
import { Button } from '@/components/ui/button';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';
import { useUserProfile } from '@/hooks/useUserProfile';

// ─── Four-delta copy (Phase 224 S-5) ──────────────────────────────────────────

const DELTA_1 =
  'Every game you import is analyzed by Stockfish automatically, with no per-game Analyze click.';
const DELTA_2 = 'Train switches from warm-up puzzles to the mistakes in your own games.';
const DELTA_3 = 'Your account, your games and your streak work on any device you log in from.';
const DELTA_4 = 'Nothing is deleted after 30 days of inactivity.';

const DELTAS = [DELTA_1, DELTA_2, DELTA_3, DELTA_4];

// ─── WelcomePage ──────────────────────────────────────────────────────────────

// 224 UAT round 1: on phones the two buttons share one row (Back left, Sign
// up free right) at the 48px Train touch height; desktop keeps the compact
// auto-width buttons.
const WELCOME_BUTTON_CLASS = cn(TRAIN_BUTTON_CLASS, 'flex-1 sm:flex-none');

/**
 * Reachable only from a "What changes?" button or a typed URL (Phase 224 S-1, D-05) —
 * never a forced redirect. DISCRETION (this phase): a registered visitor
 * renders the same four deltas with no sign-up button and no redirect; a
 * dead-end redirect on a page reachable only by a typed URL is worse than an
 * honest explanation.
 */
export function WelcomePage() {
  const navigate = useNavigate();
  const { logoutForPromotion } = useAuth();
  const { data: profile } = useUserProfile();
  const isGuest = profile?.is_guest === true;

  const handleSignUp = () => {
    logoutForPromotion();
    window.location.href = '/login?tab=register';
  };

  return (
    <main
      data-testid="welcome-page"
      className="mx-auto w-full max-w-2xl px-4 py-6 md:px-6 space-y-8"
    >
      <h1 className="text-2xl font-bold">What changes when you sign up</h1>

      <ul data-testid="welcome-delta-list" className="space-y-3">
        {DELTAS.map((delta, index) => (
          <li key={delta} data-testid={`welcome-delta-${index + 1}`} className="text-sm">
            {delta}
          </li>
        ))}
      </ul>

      <div className="flex flex-row gap-3" data-testid="welcome-actions">
        <Button
          variant="brand-outline"
          className={WELCOME_BUTTON_CLASS}
          data-testid="welcome-btn-back"
          onClick={() => navigate(-1)}
        >
          Back
        </Button>
        {isGuest && (
          <Button
            variant="default"
            className={WELCOME_BUTTON_CLASS}
            data-testid="welcome-btn-signup"
            data-umami-event="signup-cta"
            data-umami-event-source="welcome"
            onClick={handleSignUp}
          >
            Sign up free
          </Button>
        )}
      </div>
    </main>
  );
}
