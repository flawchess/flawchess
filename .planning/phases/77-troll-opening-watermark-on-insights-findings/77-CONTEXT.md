# Phase 77: Troll-opening watermark on Insights findings - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Two surfaces, both frontend-only, both showing the Troll-Face SVG when the user has reached a curated troll opening (Bongcloud, Grob, etc.):

1. **Opening Insights finding cards** — render `troll-face.svg` as a 30%-opacity watermark behind `OpeningFindingCard` content. Both desktop and mobile.
2. **Move Explorer move list** — render a small inline troll-face icon next to qualifying SAN rows in `MoveList`. **Desktop only** — too cramped on the mobile move list (`h-12` row height vs. `h-18` desktop).

Pure visual easter eggs. No behavioral change, no scoring/severity adjustments, no badges, no tooltips, no labels.

In scope:
- Curation script (Node/TS) + static TS data file in `frontend/src/data/trollOpenings.ts`.
- Frontend matching utility — derives a user-side-only key from FEN piece placement.
- `OpeningFindingCard`: conditional watermark layer (mobile + desktop).
- `MoveList` (Move Explorer): conditional inline icon next to qualifying rows (desktop only).
- Asset move: `temp/Troll-Face.svg` → `frontend/src/assets/troll-face.svg`.
- Tests: unit test for the user-side-key utility; snapshot/visual tests for both surfaces.

Out of scope:
- Backend schema field, TSV, frozenset, or any backend changes — matching is fully client-side from existing payload fields (`finding.entry_fen`, `entry.result_fen`).
- Bookmarks, Endgame analytics, time-management, Games tab surfaces.
- Tooltips, badges, "Troll Opening Detected" labels, scoring/severity adjustments, per-user opt-out.
- Mobile rendering of the Move Explorer icon — explicit space-constraint exclusion.

</domain>

<decisions>
## Implementation Decisions

### Curation breadth
- **D-01:** Strict (Bongcloud-tier) only. Curate to unambiguously meme/troll openings — Bongcloud, Grob, Borg, Halloween Gambit, Barnes, Fred, and any clearly non-serious entries from Lichess study `cEDAMVBB`. Exclude "fun but legitimate" gambits (Englund, Latvian, From's, Schliemann, Damiano) so the watermark never feels like an unfair burn on legitimate experimenters. Final TSV will be hand-pruned during the curation script run; downstream agents must surface the pruned candidate list to the user before committing the TSV.

### Visual placement
- **D-02:** Anchored bottom-right inside `OpeningFindingCard`. Sized like a stamp/seal (~60-80px), absolutely positioned, behind text via `z-index`. 30% opacity is locked. Reads as a subtle decorative stamp — lowest contrast risk on mobile (375px) and on the existing `charcoal-texture` card background.
- **D-03:** Mobile parity — same anchor (bottom-right), same opacity, same SVG sizing. Re-verify at 375px that the watermark doesn't clip or fight the prose/links column on the mobile layout (board sits left, prose stacked right; the watermark sits behind the right column's bottom area).
- **D-04:** Watermark must not block clicks on `Moves` / `Games` link buttons — use `pointer-events: none` on the SVG layer (or anchor it strictly outside the link row's interactive box).

### Severity behavior
- **D-05:** Show always. Watermark fires whenever the finding's position is in the troll set, regardless of `classification` or `severity`. The joke lands harder when the user has trolled successfully — no suppression on positive-severity strength cards.

### Move Explorer surface
- **D-06:** Add a small inline troll-face icon to `MoveList` rows in the Move Explorer when the *resulting* position (after applying the candidate move) is in the troll set for the side that just moved. The icon is a fully-opaque (or near-fully-opaque) small glyph next to the SAN — different visual register from the 30%-opacity card watermark on purpose.
- **D-07:** **Desktop only.** Mobile move list uses `h-12` row height vs. desktop's `h-18`; there isn't space for an additional inline icon without crowding the WDL bar / SAN. Implement via the existing `sm:` breakpoint or an explicit `hidden sm:inline-flex` on the icon element.

### Matching strategy (frontend-only)
- **D-08:** Derive a deterministic user-side-only key from FEN piece placement on the client. Strip opponent pieces from the placement field (lowercase chars for white-side keys, uppercase for black-side), re-canonicalize consecutive empty squares, and use the resulting string as a `Set<string>` key. No 64-bit Zobrist needed — the key only has to be stable across opponent variations of the same user-side position. Utility lives in `frontend/src/lib/trollOpenings.ts` (or sibling) alongside the curated data.
- **D-09:** Pre-compute keys offline with a small Node/TS curation script that walks `cEDAMVBB.pgn` via chess.js, extracts the defining position of each chapter, derives the side-only key for the troll player's color, and emits a literal TS data file `frontend/src/data/trollOpenings.ts` exporting two `Set<string>` (white-side keys, black-side keys). Hand-pruning to the strict Bongcloud-tier set per D-01 happens during the script run, before commit. Script is committed alongside the data file so the data path is reproducible.
- **D-10:** Insights surface uses `finding.entry_fen` + `finding.color` to compute the key. Move Explorer surface uses `entry.result_fen` (already on `NextMoveEntry`) + the side that just moved (derived from the parent position's side-to-move) to compute the key.

### Asset
- **D-11:** Move `temp/Troll-Face.svg` → `frontend/src/assets/troll-face.svg` (kebab-case per repo convention). Delete the `temp/` copy in the same commit. Frontend imports the SVG via Vite's asset pipeline.

### Claude's Discretion
- Exact pixel size of the watermark on `OpeningFindingCard` (the "60-80px" range above is a guideline, not a lock). Tune for visual balance against `MOBILE_BOARD_SIZE = 105` and `DESKTOP_BOARD_SIZE = 100`.
- Exact pixel size of the inline icon in the Move Explorer move list — should match the existing `lucide-react` icon scale used in adjacent move-list affordances (likely `h-3.5 w-3.5` or `h-4 w-4`).
- Whether the card watermark sits as a sibling element absolutely positioned via Tailwind (`absolute bottom-2 right-2 opacity-30 pointer-events-none`) or as a CSS `background-image` on the card root. Sibling element is preferred (cleaner SVG accessibility, no CSS background-position math), but planner may pick either.
- Where exactly the inline Move Explorer icon sits within the row (left of SAN, right of SAN, end of row before the WDL bar). Match whichever placement reads cleanest in `MoveList.tsx`.
- Test framing — frontend unit test for the user-side-key utility, snapshot/visual tests for the watermark and move-list icon. Match patterns already in `OpeningFindingCard.test.tsx` and the Move Explorer tests.
- Curation script's network behavior — caching the scraped PGN locally during development is fine; the script must be re-runnable offline once the PGN is cached.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase-level design
- `.planning/notes/troll-openings-design.md` — full pre-discuss-phase design notes; defines locks (side-only matching, 30% opacity, finding-card-only scope, static TSV, asset move).
- `.planning/milestones/v1.14-ROADMAP.md` § "Phase 77" — phase entry with goal, dependency, sketch of work, and the three open questions resolved by this CONTEXT.md.

### Upstream phases (consumed contracts)
- `.planning/phases/76-frontend-score-coloring-confidence-badges-label-reframe/76-CONTEXT.md` — Phase 76 finalized the visual treatment of `OpeningFindingCard` (border-left tint, opacity-on-low-confidence, mobile/desktop layouts). Phase 77's watermark layers behind that finalized treatment.
- `frontend/src/types/api.ts` — `NextMoveEntry.result_fen` and `OpeningInsightFinding.entry_fen` are the matching inputs. No schema migration; both are existing fields.

### External
- Lichess study `cEDAMVBB` — `https://lichess.org/study/cEDAMVBB/DYKeAEFt` — source for troll-opening curation. PGN endpoint: `https://lichess.org/study/cEDAMVBB.pgn`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/insights/OpeningFindingCard.tsx` — `cardStyle` already mixes `borderLeftColor` + conditional `opacity` for unreliable findings. Watermark is a new absolutely-positioned child of the existing card root `<div>`. Both mobile and desktop layouts share the same outer card div, so a single watermark element covers both layouts.
- `frontend/src/components/board/MoveList.tsx` — already renders one row per `NextMoveEntry`. Add a conditional inline icon next to qualifying SAN cells. Row container uses `h-12 sm:h-18` — the icon must be `hidden sm:inline-flex` (or equivalent) to suppress on mobile per D-07.
- `frontend/src/types/api.ts` `NextMoveEntry` — already exposes `result_fen` and `move_san`; no contract change needed for Move Explorer matching.
- `frontend/src/lib/openingInsights.ts` — existing utility module already used by `OpeningFindingCard`; the new user-side-key helper can live here or in a sibling `frontend/src/lib/trollOpenings.ts`.
- `chess.js` — already a dependency, used by the curation script to walk the Lichess study PGN and extract defining positions.

### Established Patterns
- Static client-side data tables exist for several lookups (theme tokens, brand strings); a literal TS module exporting `Set<string>` is consistent with that pattern.
- `data-testid` is required on interactive elements. Both the watermark and the move-list icon are decorative and non-interactive (`pointer-events: none` on the watermark; the move-list row click handler stays on the row, not the icon). Add `data-testid="opening-finding-card-{idx}-troll-watermark"` and `data-testid="move-list-row-{san}-troll-icon"` for snapshot tests.
- The `sm:` breakpoint is the canonical desktop/mobile split throughout the codebase — D-07's "desktop only" rule maps directly to it.

### Integration Points
- No backend changes. No schema changes. No API contract changes.
- Frontend: one new asset import; one new utility module (user-side-key + curated `Set<string>` data); one new conditional child element on `OpeningFindingCard`; one new conditional inline icon in `MoveList`; one new curation script under `frontend/scripts/` (or `scripts/`, matching repo convention for build-time codegen).

</code_context>

<specifics>
## Specific Ideas

- The Bongcloud is the canonical example. If the curated set's filtering is unclear, "would the Bongcloud belong here?" is the calibration question. Yes → strict-set candidate. "Could a 1200 player play this with a straight face?" Yes → exclude.
- Lichess study `cEDAMVBB` is the seed list — but it's a starting point, not a contract. Hand-pruning is mandatory.
- The watermark must not visually conflict with the existing severity border-left tint (red for weakness, green for strength). Bottom-right anchor keeps it in the corner farthest from the border, minimizing interaction.
- The two surfaces use deliberately different visual registers: the finding card gets a subtle 30%-opacity ambient watermark; the move-list row gets a small, fully-opaque inline icon. Don't unify them — they're solving different layout problems.

</specifics>

<deferred>
## Deferred Ideas

- Troll-opening icon on Bookmarks, Games tab, or Endgame surfaces — out of scope for v1; could become a follow-on phase if the easter egg lands well.
- Mobile rendering of the Move Explorer icon — explicitly excluded (D-07) due to row-height constraint. Revisit only if the move-list mobile layout gets re-thought independently.
- LLM narration referencing troll status ("you're 28% with the Bongcloud — bold choice") — future LLM-narration work for opening insights, not this phase.
- Per-user opt-out / settings toggle for the watermark — only worth it if user feedback flags the joke as too loud. Not warranted at v1.
- Suppress-when-winning logic — explicitly rejected (D-05); revisit only if user feedback shows the joke reads as mocking on positive-severity cards.
- Score/severity adjustment for troll openings — explicitly rejected; classification stays unchanged regardless of troll status.
- Backend matching via Zobrist hash — explicitly rejected in favor of the simpler frontend-only user-side-FEN-key approach (D-08). Revisit only if matching needs to be shared across surfaces that lack `entry_fen`/`result_fen` in their payload.

</deferred>

---

*Phase: 77-troll-opening-watermark-on-insights-findings*
*Context gathered: 2026-04-28*
