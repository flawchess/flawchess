import { Link } from 'react-router-dom';
import { Alert } from '@/components/ui/alert';

export function GuestBanner() {
  return (
    <Alert
      variant="warning"
      data-testid="guest-banner"
      className="rounded-none border-x-0 border-t-0 py-2 text-xs"
    >
      <p>
        Guest session — your data is saved for 30 days.{' '}
        <Link
          to="/login?tab=register"
          className="font-medium underline underline-offset-2"
          data-testid="guest-banner-signup"
        >
          Sign up free
        </Link>{' '}
        to keep it permanently.
      </p>
    </Alert>
  );
}
