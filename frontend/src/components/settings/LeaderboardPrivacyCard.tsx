import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { LoadError } from '@/components/ui/load-error';
import { Switch } from '@/components/ui/switch';
import { trackEvent } from '@/lib/analytics';
import { useSetLeaderboardHidden, useUserProfile } from '@/hooks/useUserProfile';

const HIDE_LABEL = 'Hide me from leaderboards';
const HIDE_HELPER =
  "Your username and weekly Train results stay off the leaderboards other people see. You still see your own position. Hidden users don't earn medals; medals you already won are kept.";
/** Setting id of the legacy `settings-change` event (same event SettingsPanel's sound switch sends). */
const LEADERBOARD_HIDDEN_SETTING_ID = 'leaderboard-hidden';
const SAVE_ERROR = "Couldn't save this setting. Please try again.";

/** The Privacy card shell around the profile-load error line. */
function PrivacyLoadErrorCard() {
  return (
    <Card as="section" data-testid="settings-section-privacy">
      <CardHeader as="h2" size="compact">Privacy</CardHeader>
      <CardBody>
        <LoadError
          resource="your privacy setting"
          variant="inline"
          data-testid="settings-section-privacy-error"
        />
      </CardBody>
    </Card>
  );
}

/**
 * Phase 230 D-16: the server-persisted "Hide me from leaderboards" switch.
 * Reads useUserProfile().data (not useAuth) and writes through the profile PUT.
 * Sends the legacy `settings-change` Umami event: the profile row is overwritten
 * in place, so switch-offs and change history would otherwise be lost
 * (quick 261004-rre). Renders nothing for guests: they never appear on boards, so there is nothing
 * to hide.
 */
export function LeaderboardPrivacyCard() {
  const { data: profile, isError } = useUserProfile();
  const mutation = useSetLeaderboardHidden();

  if (isError) return <PrivacyLoadErrorCard />;
  if (!profile || profile.is_guest) return null;

  const handleHiddenChange = (next: boolean): void => {
    mutation.mutate(next);
    trackEvent('settings-change', { setting: LEADERBOARD_HIDDEN_SETTING_ID, value: next ? 'on' : 'off' });
  };

  // While a save is in flight show the requested state, otherwise the stored one.
  // A rejected save leaves the cache untouched, so the switch falls back by itself.
  const checked = mutation.isPending ? mutation.variables : profile.leaderboard_hidden;

  return (
    <Card as="section" data-testid="settings-section-privacy">
      <CardHeader as="h2" size="compact">Privacy</CardHeader>
      <CardBody className="space-y-3">
        <div className="flex items-center gap-2">
          <Switch
            data-testid="settings-leaderboard-hidden-switch"
            aria-label={HIDE_LABEL}
            checked={checked}
            disabled={mutation.isPending}
            onCheckedChange={handleHiddenChange}
          />
          <p className="text-sm text-foreground">{HIDE_LABEL}</p>
        </div>
        <p className="text-sm text-muted-foreground">{HIDE_HELPER}</p>
        {mutation.isError && (
          <p className="text-sm text-destructive" data-testid="settings-leaderboard-hidden-error">
            {SAVE_ERROR}
          </p>
        )}
      </CardBody>
    </Card>
  );
}
