"""Frontend plugin for tools/cleanup.py (Phase 241, plan 241-04).

cleanup.py loads this module lazily for .ts/.tsx/.js/.jsx/.css files and calls:

    prose(path, text)          -> [(line, col, end_line, end_col, kind, text)]
    tokens(path, text)         -> [(kind, text, line)]
    directive_heads(records)   -> multiset of lint/type directive heads in comments

TypeScript, JSX and JS are parsed by tools/ts_scan.mjs (the repo's TypeScript compiler API, so
JSX `{/* */}` containers, JSDoc and describe/it/test titles come out right). CSS is handled here
with a small string-aware comment stripper.

Record kinds: "comment" for every comment, "test-title" for a describe/it/test title (D-14).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path, PurePosixPath

TOOLS_DIR = Path(__file__).resolve().parent
TS_SCAN = TOOLS_DIR / "ts_scan.mjs"
TS_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
CSS_SUFFIXES = {".css"}
NODE_EXIT_USAGE = 2
CSS_TOKEN_KIND = "CssWord"

ProseRecord = tuple[int, int, int, int, str, str]
TokenRecord = tuple[str, str, int]


class FrontendToolError(RuntimeError):
    """ts_scan.mjs failed or printed something unreadable."""


def _checkout_root() -> Path:
    """The checkout root: cleanup.py's ROOT when it is loaded, else derived from this file."""
    cleanup = sys.modules.get("cleanup") or sys.modules.get("__main__")
    root = getattr(cleanup, "ROOT", None)
    if isinstance(root, Path):
        return root
    return TOOLS_DIR.parents[3]


@lru_cache(maxsize=512)
def _run_ts_scan(mode: str, suffix: str, text: str, root: str) -> object:
    """Run ts_scan.mjs once per (mode, suffix, text); the diff reads each file several times."""
    proc = subprocess.run(
        ["node", str(TS_SCAN), mode, f"virtual{suffix}"],
        input=text.encode("utf-8"),
        capture_output=True,
        cwd=root,
        check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip()
        hint = " (run npm --prefix frontend ci)" if proc.returncode == NODE_EXIT_USAGE else ""
        raise FrontendToolError(f"ts_scan.mjs {mode} failed{hint}: {detail}")
    try:
        return json.loads(proc.stdout.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise FrontendToolError(f"ts_scan.mjs {mode} printed invalid JSON: {exc}") from exc


def _ts(mode: str, path: str, text: str) -> object:
    suffix = PurePosixPath(path).suffix.lower()
    return _run_ts_scan(mode, suffix, text, str(_checkout_root()))


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

# A string is matched (and kept) before a comment so `content: "/* x */"` is not a comment.
CSS_SPAN_RE = re.compile(
    r"""(?P<str>"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*')|(?P<comment>/\*.*?\*/)""",
    re.DOTALL,
)


def _line_col(text: str, pos: int) -> tuple[int, int]:
    line = text.count("\n", 0, pos) + 1
    col = pos - (text.rfind("\n", 0, pos) + 1) + 1
    return line, col


def _css_prose(text: str) -> list[ProseRecord]:
    records: list[ProseRecord] = []
    for m in CSS_SPAN_RE.finditer(text):
        if m.group("comment") is None:
            continue
        line, col = _line_col(text, m.start())
        end_line, end_col = _line_col(text, m.end())
        records.append((line, col, end_line, end_col, "comment", m.group("comment")))
    return records


def _css_tokens(text: str) -> list[TokenRecord]:
    stripped = CSS_SPAN_RE.sub(lambda m: m.group(0) if m.group("str") else " ", text)
    out: list[TokenRecord] = []
    for lineno, row in enumerate(stripped.split("\n"), start=1):
        out.extend((CSS_TOKEN_KIND, word, lineno) for word in row.split())
    return out


# ---------------------------------------------------------------------------
# Plugin surface
# ---------------------------------------------------------------------------


def prose(path: str, text: str) -> list[ProseRecord]:
    if PurePosixPath(path).suffix.lower() in CSS_SUFFIXES:
        return _css_prose(text)
    result = _ts("prose", path, text)
    assert isinstance(result, dict)
    records: list[ProseRecord] = [
        (c["line"], c["col"], c["endLine"], c["endCol"], "comment", c["text"])
        for c in result["comments"]
    ]
    for t in result["titles"]:
        records.append((t["line"], t["col"], t["line"], t["col"], "test-title", t["text"]))
    records.sort(key=lambda r: (r[0], r[1]))
    return records


def tokens(path: str, text: str) -> list[TokenRecord]:
    if PurePosixPath(path).suffix.lower() in CSS_SUFFIXES:
        return _css_tokens(text)
    result = _ts("tokens", path, text)
    assert isinstance(result, list)
    return [(kind, string, line) for kind, string, line in result]


ESLINT_RE = re.compile(
    r"\b(eslint-disable-next-line|eslint-disable-line|eslint-disable|eslint-enable)\b([^\n]*)"
)
SIMPLE_DIRECTIVE_RES = (
    re.compile(r"@ts-(?:expect-error|ignore|nocheck)\b"),
    re.compile(r"@knipignore\b"),
    re.compile(r"@vite-ignore\b"),
    re.compile(r"\bprettier-ignore\b"),
    re.compile(r"\b(?:istanbul|c8|v8) ignore (?:next|if|else|file|start|stop)\b"),
    re.compile(r"\bbiome-ignore(?:-all|-start|-end)?\b[^\n:]*"),
)
ESLINT_REASON_SEP = " -- "


def _eslint_head(keyword: str, rest: str) -> str:
    rules_text = rest.split(ESLINT_REASON_SEP, 1)[0]
    rules_text = rules_text.replace("*/", " ").strip()
    rules = sorted(r.strip() for r in rules_text.split(",") if r.strip())
    return keyword if not rules else f"{keyword} {', '.join(rules)}"


def directive_heads(prose_records: Sequence[ProseRecord]) -> Counter[str]:
    """Multiset of lint/type directive heads in comments; a rewritten comment must keep them."""
    heads: Counter[str] = Counter()
    for rec in prose_records:
        if rec[4] != "comment":
            continue
        text = rec[5]
        for m in ESLINT_RE.finditer(text):
            heads[_eslint_head(m.group(1), m.group(2))] += 1
        for rx in SIMPLE_DIRECTIVE_RES:
            for m in rx.finditer(text):
                heads[" ".join(m.group(0).split())] += 1
    return heads
