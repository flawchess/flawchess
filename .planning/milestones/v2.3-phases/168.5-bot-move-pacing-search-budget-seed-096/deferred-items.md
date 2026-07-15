# Deferred Items — Phase 168.5

Out-of-scope discoveries logged per the executor's scope-boundary rule (not fixed, only recorded).

## From Plan 01 (2026-07-12)

- **REQUIREMENTS.md `PLAY-05` wording is now stale.** `.planning/REQUIREMENTS.md`'s
  `PLAY-05` still reads "The bot paces its replies (not instant) with a think-time
  budget derived from its remaining clock (best-effort; degrades gracefully under
  time pressure)" — the exact clause Plan 01 replaced in ROADMAP.md's Phase 169 SC1
  per D-01/D-04 (fixed strength, never reads the clock). Plan 01's `files_modified`
  scoped only `ROADMAP.md` and `SEED-091-...md`; REQUIREMENTS.md was out of scope for
  this plan and was left untouched. Whoever plans/executes Phase 169 (or a future
  requirements-sync task) should reword `PLAY-05` to match the D-04 sentence so the
  milestone requirements doc doesn't contradict the roadmap and Phase 169's SC1.
