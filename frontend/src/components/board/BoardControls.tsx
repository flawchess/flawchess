import { SkipBack, ChevronLeft, ChevronRight, FlipVertical2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface BoardControlsProps {
  onBack: () => void;
  onForward: () => void;
  onReset: () => void;
  onFlip: () => void;
  canGoBack: boolean;
  canGoForward: boolean;
}

export function BoardControls({
  onBack,
  onForward,
  onReset,
  onFlip,
  canGoBack,
  canGoForward,
}: BoardControlsProps) {
  return (
    <div className="flex items-center gap-1">
      <Button
        variant="ghost"
        size="icon"
        onClick={onReset}
        disabled={!canGoBack}
        title="Reset to start"
        aria-label="Reset to start"
      >
        <SkipBack className="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        onClick={onBack}
        disabled={!canGoBack}
        title="Previous move"
        aria-label="Previous move"
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        onClick={onForward}
        disabled={!canGoForward}
        title="Next move"
        aria-label="Next move"
      >
        <ChevronRight className="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        onClick={onFlip}
        title="Flip board"
        aria-label="Flip board"
      >
        <FlipVertical2 className="h-4 w-4" />
      </Button>
    </div>
  );
}
