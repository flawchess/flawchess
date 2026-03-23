---
phase: quick
plan: 260323-rtg
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/public/icons/icon-192.png
  - frontend/public/icons/icon-512.png
  - frontend/public/icons/icon-maskable-512.png
  - frontend/public/icons/apple-touch-icon.png
  - frontend/vite.config.ts
autonomous: false
requirements: []
must_haves:
  truths:
    - "Android PWA adaptive icon does not clip the horse character's magnifying glass or edges"
    - "iOS home screen icon shows the horse character with proper padding"
    - "Browser favicon and tab icon remain unchanged"
    - "Manifest declares separate any and maskable icon entries"
  artifacts:
    - path: "frontend/public/icons/icon-192.png"
      provides: "192x192 icon with padding, transparent bg"
    - path: "frontend/public/icons/icon-512.png"
      provides: "512x512 icon with padding, transparent bg"
    - path: "frontend/public/icons/icon-maskable-512.png"
      provides: "512x512 maskable icon with #0a0a0a bg, content in safe zone"
    - path: "frontend/public/icons/apple-touch-icon.png"
      provides: "180x180 apple touch icon with padding"
  key_links:
    - from: "frontend/vite.config.ts"
      to: "frontend/public/icons/"
      via: "manifest icons array"
      pattern: "icon-maskable-512"
---

<objective>
Generate padded PWA icons from the source logo so Android adaptive icon masks (circle/squircle) no longer clip the horse character. Create separate "any" (transparent bg) and "maskable" (solid bg, safe zone) icon variants, and update the manifest accordingly.

Purpose: Fix clipped app icon on Android PWA installs
Output: New icon files + updated vite.config.ts manifest
</objective>

<context>
@frontend/vite.config.ts
@logo/flawchess-logo-portrait-1280x1280.png (source image - horse on black bg)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Generate padded icon variants using ImageMagick</name>
  <files>
    frontend/public/icons/icon-192.png
    frontend/public/icons/icon-512.png
    frontend/public/icons/icon-maskable-512.png
    frontend/public/icons/apple-touch-icon.png
  </files>
  <action>
Use ImageMagick `convert` to generate all icon variants from `logo/flawchess-logo-portrait-1280x1280.png`.

**"any" icons (transparent background, ~68% content):**

For each size (192, 512):
1. Resize the source to ~68% of target size (e.g., for 512: resize to 348x348)
2. Place centered on a transparent canvas of target size
3. Save as icon-{size}.png

Command pattern:
```
convert logo/flawchess-logo-portrait-1280x1280.png \
  -resize 348x348 \
  -gravity center \
  -background none \
  -extent 512x512 \
  frontend/public/icons/icon-512.png
```

For 192: resize to 131x131, extent 192x192.

**"maskable" icon (solid #0a0a0a background, content in 80% safe zone):**

The maskable safe zone is a centered circle of 80% diameter. To keep content comfortably inside, scale character to ~66% of canvas:
```
convert logo/flawchess-logo-portrait-1280x1280.png \
  -resize 338x338 \
  -gravity center \
  -background '#0a0a0a' \
  -extent 512x512 \
  frontend/public/icons/icon-maskable-512.png
```

**Apple touch icon (180x180, with padding, solid bg):**

Apple applies its own corner rounding. Use solid #0a0a0a background with ~70% content:
```
convert logo/flawchess-logo-portrait-1280x1280.png \
  -resize 126x126 \
  -gravity center \
  -background '#0a0a0a' \
  -extent 180x180 \
  frontend/public/icons/apple-touch-icon.png
```

Do NOT modify favicon.ico.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && identify frontend/public/icons/icon-192.png frontend/public/icons/icon-512.png frontend/public/icons/icon-maskable-512.png frontend/public/icons/apple-touch-icon.png 2>&1 | grep -E "192x192|512x512|180x180"</automated>
  </verify>
  <done>All four icon files exist at correct dimensions. icon-192 and icon-512 have transparent backgrounds. icon-maskable-512 and apple-touch-icon have #0a0a0a backgrounds. Character is visibly padded from edges in all variants.</done>
</task>

<task type="auto">
  <name>Task 2: Update manifest to use separate any and maskable icon entries</name>
  <files>frontend/vite.config.ts</files>
  <action>
In `frontend/vite.config.ts`, update the `icons` array in the PWA manifest config (around line 24-36). Replace the current two-entry array with:

```typescript
icons: [
  {
    src: '/icons/icon-192.png',
    sizes: '192x192',
    type: 'image/png',
    purpose: 'any',
  },
  {
    src: '/icons/icon-512.png',
    sizes: '512x512',
    type: 'image/png',
    purpose: 'any',
  },
  {
    src: '/icons/icon-maskable-512.png',
    sizes: '512x512',
    type: 'image/png',
    purpose: 'maskable',
  },
],
```

Key change: The old config had `purpose: 'any maskable'` on the 512 icon (combined purpose). Split into separate entries so Android uses the maskable variant (with safe-zone padding) while browsers/iOS use the "any" variant (transparent bg). The 192 icon gets explicit `purpose: 'any'`.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && npx vite build --mode development 2>&1 | tail -5</automated>
  </verify>
  <done>Manifest icons array has three entries: 192 any, 512 any, 512 maskable. Build succeeds without errors.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>Padded PWA icons with separate maskable variant for Android adaptive icons</what-built>
  <how-to-verify>
    1. Run `npm run dev` in frontend/
    2. Open Chrome DevTools > Application > Manifest — verify three icon entries appear
    3. Visually inspect the generated icons in `frontend/public/icons/`:
       - icon-192.png: transparent bg, horse centered with padding
       - icon-512.png: transparent bg, horse centered with padding
       - icon-maskable-512.png: dark bg (#0a0a0a), horse centered with extra padding for safe zone
       - apple-touch-icon.png: dark bg, horse centered with padding
    4. Use https://maskable.app/editor to upload icon-maskable-512.png and verify the character fits within all mask shapes (circle, squircle, rounded rect)
    5. Optionally: deploy and re-install PWA on Android to confirm no clipping
  </how-to-verify>
  <resume-signal>Type "approved" or describe issues with the icon appearance</resume-signal>
</task>

</tasks>

<verification>
- All icon files at correct dimensions (identify command)
- Vite build succeeds
- Manifest has three separate icon entries with correct purpose values
- Maskable icon passes maskable.app safe zone check
</verification>

<success_criteria>
- Android adaptive icon masks no longer clip the horse character
- iOS apple-touch-icon shows padded character
- Manifest correctly separates "any" and "maskable" purposes
- Build succeeds, no regressions
</success_criteria>

<output>
After completion, create `.planning/quick/260323-rtg-create-better-android-and-ios-app-icons-/260323-rtg-SUMMARY.md`
</output>
