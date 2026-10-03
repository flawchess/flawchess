# Override 2026-10-02: review documentation after the accept rule

**Decided by:** the owner, 2026-10-02 (chat approval during Phase 227 execution).
**Rule affected:** `accept-rule.md` section 1, content assertion 2. The rule file itself is not edited.

## What happened

Content assertion 2 runs `git diff --name-only R I -- . ':!.planning'` and allows only the six files Plan 227-10
lists, plus the comment-only `docs(227-09): reword harness comments` commit. After the rule was committed (`R` =
`7fb704a65`), a third, confirmation round of independent design review ran, because two round-2 repairs had changed
the loop sketch and no reviewer had seen them. Its record was committed in `652cfdeb9`:

- `reports/continuous-dispatch-227/design.md`: section 7 rows R3A-1..5 and R3B-1..8, small text repairs, and the
  round-3 SOUND lines.
- `reports/continuous-dispatch-227/reviews/r3-a.md` and `r3-b.md`: the raw reviews.

These are documentation under `reports/`, not code. Assertion 1 already excludes `reports/`; assertion 2 does not.

## The override

Assertion 2 additionally permits changes to documentation files under `reports/continuous-dispatch-227/` (Markdown
only: `design.md`, `reviews/*.md`, and override documents like this one). The check at gate start becomes:

```bash
git diff --name-only R I -- . ':!.planning' ':!reports/continuous-dispatch-227/*.md' ':!reports/continuous-dispatch-227/reviews/*.md'
```

which must list only the files assertion 2 already names. Every other part of the rule is unchanged: no harness,
pool, provider, verdict-twin or frontend file outside Plan 227-10's six may change between `R` and `I`, and
`accept-rule.md` itself must not change.
