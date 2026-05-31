"""Deterministic benchmark-report generator internals (SEED-029, Phase A).

The CLI entry point is `scripts/gen_benchmarks.py`; the per-chapter computation and
rendering live here so each SKILL.md section is independently importable and testable
(mirroring the `scripts.* <- tests/scripts/*` convention). Shared SQL building blocks
and pure stat helpers live in `sql.py`; markdown table rendering in `render.py`; one
module per chapter (`chapter1`, ...).
"""
