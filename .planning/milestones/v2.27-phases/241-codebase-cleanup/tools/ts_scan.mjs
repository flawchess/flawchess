#!/usr/bin/env node
// TypeScript-compiler-API scanner for the Phase 241 cleanup toolkit.
//
//   node ts_scan.mjs prose  <virtual-path>   source on stdin
//   node ts_scan.mjs tokens <virtual-path>   source on stdin
//
// prose  -> {"comments":[{line,col,endLine,endCol,text}], "titles":[{line,col,text}]}
// tokens -> [[kind, text, line], ...]   (comments gone; see below for what else is normalized)
//
// Run from the checkout root: TypeScript is resolved from frontend/node_modules (the TS6
// package installed as `typescript`). Exit 2 when it is missing.
//
// tokens normalization (these are the only things that make two token streams equal when the
// source differs):
//   - comments are not tokens;
//   - a JSX container that holds nothing but a comment (`{/* c */}`) is dropped with its braces;
//   - JSX text is merged across dropped containers and reduced to what React renders (the Babel
//     rule: trim line edges, drop empty lines, join with one space), then whitespace-collapsed;
//     text that renders to nothing is dropped;
//   - a describe/it/test title literal is emitted as `<TITLE>` (D-14: titles are prose).

import { createRequire } from "node:module";
import path from "node:path";

const EXIT_USAGE = 2;
const TITLE_PLACEHOLDER = "<TITLE>";
const TITLE_ROOTS = new Set(["describe", "it", "test", "suite", "bench"]);

function loadTypeScript() {
  try {
    return createRequire(path.join(process.cwd(), "frontend", "package.json"))("typescript");
  } catch {
    process.stderr.write("ts_scan: cannot load TypeScript; run npm --prefix frontend ci\n");
    process.exit(EXIT_USAGE);
  }
}

const ts = loadTypeScript();

function readStdin() {
  return new Promise((resolve, reject) => {
    const chunks = [];
    process.stdin.on("data", (c) => chunks.push(c));
    process.stdin.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    process.stdin.on("error", reject);
  });
}

function scriptKindFor(virtualPath) {
  const ext = path.extname(virtualPath).toLowerCase();
  if (ext === ".tsx") return ts.ScriptKind.TSX;
  if (ext === ".jsx") return ts.ScriptKind.JSX;
  if (ext === ".js" || ext === ".mjs" || ext === ".cjs") return ts.ScriptKind.JS;
  return ts.ScriptKind.TS;
}

// SyntaxKind has marker aliases (FirstPunctuation = OpenBraceToken, LastTemplateToken, ...):
// prefer the real member name so token kinds read the same everywhere.
const KIND_NAMES = new Map();
for (const [name, value] of Object.entries(ts.SyntaxKind)) {
  if (typeof value !== "number") continue;
  const isMarker = /^(First|Last)/.test(name) && !/^(FirstStatement|LastStatement)/.test(name);
  if (!KIND_NAMES.has(value) || (!isMarker && /^(First|Last)/.test(KIND_NAMES.get(value)))) {
    KIND_NAMES.set(value, name);
  }
}

function isJsDocNode(node) {
  return node.kind >= ts.SyntaxKind.FirstJSDocNode && node.kind <= ts.SyntaxKind.LastJSDocNode;
}

function forEachNode(node, sf, visit) {
  visit(node);
  for (const child of node.getChildren(sf)) {
    if (!isJsDocNode(child)) forEachNode(child, sf, visit);
  }
}

// --- test titles ---------------------------------------------------------------------------

// describe, it.only, test.each([...]) ... : an identifier, or a property chain / call rooted at one.
function rootedAtTestFunction(expr) {
  let cur = expr;
  for (;;) {
    if (ts.isIdentifier(cur)) return TITLE_ROOTS.has(cur.text);
    if (ts.isPropertyAccessExpression(cur) || ts.isElementAccessExpression(cur)) {
      cur = cur.expression;
    } else if (ts.isCallExpression(cur)) {
      cur = cur.expression;
    } else if (ts.isTaggedTemplateExpression(cur)) {
      cur = cur.tag;
    } else {
      return false;
    }
  }
}

function titleArgument(node) {
  if (!ts.isCallExpression(node) || !rootedAtTestFunction(node.expression)) return null;
  const first = node.arguments[0];
  if (!first) return null;
  if (
    ts.isStringLiteral(first) ||
    ts.isNoSubstitutionTemplateLiteral(first) ||
    ts.isTemplateExpression(first)
  ) {
    return first;
  }
  return null;
}

function collectTitles(sf) {
  const titles = [];
  forEachNode(sf, sf, (node) => {
    const arg = titleArgument(node);
    if (arg) titles.push(arg);
  });
  return titles;
}

// The literal pieces of a title: the literal itself, or the head/middle/tail of a template.
function titleLiteralNodes(titleRoots) {
  const set = new Set();
  for (const root of titleRoots) {
    if (ts.isTemplateExpression(root)) {
      set.add(root.head);
      for (const span of root.templateSpans) set.add(span.literal);
    } else {
      set.add(root);
    }
  }
  return set;
}

// --- prose ---------------------------------------------------------------------------------

function lineCol(sf, pos) {
  const { line, character } = sf.getLineAndCharacterOfPosition(pos);
  return { line: line + 1, col: character + 1 };
}

function jsxTextRanges(sf) {
  const ranges = [];
  forEachNode(sf, sf, (node) => {
    if (node.kind === ts.SyntaxKind.JsxText) ranges.push([node.getFullStart(), node.end]);
  });
  return ranges;
}

function proseMode(sf, text) {
  const textRanges = jsxTextRanges(sf);
  const insideJsxText = (pos) => textRanges.some(([lo, hi]) => pos >= lo && pos < hi);
  const seen = new Map();
  const add = (ranges) => {
    for (const r of ranges ?? []) {
      if (!seen.has(r.pos) && !insideJsxText(r.pos)) seen.set(r.pos, r);
    }
  };
  forEachNode(sf, sf, (node) => {
    if (node.kind === ts.SyntaxKind.JsxText) return;
    if (node.getChildren(sf).length > 0 && node.kind !== ts.SyntaxKind.EndOfFileToken) return;
    // Leaf token: its leading trivia, and the same-line trivia after the previous token end.
    add(ts.getLeadingCommentRanges(text, node.getFullStart()));
    add(ts.getTrailingCommentRanges(text, node.end));
  });
  const comments = [...seen.values()]
    .sort((a, b) => a.pos - b.pos)
    .map((r) => {
      const start = lineCol(sf, r.pos);
      const end = lineCol(sf, r.end);
      return {
        line: start.line,
        col: start.col,
        endLine: end.line,
        endCol: end.col,
        text: text.slice(r.pos, r.end),
      };
    });
  const titles = collectTitles(sf).map((root) => {
    const start = lineCol(sf, root.getStart(sf));
    const raw = root.getText(sf);
    return { line: start.line, col: start.col, text: raw.slice(1, -1) };
  });
  return { comments, titles };
}

// --- tokens --------------------------------------------------------------------------------

// What React renders for a JSX text run (Babel cleanJSXElementLiteralChild), then collapsed.
function renderedJsxText(raw) {
  const lines = raw.split(/\r\n|\n|\r/);
  const last = lines.length - 1;
  let out = "";
  lines.forEach((line, i) => {
    let s = line.replace(/\t/g, " ");
    if (i !== 0) s = s.replace(/^ +/, "");
    if (i !== last) s = s.replace(/ +$/, "");
    if (s) {
      if (i !== last) s += " ";
      out += s;
    }
  });
  return out.replace(/ +/g, " ");
}

function isCommentOnlyJsxContainer(node) {
  return node.kind === ts.SyntaxKind.JsxExpression && !node.expression && !node.dotDotDotToken;
}

function tokensMode(sf, text) {
  const titleLiterals = titleLiteralNodes(collectTitles(sf));
  const out = [];
  const lineOf = (node) => sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
  const kindName = (node) => KIND_NAMES.get(node.kind);

  function emitLeaf(node) {
    if (node.kind === ts.SyntaxKind.EndOfFileToken) return;
    const name = kindName(node);
    if (titleLiterals.has(node)) {
      out.push([name, TITLE_PLACEHOLDER, lineOf(node)]);
    } else {
      out.push([name, node.getText(sf), lineOf(node)]);
    }
  }

  function visitChildren(parent) {
    let pending = null; // {raw, line} JSX text run being merged across dropped containers
    const flush = () => {
      if (!pending) return;
      const rendered = renderedJsxText(pending.raw);
      if (rendered) out.push(["JsxText", rendered, pending.line]);
      pending = null;
    };
    for (const child of parent.getChildren(sf)) {
      if (isJsDocNode(child)) continue;
      if (child.kind === ts.SyntaxKind.JsxText) {
        // getText() skips leading whitespace trivia, which is exactly what JSX text is made of.
        const raw = text.slice(child.getFullStart(), child.end);
        pending = pending ? { raw: pending.raw + raw, line: pending.line } : { raw, line: lineOf(child) };
        continue;
      }
      if (isCommentOnlyJsxContainer(child)) continue;
      flush();
      visit(child);
    }
    flush();
  }

  function visit(node) {
    if (node.getChildren(sf).length === 0) {
      if (node.kind !== ts.SyntaxKind.SyntaxList) emitLeaf(node);
      return;
    }
    visitChildren(node);
  }

  visit(sf);
  return out;
}

// --- main ----------------------------------------------------------------------------------

async function main() {
  const [mode, virtualPath] = process.argv.slice(2);
  if ((mode !== "prose" && mode !== "tokens") || !virtualPath) {
    process.stderr.write("usage: ts_scan.mjs <prose|tokens> <virtual-path>  (source on stdin)\n");
    process.exit(EXIT_USAGE);
  }
  const text = await readStdin();
  const sf = ts.createSourceFile(
    virtualPath,
    text,
    ts.ScriptTarget.Latest,
    /* setParentNodes */ true,
    scriptKindFor(virtualPath),
  );
  const result = mode === "prose" ? proseMode(sf, text) : tokensMode(sf, text);
  process.stdout.write(JSON.stringify(result));
}

main();
