export const meta = {
  name: 'codebase-cleanup-audit',
  description: 'Read-only naming + comment audit per area, adversarial verify, write INVENTORY.md',
  whenToUse: 'Before the codebase cleanup pass; produces the inventory the owner prunes',
  phases: [
    { title: 'Audit', detail: 'one reader per area, reads every non-test file' },
    { title: 'Verify', detail: 'one skeptic per area: refute findings, measure blast radius' },
    { title: 'Synthesize', detail: 'dedupe across areas, glossary conflicts, write INVENTORY.md' },
  ],
}

// Run: Workflow({ scriptPath: 'temp/codebase-cleanup/audit-workflow.js' })
// Optional args: { includeScripts: true, only: ['backend-repositories'] }
// Agent count: 10 audit + up to 10 verify + 1 synthesis (+2 with includeScripts).

const ROOT = '/home/aimfeld/Projects/Python/flawchess'
const GUIDE = `${ROOT}/temp/codebase-cleanup/STYLE-GUIDE.md`
const OUT = `${ROOT}/temp/codebase-cleanup/INVENTORY.md`
const FE_EXCLUDE = "exclude __tests__/ dirs and *.test.ts(x) files"

const ALL_PARTITIONS = [
  { key: 'backend-surface', paths: 'app/routers/, app/schemas/, app/models/, app/core/, app/*.py' },
  { key: 'backend-repositories', paths: 'app/repositories/' },
  { key: 'services-eval-engine', paths: 'app/services/{eval_*,engine,maia_*,best_move_candidates,accuracy_acpl,position_classifier,sharp_filler,zobrist,score_confidence}.py' },
  { key: 'services-insights-stats', paths: 'app/services/{insights_*,endgame_*,opening*,stats_service,activity_*,canonical_slice_sql,percentile_compute_registry,global_percentile_cdf,user_benchmark_percentiles_service,current_strength_service}.py' },
  { key: 'services-import-train-tactics', paths: 'app/services/{import_service,normalization,chesscom_*,lichess_client,train_*,library_service,bot_game_pgn,store_*,guest_*,push_*,email_service,feedback_*,admin_service,tactic_*,forcing_line_gate,flaws_service,flaw_delta_zones}.py, plus any app/services/*.py not matched by the other services partitions' },
  { key: 'fe-components-train-analysis-bots', paths: `frontend/src/components/{train,analysis,bots}/ (${FE_EXCLUDE})` },
  { key: 'fe-components-data-views', paths: `frontend/src/components/{library,endgames,insights,charts,results,stats}/ (${FE_EXCLUDE})` },
  { key: 'fe-components-rest-and-root', paths: `every other frontend/src/components/ subdir and top-level file, plus top-level frontend/src/*.ts(x) (${FE_EXCLUDE})` },
  { key: 'fe-hooks', paths: `frontend/src/hooks/ (${FE_EXCLUDE})` },
  { key: 'fe-pages-api-types-lib', paths: `frontend/src/pages/, frontend/src/api/, frontend/src/types/, frontend/src/lib/ incl. lib/engine and lib/personas (${FE_EXCLUDE}; skip frontend/src/generated/)` },
]
const SCRIPT_PARTITIONS = [
  { key: 'scripts-a-m', paths: 'scripts/[a-m]*.py (skip scripts/archive/)' },
  { key: 'scripts-n-z', paths: 'scripts/[n-z]*.py (skip scripts/archive/)' },
]

const opts = args || {}
let partitions = ALL_PARTITIONS.concat(opts.includeScripts ? SCRIPT_PARTITIONS : [])
if (opts.only) partitions = partitions.filter(p => opts.only.includes(p.key))
if (!opts.includeScripts) log('scripts/ not audited (pass includeScripts: true); tests/, analysis/, stories/ are out of scope by design')

const NAMING_SMELLS = ['misleading', 'stale', 'inconsistent', 'vague', 'wrong-shape', 'missing-unit', 'non-predicate-bool', 'abbreviation']
const COMMENT_SMELLS = ['outdated', 'dead-reference', 'history-narration', 'restates-code', 'commented-out-code', 'stale-todo', 'wrong-docstring']
const SCOPES = ['local', 'module', 'cross-layer', 'contract']

const AUDIT_SCHEMA = {
  type: 'object',
  properties: {
    naming: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          line: { type: 'integer' },
          symbol: { type: 'string' },
          kind: { type: 'string', enum: ['function', 'class', 'variable', 'parameter', 'constant', 'type', 'field', 'component', 'hook', 'file', 'module'] },
          smell: { type: 'string', enum: NAMING_SMELLS },
          proposed: { type: 'string' },
          rationale: { type: 'string' },
        },
        required: ['file', 'line', 'symbol', 'kind', 'smell', 'proposed', 'rationale'],
      },
    },
    comments: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          line: { type: 'integer' },
          smell: { type: 'string', enum: COMMENT_SMELLS },
          excerpt: { type: 'string' },
          evidence: { type: 'string', description: 'what in the code contradicts it or proves the reference dead' },
          suggestion: { type: 'string', description: 'replacement text, or "delete"' },
        },
        required: ['file', 'line', 'smell', 'excerpt', 'evidence', 'suggestion'],
      },
    },
    terms: {
      type: 'array',
      description: 'one concept, several names (within this area or vs. names you know from elsewhere)',
      items: {
        type: 'object',
        properties: {
          concept: { type: 'string' },
          names_seen: { type: 'array', items: { type: 'string' } },
          locations: { type: 'array', items: { type: 'string' } },
        },
        required: ['concept', 'names_seen', 'locations'],
      },
    },
    seed_candidates: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, line: { type: 'integer' }, summary: { type: 'string' } }, required: ['file', 'line', 'summary'] } },
    suspected_bugs: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, line: { type: 'integer' }, summary: { type: 'string' } }, required: ['file', 'line', 'summary'] } },
    coverage: {
      type: 'object',
      properties: {
        files_in_scope: { type: 'integer' },
        files_read_fully: { type: 'integer' },
        files_skipped: { type: 'array', items: { type: 'string' } },
        notes: { type: 'string' },
      },
      required: ['files_in_scope', 'files_read_fully', 'files_skipped'],
    },
  },
  required: ['naming', 'comments', 'terms', 'seed_candidates', 'suspected_bugs', 'coverage'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    naming: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          index: { type: 'integer' },
          verdict: { type: 'string', enum: ['accept', 'modify', 'reject'] },
          final_name: { type: 'string' },
          scope: { type: 'string', enum: SCOPES },
          blast_radius: { type: 'array', items: { type: 'string' }, description: 'files referencing the symbol, incl. tests/, scripts/, frontend' },
          string_occurrences: { type: 'array', items: { type: 'string' }, description: 'file:line where the old name appears as a string (mock paths, SQL, JSON keys, getattr)' },
          reason: { type: 'string' },
        },
        required: ['index', 'verdict', 'scope', 'blast_radius', 'string_occurrences', 'reason'],
      },
    },
    comments: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          index: { type: 'integer' },
          verdict: { type: 'string', enum: ['accept', 'modify', 'reject', 'suspected-bug'] },
          final_suggestion: { type: 'string' },
          reason: { type: 'string' },
        },
        required: ['index', 'verdict', 'reason'],
      },
    },
  },
  required: ['naming', 'comments'],
}

const auditPrompt = p => `You are auditing one area of the FlawChess codebase for a naming + comment cleanup.
READ-ONLY: do not edit, create, stage or commit anything.
Repo root: ${ROOT}. All paths below are relative to it; run every shell command from there.

First read ${GUIDE} in full. It defines what counts as a finding, the off-limits contracts (§1),
the comment policy (§2) and naming smells (§3). Apply it literally.

Area: ${p.key}
Paths: ${p.paths}

Method:
1. Enumerate the files with \`git ls-files\` (respecting the path patterns and exclusions above).
2. Read EVERY file in full (chunk large files with offset/limit). Do not sample. Report coverage honestly;
   list anything you could not read in files_skipped.
3. Report:
   - naming: names that mislead or slow a reader down (§3.1). Not "marginally nicer" names. For each, give a
     concrete proposed name following §3.2. Do include names that touch an off-limits contract if they are
     genuinely misleading; the verifier will classify them as 'contract'.
   - comments: outdated, dead-reference, history-narration, restates-code, commented-out-code, stale-todo,
     wrong-docstring (§2.2). Give evidence from the code (for dead-reference: the grep that came back empty).
   - DO NOT report bare planning tags (Phase NNN, D-NN, SEED-NNN, ...). Those are handled mechanically by the §2.1
     policy. Report a tagged comment only if its CONTENT is also wrong or stale.
   - terms: concepts that go by several names (e.g. one idea called X in the model, Y in the service, Z in the UI).
   - seed_candidates: real TODOs too big for a one-line fix.
   - suspected_bugs: only incidental, where a comment and the code disagree and the code looks wrong. Don't hunt bugs.
Precision matters more than volume: every finding will be checked by a skeptic and rejected if unsupported.`

const verifyPrompt = (p, audit) => `You are the skeptic for a codebase cleanup audit of area "${p.key}" (${p.paths}).
READ-ONLY: do not edit, create, stage or commit anything. Repo root: ${ROOT} (run commands from there).
First read ${GUIDE} (§1 off-limits, §3 naming, §4 mechanics).

Below are the auditor's findings. Try to REFUTE each one. Default to reject when uncertain: a rename that
isn't clearly better is churn, and a comment that might be correct stays.

For each NAMING finding (by index):
- Check the claim against the code. Is the current name actually misleading/stale/vague, or is it fine?
- Is the proposed name clearly better, consistent with neighbors and §3.2, and collision-free? Improve it if not (verdict 'modify').
- Measure the blast radius with grep over the WHOLE repo (app/, frontend/src/, tests/, scripts/, docs/, alembic/):
  list referencing files, and separately every place the old name appears as a string (mock.patch / vi.mock
  targets, SQL text, JSON/JSONB keys, getattr, Pydantic aliases, log extra keys).
- Classify scope: local | module | cross-layer | contract. 'contract' if any reference touches a §1 item
  (DB column/table, persisted enum value, worker protocol, public API field/path, Sentry/Umami names,
  storage keys, URL params, data-testid, env/config key, generated file, LLM prompt string).
For each COMMENT finding (by index):
- Verify the evidence. Re-run the grep for dead references. If the comment is right and the code looks wrong,
  verdict 'suspected-bug'. Tighten the suggested replacement if needed (final_suggestion).

Findings (JSON):
${JSON.stringify({ naming: audit.naming.map((f, index) => ({ index, ...f })), comments: audit.comments.map((f, index) => ({ index, ...f })) })}`

phase('Audit')
const perArea = await pipeline(
  partitions,
  p => agent(auditPrompt(p), { label: `audit:${p.key}`, phase: 'Audit', schema: AUDIT_SCHEMA }),
  (audit, p) => {
    if (!audit) return null
    const cov = audit.coverage
    if (cov.files_skipped.length) log(`${p.key}: ${cov.files_skipped.length} file(s) not fully read: ${cov.files_skipped.join(', ')}`)
    if (!audit.naming.length && !audit.comments.length) return { p, audit, verdicts: { naming: [], comments: [] } }
    return agent(verifyPrompt(p, audit), { label: `verify:${p.key}`, phase: 'Verify', schema: VERDICT_SCHEMA })
      .then(verdicts => ({ p, audit, verdicts }))
  },
)

const done = perArea.filter(Boolean)
const failed = partitions.filter(p => !done.some(d => d.p.key === p.key)).map(p => p.key)
if (failed.length) log(`NOT COVERED (agent failed or skipped): ${failed.join(', ')}`)

// Join verdicts back onto findings. A finding with no verdict (verifier died) is kept as 'unverified'.
const naming = []
const comments = []
const rejected = { naming: 0, comments: 0 }
for (const { p, audit, verdicts } of done) {
  const nv = new Map((verdicts?.naming || []).map(v => [v.index, v]))
  const cv = new Map((verdicts?.comments || []).map(v => [v.index, v]))
  audit.naming.forEach((f, i) => {
    const v = nv.get(i)
    if (v && v.verdict === 'reject') { rejected.naming++; return }
    naming.push({ area: p.key, ...f, verdict: v ? v.verdict : 'unverified', final_name: v?.final_name || f.proposed, scope: v?.scope || 'unknown', blast_radius: v?.blast_radius || [], string_occurrences: v?.string_occurrences || [], verify_reason: v?.reason || '' })
  })
  audit.comments.forEach((f, i) => {
    const v = cv.get(i)
    if (v && v.verdict === 'reject') { rejected.comments++; return }
    comments.push({ area: p.key, ...f, verdict: v ? v.verdict : 'unverified', final_suggestion: v?.final_suggestion || f.suggestion, verify_reason: v?.reason || '' })
  })
}
log(`kept ${naming.length} naming / ${comments.length} comment findings; skeptics rejected ${rejected.naming} / ${rejected.comments}`)

// Cross-area grouping key: same identifier in snake_case and camelCase (backend field ↔ frontend type) collapses.
const norm = s => s.replace(/[_-]/g, '').toLowerCase()
const groups = {}
for (const f of naming) (groups[norm(f.symbol)] ||= []).push(f)
const crossArea = Object.values(groups).filter(g => new Set(g.map(f => f.area)).size > 1).map(g => g[0].symbol)

const terms = done.flatMap(d => d.audit.terms.map(t => ({ area: d.p.key, ...t })))
const seeds = done.flatMap(d => d.audit.seed_candidates.map(s => ({ area: d.p.key, ...s })))
const bugs = done.flatMap(d => d.audit.suspected_bugs.map(b => ({ area: d.p.key, ...b })))
  .concat(comments.filter(c => c.verdict === 'suspected-bug').map(c => ({ area: c.area, file: c.file, line: c.line, summary: c.verify_reason })))
const coverage = done.map(d => ({ area: d.p.key, ...d.audit.coverage }))

phase('Synthesize')
const summary = await agent(`Write the cleanup inventory to ${OUT} (overwrite). This file is the ONLY thing you may write.
Read ${GUIDE} first for vocabulary. Owner reads this to decide what to apply, so make it scannable.

Structure:
1. Summary: counts by area and by category; coverage table (files in scope vs read fully, skipped files);
   areas not covered: ${JSON.stringify(failed)}; skeptic rejections: ${JSON.stringify(rejected)}.
2. Glossary conflicts: merge the 'terms' lists across areas into one table (concept | names seen | where |
   suggested canonical term). Suggest, don't decide; this feeds STYLE-GUIDE §3.3.
3. Cross-layer renames: group naming findings that refer to the same concept across areas (hint: these symbols
   recur in several areas: ${JSON.stringify(crossArea)}), plus every finding with scope 'cross-layer'.
   One row per rename: old → new | scope | blast radius file count | string occurrences | why.
4. Contract-blocked names: scope 'contract'. Listed for awareness only, not to apply.
5. Local/module renames, grouped by area (table).
6. Comment fixes, grouped by area then category (file:line | smell | current excerpt | replacement).
7. Seed candidates and suspected bugs (verbatim lists, no action).
Mark 'unverified' findings clearly. Keep every finding; don't drop or cap anything silently.

Return a 5-line plain-text summary of the counts.

DATA (JSON):
${JSON.stringify({ naming, comments, terms, seeds, bugs, coverage })}`, { label: 'synthesize', phase: 'Synthesize' })

return { summary, out: OUT, failed, rejected, counts: { naming: naming.length, comments: comments.length, terms: terms.length, seeds: seeds.length, bugs: bugs.length } }
