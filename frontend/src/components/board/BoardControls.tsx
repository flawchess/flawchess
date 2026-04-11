import { SkipBack, ChevronLeft, ChevronRight, Repeat2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';

interface BoardControlsProps {
  onBack: () => void;
  onForward: () => void;
  onReset: () => void;
  onFlip: () => void;
  canGoBack: boolean;
  canGoForward: boolean;
  /** Optional slot for an info icon rendered at the end of the bar */
  infoSlot?: React.ReactNode;
  /** Render buttons in a vertical column (used on mobile beside the board) */
  vertical?: boolean;
  /** Button size. 'sm' = h-8 w-8 (desktop), 'md' = h-9 w-9 (mobile slim row), 'lg' = h-11 w-11 (mobile vertical column). Defaults to 'lg' when vertical, 'sm' otherwise. */
  size?: 'sm' | 'md' | 'lg';
  /** Additional CSS classes for the root container */
  className?: string;
}

const SIZE_CLASSES: Record<'sm' | 'md' | 'lg', string> = {
  sm: 'h-8 w-8',
  md: 'h-9 w-9',
  lg: 'h-11 w-11',
};

export function BoardControls({
  onBack,
  onForward,
  onReset,
  onFlip,
  canGoBack,
  canGoForward,
  infoSlot,
  vertical = false,
  size,
  className,
}: BoardControlsProps) {
  const resolvedSize = size ?? (vertical ? 'lg' : 'sm');
  const buttonSizeClass = SIZE_CLASSES[resolvedSize];
  return (
    <div className={`flex items-center justify-evenly rounded-lg charcoal-texture ${vertical ? 'flex-col' : ''} ${className ?? ''}`}>
      <Tooltip content="Reset to start">
        <Button
          variant="ghost"
          size="icon"
          className={`${buttonSizeClass} hover:bg-accent`}
          onClick={onReset}
          disabled={!canGoBack}
          aria-label="Reset to start"
          data-testid="board-btn-reset"
        >
          <SkipBack className="h-4 w-4" />
        </Button>
      </Tooltip>
      <Tooltip content="Previous move">
        <Button
          variant="ghost"
          size="icon"
          className={`${buttonSizeClass} hover:bg-accent`}
          onClick={onBack}
          disabled={!canGoBack}
          aria-label="Previous move"
          data-testid="board-btn-back"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
      </Tooltip>
      <Tooltip content="Next move">
        <Button
          variant="ghost"
          size="icon"
          className={`${buttonSizeClass} hover:bg-accent`}
          onClick={onForward}
          disabled={!canGoForward}
          aria-label="Next move"
          data-testid="board-btn-forward"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </Tooltip>
      <Tooltip content="Flip board">
        <Button
          variant="ghost"
          size="icon"
          className={`${buttonSizeClass} hover:bg-accent`}
          onClick={onFlip}
          aria-label="Flip board"
          data-testid="board-btn-flip"
        >
          <Repeat2 className="h-4 w-4" />
        </Button>
      </Tooltip>
      {infoSlot}
    </div>
  );
}
