import { useState } from 'react';
import type { ReactElement } from 'react';
import { ArrowLeft, EllipsisVertical, Repeat2, Settings } from 'lucide-react';
import { LABELLED_BUTTON_CLASS } from '@/components/board/BoardControls';
import { SettingsSheet } from '@/components/settings/SettingsSheetButton';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useTrackedOpen } from '@/hooks/useTrackedOpen';
import { trackFeature } from '@/lib/analytics';

interface BotGameMoreMenuProps {
  /** Returns to the bot roster and keeps the unfinished game's snapshot. */
  onLeave: () => void;
  onFlip: () => void;
}

/**
 * The last column of the bot game's bottom bar. It stands in for the back-arrow and
 * settings row the game used to carry above the board, whose height now goes to the board,
 * and also holds board flip. Same shape as `AnalysisMoreMenu`: opens upward, so the last
 * item is nearest the thumb, and leaving sits at the far end behind a separator.
 */
export function BotGameMoreMenu({ onLeave, onFlip }: BotGameMoreMenuProps): ReactElement {
  const [open, setOpen] = useTrackedOpen(() => trackFeature('panel-open', { target: 'bot-game-more' }));
  const [settingsOpen, setSettingsOpen] = useState(false);

  const openSettings = (): void => {
    setSettingsOpen(true);
    // Opens SettingsSheet directly, not through SettingsSheetButton.
    trackFeature('panel-open', { target: 'settings' });
  };
  const flip = (): void => {
    onFlip();
    trackFeature('board-tool', { target: 'flip' });
  };

  return (
    <>
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className={LABELLED_BUTTON_CLASS}
            aria-label="More game options"
            data-testid="bot-game-btn-more"
          >
            <EllipsisVertical className="size-5" aria-hidden="true" />
            <span className="text-sm">More</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent side="top" align="end" data-testid="bot-game-more-menu">
          <DropdownMenuItem data-testid="bots-back" onSelect={onLeave}>
            <ArrowLeft aria-hidden="true" />
            Back to bots
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem data-testid="bot-game-menu-settings" onSelect={openSettings}>
            <Settings aria-hidden="true" />
            Settings
          </DropdownMenuItem>
          <DropdownMenuItem data-testid="board-btn-flip" onSelect={flip}>
            <Repeat2 aria-hidden="true" />
            Flip board
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <SettingsSheet open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  );
}
