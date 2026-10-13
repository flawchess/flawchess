import type { TimeControlBucket } from '@/types/endgames';

/** Display label of each time-control bucket (the stats switches, section labels and copy). */
export const TC_LABELS: Record<TimeControlBucket, string> = {
  bullet: 'Bullet',
  blitz: 'Blitz',
  rapid: 'Rapid',
  classical: 'Classic',
};
