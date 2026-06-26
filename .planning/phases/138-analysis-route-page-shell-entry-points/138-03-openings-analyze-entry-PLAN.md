---
phase: 138-analysis-route-page-shell-entry-points
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/lib/analysisUrl.ts
  - frontend/src/lib/analysisUrl.test.ts
  - frontend/src/pages/Openings.tsx
autonomous: true
requirements: [ROUTE-02]

must_haves:
  truths:
    - "An 'Analyze position' action on the Openings Explorer carries the current Explorer board FEN to /analysis?fen=<url-encoded> (D-02, ROUTE-02)"
    - "The action appears on BOTH the desktop and mobile Openings board surfaces (CLAUDE.md mobile+desktop parity)"
    - "The FEN→URL construction url-encodes the FEN (spaces and slashes), verified by an isolated unit test"
  artifacts:
    - path: "frontend/src/lib/analysisUrl.ts"
      provides: "buildAnalysisUrl(fen) — pure, unit-testable /analysis?fen= constructor (encodeURIComponent)"
      exports: ["buildAnalysisUrl"]
    - path: "frontend/src/lib/analysisUrl.test.ts"
      provides: "Unit test proving FEN url-encoding (spaces → %20, / → %2F)"
    - path: "frontend/src/pages/Openings.tsx"
      provides: "'Analyze position' button (desktop + mobile, explorer tab) navigating via buildAnalysisUrl(chess.position)"
      contains: "btn-analyze-position"
  key_links:
    - from: "frontend/src/pages/Openings.tsx"
      to: "frontend/src/lib/analysisUrl.ts"
      via: "navigate(buildAnalysisUrl(chess.position)) on Analyze-position click"
      pattern: "buildAnalysisUrl\\("
---

<objective>
Add the opening-position entry point (D-02, ROUTE-02): an "Analyze position" action on the Openings Explorer that navigates to `/analysis?fen=<url-encoded current Explorer FEN>`. Because the Openings page needs 15+ hook mocks to full-render (its existing test deliberately avoids that), the FEN→URL construction is extracted to a tiny pure helper `buildAnalysisUrl` (mirroring the `openingsBoardLayout.ts` extraction precedent) so the load-bearing encoding behavior is unit-testable in isolation.

Purpose: Deliver the only in-scope ROUTE-02 entry (game-review-ply is descoped to Phase 139 per D-03). Read-only `?fen=` transport — no write-back, no backend (D-01/D-04).
Output: `analysisUrl.ts` + `analysisUrl.test.ts` (new) + the button on both Openings board surfaces.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/138-analysis-route-page-shell-entry-points/138-RESEARCH.md
@.planning/phases/138-analysis-route-page-shell-entry-points/138-PATTERNS.md
@.planning/phases/138-analysis-route-page-shell-entry-points/138-UI-SPEC.md
@frontend/src/lib/openingsBoardLayout.ts
</context>

<artifacts_produced>
NEW symbols/files created by this plan (exclude from drift verification):
- `frontend/src/lib/analysisUrl.ts` — new module exporting `buildAnalysisUrl(fen: string): string`.
- `frontend/src/lib/analysisUrl.test.ts` — new Vitest unit test for the encoder.
- In `frontend/src/pages/Openings.tsx`: a `handleAnalyzePosition` handler and the "Analyze position" `<Button>` on the desktop board surface (testid `btn-analyze-position`) and the mobile board surface (testid `btn-analyze-position-mobile`).
</artifacts_produced>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extract and unit-test buildAnalysisUrl (the FEN→/analysis encoder)</name>
  <files>frontend/src/lib/analysisUrl.ts, frontend/src/lib/analysisUrl.test.ts</files>
  <behavior>
    - `buildAnalysisUrl('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')` returns `/analysis?fen=` followed by the `encodeURIComponent` of that FEN.
    - Spaces in the FEN encode to `%20` and `/` encodes to `%2F` in the output (so the query param survives the URL intact).
  </behavior>
  <read_first>
    - `frontend/src/lib/openingsBoardLayout.ts` — the precedent for extracting a pure, page-decoupled helper to `lib/` (and why: the Openings page is impractical to full-render in tests). Mirror its module style.
    - `frontend/src/lib/__tests__/tacticDepth.test.ts` (or any `frontend/src/lib/*.test.ts`) — the lib unit-test convention.
    - `.planning/phases/138-analysis-route-page-shell-entry-points/138-RESEARCH.md` §"Pattern C" / §"Code Examples" → "Navigating from Openings" (the `encodeURIComponent` requirement — FENs contain spaces and `/`).
  </read_first>
  <action>
    Create `frontend/src/lib/analysisUrl.ts` exporting a single pure function `buildAnalysisUrl(fen: string): string` that returns the `/analysis` path with the FEN url-encoded as the `fen` query param via `encodeURIComponent`. Keep it a one-purpose module — name a constant for the route path (`/analysis`) and the param key (`fen`) rather than inlining bare literals (CLAUDE.md no-magic-values). Type the signature explicitly.

    Create `frontend/src/lib/analysisUrl.test.ts` (co-located lib-test convention) asserting: (a) the start-position FEN round-trips to `/analysis?fen=` + its `encodeURIComponent`; (b) the output contains `%20` (encoded space) and `%2F` (encoded slash) and contains no raw space or raw `/` after the `fen=` marker. This is the isolated, deterministic ROUTE-02 encoding gate that replaces an impractical full-page Openings render.
  </action>
  <acceptance_criteria>
    - `frontend/src/lib/analysisUrl.ts` exports `buildAnalysisUrl` (grep: `export function buildAnalysisUrl` or `export const buildAnalysisUrl`) with an explicit return type, no bare-literal route/param strings.
    - `frontend/src/lib/analysisUrl.test.ts` asserts the encoded output contains `%20` and `%2F` and equals `/analysis?fen=` + `encodeURIComponent(fen)`.
    - `cd frontend && npm test -- --run src/lib/analysisUrl.test.ts` is GREEN.
    - `npx tsc -b` clean; `npm run knip` reports no dead export (the helper is imported by Task 2).
  </acceptance_criteria>
  <verify>
    <automated>cd frontend && npm test -- --run src/lib/analysisUrl.test.ts && npx tsc -b</automated>
  </verify>
  <done>The FEN→`/analysis` encoder is a tested pure function; the url-encoding correctness (the load-bearing ROUTE-02 behavior) is locked by an isolated unit test.</done>
</task>

<task type="auto">
  <name>Task 2: Add the "Analyze position" button to both Openings board surfaces</name>
  <files>frontend/src/pages/Openings.tsx</files>
  <read_first>
    - `.planning/phases/138-analysis-route-page-shell-entry-points/138-PATTERNS.md` §"frontend/src/pages/Openings.tsx (entry button)" — the exact in-file analogs: `navigate` already in scope (`Openings.tsx:115`), `chess.position` live FEN (`Openings.tsx:132`, used `:920`/`:1045`), the `brand-outline` secondary-button idiom (`Openings.tsx:637-639`, `:1025-1026`, `:1232-1234`), the desktop board column (`:917-954`) and mobile board+settings column (`:1042-1115`, `lg:hidden` branch at `:966`), and the existing `lucide-react` icon import site (`:15`). Note: place the button in `Openings.tsx`, NOT `ExplorerTab.tsx` (presentational child, no `navigate`/`chess` in scope).
    - `.planning/phases/138-analysis-route-page-shell-entry-points/138-UI-SPEC.md` §"'Analyze position' Entry Button" + §"Copywriting Contract" (label "Analyze position", `lucide` `Microscope` icon, `variant="brand-outline"`, may collapse to icon-only with `aria-label` on a cramped mobile row) and §"Color" (accent reserved for this `brand-outline` button — do not paint generic elements brown).
    - `frontend/src/lib/analysisUrl.ts` (Task 1 — the `buildAnalysisUrl` import).
  </read_first>
  <action>
    In `Openings.tsx`, add `const handleAnalyzePosition = useCallback(() => navigate(buildAnalysisUrl(chess.position)), [navigate, chess.position])` (import `buildAnalysisUrl` from `@/lib/analysisUrl`; `navigate` and `chess` are already in scope). Read-only entry, no write-back (D-01/D-02).

    Render an "Analyze position" `<Button>` on BOTH board surfaces, near the board controls so it reads as "take this position to the analysis board", and ONLY on the position-bearing explorer tab surface:
    - Desktop board column (`Openings.tsx:917-954` region): `data-testid="btn-analyze-position"`.
    - Mobile board column (`Openings.tsx:1042-1115`, the `lg:hidden` branch): `data-testid="btn-analyze-position-mobile"`.
    Use `Button variant="brand-outline"` (CLAUDE.md secondary action — `brand-outline`, never `variant="secondary"`, never hand-rolled `bg-*`/color `className`). Use the `lucide-react` `Microscope` icon (add to the existing icon import — `Swords`/`Sparkles` are already imported there; prefer `Microscope` per UI-SPEC, with a `mr-2 h-4 w-4` icon gap when a visible label is shown). Visible label "Analyze position" on desktop; on a cramped mobile control row the label may collapse to icon-only with `aria-label="Analyze position"`. Keep all copy at the `text-sm` floor. Both buttons call `onClick={handleAnalyzePosition}`.

    Apply the parity rule strictly: the button, its handler, icon, and variant must match on both surfaces (only the testid and the optional label collapse differ). Search the file for duplicated board markup before considering this complete.
  </action>
  <acceptance_criteria>
    - `Openings.tsx` imports `buildAnalysisUrl` from `@/lib/analysisUrl` and defines `handleAnalyzePosition` calling `navigate(buildAnalysisUrl(chess.position))`.
    - Two buttons exist: `data-testid="btn-analyze-position"` (desktop board column) and `data-testid="btn-analyze-position-mobile"` (mobile board column), each `variant="brand-outline"`, each wired to `handleAnalyzePosition`.
    - Icon-only variant (if used on mobile) carries `aria-label="Analyze position"`; no hand-rolled `bg-*`/color classes on the buttons; no `variant="secondary"`.
    - Buttons render only on the explorer (position-bearing) tab surface.
    - `cd frontend && npx tsc -b && npm run lint && npm run knip` clean; `npm test -- --run src/lib/analysisUrl.test.ts src/pages/__tests__/Openings.statsBoard.test.tsx` (this plan's own surfaces) green. NOTE: scoped to this plan's files on purpose — Plan 03 runs in Wave 1 in parallel with Plan 02, and the full suite includes the Wave-0 `Analysis.test.tsx` which stays RED until Plan 02 creates `Analysis.tsx`. The full-suite green is asserted at the post-wave merge gate, not inside this parallel plan.
  </acceptance_criteria>
  <verify>
    <automated>cd frontend && npx tsc -b && npm run lint && npm run knip && npm test -- --run src/lib/analysisUrl.test.ts src/pages/__tests__/Openings.statsBoard.test.tsx</automated>
  </verify>
  <done>From either the desktop or mobile Openings Explorer, "Analyze position" navigates to `/analysis?fen=<encoded current position>`; surfaces are at parity and the encoder is the tested `buildAnalysisUrl`.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Explorer FEN → URL | The live `chess.position` FEN is serialized into a navigable `/analysis?fen=` URL; it is app-internal (not user-typed) but must be url-encoded to survive the query string intact. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-138-04 | Tampering (param corruption) | `buildAnalysisUrl` FEN serialization | mitigate | `encodeURIComponent` the FEN (spaces/`/` are otherwise query-breaking); locked by the `analysisUrl.test.ts` `%20`/`%2F` assertions. The receiving side (Plan 02) additionally FEN-guards the param (T-138-01), so even a corrupted URL degrades to the start position rather than crashing. |
| T-138-02 | Tampering / XSS | Navigation target string | accept | The constructed URL is consumed by React Router `navigate()` (client-side route change), not injected into the DOM as HTML; no XSS surface. |
| T-138-SC | Tampering | npm/pip/cargo installs | accept (N/A) | No package installs this phase — verified RESEARCH.md §"Package Legitimacy Audit" (zero new packages). No legitimacy checkpoint required. |
</threat_model>

<verification>
- Automated: `npm test -- --run src/lib/analysisUrl.test.ts src/pages/__tests__/Openings.statsBoard.test.tsx` green; `npx tsc -b && npm run lint && npm run knip` clean. (Full-suite green is verified at the post-wave merge gate, after Plan 02's `Analysis.tsx` lands — not inside this parallel Wave-1 plan.)
- Manual (folds into Plan 02's checkpoint): click "Analyze position" on desktop and mobile Openings Explorer → URL becomes `/analysis?fen=<encoded current position>` and the Analysis board loads that position.
</verification>

<success_criteria>
- ROUTE-02 (opening-position entry, the only in-scope ROUTE-02 surface this phase): the current Explorer position is carried to `/analysis` via an encoded `?fen=` param, from both desktop and mobile.
</success_criteria>

<output>
Create `.planning/phases/138-analysis-route-page-shell-entry-points/138-03-SUMMARY.md` when done.
</output>
