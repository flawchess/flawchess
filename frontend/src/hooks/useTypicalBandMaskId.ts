import { useId } from 'react';

/**
 * A unique mask id per chart. Pass it to TypicalBandWatermark, and as
 * mask={`url(#${maskId})`} to any reference line through the band's middle, so the line
 * shares the cutout instead of striking through the letters.
 */
export function useTypicalBandMaskId(): string {
  // useId output carries characters (colons, guillemets) that are unsafe in a url(#...) ref.
  return `typical-band-mask-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
}
