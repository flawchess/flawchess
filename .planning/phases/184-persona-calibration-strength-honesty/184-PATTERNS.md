# Phase 184: Persona Calibration & Strength Honesty - Pattern Map

**Mapped:** 2026-07-22
**Files analyzed:** 11 (5 new, 6 modified)
**Analogs found:** 11 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|---------------|
| `scripts/calibration-harness.mjs` (MODIFY: thread `style` into `playGame`/`selectBotMoveOnce`) | service (game-loop CLI) | event-driven (per-ply callback) + batch | itself (existing `playGame`/`selectBotMoveOnce`, lines 539-629) | exact — same file, extend the seam |
| `scripts/lib/calibration-persona-cell-schedule.mjs` (NEW) | utility (pure scheduler) | transform | `scripts/lib/calibration-bot-cell-schedule.mjs` | exact — same shape, different grouping key |
| `scripts/lib/calibration-persona-cell-schedule.check.mjs` (NEW) | test | transform | `scripts/lib/calibration-bot-cell-schedule.check.mjs` (sibling of the analog above; not read directly but same naming/fixture convention as every other `*.check.mjs` in `scripts/lib/`) | role-match |
| `scripts/calibration_persona_fit.py` (NEW) | service (batch fit script) | batch/transform | `scripts/calibration_anchor_fit.py` (`fit_bot_cell_rating`, reused verbatim, not re-derived) | exact — reuse the function, mirror the CLI/module shape |
| `scripts/gen_persona_calibration.py` (NEW) | utility (codegen) | file-I/O (JSON → TS) | `scripts/gen_bot_strength_curves.py` | exact — same PAVA + codegen + `--check` drift pattern |
| `bin/run_persona_calibration_sweep.sh` (NEW) | config/script (operator runbook) | batch | `bin/run_bot_curves_sweep.sh` | exact |
| `bin/preset-supervisor.sh` | config/script (crash-recovery) | batch | itself — reused as-is, no modification expected | exact (no change) |
| `reports/data/persona-calibration.json` (NEW, generated) | config (generated data) | file-I/O | `reports/data/bot-strength-lookup.json` | exact |
| `frontend/src/generated/personaCalibration.ts` (NEW, generated) | config (generated TS) | file-I/O | `frontend/src/generated/botStrengthCurves.ts` | exact |
| `frontend/src/lib/personas/personaRegistry.ts` (MODIFY: `botElo`/label sourced from generated file) | model/registry | CRUD (static lookup) | itself (current A1-placeholder registry) | exact — same file |
| `frontend/src/components/bots/PersonaCard.tsx` (MODIFY: swap `~${persona.rung}` for calibrated label) | component | request-response (render) | itself | exact — same file |
| `frontend/src/components/bots/PersonaDetailSurface.tsx` (MODIFY: add D-08 disclosure popover) | component | request-response (render) | itself, + `frontend/src/components/popovers/MetricStatPopover.tsx` for the popover shell | exact (surface) / role-match (popover) |

## Pattern Assignments

### `scripts/calibration-harness.mjs` (service, event-driven+batch)

**Analog:** itself — `playGame`/`selectBotMoveOnce`, lines 539-629 (verified on disk)

**Current seam missing `style`** (lines 565-587):
```js
const selectBotMoveOnce = async (fen, rng) => {
  const botUci = await selectBotMove(
    fen,
    {
      elo: botElo,
      blend: botBlend,
      budget: {
        maxNodes,
        maxPlies,
        concurrency: FLAWCHESS_BOT_CONCURRENCY,
        stopRule: FLAWCHESS_BOT_STOP_RULE,
      },
      // style: MISSING — Phase 184 adds this
    },
    { policy: providers.policy, grade: providers.grade, rng },
    // deps.search intentionally omitted (CAL-02) — defaults to the real mctsSearch.
  );
  ...
};
```

**`playGame`'s destructured param signature to extend** (line 539-552):
```js
export async function playGame({
  Chess,
  providers,
  pool,
  botElo,
  botBlend,
  anchorSpec,
  startFen,
  botIsWhite,
  gameRng,
  onPly,
  maxNodes = FLAWCHESS_BOT_MAX_NODES,
  maxPlies = FLAWCHESS_BOT_MAX_PLIES,
}) {
```
Add an optional `style` param here (defaulting to `undefined`, mirroring `selectBotMove`'s own optional `BotSettings.style?: BotStyleParams`), thread it into the `selectBotMove(...)` call above. Every caller (`runCell`, the persona-cell orchestration script) must pass `style: undefined` for byte-identical unstyled runs — this is the existing STYLE-05 absent-style invariant (frontend engine side) mirrored on the harness side; extend `calibration-determinism.check.mjs` to assert it.

**Cell-key pattern to explicitly NOT reuse verbatim** (line 922-924, `cellKey`):
```js
export function cellKey(botElo, botBlend, anchorLabel) {
  return `${botElo}|${botBlend}|${anchorLabel}`;
}
```
The persona-cell schedule/ledger MUST key by `personaId` (or `${personaId}|${anchorLabel}`), never `(botElo, botBlend)` — verified real collisions exist (rung 1800 all 4 styles → identical `(2300, 0.5)`; rung 800/1000 → identical `(1100, 0)` within every style). Mirror the resume/ledger machinery (`readPriorTsvLines`, `cellKey`-style fail-loud header/truncation checks, lines 914-952) but substitute the key.

---

### `scripts/lib/calibration-persona-cell-schedule.mjs` (utility, transform)

**Analog:** `scripts/lib/calibration-bot-cell-schedule.mjs` (full file, 195 lines, verified on disk)

**Reuse verbatim (import, don't fork)** — these are pure functions with no `(botElo, blend)` assumption baked in:
```js
import { INTERNAL_RATING } from './calibration-internal-scale.mjs';
import { scoreInInformativeBand, bandDistance } from './calibration-anchor-schedule.mjs';
import { combineAnchorEstimates } from './calibration-elo.mjs';

export const LOCATE_PASS_GAMES = 8;
export const DEFAULT_BRACKET_SIZE = 4;
export const MIN_BRACKET_PER_FAMILY = 2;

export function internalRatingFor(anchorSpec) { /* fail-loud INTERNAL_RATING lookup, throws on unmeasured label */ }
export function pickLocateAnchors(anchorSpecs) { /* two widest-spaced anchors by MEASURED rating */ }
export function locateEstimate(locateResults) { /* combineAnchorEstimates + informative-band fallback */ }
export function selectMeasureBracket(anchorSpecs, estimate, bracketSize = DEFAULT_BRACKET_SIZE) { /* nearest-N + cross-family floor */ }
export function bracketBeyondLadder(estimate, bracketSpecs) { /* warn-and-proceed edge flag, never throws */ }
```

Per the Open Questions in RESEARCH.md: **default to importing these functions directly** from `calibration-bot-cell-schedule.mjs` in the new orchestration script rather than duplicating them. Only write NEW code for: the persona-keyed outer grid loop (`for personaId of ALL_PERSONA_IDS` instead of `for elo × for blend`), and the ledger/TSV column schema (`persona_id` column replacing/supplementing `bot_elo`/`bot_blend`).

**Fail-loud doc-comment convention to mirror** (lines 53-75, `internalRatingFor`):
```js
/**
 * MEASURED internal-scale rating for an anchor spec — the ONLY rating source a
 * bot-cell schedule may use. ... THROWS (fail-loud, WR-02) on any label not
 * among the 10 Phase-173 measured anchors...
 */
export function internalRatingFor(anchorSpec) {
  const rating = INTERNAL_RATING[anchorSpec.label];
  if (rating === undefined) {
    throw new Error(`internalRatingFor: no measured INTERNAL_RATING for ${anchorSpec.label} — ...`);
  }
  return rating;
}
```

---

### `scripts/lib/calibration-persona-cell-schedule.check.mjs` (test)

**Analog:** the sibling `.check.mjs` convention (naming pattern verified: `calibration-bot-cell-schedule.check.mjs`, `calibration-anchors.check.mjs`, `calibration-determinism.check.mjs` all referenced in RESEARCH.md's Validation Architecture). Hand-rolled `node:assert/strict` fixtures, run via:
```bash
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-persona-cell-schedule.check.mjs
```
Not part of `npm test`/CI automatically — manually invoked, mirroring the existing convention exactly (no pytest, no vitest for this file).

---

### `scripts/calibration_persona_fit.py` (service, batch)

**Analog:** `scripts/calibration_anchor_fit.py` (`fit_bot_cell_rating` at lines 455-498, `fit_all_bot_cells` at lines 635-666 — reused, not re-read line-by-line here since RESEARCH.md already extracted the call contract)

**Reuse unmodified:**
```python
rating_vs_maia = fit_bot_cell_rating(wins_vs_maia, games_vs_maia, fixed_ratings)
# fixed_ratings = INTERNAL_RATING (the same 10-anchor dict every existing fit call uses)
```

**Pitfall 2 (from RESEARCH.md) — MUST fit twice per persona cell**, mirroring `fit_all_bot_cells`'s "the two families are NEVER merged before fitting": fit once against Maia-family anchors only (→ `rating_vs_maia`), once against SF-family anchors only (→ `rating_vs_sf`, optional telemetry). Never fit a single combined-bracket rating and subtract `g_preset_combined` from it.

**Conversion formula** (mirrors `gen_bot_strength_curves.py`'s `approx_blitz_points`, reading `g_preset_combined` from `bot-strength-lookup.json` at fit time, never hardcoded):
```python
G = json.load(open("reports/data/bot-strength-lookup.json"))["components"][preset]["g_preset_combined"]
BLITZ_OFFSET_C = 40  # same named constant as gen_bot_strength_curves.py — reuse the literal import, don't retranscribe
approx_blitz = rating_vs_maia - G + BLITZ_OFFSET_C
```

---

### `scripts/gen_persona_calibration.py` (utility, file-I/O codegen)

**Analog:** `scripts/gen_bot_strength_curves.py` (full file, 334 lines, verified on disk)

**PAVA pooling — reuse verbatim, but sort/pool by RUNG not bot_elo** (lines 99-131):
```python
@dataclass
class _Block:
    x_lo: float
    x_hi: float
    weight: float
    value: float

def isotonic_fit(points: list[tuple[float, float]]) -> list[_Block]:
    """Pool-Adjacent-Violators, stack-of-blocks (D-04 for personas).
    `points` MUST be pre-sorted ascending by x (RUNG here, not bot_elo —
    two rungs may already collide on botElo per Pitfall 1)."""
    blocks: list[_Block] = []
    for x, y in points:
        block = _Block(x_lo=x, x_hi=x, weight=1.0, value=y)
        blocks.append(block)
        while len(blocks) >= 2 and blocks[-2].value > blocks[-1].value:
            b2 = blocks.pop()
            b1 = blocks.pop()
            total_weight = b1.weight + b2.weight
            blocks.append(_Block(
                x_lo=b1.x_lo, x_hi=b2.x_hi, weight=total_weight,
                value=(b1.value * b1.weight + b2.value * b2.weight) / total_weight,
            ))
    return blocks
```
**Run PAVA separately per style column** (D-04: "weak monotonicity within each style column") — 4 separate `isotonic_fit` calls, one per style, each over its 6 `(rung, approx_blitz)` points ascending by rung.

**Global ceiling clamp — apply AFTER pooling, not before** (D-07, explicit Anti-Pattern in RESEARCH.md):
```python
GLOBAL_CEILING = 1800  # D-07 — Deep's measured ceiling; clamp post-PAVA only
final_label = min(round(pooled_value / 50) * 50, GLOBAL_CEILING)  # D-03: round to nearest 50
```

**`--check` drift-mode CLI structure — reuse verbatim** (lines 302-330, `main()`):
```python
def main() -> None:
    check_mode = "--check" in sys.argv
    payload = load_persona_cells(str(_INPUT))
    artifact = compute_artifact(payload)
    outputs = [
        (_render_lookup_json(artifact), _LOOKUP_JSON),
        (_render_ts(artifact), _TS_OUTPUT),
    ]
    if check_mode:
        drifted = [p for content, p in outputs if not p.exists() or p.read_text(encoding="utf-8") != content]
        if drifted:
            print(f"DRIFT: {', '.join(str(p.relative_to(_REPO_ROOT)) for p in drifted)} out of date. "
                  "Run `uv run python scripts/gen_persona_calibration.py` to regenerate.", file=sys.stderr)
            sys.exit(1)
        print("OK: persona calibration artifacts are up to date.")
    else:
        for content, output_path in outputs:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
```

**Fail-loud loader convention** (mirrors `load_internal_scale`, lines 82-96): never coerce a missing/malformed field to a default; raise `ValueError` on missing `cells`/expected-count mismatch (mirrors the `EXPECTED_CELLS_PER_PRESET` D-08 guard — persona equivalent: expect exactly 24 persona entries, raise loud if any are silently dropped).

**Generated-TS header convention to mirror exactly** (lines 279-299, `_render_ts`):
```python
"// AUTO-GENERATED — do not edit by hand.\n"
"// Source: scripts/gen_persona_calibration.py, reports/data/persona-calibration-cells.tsv\n"
"// Regenerate with: uv run python scripts/gen_persona_calibration.py\n"
"\n"
"// STALENESS (D-11): changing botStyleBundles.ts params or the anchor ladder\n"
"// invalidates this calibration — re-run the persona sweep before regenerating.\n"
```
D-11 requires this staleness doc-comment be prominent in the generated file's header (and mirrored in `botStyleBundles.ts`'s own header) — no hash-guard automation, just the comment.

---

### `bin/run_persona_calibration_sweep.sh` / `bin/preset-supervisor.sh` (config/script, batch)

**Analog:** `bin/run_bot_curves_sweep.sh` (189 lines) + `bin/preset-supervisor.sh` (70 lines, reused as-is — already generic over `<name> <blend> <elo-csv> [adopt-pid]`)

Not re-read line-by-line (RESEARCH.md already extracted the operative contract): the new runbook script parallel-launches the persona-cell schedule under the supervisor, combines per-persona TSVs, and invokes the fit script — same shape as `run_bot_curves_sweep.sh`'s launch/combine/fit pipeline. `preset-supervisor.sh` needs NO modification; pass persona-sweep name/blend/elo triples (or extend its `launch()` to accept a `--style` flag if the persona axis doesn't map cleanly onto its existing CLI shape — implementation detail for the plan).

---

### `frontend/src/lib/personas/personaRegistry.ts` (model/registry, CRUD)

**Analog:** itself (full file, 461 lines, verified on disk) — this is a MODIFY, not a new file

**Current A1-placeholder doc comment to REPLACE** (lines 14-22):
```ts
/**
 * A1 (pre-calibration decision, RESEARCH.md Pitfall 2 / Assumption A1):
 * `botElo === rung` for every persona this phase. ...
 * this is a DELIBERATE placeholder, not the actual measured
 * strength — Phase 184 (CAL-04/05) replaces these provisional labels...
 */
```
Update to document the calibrated-value provenance instead (pointer to `personaCalibration.ts` + the fit script + D-11 staleness policy).

**Current per-persona shape to modify** (e.g. lines 138-148, `attacker-1200`):
```ts
'attacker-1200': {
  id: personaId('Attacker', 1200),
  style: 'Attacker',
  rung: 1200,
  botElo: 1200,
  blend: RUNG_BLEND[1200],
  name: 'Talon the Falcon',
  species: 'Falcon',
  bio: '...',
  avatarEmoji: '🦅',
},
```
`botElo` becomes `PERSONA_CALIBRATION['attacker-1200'].botElo` (retargeted, e.g. ~1900) sourced from the generated file; a new `label` field (or equivalent) holds the calibrated display string. `rung` stays as the structural grid key (per CONTEXT.md's explicit discretion note) — do not repurpose it.

**Exhaustiveness-enforcement pattern to preserve** (lines 417-428): `Record<PersonaId, Persona>` continues to force all 24 slots; if a `label`/calibrated-value field is added to the `Persona` interface, it too should be sourced via a lookup keyed by `PersonaId` from `personaCalibration.ts` (mirrors `RUNG_BLEND: Record<Rung, number>`'s exhaustive-record convention, lines 94-101).

---

### `frontend/src/generated/personaCalibration.ts` (config, generated)

**Analog:** `frontend/src/generated/botStrengthCurves.ts` (not re-read directly — its shape is fully specified by `gen_bot_strength_curves.py`'s `_render_ts`, already excerpted above). Mirror the `export type X = ...`, `export const Y: Record<...> = {...} as const;` shape, keyed by `PersonaId` instead of `BotStrengthPreset`. CI drift-checks it exactly like `botStrengthCurves.ts` (`.github/workflows/ci.yml` lines 40-68 per RESEARCH.md — not re-read, referenced only).

---

### `frontend/src/components/bots/PersonaCard.tsx` (component, request-response)

**Analog:** itself (full file, 61 lines, verified on disk) — MODIFY only

**Current label render to replace** (line 58):
```tsx
<span className="text-sm text-muted-foreground">{`~${persona.rung}`}</span>
```
Swap `persona.rung` for the calibrated label field (e.g. `persona.calibratedLabel` or a lookup call) — keep the `~` prefix and the exact `text-sm text-muted-foreground` classes (D-03/D-06: tilde format is uniform for every persona including the bottom rung, no card-level qualifier).

**`aria-label` also references `rung`** (line 38) — update in lockstep:
```tsx
aria-label={`${persona.name}, approximately ${persona.rung} ELO`}
```
should read the calibrated value too, so the accessible name matches the visible label.

---

### `frontend/src/components/bots/PersonaDetailSurface.tsx` (component, request-response)

**Analog:** itself (full file, 272 lines, verified on disk) for the surface structure; `MetricStatPopover.tsx` (full file, 96 lines, verified on disk) for the NEW D-08 disclosure popover.

**Current display-only meta line to modify** (lines 219-223):
```tsx
{/* Display-only ELO/style text — never an EloSelector/PlayStyleControl
    (Pitfall 3): this surface has no strength picker. */}
<p className="text-sm text-muted-foreground" data-testid="persona-detail-meta">
  {`${persona.style} · ~${persona.rung}`}
</p>
```
Swap `persona.rung` for the calibrated label; add the D-08 popover trigger inline next to this text (a `<span>` housing the `MetricStatPopover`-style trigger, NOT replacing the visible label — the popover is supplementary disclosure, mirroring how `PercentileChip` pairs a visible number with a hover-disclosure affordance elsewhere in the app).

**Popover shell to copy verbatim (rename only)** — `MetricStatPopover.tsx` full source (already captures the exact hover/tap/Portal/animation contract):
```tsx
const HOVER_OPEN_DELAY_MS = 100;

export function PersonaEloDisclosurePopover({ testId, ariaLabel, ...bodyProps }: Props) {
  const [open, setOpen] = React.useState(false);
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = (): void => {
    hoverTimeout.current = setTimeout(() => setOpen(true), HOVER_OPEN_DELAY_MS);
  };
  const handleMouseLeave = (): void => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setOpen(false);
  };

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <span
          role="button"
          tabIndex={0}
          className="inline-flex items-center text-brand-brown-light/70 hover:text-brand-brown focus:outline-none cursor-pointer"
          aria-label={ariaLabel}
          data-testid={testId}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <Search className="h-4 w-4" />
        </span>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side="top"
          sideOffset={4}
          onMouseEnter={() => { if (hoverTimeout.current) clearTimeout(hoverTimeout.current); }}
          onMouseLeave={handleMouseLeave}
          className={cn(
            'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
            'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2',
            'data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
          )}
        >
          {/* D-08 body: measured in bot-vs-engine games on the internal anchor
              ladder, approx blitz scale. Bottom-rung variant (D-06) appends a
              floor-acknowledgment line. text-xs is the documented CLAUDE.md
              popover exception. */}
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
```
`data-testid="persona-elo-disclosure"` per the naming convention (`{component}-{element}`), placed adjacent to the `persona-detail-meta` text.

## Shared Patterns

### Fail-loud validation (no silent defaults)
**Source:** `scripts/lib/calibration-bot-cell-schedule.mjs:66-75` (`internalRatingFor`), `scripts/gen_bot_strength_curves.py:82-96` (`load_internal_scale`), `scripts/gen_bot_strength_curves.py:209-213` (`EXPECTED_CELLS_PER_PRESET` guard)
**Apply to:** the new persona-cell schedule, `calibration_persona_fit.py`, `gen_persona_calibration.py` — every loader throws/raises on a missing or malformed field (missing anchor rating, missing persona cell, cell-count mismatch), never coerces to a default. This is a project-wide convention across all 3 calibration-pipeline Python/JS files reused here.

### PersonaId-keyed schema (the load-bearing fix, Pitfall 1)
**Source:** `scripts/calibration-harness.mjs:922-924` (`cellKey`, the pattern to AVOID for personas) vs. `frontend/src/lib/personas/personaRegistry.ts:56` (`PersonaId` template-literal type, the correct key)
**Apply to:** the persona-cell schedule, the raw ledger schema, the aggregate TSV, the fit script's input, and `personaCalibration.ts`'s generated `Record<PersonaId, ...>` — every one of these must key by `PersonaId`, never `(botElo, blend)`, because verified collisions exist post-retargeting (rung 1800 all 4 styles share `(2300, 0.5)`; rung 800/1000 share `(1100, 0)` within every style).

### Generated-file + CI drift-check pipeline
**Source:** `scripts/gen_bot_strength_curves.py:302-330` (`main()`'s `--check` mode) + `frontend/src/generated/botStrengthCurves.ts`'s header convention
**Apply to:** `gen_persona_calibration.py` → `frontend/src/generated/personaCalibration.ts` — identical `--check` exit-1-on-drift contract, identical `// AUTO-GENERATED — do not edit by hand.` header, identical `git diff --exit-code` CI step (extend `.github/workflows/ci.yml`'s existing generated-file drift job to add this new pair, mirroring how `endgameZones`/`flawThresholds`/`botStrengthCurves` are already listed there).

### Measurement-disclosure popover (D-08)
**Source:** `frontend/src/components/popovers/MetricStatPopover.tsx` (full file, verified)
**Apply to:** the new persona ELO disclosure popover in `PersonaDetailSurface.tsx` — 100ms hover-open timeout, `PopoverPrimitive.Root`/`Trigger`/`Portal`/`Content` shell, `side="top" sideOffset={4}`, identical Tailwind animation classes, `text-xs` body (the documented CLAUDE.md exception for this component class).

### Resumable per-game ledger + supervisor crash recovery
**Source:** `scripts/calibration-harness.mjs:914-952` (`readPriorTsvLines`, header/truncation fail-loud checks) + `bin/preset-supervisor.sh` (reused as-is)
**Apply to:** the persona sweep's ledger writer/reader and the operator runbook — append-mode resume on the known onnxruntime-web wasm OOB crash (~5-6h into blend>0 runs); never launch the bare driver unsupervised.

## No Analog Found

None — every file in scope has a direct, verified analog already read from disk (this phase is explicitly a "copy-adapt from Phase 173/180/181" data-pipeline phase, not new-pattern work, per RESEARCH.md's Summary).

## Metadata

**Analog search scope:** `scripts/`, `scripts/lib/`, `bin/`, `reports/data/`, `frontend/src/generated/`, `frontend/src/lib/personas/`, `frontend/src/components/bots/`, `frontend/src/components/popovers/`
**Files scanned:** 11 (all read in full or via already-verified RESEARCH.md excerpts; no file exceeded 2,000 lines except `calibration-harness.mjs` at 1659 lines, read via 2 non-overlapping targeted ranges: 530-629 for the `playGame`/`selectBotMoveOnce` seam, 900-960 for the `cellKey`/resume-ledger schema)
**Pattern extraction date:** 2026-07-22
