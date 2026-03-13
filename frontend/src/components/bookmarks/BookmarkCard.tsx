import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { MiniBoard } from '@/components/board/MiniBoard';
import { WDLBar } from '@/components/results/WDLBar';
import { useUpdateBookmarkLabel, useDeleteBookmark } from '@/hooks/useBookmarks';
import type { BookmarkResponse } from '@/types/bookmarks';
import type { WDLStats } from '@/types/api';

interface Props {
  bookmark: BookmarkResponse;
  stats?: WDLStats;
}

function formatColor(color: string | null): string {
  if (!color) return 'Any';
  return color.charAt(0).toUpperCase() + color.slice(1);
}

function formatMatchSide(side: string): string {
  if (side === 'full') return 'Both';
  return side.charAt(0).toUpperCase() + side.slice(1);
}

export function BookmarkCard({ bookmark, stats }: Props) {
  const navigate = useNavigate();
  const updateLabel = useUpdateBookmarkLabel();
  const deleteBookmark = useDeleteBookmark();

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
    navigate('/', {
      state: {
        bookmark: {
          id: bookmark.id,
          moves: bookmark.moves,
          color: bookmark.color,
          matchSide: bookmark.match_side,
          is_flipped: bookmark.is_flipped,
        },
      },
    });
  };

  const handleDelete = () => {
    deleteBookmark.mutate(bookmark.id);
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      className="rounded-md border border-border bg-card p-3"
      data-testid={`bookmark-card-${bookmark.id}`}
    >
      <div className="flex gap-3">
        {/* Drag handle */}
        <div className="flex flex-col items-center justify-center">
          <span
            {...listeners}
            className="cursor-grab touch-none select-none text-muted-foreground"
            aria-label="Drag to reorder"
          >
            ☰
          </span>
        </div>

        {/* Mini board */}
        <MiniBoard fen={bookmark.fen} size={100} flipped={bookmark.is_flipped} />

        {/* Info */}
        <div className="flex flex-1 flex-col justify-between min-w-0">
          <div>
            {/* Label */}
            {isEditing ? (
              <input
                autoFocus
                value={labelValue}
                onChange={(e) => setLabelValue(e.target.value)}
                onBlur={handleLabelBlur}
                onKeyDown={handleLabelKeyDown}
                data-testid={`bookmark-label-input-${bookmark.id}`}
                className="w-full bg-transparent text-sm font-medium outline-none border-b border-primary focus:border-primary"
              />
            ) : (
              <button
                className="cursor-text text-sm font-medium truncate block w-full text-left bg-transparent border-none p-0"
                onClick={handleLabelClick}
                title={bookmark.label}
                data-testid={`bookmark-label-${bookmark.id}`}
                aria-label={`Edit bookmark label: ${bookmark.label}`}
              >
                {bookmark.label}
              </button>
            )}

            {/* Filter badges */}
            <div className="mt-1.5 flex flex-wrap gap-1">
              <Badge variant="outline" className="text-[10px] h-4 px-1.5">
                Played as: {formatColor(bookmark.color)}
              </Badge>
              <Badge variant="outline" className="text-[10px] h-4 px-1.5">
                Match: {formatMatchSide(bookmark.match_side)}
              </Badge>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-1.5 mt-2">
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onMouseDown={(e) => e.preventDefault()}
              onClick={handleLoad}
              data-testid={`bookmark-btn-load-${bookmark.id}`}
            >
              Load
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs text-muted-foreground hover:text-destructive"
              onMouseDown={(e) => e.preventDefault()}
              onClick={handleDelete}
              disabled={deleteBookmark.isPending}
              data-testid={`bookmark-btn-delete-${bookmark.id}`}
            >
              Delete
            </Button>
          </div>
        </div>
      </div>
      {stats && stats.total > 0 && (
        <div className="mt-3 pt-3 border-t border-border">
          <WDLBar stats={stats} />
        </div>
      )}
    </div>
  );
}
