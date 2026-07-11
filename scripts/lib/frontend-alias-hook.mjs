#!/usr/bin/env node
/**
 * frontend-alias-hook.mjs — Node module-customization hook rewriting `@/...`
 * specifiers to `frontend/src/*.ts`, so headless scripts under scripts/*.mjs
 * can import the LIVE frontend TypeScript source with zero new packages
 * (Phase 165 D-03; RESEARCH Q5 "Option D — native type-stripping + tiny `@/`
 * resolve hook").
 *
 * Usage: node --import ./scripts/lib/frontend-alias-hook.mjs <script.mjs>
 *
 * This hook only rewrites the specifier — it relies on Node v24's default-on
 * TypeScript type-stripping to actually load the resolved `.ts` file. Every
 * OTHER specifier (bare package names, relative imports, etc.) is delegated
 * unchanged to `nextResolve`. `chess.js` (a bare specifier imported by the
 * aliased `.ts` files) resolves natively because those `.ts` files physically
 * live under `frontend/src`, so Node's normal upward node_modules walk finds
 * `frontend/node_modules/chess.js` from there — no extra handling needed here.
 *
 * A future non-erasable edit (enum/namespace/parameter property) to one of
 * the imported frontend modules would break type-stripping; the gem-parity
 * check (scripts/lib/gem-parity.check.mjs) is the tripwire that catches this
 * before a full calibration run (T-165-02).
 */
import { registerHooks } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** Absolute path to frontend/src — the root that `@/...` specifiers resolve against. */
const FRONTEND_SRC = path.resolve(__dirname, '../../frontend/src');

/** The alias prefix mirrored from frontend/vite.config.ts + frontend/tsconfig.json. */
const ALIAS_PREFIX = '@/';

registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier.startsWith(ALIAS_PREFIX)) {
      const relativePath = specifier.slice(ALIAS_PREFIX.length);
      const absolutePath = path.join(FRONTEND_SRC, `${relativePath}.ts`);
      return { url: pathToFileURL(absolutePath).href, shortCircuit: true };
    }
    return nextResolve(specifier, context);
  },
});
