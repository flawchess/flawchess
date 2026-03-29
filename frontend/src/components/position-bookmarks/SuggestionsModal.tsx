import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { MiniBoard } from './MiniBoard';
import { positionBookmarksApi } from '@/api/client';
import { pgnToSanArray } from '@/lib/pgn';
import type { MostPlayedOpeningsResponse, OpeningWDL } from '@/types/stats';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';

// Maximum openings per color to consider before filtering already-bookmarked ones
const SUGGESTIONS_POOL_SIZE = 10;
// Maximum suggestions to show per color after filtering
const SUGGESTIONS_PER_COLOR = 5;

interface SuggestionsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mostPlayedData: MostPlayedOpeningsResponse | undefined;
  bookmarks: PositionBookmarkResponse[];
}

export function SuggestionsModal({ open, onOpenChange, mostPlayedData, bookmarks }: SuggestionsModalProps) {
  const qc = useQueryClient();

  // Per-suggestion state: selected for saving (keyed by color+index string)
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const [saving, setSaving] = useState(false);
  const [saveProgress, setSaveProgress] = useState(0);

  // Derive suggestions from mostPlayedData, filtering out already-bookmarked positions
  const bookmarkedHashes = new Set(
    bookmarks.filter(b => b.match_side === 'both').map(b => b.target_hash)
  );

  const whiteSuggestions: OpeningWDL[] = mostPlayedData
    ? mostPlayedData.white
        .slice(0, SUGGESTIONS_POOL_SIZE)
        .filter(o => !bookmarkedHashes.has(o.full_hash))
        .slice(0, SUGGESTIONS_PER_COLOR)
    : [];

  const blackSuggestions: OpeningWDL[] = mostPlayedData
    ? mostPlayedData.black
        .slice(0, SUGGESTIONS_POOL_SIZE)
        .filter(o => !bookmarkedHashes.has(o.full_hash))
        .slice(0, SUGGESTIONS_PER_COLOR)
    : [];

  const allSuggestions = whiteSuggestions.length === 0 && blackSuggestions.length === 0;
  const allBookmarked =
    mostPlayedData !== undefined &&
    mostPlayedData.white.slice(0, SUGGESTIONS_POOL_SIZE).every(o => bookmarkedHashes.has(o.full_hash)) &&
    mostPlayedData.black.slice(0, SUGGESTIONS_POOL_SIZE).every(o => bookmarkedHashes.has(o.full_hash));

  const makeKey = (color: 'white' | 'black', index: number) => `${color}-${index}`;

  const toggleSelected = (color: 'white' | 'black', index: number) => {
    const key = makeKey(color, index);
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const handleSave = async () => {
    const toSave: { opening: OpeningWDL; color: 'white' | 'black' }[] = [];
    whiteSuggestions.forEach((o, i) => {
      if (selected.has(makeKey('white', i))) toSave.push({ opening: o, color: 'white' });
    });
    blackSuggestions.forEach((o, i) => {
      if (selected.has(makeKey('black', i))) toSave.push({ opening: o, color: 'black' });
    });

    if (toSave.length === 0) return;

    setSaving(true);
    setSaveProgress(0);

    for (let i = 0; i < toSave.length; i++) {
      const { opening, color } = toSave[i];

      await positionBookmarksApi.create({
        label: opening.label,
        target_hash: opening.full_hash,
        fen: opening.fen,
        moves: pgnToSanArray(opening.pgn),
        color: color,
        match_side: 'both',
        is_flipped: color === 'black',
      });

      setSaveProgress(i + 1);
    }

    await qc.invalidateQueries({ queryKey: ['position-bookmarks'] });
    await qc.refetchQueries({ queryKey: ['position-bookmarks'] });
    setSaving(false);
    setSelected(new Set());
    onOpenChange(false);
  };

  const selectedCount = selected.size;
  const savingLabel = saving
    ? `Saving ${saveProgress} of ${selectedCount}...`
    : selectedCount > 0
      ? `Save ${selectedCount} bookmark${selectedCount !== 1 ? 's' : ''}`
      : 'Save selected';

  const renderSuggestionCard = (opening: OpeningWDL, color: 'white' | 'black', index: number) => {
    const key = makeKey(color, index);
    const isSelected = selected.has(key);

    return (
      <div
        key={key}
        data-testid={`suggestion-card-${key}`}
        className={`flex gap-3 items-start p-3 rounded-lg border transition-colors ${
          isSelected ? 'border-primary/50 bg-primary/5' : 'border-border bg-muted/30'
        }`}
      >
        <Checkbox
          checked={isSelected}
          onCheckedChange={() => toggleSelected(color, index)}
          aria-label={`Select ${opening.label}`}
          className="mt-1 flex-shrink-0"
          data-testid={`suggestion-checkbox-${key}`}
        />
        <MiniBoard
          fen={opening.fen}
          flipped={color === 'black'}
          size={100}
        />
        <div className="flex flex-col gap-1 flex-1 min-w-0">
          <span className="font-medium text-sm truncate">
            {opening.label}
          </span>
          <Badge variant="secondary" className="w-fit text-xs">
            {opening.total} {opening.total === 1 ? 'game' : 'games'}
          </Badge>
        </div>
      </div>
    );
  };

  const renderSection = (title: string, sectionSuggestions: OpeningWDL[], color: 'white' | 'black') => {
    if (sectionSuggestions.length === 0) return null;
    return (
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          {title}
        </h3>
        {sectionSuggestions.map((o, i) => renderSuggestionCard(o, color, i))}
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        data-testid="suggestions-modal"
        className="max-w-lg w-full max-h-[80vh] flex flex-col"
      >
        <DialogHeader>
          <DialogTitle>Suggested Bookmarks</DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-4 pr-1">
          {mostPlayedData === undefined && (
            <div className="text-center py-8 text-muted-foreground text-sm">
              Loading suggestions...
            </div>
          )}

          {mostPlayedData !== undefined && allSuggestions && allBookmarked && (
            <div className="text-center py-8 text-muted-foreground text-sm">
              All your most-played openings are already bookmarked. Try creating custom bookmarks on the board and experimenting with the Piece filter.
            </div>
          )}

          {mostPlayedData !== undefined && allSuggestions && !allBookmarked && (
            <div className="text-center py-8 text-muted-foreground text-sm">
              No suggestions available. Import games to get bookmark suggestions based on your most-played openings.
            </div>
          )}

          {mostPlayedData !== undefined && !allSuggestions && (
            <>
              {renderSection('White openings', whiteSuggestions, 'white')}
              {renderSection('Black openings', blackSuggestions, 'black')}
            </>
          )}
        </div>

        {mostPlayedData !== undefined && !allSuggestions && (
          <DialogFooter>
            <Button
              data-testid="btn-save-suggestions"
              onClick={handleSave}
              disabled={saving || selectedCount === 0}
              className="w-full sm:w-auto"
            >
              {savingLabel}
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
