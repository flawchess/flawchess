import { SkipBack, ChevronLeft, ChevronRight, FlipVertical2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface BoardControlsProps {
  onBack: () => void;
  onForward: () => void;
  onReset: () => void;
  onFlip: () => void;
  canGoBack: boolean;
  canGoForward: boolean;
  /** Optional slot for an info icon rendered on the far right of the row */
  infoSlot?: React.ReactNode;
}

export function BoardControls({
  onBack,
  onForward,
  onReset,
  onFlip,
  canGoBack,
  canGoForward,
  infoSlot,
}: BoardControlsProps) {
  return (
    <div className="flex items-center rounded-lg bg-muted">
      {/* 4 move buttons spread evenly across available width */}
      <div className="flex flex-1 items-center justify-evenly">
        <Button
          variant="ghost"
          size="icon"
          className="h-11 w-11 sm:h-8 sm:w-8 hover:bg-accent"
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
          className="h-11 w-11 sm:h-8 sm:w-8 hover:bg-accent"
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
          className="h-11 w-11 sm:h-8 sm:w-8 hover:bg-accent"
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
          className="h-11 w-11 sm:h-8 sm:w-8 hover:bg-accent"
          onClick={onFlip}
          title="Flip board"
          aria-label="Flip board"
          data-testid="board-btn-flip"
        >
          <FlipVertical2 className="h-4 w-4" />
        </Button>
      </div>

      {/* Info icon slot on the far right */}
      {infoSlot && (
        <div className="flex-shrink-0 mr-1">
          {infoSlot}
        </div>
      )}
    </div>
  );
}
