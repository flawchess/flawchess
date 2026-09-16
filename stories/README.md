# FlawChess Data Stories (GitHub Pages)

Public, interactive data stories published at **https://stories.flawchess.com/**
(GitHub Pages with a custom domain; `flawchess.github.io/flawchess/*` 301-redirects there).
This directory is the site source: `.github/workflows/pages.yml` runs `stories/stage.sh`
on every push to `main` that touches `stories/**` and deploys the staged result. Only the
story directories listed in `stories/published.txt` are staged; everything else on `main`
stays offline (see "Publishing a story" below).

DNS: `stories` CNAME `flawchess.github.io` in Cloudflare, **DNS-only (grey cloud)** —
GitHub provisions and renews the TLS certificate itself, which requires seeing the
CNAME directly; Pages is already a CDN, so proxying adds nothing. The custom domain
is set in the repo's Pages settings (`gh api repos/flawchess/flawchess/pages`), not
via a CNAME file (that mechanism is for branch-based builds, not workflow deploys).

## Layout

```
stories/
  index.html          # landing page listing all stories
  logo.png            # shared FlawChess logo (stories reference ../logo.png)
  social-card.png     # 1200x630 Open Graph image for the landing page
  sitemap.xml         # lists the landing page + every story URL
  robots.txt          # allow-all + sitemap pointer
  published.txt       # allowlist of story slugs the workflow deploys; unlisted dirs stay offline
  stage.sh            # builds the deployable site from published.txt (used by CI, runnable locally)
  two-pawns-up/       # one directory per story -> flawchess.github.io/flawchess/two-pawns-up/
    index.html        # self-contained page: inline CSS/JS, vanilla SVG charts, no CDNs
    social-card.png   # 1200x630 Open Graph image for this story
    two-pawns-up-report-latest.md  # the technical report the story summarizes
```

## Adding a story

1. Create `stories/<slug>/index.html` (kebab-case slug; it becomes the URL).
   Keep it self-contained: inline styles/scripts, no external dependencies, and put
   the underlying numbers in the page (plus a `<details>` data table per chart).
2. Add a card for it in `stories/index.html`.
3. Co-locate the technical report it summarizes as `stories/<slug>/<slug>-report.md`
   and link it (GitHub blob URL) in the story footer.
4. Iterate locally by opening the file in a browser. Merging the study branch to `main`
   does **not** publish anything yet.

## Publishing a story

Publishing is one explicit commit on `main`:

1. Add the slug to `stories/published.txt`.
2. Add the landing-page card in `stories/index.html` (and its JSON-LD `blogPost` entry) and
   the URL in `stories/sitemap.xml`. The deploy fails if either references an unlisted slug,
   so these cannot go live ahead of the allowlist.
3. Push; the Pages workflow deploys in about a minute. Check the run with `gh run list`.

Preview exactly what a push would deploy: `bash stories/stage.sh stories /tmp/site &&
python3 -m http.server -d /tmp/site`. To take a story offline, reverse step 1 and 2; the
directory can stay in the repo.

Conventions: see `stories/CLAUDE.md` for the full ruleset (branding/header, publication
dates, terminology, chart styling, report co-location).
