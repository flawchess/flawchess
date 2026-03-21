import { useState, useEffect } from 'react';
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
import { usePositionSuggestions } from '@/hooks/usePositionBookmarks';
import { positionBookmarksApi } from '@/api/client';
import type { PositionSuggestion } from '@/types/position_bookmarks';

interface SuggestionsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SuggestionsModal({ open, onOpenChange }: SuggestionsModalProps) {
  const qc = useQueryClient();
  const { data, isFetching, refetch } = usePositionSuggestions();
  const suggestions = data?.suggestions ?? [];

  // Per-suggestion state: selected for saving
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const [saving, setSaving] = useState(false);
  const [saveProgress, setSaveProgress] = useState(0);

  // Fetch on open
  useEffect(() => {
    if (open) {
      refetch();
    }
  }, [open, refetch]);

  // Reset selection when suggestions load
  /* eslint-disable react-hooks/set-state-in-effect -- intentional: reset state on new data */
  useEffect(() => {
    if (suggestions.length > 0) {
      setSelected(new Set());
      setSaveProgress(0);
    }
  }, [suggestions]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const whiteSuggestions = suggestions.filter(s => s.color === 'white');
  const blackSuggestions = suggestions.filter(s => s.color === 'black');

  const getIndexInSuggestions = (s: PositionSuggestion) => suggestions.indexOf(s);

  const toggleSelected = (index: number) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const handleSave = async () => {
    const toSave = suggestions
      .map((s, i) => ({ suggestion: s, index: i }))
      .filter(({ index }) => selected.has(index));

    if (toSave.length === 0) return;

    setSaving(true);
    setSaveProgress(0);

    for (let i = 0; i < toSave.length; i++) {
      const { suggestion, index } = toSave[i];

      const label = suggestion.opening_name
        ?? `${suggestion.color} opening #${index + 1}`;

      await positionBookmarksApi.create({
        label,
        target_hash: suggestion.full_hash,
        fen: suggestion.fen,
        moves: suggestion.moves,
        color: suggestion.color,
        match_side: 'both',
        is_flipped: suggestion.color === 'black',
      });

      setSaveProgress(i + 1);
    }

    await qc.invalidateQueries({ queryKey: ['position-bookmarks'] });
    await qc.refetchQueries({ queryKey: ['position-bookmarks'] });
    setSaving(false);
    onOpenChange(false);
  };

  const selectedCount = selected.size;
  const savingLabel = saving
    ? `Saving ${saveProgress} of ${selectedCount}...`
    : selectedCount > 0
      ? `Save ${selectedCount} bookmark${selectedCount !== 1 ? 's' : ''}`
      : 'Save selected';

  const renderSuggestionCard = (suggestion: PositionSuggestion) => {
    const globalIndex = getIndexInSuggestions(suggestion);
    const isSelected = selected.has(globalIndex);
    const openingLabel = suggestion.opening_name ?? 'Unknown opening';
    const ecoLabel = suggestion.opening_eco ? ` (${suggestion.opening_eco})` : '';

    return (
      <div
        key={globalIndex}
        data-testid={`suggestion-card-${globalIndex}`}
        className={`flex gap-3 items-start p-3 rounded-lg border transition-colors ${
          isSelected ? 'border-primary/50 bg-primary/5' : 'border-border bg-muted/30'
        }`}
      >
        <Checkbox
          checked={isSelected}
          onCheckedChange={() => toggleSelected(globalIndex)}
          aria-label={`Select ${openingLabel}`}
          className="mt-1 flex-shrink-0"
          data-testid={`suggestion-checkbox-${globalIndex}`}
        />
        <MiniBoard
          fen={suggestion.fen}
          flipped={suggestion.color === 'black'}
          size={100}
        />
        <div className="flex flex-col gap-1 flex-1 min-w-0">
          <span className="font-medium text-sm truncate">
            {openingLabel}{ecoLabel}
          </span>
          <Badge variant="secondary" className="w-fit text-xs">
            {suggestion.game_count} {suggestion.game_count === 1 ? 'game' : 'games'}
          </Badge>
        </div>
      </div>
    );
  };

  const renderSection = (title: string, sectionSuggestions: PositionSuggestion[]) => {
    if (sectionSuggestions.length === 0) return null;
    return (
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          {title}
        </h3>
        {sectionSuggestions.map((s) => renderSuggestionCard(s))}
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
          {isFetching && (
            <div className="text-center py-8 text-muted-foreground text-sm">
              Loading suggestions...
            </div>
          )}

          {!isFetching && suggestions.length === 0 && (
            <div className="text-center py-8 text-muted-foreground text-sm">
              No suggestions available. Import games to get bookmark suggestions based on your most-played openings.
            </div>
          )}

          {!isFetching && suggestions.length > 0 && (
            <>
              {renderSection('White openings', whiteSuggestions)}
              {renderSection('Black openings', blackSuggestions)}
            </>
          )}
        </div>

        {!isFetching && suggestions.length > 0 && (
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
