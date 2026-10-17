---
phase: 241-codebase-cleanup
plan: 04
subsystem: tooling
tags: [cleanup, comments, typescript, jsx, css, ts-compiler-api, token-diff]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff/ledger with the fe_support.py plugin hook"
provides:
  - "tools/ts_scan.mjs: TypeScript-compiler-API scanner, modes `prose` and `tokens`, JSON on stdout, source on stdin"
  - "tools/fe_support.py: cleanup.py plugin for .ts/.tsx/.js/.jsx/.css (prose, tokens, directive_heads)"
  - "FE entry slice (main.tsx, instrument.ts, vitest.setup.ts, index.css, components/layout, install, import and their tests) free of planning tags, with ledgers/241-04.txt"
affects: [241-05, 241-06, 241-52, 241-67, 241-70]

actuals:
  tokens: 9000
  tasks: 2
  commits: 2
plan_head_before: ac91cbb7b07b3282d3dbe4459c01f34db7714098
plan_head_after: 164a8a39246f69f046cc052c6d1c271e89390d4f

tech-stack:
  added: []
  patterns:
    - "FE token diff: comments gone, comment-only JSX containers dropped, JSX text reduced to what React renders, describe/it/test titles replaced by <TITLE>"
    - "One node process per (mode, extension, text) per cleanup.py run, memoized with lru_cache (diff reads each file several times)"

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/tools/ts_scan.mjs
    - .planning/phases/241-codebase-cleanup/tools/fe_support.py
    - .planning/phases/241-codebase-cleanup/ledgers/241-04.txt
  modified:
    - frontend/src/instrument.ts
    - frontend/src/main.tsx
    - frontend/src/vitest.setup.ts
    - frontend/src/index.css
    - frontend/src/components/import/ImportBotBubble.tsx
    - frontend/src/components/import/__tests__/ImportBotBubble.test.tsx
    - frontend/src/components/install/InstallPromptBanner.tsx
    - frontend/src/components/install/__tests__/InstallPromptBanner.test.tsx
    - frontend/src/components/layout/SidebarLayout.tsx
    - frontend/src/components/layout/__tests__/panelOpenTracking.test.tsx

key-decisions:
  - "JSX text is merged across dropped comment-only containers and reduced with the Babel/React whitespace rule (trim line edges, drop empty lines, join with one space, then collapse spaces). A same-line single space between two elements is therefore kept as a token, which is stricter than the plan's 'whitespace-only JSX text is dropped' but catches a real rendered change; a whitespace-only run containing a newline renders to nothing and is dropped"
  - "JSX text range is excluded when collecting comments, because ts.getTrailingCommentRanges would otherwise report `// ...` inside JSX text as a comment"
  - "The mutation checks were run on the working tree with file copies in the scratchpad instead of `git checkout --`, because instrument.ts edits were still uncommitted at that point"

patterns-established:
  - "Run the scan/diff/ledger trio per scope; ledger lines for rows outside the scope are written as `#` comments because the ledger parser only accepts plain `INV-L<n>: STATUS` lines"

requirements-completed: [D-10, D-11, D-13, D-14, D-15]

duration: 70min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 04: TypeScript, JSX and CSS Toolkit Support Summary

**`cleanup.py` now scans and token-diffs TypeScript, JSX and CSS through the repo's own TypeScript compiler API, proven on the frontend entry slice where all 34 planning-tag lines (incl. 5 test titles) are gone and the token diff against PHASE_BASE is empty.**

## Performance

- **Duration:** ~70 min
- **Tasks:** 2 (tracer + slice cleanup)
- **Files modified:** 13 (3 created, 10 edited)

## Accomplishments

- `ts_scan.mjs prose` finds line, block, JSDoc and JSX `{/* */}` comments and describe/it/test titles (`it.only`, `test.each(...)`, template titles); `tokens` emits the TypeScript token stream without comments.
- `fe_support.py` wires both into `cleanup.py` (comment records, `test-title` records, directive heads for eslint-disable* with sorted rule lists, `@ts-*`, `@knipignore`, `@vite-ignore`, `prettier-ignore`, istanbul/c8/v8 ignore, biome-ignore) and handles CSS in Python with a string-aware comment stripper.
- First scan of the slice: 34 matches in 14 files. Final `scan --gate --advisory`: 0.
- Planning-tag removal from 9 files; INV-L1068, INV-L1069, INV-L1130 applied after re-verifying against the code; index.css dead reference (INVENTORY §7.1 #39) fixed.

## Task Commits

1. **Task 1 (tracer): ts_scan.mjs + fe_support.py proven on instrument.ts** - `140bd5a28` (`chore(241): toolkit TypeScript, JSX and CSS support`, includes the instrument.ts tag removal)
2. **Task 2: FE entry slice** - `164a8a392` (`chore(comments): frontend entry, layout, install, import`)

`commits: 2` above is measured with `git rev-list --count ac91cbb7b..HEAD` before the SUMMARY commit.

## Commands and exit codes (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-04.txt` | exit 0 (14 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-04.txt` | exit 0 (14 selected, 10 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-04.txt --ledger ledgers/241-04.txt` | exit 0 |
| `cleanup.py diff frontend/src/index.css` (comment-only CSS change) | exit 0 |
| `cleanup.py scan --scope scopes/241-47.txt \| grep -c ':test-title:'` | 165 |
| `ruff check` / `ruff format --check` on tools | clean |
| `npm --prefix frontend run lint` | clean |
| `npm --prefix frontend run build` | `tsc -b` + vite build pass |
| `source_scan_tests.sh` | py 95 + 5 passed, fe 9 files / 131 tests passed (same as the untouched baseline) |
| `npm --prefix frontend test -- src/components/import src/components/install src/components/layout` | 3 files, 17 tests passed |

Step 0 baseline (untouched tree): lint, build and `source_scan_tests.sh` all passed before any edit.

## Mutation checks (not vacuous)

```
# 1. one code token in instrument.ts
$ sed: const FILTERED_QUERY_PLACEHOLDER = "[Filtered]"  ->  "[Filtered2]"
$ cleanup.py diff frontend/src/instrument.ts
frontend/src/instrument.ts:120: - "[Filtered]" / + "[Filtered2]"          exit 1
(restored)  -> diff exit 0

# 2. injected JSX tag comment in components/layout/SidebarLayout.tsx
+        {/* Phase 123 */}
$ cleanup.py scan --gate frontend/src/components/layout/SidebarLayout.tsx
frontend/src/components/layout/SidebarLayout.tsx:166:comment: /* Phase 123 */   (plus 3 real tags, then removed in Task 2)   exit 1
$ cleanup.py diff frontend/src/components/layout/SidebarLayout.tsx            exit 0 (a comment-only addition is not residue)

# 3. deleted existing JSX comment {/* Scrollable content area ... */} (scratch edit)
$ cleanup.py diff frontend/src/components/layout/SidebarLayout.tsx            exit 0
(restored)
```

Spot check that no string literal matches (acceptance item): `cleanup.py scan frontend/src/lib/engine/maiaWorkerHost.ts` lists 65 matches; lines 3 (` * \`/analysis\` consumer (quick 260729-sod, FIX 3).`), 134 (`// Phase 219 (D-08/D-10): ...`) and 221 (`/** Phase 219 (D-10, Pitfall 9): ...`) are all comments, and `git grep` finds no tag outside a comment line in that file. A direct fixture check through `fe_support.prose` (tags inside a plain string, a `data-testid` attribute, a template literal, `trackEvent("D-12-event")`, JSX text) returned only the real comments.

## Rewritten test titles (D-14)

| File | Old | New |
|---|---|---|
| ImportBotBubble.test.tsx | `renders exactly two buttons: btn-signup-why-import-promo and btn-signup-free-import-promo (D-02: no third button)` | `... btn-signup-free-import-promo (no third button)` |
| InstallPromptBanner.test.tsx | `renders nothing on /train (D-07 route suppression)` | `renders nothing on /train (route suppression)` |
| InstallPromptBanner.test.tsx | `renders the drawer on /train when the handoff marker is active (D-11 override)` | `... is active (override)` |
| InstallPromptBanner.test.tsx | `the drawer body makes no notification/reminder/alert/push promise (INSTALL-06)` | `the drawer body makes no notification/reminder/alert/push promise` |
| panelOpenTracking.test.tsx | `fires nothing when mounted already open (D-03)` | `fires nothing when mounted already open` |

No test body or assertion changed.

## Ledger (ledgers/241-04.txt)

- INV-L1068: APPLIED (re-verified: 422s also come from admin_activity.py, bots.py, endgames.py, eval_remote.py)
- INV-L1069: APPLIED (re-verified: 9 hard navigations now, so the "8" was stale; the count is dropped)
- INV-L1130: APPLIED
- INV-L1070 (secondary index.css): APPLIED, kept as a `#` comment line (see Deviations)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `npm --prefix frontend ci` and `uv sync --group maia-inference` (lockfile installs only, no new packages) before the baseline gates; no tracked files changed.

**2. [Plan note] INV-L1070 ledger line is a comment**
- The plan asks for an extra `INV-L1070 (secondary index.css): APPLIED` line, but the ledger parser (`LEDGER_LINE_RE`, cleanup.py, which this plan must not edit) rejects any line that is not `INV-L<n>: STATUS ...`, and `ledger` would exit 1. The line is therefore written as a `# INV-L1070 (secondary index.css): APPLIED ...` comment. The plan that owns ChessBoard.tsx still has to write the real INV-L1070 line for the primary clause.

**3. [Plan note] Stricter JSX whitespace rule**
- See key-decisions: single same-line spaces between JSX elements stay tokens. No false residue occurred in the slice.

**4. [Rule 2 - stale content, §2.2] Small wording fixes next to removed tags**
- ImportBotBubble.test.tsx header said "both variants" while three are tested; now "three variants".
- ImportBotBubble.tsx: dropped "UAT rounds" provenance; "(accepted, S-6)" became "(accepted)".
- index.css: `ARROW_OPACITY` is in `lib/theme.ts`, not ChessBoard.tsx; "360 Human column" became "360 Maia column" (glossary row 61); Train bubble nudge comment no longer cites `TrainScoreScreen.tsx:116,126` line numbers; main.tsx dropped "Growth item 16:".
- vitest.setup.ts and the index.css tour-spotlight comments were rewritten from history narration to present tense.

**Total deviations:** 1 blocking env prep, 3 plan notes/wording; none touch code, testids, Umami names, storage keys or URLs.

## Issues Encountered

- `ts.getTrailingCommentRanges` reports `// ...` inside JSX text as a comment; handled by excluding comment ranges that start inside a JsxText node.
- `JsxText.getText()` strips leading whitespace, so whitespace-only text came back empty and a real inter-element space was dropped; fixed by slicing `sf.text` from `getFullStart()`.
- `SyntaxKind[...]` returns marker aliases (`FirstPunctuation` for `{`); `ts_scan.mjs` prefers the real member name so kinds are stable.
- The worktree sandbox rejected compound shell lines; commands were issued one at a time.

## Known Stubs

None.

## Threat Flags

None. The tools read source from stdin and write only through `apply-edits`' in-scope filter; no packages were added.

## Self-Check: PASSED

Files verified present: tools/ts_scan.mjs, tools/fe_support.py, ledgers/241-04.txt, and the 10 edited frontend files. Commits `140bd5a28` and `164a8a392` are ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
