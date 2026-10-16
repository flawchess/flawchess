# Codebase Cleanup Style Guide

Scope: naming and comment hygiene only. No architecture changes, no behavior changes, no new features.
A cleanup commit passes the full pre-merge gate **with no test assertion changed** (test code may change
only to follow a rename). Any diff line that is neither a comment nor a rename needs a justification.

Baseline (2026-10-16): ~11,400 planning-artifact tags (`Phase NNN`, `D-NN`, `SEED-NNN`) in `app/` +
`frontend/src`, ~3,500 more in `tests/`; ~550 TODO / legacy / deprecated / "no longer" markers.

---

## 1. Off-limits (never rename, flag instead)

Anything a type checker cannot see the other side of. Renaming these breaks something outside the repo
or outside the current deploy.

| Contract | Where | Why |
|---|---|---|
| DB tables, columns, indexes, constraint names | `app/models/`, raw SQL | needs a migration; not cleanup |
| Persisted enum values (`IntEnum` ints, `TEXT CHECK` strings) | models, schemas | stored in rows |
| Alembic migrations (code AND comments) | `alembic/versions/` | historical record |
| Remote-worker protocol: endpoint paths, JSON fields | `app/routers/eval_remote.py`, `app/schemas/eval_remote.py`, `scripts/remote_eval_worker.py` | workers in the fleet run older code |
| Public API paths and JSON field names | `app/routers/`, `app/schemas/` ↔ `frontend/src/api`, `frontend/src/types` | separate planned change if worth it |
| Generated files | `frontend/src/generated/*` | edit the source registry, re-run `scripts/gen_*.py` |
| Sentry messages, tags, context keys | `sentry_sdk.*`, `Sentry.*` | issue grouping and dashboard continuity |
| Umami event names and props | `trackEvent(...)` | analytics history |
| `localStorage` / `sessionStorage` keys, cookie names | frontend | users lose saved state |
| URL paths and query params | routes, `?type=` etc. | shared links |
| `data-testid` values | frontend | tests and UAT tooling |
| Env vars, config keys | `app/core/config.py`, `.env*` | deploy config |
| LLM prompt text (strings, not comments) | `app/services/insights_llm.py` | changes model output |
| Out of tree | `CHANGELOG.md`, `.planning/`, `fixtures/`, `stories/`, `analysis/`, `scripts/archive/` | history, data, or separate projects |

Internal names that *happen to match* a contract (a Python attribute mirroring a JSON field) may be
renamed only if the wire name is pinned explicitly (Pydantic `serialization_alias`, explicit mapping).
Default: don't.

---

## 2. Comments

### 2.1 Planning-artifact tags

Tags: `Phase NNN`, `D-NN`, `SEED-NNN`, `CR-NN`, `WR-NN`, `FE-IN-NN`, `SC2`, `RESEARCH Pitfall N`,
quick-task IDs (`261016-fwd`), `REQ-IDs`. They point into `.planning/`, which readers of the code
don't have open, and most refer to closed work.

| Comment shape | Action |
|---|---|
| Tag + non-obvious *why* | Drop the tag, keep the why |
| Tag only, or tag + provenance ("Phase 238: added X") | Delete the comment |
| Tag stands in for a decision ("per D-04") | Replace the tag with the decision itself, in one clause |
| Pointer to an **open** seed for deliberately deferred work | Keep as `(see SEED-NNN)`. Open = file is in `.planning/seeds/`, not `.planning/seeds/closed/` |
| Bug-fix comment (required by CLAUDE.md) | Keep the explanation of what broke and why; drop the tag |

Before:
```python
# Phase 230 D-16: None means unchanged (the repository drops None values),
```
After:
```python
# None means unchanged (the repository drops None values),
```

Before (`frontend/src/hooks/useChessGame.ts`):
```ts
// Phase 210 (SEED-042): this loop was fully unguarded, and chess.js 1.4
// move() throws on illegal SAN. The history comes from sessionStorage, so a
// stale or hand-edited payload (...) would throw straight through the caller.
// Stop at the last legal ply and report that ply, rather than claiming one we never reached.
```
After (the history becomes a rule):
```ts
// chess.js 1.4 move() throws on illegal SAN, and the history comes from
// sessionStorage, so a stale or hand-edited payload (...) must not throw through
// the caller. Stop at the last legal ply and report that ply, rather than
// claiming one we never reached.
```

### 2.2 Content

| Smell | Action |
|---|---|
| Contradicted by the code (outdated) | Fix to match the code. If the *code* looks wrong, don't touch either; flag it as a suspected bug |
| Refers to a function, file, column, component, or flag that no longer exists | Fix or delete (grep before deciding) |
| History narration ("previously", "used to", "was renamed", "retired in") | Rewrite in present tense. Keep history only when it prevents a likely regression, phrased as a rule: "Don't X: Y breaks" |
| Restates the code | Delete |
| Commented-out code | Delete |
| TODO that is done or obsolete | Delete |
| TODO that is real | Keep if actionable in one line; otherwise list it as a seed candidate (don't create seeds) |
| Wrong or stale docstring | Fix; don't add docstrings where none existed |

Don't raise comment density. The only new comment text allowed is the reason that replaces a tag.

Section-divider and banner comments (`# ─── Seam A ───`) stay unless they label code that's gone.

---

## 3. Naming

### 3.1 What counts as a finding

Report a name only if a reader would be **misled or slowed down**, not because another name is
marginally nicer. Churn without clear gain is a rejection.

| Smell | Example |
|---|---|
| Misleading: says X, does/holds Y | `get_games()` that also writes; `flaws` that holds only blunders |
| Stale: the concept was renamed elsewhere (UI, schema, other layer) and this name kept the old term | old feature name in code after a UI rename |
| Inconsistent: one concept, several names across layers or files | see §3.3 glossary |
| Vague: `data`, `info`, `result2`, `tmp`, `handle`, `process`, `do_stuff`, `obj`, `item` in a non-trivial scope | |
| Wrong shape: `_list` that's a dict, plural for a scalar, `get_` for something expensive or side-effecting | |
| Missing unit on a time/size/score quantity | `timeout` (ms or s?), `delta` (cp or score?) |
| Boolean not predicate-shaped | `analysis` for a bool → `is_analyzed` / `hasAnalysis` |
| Unexplained abbreviation outside the domain vocabulary | `cnt`, `prc`, `tmpRes` |

Short names in tiny scopes (`i`, `fen`, `ply`, `cp`, `wdl`, `tc`, lambda args) are fine.

### 3.2 Conventions (match what the codebase already does)

| | Python | TypeScript |
|---|---|---|
| Case | `snake_case`, `PascalCase` classes, `UPPER_SNAKE` constants | `camelCase`, `PascalCase` components and types, `UPPER_SNAKE` module constants |
| Booleans | `is_ / has_ / should_ / can_` | `is / has / should / can` |
| Counts | `<thing>_count` (preferred) or `n_<things>` in math-heavy code | `<thing>Count` |
| Units | `_ms`, `_seconds`, `_cp`; avoid bare `_s` | `Ms`, `Seconds`, `Cp` |
| Hooks | — | `useXyz`; data-shaping hooks `useXyzData` |
| Repos / services | `<entity>_repository.py`, `<domain>_service.py` | — |

Domain vocabulary that needs no expansion: `fen`, `ply`, `cp`, `wdl`, `tc`, `elo`, `pv`, `uci`, `san`,
`pgn`, `acpl`, `maia`, `zobrist`, `eval`.

### 3.3 Glossary

The audit produces a terminology-conflict table (one concept, several names). For each conflict the
owner picks the canonical term; the result is appended here and becomes binding for the rename pass.

| Concept | Canonical | Also seen (to retire) | Decided |
|---|---|---|---|
| _(filled after audit)_ | | | |

---

## 4. Rename mechanics

1. **Classify the blast radius** before renaming:
   - `local`: function or file internal
   - `module`: exported but used in one layer
   - `cross-layer`: crosses backend ↔ frontend, or reaches tests and scripts
   - `contract`: touches §1 → don't rename, flag
2. **Python:** after a rename, grep the old name *as a string* too. ty does not see `getattr`, `text()` SQL,
   Pydantic aliases, JSONB keys, string-keyed dicts, `mock.patch("module.name")` targets, or log `extra=` keys.
3. **TypeScript:** `npm run build` (tsc), not just lint and test, because esbuild strips types.
   Also grep for the old name in `vi.mock(...)` paths and string keys.
4. **File renames:** update imports, `vi.mock` / `mock.patch` paths, and doc references in `docs/`, `CLAUDE.md` files.
5. **One cross-layer rename per commit**, message `refactor(naming): old_name → new_name`.
   Comment cleanup is a separate commit per area: `chore(comments): <area>`.

---

## 5. Process

1. Owner approves this guide and the off-limits list.
2. The audit workflow (`.planning/phases/241-codebase-cleanup/241-audit-workflow.js`) writes `.planning/phases/241-codebase-cleanup/241-INVENTORY.md`.
3. Owner prunes the inventory and fills the §3.3 glossary.
4. Comment cleanup, parallel by area (disjoint files).
5. Local and module renames, per area.
6. Cross-layer renames, one at a time in sequence.
7. Full pre-merge gate, squash-merge between phases (no open feature branches).
