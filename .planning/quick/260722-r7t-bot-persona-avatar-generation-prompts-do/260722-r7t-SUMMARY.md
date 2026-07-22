---
phase: quick-260722-r7t
plan: 01
subsystem: ui
tags: [pydantic-ai, gemini, image-generation, pillow, vite, import-meta-glob, bots]

requires:
  - phase: 183-persona-registry-bots-page
    provides: personaAvatarPrompts.md (placeholder-era prompts doc), personaAvatars.ts (D-17 forward-compat stub), PersonaId/Persona registry
provides:
  - Self-contained personaAvatarPrompts.md carrying all 24 persona bios woven into their descriptor bullets
  - scripts/gen_persona_avatars.py — parses the doc, generates a webp per missing persona via Gemini image generation, downscales to 512x512 with Pillow
  - Glob-backed resolveAvatarSrc() (assets/personas/*.webp keyed by persona id), emoji fallback intact
affects: [184-persona-calibration, future avatar-curation quick tasks, SEED-114 (>2000-ELO extension)]

tech-stack:
  added: [Pillow (dev dependency, image downscale/webp encode)]
  patterns:
    - "Doc-as-generation-source: a committed markdown file is the single input a generation script parses, never TypeScript — regex-parseable bullet shape is the doc<->script contract"
    - "Vite import.meta.glob(eager, query: '?url', import: 'default') for a build-time asset-existence lookup keyed by filename stem"

key-files:
  created:
    - scripts/gen_persona_avatars.py
  modified:
    - frontend/src/data/personaAvatarPrompts.md
    - frontend/src/lib/personas/personaAvatars.ts
    - pyproject.toml
    - uv.lock

key-decisions:
  - "NativeTool import path corrected from the plan's assumed pydantic_ai top-level export to the verified pydantic_ai.capabilities.NativeTool (installed 1.104.0 does not re-export it at top level)"
  - "Demeanor-placeholder splice includes the trailing period so persona/style text concatenation never produces a double period"
  - "ty: ignore[unresolved-attribute] on result.output.data — ty infers str instead of BinaryImage for the output_type=BinaryImage kwarg form; verified correct at runtime via manual construction against the installed package"
  - "Regex parser validates exactly 24 descriptor bullets and raises loudly on drift, rather than silently generating a partial set"

requirements-completed: [D-15, D-16, D-17]

coverage:
  - id: D1
    description: "personaAvatarPrompts.md is self-contained — every one of the 24 descriptor bullets carries its persona's bio, parseable prefix intact"
    requirement: D-15
    verification:
      - kind: unit
        ref: "grep -cE '^- `(attacker|trickster|grinder|wall)-(800|1000|1200|1400|1600|1800)` — ' frontend/src/data/personaAvatarPrompts.md == 24"
        status: pass
    human_judgment: false
  - id: D2
    description: "scripts/gen_persona_avatars.py parses all 24 personas from the doc, targets only personas missing a webp, supports --limit/--logo-ref/--dry-run, and --help/--dry-run work with no GOOGLE_API_KEY"
    requirement: D-16
    verification:
      - kind: unit
        ref: "uv run python scripts/gen_persona_avatars.py --help (exit 0, no API key)"
        status: pass
      - kind: unit
        ref: "uv run python scripts/gen_persona_avatars.py --dry-run (lists 24 pending personas + assembled prompts, no API key)"
        status: pass
      - kind: unit
        ref: "uv run ruff check scripts/gen_persona_avatars.py"
        status: pass
    human_judgment: true
    rationale: "Real image generation (GOOGLE_API_KEY + network call to Gemini) was explicitly out of scope for this task per the dispatch constraints — the operator runs and curates it themselves. Only the parse/dry-run/CLI-flag surface is machine-verified here."
  - id: D3
    description: "resolveAvatarSrc() resolves real art via import.meta.glob over assets/personas/*.webp keyed by persona id, falling back to the emoji placeholder when no webp exists"
    requirement: D-17
    verification:
      - kind: unit
        ref: "frontend: npx tsc -b"
        status: pass
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/PersonaCard.test.tsx (all 15 tests, incl. both avatarSrc-present/absent backstop tests)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/personas/__tests__/personaRegistry.test.ts (no persona ships avatarSrc — unchanged)"
        status: pass
      - kind: unit
        ref: "frontend: npm run lint"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-22
status: complete
---

# Quick Task 260722-r7t: Bot Persona Avatar Generation Pipeline Summary

**Ships the generate-curate-swap avatar pipeline: bios woven into `personaAvatarPrompts.md`, a new `scripts/gen_persona_avatars.py` (Gemini image generation via pydantic-ai + Pillow downscale), and a glob-backed `resolveAvatarSrc()` — no avatar images generated or committed.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-22T17:51:42Z
- **Tasks:** 3
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments

- `frontend/src/data/personaAvatarPrompts.md` is now the single self-contained generation source: all 24 descriptor bullets carry their persona's bio (copied verbatim from `personaRegistry.ts`), and the framing prose describes the real workflow instead of the Phase-183 placeholder-only framing.
- `scripts/gen_persona_avatars.py` parses the doc (master style prompt + 4 per-style demeanor blocks + 24 persona descriptors), targets only personas with no existing `frontend/src/assets/personas/{id}.webp`, and generates via a `pydantic_ai.Agent` using `capabilities=[NativeTool(ImageGenerationTool(...))]` against `google:gemini-3.1-flash-image`, then downscales to 512x512 and saves as webp with Pillow (now a dev dependency).
- `resolveAvatarSrc()` in `personaAvatars.ts` now does a real `import.meta.glob('../../assets/personas/*.webp', { eager: true, query: '?url', import: 'default' })` lookup keyed by filename stem, with `persona.avatarSrc` retained as an explicit override and the D-18 emoji fallback preserved when no webp exists (true for all 24 personas today — zero webp files are committed by this task).

## Task Commits

Each task was committed atomically:

1. **Task 1: Enrich prompts doc so it is the single generation source (D-15)** - `fd3bbcd7` (docs)
2. **Task 2: Add scripts/gen_persona_avatars.py + Pillow dev dep (D-16)** - `fa3a2bde` (feat)
3. **Task 3: Swap resolveAvatarSrc seam to import.meta.glob (D-17)** - `729b5ba2` (feat)

**Plan metadata:** (this SUMMARY.md + STATE.md commit, made by the orchestrator)

## Files Created/Modified

- `frontend/src/data/personaAvatarPrompts.md` - all 24 descriptor bullets gained a woven-in bio; intro + "Notes for the Future Real-Art PR" rewritten as "Generating and Curating Avatars", describing the real script/glob workflow
- `scripts/gen_persona_avatars.py` - new operator script: doc parser (master prompt, per-style demeanor, 24 descriptors), pending-persona filter, Gemini image generation via pydantic-ai, Pillow downscale-to-webp, `--limit`/`--logo-ref`/`--dry-run` CLI
- `frontend/src/lib/personas/personaAvatars.ts` - `resolveAvatarSrc()` body swapped from the `persona.avatarSrc ?? undefined` stub to a real glob-backed lookup; module docstring rewritten to describe the D-17 seam
- `pyproject.toml` / `uv.lock` - Pillow added to `[dependency-groups].dev` via `uv add --dev pillow`

## Decisions Made

- **Corrected the plan's `NativeTool` import path.** The plan's "verified facts" claimed `from pydantic_ai import Agent, NativeTool, BinaryImage, BinaryContent` — checking the installed 1.104.0 package showed `NativeTool` is NOT re-exported at the `pydantic_ai` top level; it lives at `pydantic_ai.capabilities.NativeTool`. Confirmed by constructing the exact `Agent(..., capabilities=[NativeTool(ImageGenerationTool(...))])` call against the installed package (it fails only on the expected missing-`GOOGLE_API_KEY` error, confirming the import/construction path is otherwise correct).
- **Fixed a double-period artifact** in the master-prompt/demeanor splice: the doc's placeholder text is immediately followed by a period (`...notes below]. Warm, approachable...`), and each per-style demeanor bullet also ends in a period, so a naive substring replace produced `"...aggressive.. Warm..."`. Fixed by including the trailing period in the placeholder match constant.
- **Added a `# ty: ignore[unresolved-attribute]`** on `result.output.data` — `ty` infers `result.output` as `str` for the `Agent(..., output_type=BinaryImage)` kwarg-form construction (a pydantic-ai generic-inference limitation, not a real bug); verified correct at runtime by manually constructing the same `Agent` and inspecting its type. scripts/ is outside the CI `ty check` path, so this doesn't block the gate either way, but keeping it clean avoids confusing future readers of the script.
- **Added a hard 24-persona-count assertion** in `build_persona_prompts()` (not explicitly requested by the plan, but directly serves D-16's "parses all 24 personas" requirement) — a doc-shape drift now raises loudly instead of silently generating a partial set.

## Deviations from Plan

None beyond the corrections documented under Decisions Made above (all Rule 1/Rule 3 auto-fixes — a wrong import path, a formatting artifact, and a type-checker false positive, all directly blocking or breaking the plan's own described behavior).

## Issues Encountered

None beyond the pydantic-ai API surface verification called out in Decisions Made — resolved by inspecting the installed package directly (`.venv/lib/python3.13/site-packages/pydantic_ai/`) rather than trusting the plan's cached "verified facts", per the task's own instruction to "verify against the installed package before finalizing."

## User Setup Required

**Real avatar generation requires the user's own `GOOGLE_API_KEY`.** This task deliberately does NOT call the Gemini API or generate any avatar images — that is an explicit constraint, not a gap. To generate avatars:

1. Ensure `GOOGLE_API_KEY` is set in `.env` (pydantic-ai's `GoogleProvider` reads it automatically).
2. `uv run python scripts/gen_persona_avatars.py --dry-run` to preview all 24 assembled prompts first (no API key needed).
3. `uv run python scripts/gen_persona_avatars.py --limit 3` for a small smoke batch, or omit `--limit` to generate all 24.
4. Curate: delete any avatar's `.webp` under `frontend/src/assets/personas/` and rerun to regenerate (optionally editing that persona's descriptor line in `personaAvatarPrompts.md` first).
5. `resolveAvatarSrc()` picks up curated webp files automatically at the next frontend build — no code change needed.

## Next Phase Readiness

- The full pipeline (doc, script, glob seam) is shippable as-is: with zero webp files committed, every persona card renders the D-18 emoji placeholder exactly as before this task, so there is no visual regression.
- Once the user runs the script and curates results, committing the resulting `frontend/src/assets/personas/*.webp` files is a follow-up (likely another quick task or the SEED-114 >2000-ELO extension) — no code changes will be needed at that point.

---
*Phase: quick-260722-r7t*
*Completed: 2026-07-22*

## Self-Check: PASSED

- FOUND: scripts/gen_persona_avatars.py
- FOUND: frontend/src/data/personaAvatarPrompts.md
- FOUND: frontend/src/lib/personas/personaAvatars.ts
- FOUND: pyproject.toml
- FOUND: uv.lock
- FOUND: fd3bbcd7 (Task 1 commit)
- FOUND: fa3a2bde (Task 2 commit)
- FOUND: 729b5ba2 (Task 3 commit)
