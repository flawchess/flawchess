import { Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { SettingsPanel } from '@/components/settings/SettingsPanel';
import { cn } from '@/lib/utils';
import { trackFeature } from '@/lib/analytics';
import { useTrackedOpen } from '@/hooks/useTrackedOpen';

interface SettingsDialogButtonProps {
  testId: string;
  className?: string;
}

/**
 * Desktop header cogwheel plus a modal holding the FULL SettingsPanel. Replaced the
 * /settings page (228 UAT): navigating to a page unmounted whatever was open, e.g.
 * the Train solution screen started the next puzzle on return. The modal never
 * navigates and changes apply live underneath.
 */
export function SettingsDialogButton({ testId, className }: SettingsDialogButtonProps) {
  // Every open of settings is a deliberate click, so no once option (Phase 229 D-13).
  const [open, setOpen] = useTrackedOpen(() => trackFeature('panel-open', { target: 'settings' }));

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      {/* DialogTrigger, not a plain onClick button: Radix returns focus on close only
          to the trigger it registered, so a bare button left focus on <body> after
          Escape/Close (228 code review WR-01, second pass). */}
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={cn(open ? 'bg-white/10 text-foreground' : 'text-muted-foreground hover:text-foreground', className)}
          aria-label="Settings"
          title="Settings"
          data-testid={testId}
        >
          <Settings className="h-4 w-4" aria-hidden="true" />
        </Button>
      </DialogTrigger>
      {/* aria-modal: Radix never sets it, and useBoardNavigationInput only suppresses
          arrow-key board stepping behind '[role="dialog"][aria-modal="true"]'
          (same fix as the mobile sheet, 228 code review WR-02). */}
      <DialogContent
        data-testid="settings-dialog"
        aria-modal="true"
        aria-describedby={undefined}
        className="max-h-[85vh] overflow-y-auto thin-scrollbar sm:max-w-xl"
      >
        <DialogTitle className="text-lg font-medium">Settings</DialogTitle>
        <SettingsPanel />
      </DialogContent>
    </Dialog>
  );
}
