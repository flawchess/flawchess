import { describe, it, expect } from 'vitest';
import { DEFAULT_FILTERS, type FilterState } from '@/components/filters/FilterPanel';
import { PRESET_RANGES } from '@/lib/opponentStrength';
import { toInsightsFilters } from './insightsFilters';

describe('toInsightsFilters', () => {
  it('leaves the default filters unchanged', () => {
    expect(toInsightsFilters(DEFAULT_FILTERS)).toEqual(DEFAULT_FILTERS);
  });

  it('resets every other filter but keeps a preset opponent strength', () => {
    const filters: FilterState = {
      ...DEFAULT_FILTERS,
      timeControls: ['blitz'],
      platforms: ['lichess'],
      rated: false,
      opponentType: 'bot',
      recency: 'month',
      opponentStrength: PRESET_RANGES.stronger,
    };
    expect(toInsightsFilters(filters)).toEqual({
      ...DEFAULT_FILTERS,
      opponentStrength: PRESET_RANGES.stronger,
    });
  });

  it('resets a custom (non-preset) opponent strength range to the default', () => {
    const filters: FilterState = { ...DEFAULT_FILTERS, opponentStrength: { min: -37, max: 142 } };
    expect(toInsightsFilters(filters).opponentStrength).toEqual(DEFAULT_FILTERS.opponentStrength);
  });
});
