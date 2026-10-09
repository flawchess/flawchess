# Phase 232 API Coverage

Dependency-upgrade phase. The only external surface is the Sentry browser SDK, already integrated before this phase; the major bump keeps the existing usage and does not widen data collection (D-03).

| capability | decision | reason |
|---|---|---|
| Sentry error capture via SDK envelope transport | INTEGRATE | |
| Sentry browser tracing / performance | OPT-OUT | Not used before the upgrade; adding it is out of phase scope |
| Sentry session replay | OPT-OUT | Not used; would widen data collection, violating D-03 |
| Sentry user feedback widget | OPT-OUT | Not used; out of phase scope |
| Sentry logs / metrics / profiling | OPT-OUT | Not used; out of phase scope |
| Sentry source-map upload | OPT-OUT | Deliberately deferred to SEED-189 |
