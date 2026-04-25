import { useState, useRef } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { FolderOpen, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { useUpdatePositionBookmarkLabel, useDeletePositionBookmark, useUpdateMatchSide } from '@/hooks/usePositionBookmarks';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';
import type { MatchSide } from '@/types/api';
import { MiniBoard } from './MiniBoard';

interface Props {
  bookmark: PositionBookmarkResponse;
  onLoad: (bookmark: PositionBookmarkResponse) => void;
  chartEnabled: boolean;
  onChartEnabledChange: (id: number, enabled: boolean) => void;
  /** When provided, overrides the internal mutation — used for deferred updates (mobile drawer). */
  onMatchSideChange?: (id: number, matchSide: MatchSide) => void;
}

export function PositionBookmarkCard({ bookmark, onLoad, chartEnabled, onChartEnabledChange, onMatchSideChange }: Props) {
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
      // Save directly on Enter — don't rely on blur chain which can be
      // interrupted by sortable container focus management
      const trimmed = labelValue.trim();
      if (trimmed && trimmed !== bookmark.label) {
        updateLabel.mutate({ id: bookmark.id, data: { label: trimmed } });
      }
      isDirtyRef.current = true; // prevent double-save from subsequent blur
      setIsEditing(false);
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
    if (onMatchSideChange) {
      onMatchSideChange(bookmark.id, value as MatchSide);
    } else {
      updateMatchSide.mutate({ id: bookmark.id, data: { match_side: value as MatchSide } });
    }
  };

  const dragHandle = (
    <span
      {...listeners}
      className="cursor-grab touch-none select-none text-muted-foreground shrink-0"
      aria-label="Drag to reorder"
    >
      ☰
    </span>
  );

  const colorCircle = bookmark.color ? (
    <span
      className={`inline-block h-3 w-3 rounded-xs border border-muted-foreground shrink-0 ${bookmark.color === 'white' ? 'bg-white' : 'bg-zinc-900'}`}
      data-testid={`bookmark-color-${bookmark.id}`}
    />
  ) : null;

  const labelControl = isEditing ? (
    <input
      autoFocus
      value={labelValue}
      onChange={(e) => setLabelValue(e.target.value)}
      onBlur={handleLabelBlur}
      onKeyDown={handleLabelKeyDown}
      data-testid={`bookmark-label-input-${bookmark.id}`}
      className="min-w-0 flex-1 bg-transparent text-sm font-medium outline-none border-b border-primary focus:border-primary"
    />
  ) : (
    <button
      className="min-w-0 flex-1 truncate cursor-text text-sm font-medium text-left bg-transparent border-none p-0"
      onClick={handleLabelClick}
      title={bookmark.label}
      data-testid={`bookmark-label-${bookmark.id}`}
      aria-label={`Edit bookmark label: ${bookmark.label}`}
    >
      {bookmark.label}
    </button>
  );

  const miniBoard = (
    <div
      className="shrink-0"
      data-testid={`bookmark-mini-board-${bookmark.id}`}
      style={{ opacity: updateMatchSide.isPending ? 0.6 : 1, transition: 'opacity 0.15s' }}
    >
      <MiniBoard fen={bookmark.fen} flipped={bookmark.is_flipped} size={84} />
    </div>
  );

  const pieceFilterToggle = (
    <ToggleGroup
      type="single"
      value={bookmark.match_side}
      onValueChange={handleMatchSideChange}
      variant="outline"
      size="sm"
      data-testid={`bookmark-match-side-${bookmark.id}`}
      className="w-full"
      aria-label="Piece filter"
    >
      <ToggleGroupItem
        value="mine"
        data-testid={`bookmark-match-side-${bookmark.id}-mine`}
        aria-label="Match my pieces only"
        className="text-xs h-6 px-2 flex-1"
      >
        Mine
      </ToggleGroupItem>
      <ToggleGroupItem
        value="opponent"
        data-testid={`bookmark-match-side-${bookmark.id}-opponent`}
        aria-label="Match opponent pieces only"
        className="text-xs h-6 px-2 flex-1"
      >
        Opponent
      </ToggleGroupItem>
      <ToggleGroupItem
        value="both"
        data-testid={`bookmark-match-side-${bookmark.id}-both`}
        aria-label="Match both sides"
        className="text-xs h-6 px-2 flex-1"
      >
        Both
      </ToggleGroupItem>
    </ToggleGroup>
  );

  const buttonRow = (
    <div className="flex items-center justify-between">
      {/* Chart toggle on left */}
      <Tooltip content={chartEnabled ? 'Exclude from opening results' : 'Include in opening results'}>
        <button
          role="switch"
          aria-checked={chartEnabled}
          aria-label={chartEnabled ? 'Exclude from opening results' : 'Include in opening results'}
          onClick={() => onChartEnabledChange(bookmark.id, !chartEnabled)}
          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${chartEnabled ? 'bg-toggle-active' : 'bg-muted'}`}
          data-testid={`bookmark-chart-toggle-${bookmark.id}`}
        >
          <span className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${chartEnabled ? 'translate-x-4' : 'translate-x-0.5'}`} />
        </button>
      </Tooltip>
      {/* Load button in middle */}
      <Tooltip content="Load bookmark">
        <Button variant="ghost" size="icon"
          className="h-7 w-7 text-muted-foreground hover:text-foreground"
          onMouseDown={() => { isDirtyRef.current = true; }}
          onClick={handleLoad}
          data-testid={`bookmark-btn-load-${bookmark.id}`}
          aria-label="Load bookmark">
          <FolderOpen size={15} />
        </Button>
      </Tooltip>
      {/* Delete button on right */}
      <Tooltip content={`Delete bookmark: ${bookmark.label}`}>
        <Button variant="ghost" size="icon"
          className="h-7 w-7 text-muted-foreground hover:text-destructive"
          onMouseDown={() => { isDirtyRef.current = true; }}
          onClick={handleDelete}
          disabled={deleteBookmark.isPending}
          data-testid={`bookmark-btn-delete-${bookmark.id}`}
          aria-label={`Delete bookmark: ${bookmark.label}`}>
          <Trash2 size={15} />
        </Button>
      </Tooltip>
    </div>
  );

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      className="rounded-md bg-card px-3 py-2"
      data-testid={`bookmark-card-${bookmark.id}`}
    >
      {/* Mobile layout: drag/color/label full width on top, then board + (Piece Filter caption + toggle + buttons) below */}
      <div className="flex flex-col gap-2 sm:hidden">
        <div className="flex items-center gap-1.5">
          {dragHandle}
          {colorCircle}
          {labelControl}
        </div>
        <div className="flex gap-2 items-start">
          {miniBoard}
          <div className="flex-1 min-w-0 flex flex-col gap-1">
            <div>
              <p className="mb-1 text-xs text-muted-foreground">Piece Filter</p>
              {pieceFilterToggle}
            </div>
            {buttonRow}
          </div>
        </div>
      </div>

      {/* Desktop layout: drag handle, board, then column with label + toggle + buttons */}
      <div className="hidden sm:flex items-center gap-2">
        {dragHandle}
        {miniBoard}
        <div className="flex-1 min-w-0 flex flex-col gap-1">
          <div className="flex items-center gap-1.5">
            {colorCircle}
            {labelControl}
          </div>
          {pieceFilterToggle}
          {buttonRow}
        </div>
      </div>
    </div>
  );
}
