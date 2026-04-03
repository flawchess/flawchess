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
        <p className="px-2 text-xs text-muted-foreground break-words">
          No opening bookmarks yet. Use the &apos;Save&apos; button to save positions, or use &apos;Suggest&apos; to auto-generate from your most-played openings.
        </p>
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
