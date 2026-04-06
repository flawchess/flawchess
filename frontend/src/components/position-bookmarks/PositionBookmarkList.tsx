import { useEffect, useState } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable';
import { Sparkles, Save } from 'lucide-react';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';
import type { MatchSide } from '@/types/api';
import { PositionBookmarkCard } from './PositionBookmarkCard';

interface Props {
  bookmarks: PositionBookmarkResponse[];
  onReorder: (orderedIds: number[]) => void;
  onLoad: (bookmark: PositionBookmarkResponse) => void;
  chartEnabledMap: Record<number, boolean>;
  onChartEnabledChange: (id: number, enabled: boolean) => void;
  /** When provided, overrides the internal mutation — used for deferred updates (mobile drawer). */
  onMatchSideChange?: (id: number, matchSide: MatchSide) => void;
}

export function PositionBookmarkList({ bookmarks, onReorder, onLoad, chartEnabledMap, onChartEnabledChange, onMatchSideChange }: Props) {
  const [items, setItems] = useState(bookmarks);

  // Sync when server data refreshes (e.g., after delete or label edit)
  useEffect(() => {
    setItems(bookmarks);
  }, [bookmarks]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = items.findIndex((b) => b.id === active.id);
      const newIndex = items.findIndex((b) => b.id === over.id);
      const reordered = arrayMove(items, oldIndex, newIndex);
      setItems(reordered);
      onReorder(reordered.map((b) => b.id));
    }
  };

  return (
    <>
      {items.length === 0 ? (
        <div className="px-2 space-y-2 text-xs text-muted-foreground" data-testid="bookmarks-empty-state">
          <p>No opening bookmarks yet.</p>
          <div className="flex items-start gap-2">
            <Sparkles className="h-3.5 w-3.5 shrink-0 mt-0.5 text-primary" />
            <p>
              Click <strong className="text-foreground">Suggest</strong> above to auto-generate bookmarks from your most-played openings — the fastest way to get started.
            </p>
          </div>
          <div className="flex items-start gap-2">
            <Save className="h-3.5 w-3.5 shrink-0 mt-0.5 text-primary" />
            <p>
              Or navigate to a position on the board and click <strong className="text-foreground">Save</strong> to bookmark it manually.
            </p>
          </div>
        </div>
      ) : (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={items.map((b) => b.id)} strategy={verticalListSortingStrategy}>
            <div className="space-y-2">
              {items.map((b) => (
                <PositionBookmarkCard
                  key={b.id}
                  bookmark={b}
                  onLoad={onLoad}
                  chartEnabled={chartEnabledMap[b.id] !== false}
                  onChartEnabledChange={onChartEnabledChange}
                  onMatchSideChange={onMatchSideChange}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      )}
    </>
  );
}
