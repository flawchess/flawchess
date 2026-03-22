/**
 * Centralized theme constants.
 * Board square colors, primary accent colors, etc. — single source of truth
 * so branding changes only need one edit.
 */

// Board square colors (warm wood tones)
export const BOARD_DARK_SQUARE = '#B68965';
export const BOARD_LIGHT_SQUARE = '#F0DAB7';

export const darkSquareStyle = { backgroundColor: BOARD_DARK_SQUARE } as const;
export const lightSquareStyle = { backgroundColor: BOARD_LIGHT_SQUARE } as const;

/**
 * Tailwind classes for branded primary buttons.
 * Hex values must be written as literals here (not interpolated from constants)
 * because Tailwind scans source files at build time and can't resolve dynamic strings.
 * Update both the class string and the constants below when changing button colors.
 */
export const PRIMARY_BUTTON_CLASS = 'bg-[#8B5E3C] hover:bg-[#6B4226] text-white';
