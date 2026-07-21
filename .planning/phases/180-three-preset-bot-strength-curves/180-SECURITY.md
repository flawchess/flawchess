---
phase: 180
slug: three-preset-bot-strength-curves
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-07-21
---

# Phase 180 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| TSV file -> fitter | Harness-emitted aggregated WDL TSV read from local disk (developer-produced, not untrusted) and fitted into a published downstream artifact | Local measurement data, no user data |
| local engine subprocesses -> harness | Harness spawns local Stockfish/ONNX-Maia subprocesses and reads UCI/policy output; no network, no untrusted external input | Engine eval/policy output, local only |
| prior ledger TSV -> resume | `--resume` reads a developer-produced raw ledger from local disk | Local measurement data |
| bot-curves JSON -> SEED-104 | Published internal-scale artifact (`reports/data/bot-curves-internal-scale.json`) consumed by a future phase | Derived ratings on the internal scale |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-180-01 | Tampering | internalRatingFor on a malformed/unknown anchor token | low | mitigate | Fail-loud throw on any label absent from INTERNAL_RATING (`scripts/lib/calibration-bot-cell-schedule.mjs:66-72`) | closed |
| T-180-02 | Tampering | fit_bot_cell_rating / load_bot_cells on a corrupted or mis-keyed TSV | medium | mitigate | Fail-loud ValueError on empty games / missing anchor label / missing column (`scripts/calibration_anchor_fit.py:479-546`); covered by `tests/scripts/test_calibration_anchor_fit.py::test_fit_bot_cell_rating_rejects_bad_input` | closed |
| T-180-03 | Information Disclosure | bot-curves JSON mis-read downstream as human ELO | low | mitigate | `_caveat: INTERNAL_SCALE_HEADER` written verbatim into the JSON header (`scripts/calibration_anchor_fit.py:382,722`) | closed |
| T-180-04 | Tampering | internalRatingFor on a malformed anchor token from --anchors | low | mitigate | Same fail-loud throw path as T-180-01 (Plan 01 module) — a bad token cannot silently degrade to the nominal-scale bug | closed |
| T-180-05 | Tampering | --resume replaying a corrupted/mismatched ledger | low | mitigate | Ledger replay validates grid membership, games-count, and budget on fast-forward; guards asserted in `scripts/lib/calibration-pruning.check.mjs` | closed |
| T-180-06 | Information Disclosure | bot-curves JSON / findings note mis-read downstream as human ELO | low | mitigate | Caveat present in the shipped `reports/data/bot-curves-internal-scale.json` `_caveat` header ("INTERNAL SCALE — NOT human ELO (D-13)") | closed |
| T-180-07 | Denial of Service | a killed multi-hour operator sweep loses all progress | low | mitigate | `--resume` from the durable raw ledger (harness + `bin/run_bot_curves_sweep.sh`); `bin/preset-supervisor.sh` self-heals wasm crashes via append-mode resume | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-21 | 7 | 7 | 0 | gsd-secure-phase (L1 short-circuit: plan-time register, all mitigations evidenced) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-21

Scope note: phase 180 is a scripts-only local calibration harness (Node .mjs + Python stdlib CLI). It adds no network endpoints, auth paths, secrets, or persisted user data; no `app/` or `frontend/` code changed.
