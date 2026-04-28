/**
 * Curated troll-opening keys (user-side-only piece-placement FENs).
 *
 * STUB FILE: shipped by Plan 77-01 so the import in
 * `frontend/src/lib/trollOpenings.ts` resolves at module-load time (vitest
 * resolves source-file imports before applying vi.mock factories — without a
 * real file the resolver throws "Cannot find package").
 *
 * Plan 77-02 replaces this stub with the curated set. Tests in this file
 * mock the module via `vi.mock('@/data/trollOpenings', ...)` so they are
 * independent of the curated content.
 */

export const WHITE_TROLL_KEYS: ReadonlySet<string> = new Set<string>();
export const BLACK_TROLL_KEYS: ReadonlySet<string> = new Set<string>();
