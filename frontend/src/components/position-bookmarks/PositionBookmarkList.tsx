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
import { Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';
import { PositionBookmarkCard } from './PositionBookmarkCard';
import { SuggestionsModal } from './SuggestionsModal';

interface Props {
  bookmarks: PositionBookmarkResponse[];
  onReorder: (orderedIds: number[]) => void;
  onLoad: (bookmark: PositionBookmarkResponse) => void;
}

export function PositionBookmarkList({ bookmarks, onReorder, onLoad }: Props) {
  const [items, setItems] = useState(bookmarks);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);

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
          No position bookmarks yet. Use the &apos;Bookmark&apos; button above to save positions, or use &apos;Suggest bookmarks&apos; to auto-generate from your most-played openings.
        </p>
      ) : (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={items.map((b) => b.id)} strategy={verticalListSortingStrategy}>
            <div className="space-y-2">
              {items.map((b) => (
                <PositionBookmarkCard key={b.id} bookmark={b} onLoad={onLoad} />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      )}

      <Button
        variant="outline"
        size="lg"
        className="w-full mt-2"
        onClick={() => setSuggestionsOpen(true)}
        data-testid="btn-suggest-bookmarks"
      >
        <Sparkles className="h-4 w-4 mr-1" />
        Suggest bookmarks
      </Button>

      <SuggestionsModal open={suggestionsOpen} onOpenChange={setSuggestionsOpen} />
    </>
  );
}
