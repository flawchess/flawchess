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
import { PositionBookmarkCard } from './PositionBookmarkCard';

interface Props {
  bookmarks: PositionBookmarkResponse[];
  onReorder: (orderedIds: number[]) => void;
  onLoad: (bookmark: PositionBookmarkResponse) => void;
}

export function PositionBookmarkList({ bookmarks, onReorder, onLoad }: Props) {
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
            <PositionBookmarkCard key={b.id} bookmark={b} onLoad={onLoad} />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}
