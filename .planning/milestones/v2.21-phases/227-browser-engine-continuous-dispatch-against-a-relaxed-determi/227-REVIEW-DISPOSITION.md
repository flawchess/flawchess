# 227 Review Disposition

Source: `227-REVIEW.md` (standard depth, 35 files; 0 critical, 1 warning, 4 info). Fixes in commit `a5dc20be1`.

| ID | Severity | Disposition | Note |
|---|---|---|---|
| WR-01 | warning | fixed | `evaluate_mq_report_only` raises `IncompleteDataError` when an arm has no rows, so the cell reads `unreadable`; 3 parametrized tests, mutation-checked (fail without the guard). Gates verdict on committed data unchanged. |
| IN-01 | info | fixed | `useBotGame.ts` / `useFlawChessEngine.ts` comments now say `'continuous'` since the ship decision. |
| IN-02 | info | fixed | `FLAWCHESS_BOT_CONCURRENCY` doc: exact reproducibility only in round mode. |
| IN-03 | info | fixed | `dispatch-mode.mjs`, `dispatch-mode.check.mjs`, `engine-move-quality.mjs`, `engine-dispatch-stop-rule.mjs` headers reworded to past tense. |
| IN-04 | info | wont-fix | Docstring is accurate (`N_rs` is a signed per-pair net, the max takes its absolute value) and `math.ceil` mirrors the accept rule's formula verbatim; the twin's frozen rule text is kept as written. |
