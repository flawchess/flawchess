---
id: SEED-261107-232
status: dormant
priority: low
planted: 2026-11-07
planted_during: v2.27 (standalone feasibility discussion)
trigger_when: when PWA use among bot players grows, users ask for offline play, or an offline-visit counter shows real demand
scope: small phase (2-2.5 days including device testing, mostly frontend plus one small backend change)
---

# SEED-261107-232: Offline bot play (low priority)

Let a user who has already downloaded the engine keep playing bots with no connection, and upload those games when the connection returns.

## Why This Matters

Bot move selection already runs entirely in the browser, so the cost is modest. Offline computer play is a common feature of chess apps, and it suits installed-PWA users on planes or commutes.

Low priority because there is no sign of demand from FlawChess users, and a web-first product may not inherit a native app's expectations.

### Demand evidence (2026-11-07)

Internal:

- Bot games: 1,562 from 133 players all time; 445 from 55 players in the last 30 days.
- `/bots` sessions, last 90 days: 806 of 5,197 total (16%). Mobile or tablet: 370 of the 805 with a device recorded (46%). Also had a PWA launch: 64 of 805 (8%).
- Feedback mentioning offline: 0 of 27.
- Blind spot: Umami and the database cannot record a failed offline attempt, and 27 feedback entries is too few to conclude anything. This is no evidence of demand, not evidence of no demand.

External:

- Lichess: an update post reportedly called offline computer play "by far our most requested feature", and the official release lists it. The blog returned 403 to fetching, so this comes from search summaries and the wording is unconfirmed.
- Chess.com: forum replies say the apps allow bot play with no connection, and the website has no offline option. A 2024 user asked for offline bot games to save once back online, because that errored at the time (current state unknown).
- Standalone apps market on "offline" (Chess King 10M+ installs band, Chess - Online & Offline 5M+ band, via third-party trackers). That shows a selling point, not usage, since "offline" is also a search keyword.
- No survey found on the share of chess or mobile game sessions played offline.

Sources:

- https://lichess.org/@/Lichess/blog/mobile-app-official-release/wiwu6goO
- https://lichess.org/@/Lichess/blog/lichess-mobile-app-update/VGPcQtN3
- https://lichess.org/forum/lichess-feedback/offline-bots-in-the-android-app-beta
- https://www.chess.com/forum/view/help-support/offline-mode
- https://www.chess.com/clubs/forum/view/suggestions-for-offline-mode-in-android-apps
- https://www.appbrain.com/app/knightmate-chess-puzzles/com.rvmobileappdev.chess.knightmate
- https://www.appbrain.com/app/timepass-chess%C2%AE-play-learn/com.chess.multiplayer

## When to Surface

**Trigger:** PWA use among bot players grows, users ask for offline play, or a counter shows real offline demand.

Cheap first step if the question comes up: a local counter of `/bots` visits made offline, sent after reconnecting. It would replace the blind spot above with a real number before committing to the build. Note that `trackFeature` must not fire on mount (frontend/CLAUDE.md D-03), so this needs a deliberate design.

## Scope Estimate

**Small phase, 2-2.5 days including device testing.** All findings below come from reading the code on 2026-11-07; nothing was run offline. Verify them first.

### Already works offline

- App shell (`html-shell` NetworkFirst route) and precached JS/CSS chunks, including the lazy Bots chunk.
- Maia model, ORT runtime and Stockfish wasm in CacheStorage after first download (`engineAssetCache.ts`, `maia-worker.js`).
- Auth token in localStorage.
- Finished games queue in `botPendingStore.ts`. The drain in `useStoreBotGame.ts` is sequential and removes an entry only on a 2xx or 422. The server is idempotent on `game_uuid`.

### Blockers

1. **Profile gate:** `pages/Bots.tsx:706` renders an error page when `/users/me/profile` fails, and no query is persisted. The snapshot and pending-queue keys use the profile email, so the last profile must be saved locally. Keep the existing guard against reading or draining under the wrong owner key.
2. **Worker scripts uncached:** `maia-worker.js`, the ORT `.js`/`.mjs` files and the Stockfish glue are excluded by `globIgnores` with no runtime route (`vite.config.ts:210`). They need a service worker route. `maia-worker.js` is served `no-cache` on purpose, so it should not be plain CacheFirst.
3. **Static files not precached:** `openings.tsv` (bot opening book), persona `.webp` avatars, `.mp3` sounds. Google Fonts would fall back to system fonts, which is cosmetic.

### Multi-game upload gaps

1. **Wrong game date (backend):** `played_at` is set to server time at upload (`app/services/normalization.py:727`). Offline games would all be dated at reconnect. `enqueuedAt` exists on the client but is not sent. Add an optional request field and have the server reject or clamp implausible values such as future dates.
2. **Oldest games lost:** `MAX_PENDING_STORE_ENTRIES = 10` silently drops the oldest. About 2 KB per entry, so around 50 is safe.
3. **Upload timing:** the drain runs once per `/bots` mount (`hasDrainedRef`). Also run it on the browser `online` event, with a guard against overlapping runs.
4. **Stuck analyze spinner (inferred, test first):** TanStack Query 5 pauses mutations when the browser reports offline, and no `networkMode` is set. `analyzeBusy` (`Bots.tsx:347`) would keep spinning. A paused mutation may also resume by itself on reconnect, while an app launched offline starts with `onlineManager` assuming online and fails immediately, so test both paths.

### Smaller fixes

- Offline state in the post-game dialog, since analysis needs the server.
- A clear message in `EngineReadyGate` when the engine was never downloaded, instead of offering Retry.
- Check that a PWA launch at `/` offline can reach `/bots`, because the Home redirect depends on the profile.

### Risks

- **First use needs a connection:** the device must have logged in (a guest account counts) and downloaded the engine online, about 66 MB on the CPU path.
- **COEP headers:** cached worker scripts must keep COOP/COEP. A stale runtime cache plus missing COEP has already hung threaded ORT silently. This is the main trap.
- **iOS storage:** a comment in `vite.config.ts` cites an iOS Cache API limit of about 50 MB, below that 66 MB. Sentry showed no `engine-asset-cache` issues in 90 days, which is weak evidence. Consider `navigator.storage.persist()` and test on a real iPhone.
- **WebGPU fallback:** falling back from WebGPU to CPU needs a different runtime binary, which may not have been downloaded, so the fallback could fail offline.
- **Main bundle size:** the main JS chunk was about 1.77 MB in a local build, close to Workbox's 2 MiB default precache limit. Above that it is silently left out of the precache, which would break the offline shell.

### Out of scope

The rest of the app keeps showing its normal API errors offline. A true first visit with no connection is not possible.

## Breadcrumbs

- `frontend/vite.config.ts`: VitePWA `globIgnores` and `runtimeCaching`
- `frontend/src/lib/engine/engineAssetCache.ts`: engine asset cache and `?v=` versioning
- `frontend/public/maia/maia-worker.js`: `fetchModelBuffer` cache read
- `frontend/src/lib/engine/stockfishWorkerSource.ts`: Stockfish worker spawn
- `frontend/src/pages/Bots.tsx`: profile gate, drain trigger, `analyzeBusy`
- `frontend/src/hooks/useStoreBotGame.ts`: drain loop
- `frontend/src/lib/botPendingStore.ts`: finished-game queue
- `frontend/src/lib/openings.ts`: fetches `/openings.tsv`
- `frontend/src/lib/sounds.ts`: fetches `/sound/*.mp3`
- `frontend/src/lib/htmlShellCache.ts`: app shell cache
- `app/services/normalization.py`: `played_at` for bot games
- `app/services/store_bot_game_service.py`: bot game store and idempotency

## Notes

Captured after a feasibility and demand discussion on 2026-11-07. Recommendation at capture: do not prioritize now. Build only on the trigger above.
