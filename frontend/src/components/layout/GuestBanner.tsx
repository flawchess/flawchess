import { Alert } from '@/components/ui/alert';

interface GuestBannerProps {
  onPromote: () => void;
}

export function GuestBanner({ onPromote }: GuestBannerProps) {
  return (
    <Alert
      variant="warning"
      data-testid="guest-banner"
      className="rounded-none border-x-0 border-t-0 py-2 text-xs"
    >
      <p>
        Guest session — your data is saved for 30 days.{' '}
        <button
          onClick={onPromote}
          className="font-medium underline underline-offset-2"
          data-testid="guest-banner-signup"
        >
          Sign up free
        </button>{' '}
        to keep it permanently.
      </p>
    </Alert>
  );
}
