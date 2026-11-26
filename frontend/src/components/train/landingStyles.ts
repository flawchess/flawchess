/**
 * Shared sizing for the Train landing's cards.
 *
 * Desktop minimum height of the streak card and the two mode cards, so the three line up and
 * the second row (Blunder Check beside Train schedule) starts at the same height on both sides.
 * It is the streak card's natural height: the flame box (`w-[6rem]`, aspect 100:122, about
 * 7.3rem tall) plus the card body's `p-4` (2rem), rounded up to 9.5rem. A taller card (an
 * expanded settings panel, the streak-reset line) simply grows past it. Phones stack the cards,
 * so the minimum applies from `lg` only.
 */
export const TRAIN_LANDING_CARD_MIN_H_CLASS = 'lg:min-h-[9.5rem]';
