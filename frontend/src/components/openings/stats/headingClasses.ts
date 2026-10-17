import { cn } from '@/lib/utils';

/** The h2 look of every Openings Stats section (repertoire groups, findings). */
export const SECTION_HEADING_CLASS = 'font-brand text-lg font-semibold text-foreground';

/** Repertoire group headings: lg:h-8 because the desktop colour bar (StickyTcBar in StatsTab) overlays the first one. */
export const REPERTOIRE_HEADING_CLASS = cn(SECTION_HEADING_CLASS, 'lg:flex lg:h-8 lg:items-center');
