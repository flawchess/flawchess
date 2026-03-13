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
import type { BookmarkResponse } from '@/types/bookmarks';
import { BookmarkCard } from './BookmarkCard';

interface WDLStats {
  wins: number;
  draws: number;
  losses: number;
  total: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
}

interface Props {
  bookmarks: BookmarkResponse[];
  onReorder: (orderedIds: number[]) => void;
  wdlStatsMap: Record<number, WDLStats>;
}

export function BookmarkList({ bookmarks, onReorder, wdlStatsMap }: Props) {
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
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={items.map((b) => b.id)} strategy={verticalListSortingStrategy}>
        <div className="space-y-2">
          {items.map((b) => (
            <BookmarkCard key={b.id} bookmark={b} stats={wdlStatsMap[b.id]} />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}
