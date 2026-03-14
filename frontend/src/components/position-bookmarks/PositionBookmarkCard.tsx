import { useState, useRef } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Button } from '@/components/ui/button';
import { useUpdatePositionBookmarkLabel, useDeletePositionBookmark } from '@/hooks/usePositionBookmarks';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';

interface Props {
  bookmark: PositionBookmarkResponse;
  onLoad: (bookmark: PositionBookmarkResponse) => void;
}

export function PositionBookmarkCard({ bookmark, onLoad }: Props) {
  const updateLabel = useUpdatePositionBookmarkLabel();
  const deleteBookmark = useDeletePositionBookmark();

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

      {/* Editable label */}
      {isEditing ? (
        <input
          autoFocus
          value={labelValue}
          onChange={(e) => setLabelValue(e.target.value)}
          onBlur={handleLabelBlur}
          onKeyDown={handleLabelKeyDown}
          data-testid={`bookmark-label-input-${bookmark.id}`}
          className="flex-1 min-w-0 bg-transparent text-sm font-medium outline-none border-b border-primary focus:border-primary"
        />
      ) : (
        <button
          className="flex-1 min-w-0 cursor-text text-sm font-medium truncate text-left bg-transparent border-none p-0"
          onClick={handleLabelClick}
          title={bookmark.label}
          data-testid={`bookmark-label-${bookmark.id}`}
          aria-label={`Edit bookmark label: ${bookmark.label}`}
        >
          {bookmark.label}
        </button>
      )}

      {/* Load button */}
      <Button
        variant="outline"
        size="sm"
        className="h-7 text-xs shrink-0"
        onMouseDown={() => { isDirtyRef.current = true; }}
        onClick={handleLoad}
        data-testid={`bookmark-btn-load-${bookmark.id}`}
      >
        Load
      </Button>

      {/* Delete button */}
      <Button
        variant="ghost"
        size="sm"
        className="h-7 text-xs text-muted-foreground hover:text-destructive shrink-0"
        onMouseDown={() => { isDirtyRef.current = true; }}
        onClick={handleDelete}
        disabled={deleteBookmark.isPending}
        data-testid={`bookmark-btn-delete-${bookmark.id}`}
        aria-label={`Delete bookmark: ${bookmark.label}`}
      >
        x
      </Button>
    </div>
  );
}
