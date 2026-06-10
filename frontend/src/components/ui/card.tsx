import * as React from 'react';

import { cn } from '@/lib/utils';

// FlawChess themed card primitive: a textured surface with an optional banded
// header. This is the canonical "card with header" used across Openings, Endgames,
// Stats, and the game lists. The visual treatment (texture, header band) lives here
// so it can change in one place; callers describe ROLE (accent, header size), not style.
//
// Composition:
//   <Card accentColor={resultColor}>
//     <CardHeader size="compact">Title <RightControls className="ml-auto" /></CardHeader>
//     <CardBody>…</CardBody>
//   </Card>
//
// The stock shadcn card (neutral bg-card) lives in ui/form-card.tsx as FormCard*.

interface CardProps extends React.HTMLAttributes<HTMLElement> {
  /** Root element. Defaults to div; use section/article to keep page semantics. */
  as?: 'div' | 'section' | 'article';
  /** Optional colored left spine — renders a 4px left border in this color. */
  accentColor?: string;
  /**
   * Let content overflow the card bounds (default clips). Needed only for cards
   * whose children must visually escape the border, e.g. an eval-chart tooltip.
   * When set, give CardHeader `className="rounded-t-md"` so the header band's top
   * corners still conform to the radius (the clip no longer rounds them).
   */
  overflowVisible?: boolean;
}

function Card({
  as: Tag = 'div',
  accentColor,
  overflowVisible = false,
  className,
  style,
  ...props
}: CardProps) {
  return (
    <Tag
      className={cn(
        'charcoal-texture rounded-md',
        overflowVisible ? 'overflow-visible' : 'overflow-hidden',
        className,
        // Accent spine last: tailwind-merge must keep border-l-4 over any `border`
        // width the caller passes in className (else the left spine width is lost).
        accentColor && 'border-l-4',
      )}
      style={accentColor ? { borderLeftColor: accentColor, ...style } : style}
      {...props}
    />
  );
}

type CardHeaderTag = 'h2' | 'h3' | 'h4';

interface CardHeaderProps extends React.HTMLAttributes<HTMLHeadingElement> {
  /** Heading level for the title bar. Defaults to h3. */
  as?: CardHeaderTag;
  /** 'default' = text-base / py-3 (section cards); 'compact' = text-sm / py-2 (list/result cards). */
  size?: 'default' | 'compact';
}

function CardHeader({
  as: Tag = 'h3',
  size = 'default',
  className,
  ...props
}: CardHeaderProps) {
  return (
    <Tag
      className={cn(
        'flex items-center gap-2 px-4 bg-black/20 border-b border-border/40 font-semibold',
        size === 'compact' ? 'py-2 text-sm' : 'py-3 text-base',
        className,
      )}
      {...props}
    />
  );
}

function CardBody({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('p-4', className)} {...props} />;
}

export { Card, CardHeader, CardBody };
