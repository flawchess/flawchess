import { useState, useRef } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Upload, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { useUpdatePositionBookmarkLabel, useDeletePositionBookmark, useUpdateMatchSide } from '@/hooks/usePositionBookmarks';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';
import type { MatchSide } from '@/types/api';
import { MiniBoard } from './MiniBoard';

interface Props {
  bookmark: PositionBookmarkResponse;
  onLoad: (bookmark: PositionBookmarkResponse) => void;
}

export function PositionBookmarkCard({ bookmark, onLoad }: Props) {
  const updateLabel = useUpdatePositionBookmarkLabel();
  const deleteBookmark = useDeletePositionBookmark();
  const updateMatchSide = useUpdateMatchSide();

  const [isEditing, setIsEditing] = useState(false);
  const [labelValue, setLabelValue] = useState(bookmark.label);
  const isDirtyRef = useRef(false);

  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: bookmark.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const handleLabelClick = () => {
    setLabelValue(bookmark.label);
    setIsEditing(true);
  };

  const handleLabelBlur = () => {
    if (!isDirtyRef.current && isEditing) {
      const trimmed = labelValue.trim();
      if (trimmed && trimmed !== bookmark.label) {
        updateLabel.mutate({ id: bookmark.id, data: { label: trimmed } });
      }
    }
    isDirtyRef.current = false;
    setIsEditing(false);
  };

  const handleLabelKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.currentTarget.blur();
    } else if (e.key === 'Escape') {
      isDirtyRef.current = true;
      setLabelValue(bookmark.label);
      setIsEditing(false);
    }
  };

  const handleLoad = () => {
    isDirtyRef.current = true;
    onLoad(bookmark);
  };

  const handleDelete = () => {
    deleteBookmark.mutate(bookmark.id);
  };

  const handleMatchSideChange = (value: string) => {
    if (!value) return; // ToggleGroup fires empty string when clicking the active item
    updateMatchSide.mutate({ id: bookmark.id, data: { match_side: value as MatchSide } });
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2"
      data-testid={`bookmark-card-${bookmark.id}`}
    >
      {/* Drag handle */}
      <span
        {...listeners}
        className="cursor-grab touch-none select-none text-muted-foreground shrink-0"
        aria-label="Drag to reorder"
      >
        ☰
      </span>

      {/* Mini board thumbnail — hidden on very small screens */}
      <div
        className="hidden sm:block shrink-0"
        data-testid={`bookmark-mini-board-${bookmark.id}`}
        style={{ opacity: updateMatchSide.isPending ? 0.6 : 1, transition: 'opacity 0.15s' }}
      >
        <MiniBoard fen={bookmark.fen} flipped={bookmark.is_flipped} size={80} />
      </div>

      {/* Label + piece filter stacked */}
      <div className="flex-1 min-w-0 flex flex-col gap-1">
        {/* Editable label with color circle */}
        <div className="flex items-center gap-1.5">
          {bookmark.color && (
            <span
              className={`inline-block h-3 w-3 rounded-full border border-muted-foreground shrink-0 ${bookmark.color === 'white' ? 'bg-white' : 'bg-zinc-900'}`}
              data-testid={`bookmark-color-${bookmark.id}`}
            />
          )}
          {isEditing ? (
            <input
              autoFocus
              value={labelValue}
              onChange={(e) => setLabelValue(e.target.value)}
              onBlur={handleLabelBlur}
              onKeyDown={handleLabelKeyDown}
              data-testid={`bookmark-label-input-${bookmark.id}`}
              className="min-w-0 bg-transparent text-sm font-medium outline-none border-b border-primary focus:border-primary"
            />
          ) : (
            <button
              className="min-w-0 cursor-text text-sm font-medium truncate text-left bg-transparent border-none p-0"
              onClick={handleLabelClick}
              title={bookmark.label}
              data-testid={`bookmark-label-${bookmark.id}`}
              aria-label={`Edit bookmark label: ${bookmark.label}`}
            >
              {bookmark.label}
            </button>
          )}
        </div>

        {/* Piece filter toggle */}
        <ToggleGroup
          type="single"
          value={bookmark.match_side}
          onValueChange={handleMatchSideChange}
          variant="outline"
          size="sm"
          data-testid={`bookmark-match-side-${bookmark.id}`}
          className="justify-start"
          aria-label="Piece filter"
        >
          <ToggleGroupItem
            value="mine"
            data-testid={`bookmark-match-side-${bookmark.id}-mine`}
            aria-label="Match my pieces only"
            className="text-xs h-6 px-2"
          >
            Mine
          </ToggleGroupItem>
          <ToggleGroupItem
            value="opponent"
            data-testid={`bookmark-match-side-${bookmark.id}-opponent`}
            aria-label="Match opponent pieces only"
            className="text-xs h-6 px-2"
          >
            Opponent
          </ToggleGroupItem>
          <ToggleGroupItem
            value="both"
            data-testid={`bookmark-match-side-${bookmark.id}-both`}
            aria-label="Match both sides"
            className="text-xs h-6 px-2"
          >
            Both
          </ToggleGroupItem>
        </ToggleGroup>
      </div>

      {/* Load & Delete buttons stacked */}
      <div className="flex flex-col justify-between self-stretch shrink-0">
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onMouseDown={() => { isDirtyRef.current = true; }}
          onClick={handleLoad}
          data-testid={`bookmark-btn-load-${bookmark.id}`}
          aria-label="Load bookmark"
        >
          <Upload size={15} />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-muted-foreground hover:text-destructive"
          onMouseDown={() => { isDirtyRef.current = true; }}
          onClick={handleDelete}
          disabled={deleteBookmark.isPending}
          data-testid={`bookmark-btn-delete-${bookmark.id}`}
          aria-label={`Delete bookmark: ${bookmark.label}`}
        >
          <Trash2 size={15} />
        </Button>
      </div>
    </div>
  );
}
