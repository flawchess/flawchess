import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Button } from '@/components/ui/button';
import { WDLBar } from '@/components/results/WDLBar';
import { useUpdateBookmarkLabel, useDeleteBookmark } from '@/hooks/useBookmarks';
import type { BookmarkResponse } from '@/types/bookmarks';
import type { WDLStats } from '@/types/api';

interface Props {
  bookmark: BookmarkResponse;
  stats?: WDLStats;
}

export function BookmarkRow({ bookmark, stats }: Props) {
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
      isDirtyRef.current = true; // cancel save
      setLabelValue(bookmark.label);
      setIsEditing(false);
    }
  };

  const handleLoad = () => {
    isDirtyRef.current = true; // prevent blur saving before navigate
    navigate('/', {
      state: {
        bookmark: {
          id: bookmark.id,
          moves: bookmark.moves,
          color: bookmark.color,
          matchSide: bookmark.match_side,
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
    >
      <div className="flex items-center gap-3">
        {/* Drag handle */}
        <span
          {...listeners}
          className="cursor-grab touch-none select-none text-muted-foreground"
          aria-label="Drag to reorder"
        >
          ☰
        </span>

        {/* Label / edit input */}
        <div className="flex-1 min-w-0">
          {isEditing ? (
            <input
              autoFocus
              value={labelValue}
              onChange={(e) => setLabelValue(e.target.value)}
              onBlur={handleLabelBlur}
              onKeyDown={handleLabelKeyDown}
              className="w-full bg-transparent text-sm outline-none border-b border-primary focus:border-primary"
            />
          ) : (
            <span
              className="cursor-text text-sm truncate block"
              onClick={handleLabelClick}
              title={bookmark.label}
            >
              {bookmark.label}
            </span>
          )}
        </div>

        {/* Load button */}
        <Button
          variant="outline"
          size="sm"
          onMouseDown={(e) => e.preventDefault()}
          onClick={handleLoad}
        >
          Load
        </Button>

        {/* Delete button */}
        <Button
          variant="ghost"
          size="sm"
          onMouseDown={(e) => e.preventDefault()}
          onClick={handleDelete}
          disabled={deleteBookmark.isPending}
          className="text-muted-foreground hover:text-destructive"
        >
          ✕
        </Button>
      </div>

      {/* WDL bar — only rendered when stats provided (plan 05 wires actual data) */}
      {stats && (
        <div className="mt-2">
          <WDLBar stats={stats} />
        </div>
      )}
    </div>
  );
}
