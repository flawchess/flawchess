import { useState, type ReactNode } from 'react';
import { Settings, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from '@/components/ui/drawer';
import { SettingsPanel } from '@/components/settings/SettingsPanel';

interface SettingsSheetButtonProps {
  testId: string;
  className?: string;
}

interface SettingsSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Optional DrawerTrigger rendered inside the Drawer so focus returns to it on close. */
  trigger?: ReactNode;
}

/**
 * Mobile bottom drawer rendering the FULL SettingsPanel (D-06). Controlled, so the
 * mobile More drawer's Settings row can open it after closing itself (228 UAT:
 * settings never navigate, a /settings page lost the puzzle being solved).
 */
export function SettingsSheet({ open, onOpenChange, trigger }: SettingsSheetProps) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange} direction="bottom">
      {trigger}
      {/* aria-modal: the vaul/Radix dialog never sets it, and
          useBoardNavigationInput only suppresses arrow-key board stepping
          behind '[role="dialog"][aria-modal="true"]'. Without it, ArrowLeft/Right
          on the Sound switch or Reset button stepped the analysis board behind
          the open sheet (228 code review WR-02). */}
      <DrawerContent data-testid="settings-sheet" aria-modal="true">
        <DrawerHeader className="flex flex-row items-center justify-between">
          <DrawerTitle>Settings</DrawerTitle>
          <DrawerClose asChild>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Close settings"
              data-testid="btn-settings-sheet-close"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </Button>
          </DrawerClose>
        </DrawerHeader>
        {/* drawer.tsx caps bottom drawers at max-h-[80vh] with no scroll of their
            own, so the body scrolls itself (MobileFilterDrawer pattern). */}
        <div className="overflow-y-auto thin-scrollbar flex-1 px-4 pb-4">
          <SettingsPanel />
        </div>
      </DrawerContent>
    </Drawer>
  );
}

/**
 * Cogwheel trigger plus the settings drawer. Used in the mobile shells that hide
 * the bottom bar: /analysis (D-03) and the bot game (D-04). It never navigates;
 * changes apply live underneath because the store notifies subscribers.
 */
export function SettingsSheetButton({ testId, className }: SettingsSheetButtonProps) {
  const [open, setOpen] = useState(false);

  // DrawerTrigger, not a plain onClick button: vaul/Radix return focus on close only
  // to the trigger they registered, so a bare button left focus on <body> after the
  // sheet closed (228 code review WR-01, second pass).
  return (
    <SettingsSheet
      open={open}
      onOpenChange={setOpen}
      trigger={
        <DrawerTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className={className}
            aria-label="Settings"
            title="Settings"
            data-testid={testId}
          >
            <Settings className="size-5" aria-hidden="true" />
          </Button>
        </DrawerTrigger>
      }
    />
  );
}
