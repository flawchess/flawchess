#!/usr/bin/env node
// Real-build invariants for the PWA stale-build fix (quick 261107-dnz).
//
// Run after `npm run build`. Reads dist/ and fails non-zero unless:
//   - dist/version.json parses and carries a non-empty buildId;
//   - dist/index.html references the entry chunk /assets/index-*.js and that
//     chunk contains the SAME build ID literally. A bundle/version.json ID
//     split would reload every client on every resume, so it must never reach
//     a release. (An unused literal is tree-shaken, so this also proves
//     main.tsx still wires installBuildVersionCheck.)
//   - the sw.js precache list is non-empty and contains no .html entry and no
//     version.json entry (the version check must always see the network);
//
// Node built-ins only. No network, no browser.

import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DIST_DIR = path.join(__dirname, "..", "dist");

const failures = [];
const fail = (message) => failures.push(message);

function readDist(relativePath) {
  const full = path.join(DIST_DIR, relativePath);
  if (!existsSync(full)) {
    fail(`dist/${relativePath} is missing (run npm run build first)`);
    return null;
  }
  return readFileSync(full, "utf8");
}

function checkVersionAndEntry() {
  const versionRaw = readDist("version.json");
  const indexHtml = readDist("index.html");
  if (versionRaw === null || indexHtml === null) return;

  let buildId = null;
  try {
    const parsed = JSON.parse(versionRaw);
    if (typeof parsed.buildId === "string" && parsed.buildId !== "") buildId = parsed.buildId;
  } catch {
    // reported below
  }
  if (buildId === null) {
    fail("dist/version.json is not JSON with a non-empty string buildId");
    return;
  }

  const entryMatch = indexHtml.match(/src="(\/assets\/index-[^"]+\.js)"/);
  if (entryMatch === null) {
    fail('dist/index.html has no src="/assets/index-*.js" entry chunk reference');
    return;
  }
  const entry = readDist(entryMatch[1].slice(1));
  if (entry !== null && !entry.includes(buildId)) {
    fail(`entry chunk ${entryMatch[1]} does not contain build ID ${buildId} (bundle and version.json disagree, or main.tsx no longer calls installBuildVersionCheck)`);
  }
}

function checkServiceWorker() {
  const sw = readDist("sw.js");
  if (sw === null) return;

  const precacheUrls = [...sw.matchAll(/url:"([^"]+)"/g)].map((m) => m[1]);
  if (precacheUrls.length === 0) fail("dist/sw.js precache list is empty or unparseable");
  for (const url of precacheUrls) {
    if (url.endsWith(".html")) fail(`dist/sw.js precaches an HTML file: ${url}`);
    if (url.includes("version.json")) fail(`dist/sw.js precaches ${url}`);
  }

  for (const needle of ["cacheKeyWillBeUsed", "/__html-shell__", 'cacheName:"html-shell"']) {
    if (!sw.includes(needle)) fail(`dist/sw.js does not contain ${needle}`);
  }
}

checkVersionAndEntry();
checkServiceWorker();

if (failures.length > 0) {
  console.error("check-pwa-build FAILED:");
  for (const message of failures) console.error(`  - ${message}`);
  process.exit(1);
}
console.log("check-pwa-build OK");
