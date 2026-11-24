import { useState } from 'react';
import type { ReactElement } from 'react';
import { ArrowLeft, EllipsisVertical, Repeat2, Settings } from 'lucide-react';
import { useNavigate } from 'react-router';
import { PgnFenMenuItems, type MoveListHeaderContentProps } from '@/components/analysis/AnalysisTabs';
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
import { cn } from '@/lib/utils';

/** Where Leave goes when the analysis page is the first in-app history entry. */
const LEAVE_FALLBACK_PATH = '/library';

/**
 * Whether the router has an earlier in-app entry. React Router stores its entry index
 * in `history.state.idx`. `history.length` would also count pages of other sites, and
 * `location.key` changes when the first entry is replaced.
 */
function hasInAppHistory(): boolean {
  const state: unknown = window.history.state;
  if (typeof state !== 'object' || state === null || !('idx' in state)) return false;
  return typeof state.idx === 'number' && state.idx > 0;
}

export type AnalysisMoreMenuProps = MoveListHeaderContentProps & {
  onFlip: () => void;
};

/**
 * The last column of the phone footer on /analysis. It stands in for the page header
 * (exit, settings), which phones drop to give the tab panel its height, and also holds
 * the PGN/FEN tools and board flip. Opens upward, so the last item is nearest the thumb;
 * Leave sits at the far end, behind a separator.
 */
export function AnalysisMoreMenu({ onFlip, ...pgnFenProps }: AnalysisMoreMenuProps): ReactElement {
  const navigate = useNavigate();
  const [open, setOpen] = useTrackedOpen(() => trackFeature('panel-open', { target: 'analysis-more' }));
  const [settingsOpen, setSettingsOpen] = useState(false);

  const leave = (): void => {
    if (hasInAppHistory()) void navigate(-1);
    else void navigate(LEAVE_FALLBACK_PATH, { replace: true });
  };
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
            className={cn(LABELLED_BUTTON_CLASS, 'hover:bg-accent')}
            aria-label="More analysis options"
            data-testid="analysis-btn-more"
          >
            <EllipsisVertical className="h-5 w-5" aria-hidden="true" />
            <span className="text-sm">More</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent side="top" align="end" data-testid="analysis-more-menu">
          <DropdownMenuItem data-testid="analysis-menu-leave" onSelect={leave}>
            <ArrowLeft aria-hidden="true" />
            Leave analysis
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <PgnFenMenuItems {...pgnFenProps} />
          <DropdownMenuItem data-testid="analysis-menu-settings" onSelect={openSettings}>
            <Settings aria-hidden="true" />
            Settings
          </DropdownMenuItem>
          <DropdownMenuItem data-testid="analysis-menu-flip" onSelect={flip}>
            <Repeat2 aria-hidden="true" />
            Flip board
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <SettingsSheet open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  );
}
