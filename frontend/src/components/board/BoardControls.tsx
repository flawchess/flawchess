import { SkipBack, ChevronLeft, ChevronRight, FlipVertical2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

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
  /** Additional CSS classes for the root container */
  className?: string;
}

export function BoardControls({
  onBack,
  onForward,
  onReset,
  onFlip,
  canGoBack,
  canGoForward,
  infoSlot,
  vertical = false,
  className,
}: BoardControlsProps) {
  return (
    <div className={`flex items-center justify-evenly rounded-lg charcoal-texture ${vertical ? 'flex-col' : ''} ${className ?? ''}`}>
      <Button
        variant="ghost"
        size="icon"
        className="h-9 w-9 sm:h-8 sm:w-8 hover:bg-accent"
        onClick={onReset}
        disabled={!canGoBack}
        title="Reset to start"
        aria-label="Reset to start"
        data-testid="board-btn-reset"
      >
        <SkipBack className="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="h-9 w-9 sm:h-8 sm:w-8 hover:bg-accent"
        onClick={onBack}
        disabled={!canGoBack}
        title="Previous move"
        aria-label="Previous move"
        data-testid="board-btn-back"
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="h-9 w-9 sm:h-8 sm:w-8 hover:bg-accent"
        onClick={onForward}
        disabled={!canGoForward}
        title="Next move"
        aria-label="Next move"
        data-testid="board-btn-forward"
      >
        <ChevronRight className="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="h-9 w-9 sm:h-8 sm:w-8 hover:bg-accent"
        onClick={onFlip}
        title="Flip board"
        aria-label="Flip board"
        data-testid="board-btn-flip"
      >
        <FlipVertical2 className="h-4 w-4" />
      </Button>
      {infoSlot}
    </div>
  );
}
