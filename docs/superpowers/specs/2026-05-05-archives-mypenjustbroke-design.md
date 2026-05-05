# archives.mypenjustbroke.com — Design Spec

**Date:** 2026-05-05
**Status:** Draft, pending user approval
**Author:** Walker Wambsganss (with Claude)

## Goal

Stand up a public, durable mirror of the SimDemocracy wiki at `archives.mypenjustbroke.com`. Source wiki at `qwrky.dev` has gone offline; the only known surviving copy is the dump on the existing Pi (`100.126.251.95:~/wiki-updater/`). This site is the new canonical reading surface for that content.

Static site, no live wiki software, no ongoing server. Frozen snapshot dated 2026-05-05.

## Non-goals

- Public editing or community contributions (this is read-only)
- Recovery of dead images (132 references; sources are gone)
- Recreating MediaWiki features beyond what static HTML supports
- Preserving original `qwrky.dev/mediawiki/index.php/...` URL paths
- Mirroring any wiki content uploaded after 2026-05-05

## Architecture

```
[ Pi 100.126.251.95 ]                 [ Mac (one-time) ]              [ GitHub Pages ]
  ~/wiki-updater/html/      scp →     ~/Documents/archives/    push → mypenjustbroke/archives
  (1324 HTML files)                   build pipeline                   served at
                                      generates output                 archives.mypenjustbroke.com
```

- **Pi**: source-only. No service role. Files are copied off, then the Pi is unrelated to the live site.
- **Mac (`~/Documents/archives/`)**: working directory and git repo. Contains source HTML (gitignored), build script, transformed output (committed), and Pagefind index.
- **GitHub Pages**: serves the repo's `main` branch root. Custom domain via `CNAME` file + Squarespace DNS.
- **DNS**: single `CNAME` record at Squarespace: `archives` → `mypenjustbroke.github.io.`. Apex Google Sites and `outlines.` GitHub Pages are unchanged.

## Source data state

The dump on the Pi has 1324 HTML files in two incompatible formats:

| Format | Count | Origin | State |
|---|---|---|---|
| **Scraper format** | 312 | `wiki_updater.py` (API + custom HTML wrapper, inline minimal CSS) | ✅ Self-contained, renders cleanly |
| **Wget mirror format** | 1012 | Earlier `wget --mirror` against MediaWiki's Timeless skin | ❌ References `../resources/assets/*` and `../load.php?modules=skins.timeless...`; those paths do not exist anywhere; renders unstyled with broken chrome icons |

Plus 132 content image references in wget pages pointing at `../images/X/YY/<file>` — directory does not exist; all dead.

The Pi's `wiki.db` SQLite contains stripped plaintext (search-optimized), not wikitext. No usable wikitext source exists. This is why MediaWiki re-import was ruled out.

## Conversion pipeline

A Python script (`tools/build.py`) runs once locally on the Mac. Idempotent, re-runnable.

### Inputs
- `source-html/` — raw scp from Pi at `~/wiki-updater/html/` (gitignored)
- `tools/template.html` — minimal HTML shell with the same inline CSS the scraper format uses
- `tools/search-snippet.html` — Pagefind UI snippet for site-wide injection

### Steps

1. **Detect format** for each file: scraper format if it contains the marker `max-width: 900px` in the inline `<style>` block; otherwise wget format.

2. **Wget pages** (1012):
   - Parse with BeautifulSoup
   - Extract `<div class="mw-parser-output">` body
   - Discard everything else (Timeless sidebar, header, footer, broken `<link>`, `<script>`, MediaWiki chrome)
   - Strip all `<img>` tags from the body (chrome and content images alike)
   - Extract page title from `<title>` tag (strip `" - SimDemocracy Archives"` suffix if present)
   - Wrap body in `template.html` with extracted title
   - Output to repo root as `<original-filename>.html`

3. **Scraper pages** (312):
   - Already match the target format
   - Strip any `<img>` tags (chrome icons, if present)
   - Output to repo root as `<original-filename>.html`

4. **Link rewriting** (applied to every output file):
   - `https://qwrky.dev/mediawiki/index.php/<Title>` → `/<URL-encoded Title>` (clean URLs; GitHub Pages serves `<Title>.html` at `/<Title>`)
   - `https://qwrky.dev/mediawiki/index.php/Special:*` → strip the `<a>` wrapper, leave the inner text (no replacement target exists)
   - HTML-entity-encoded variants of the above
   - For wget pages, relative links like `./Foo.html`, `Foo.html` → `/Foo`
   - External (non-qwrky) links: untouched

5. **Search box injection** (applied to every output file):
   - Inject a single `<div id="archives-search">` element at the top of `<body>`, before the `<h1>`
   - The element references `/pagefind/pagefind-ui.js` and `/pagefind/pagefind-ui.css`
   - Visually consistent with the page CSS (same font stack, sized to fit)

6. **Index page**:
   - Copy transformed `Main_Page.html` to `index.html` so GitHub Pages serves it at `/`
   - Both `/` and `/Main_Page` resolve to the same content

7. **Pagefind index**:
   - Run `pagefind --site .` from the repo root after all HTML is generated
   - Outputs `pagefind/` directory with JSON shards + UI assets
   - Both transformed pages and Pagefind output get committed

### Idempotence

`build.py` owns the transformed output. On each run it deletes all `*.html` files at repo root and the `pagefind/` directory, then regenerates them. Everything else (`tools/`, `docs/`, `CNAME`, `.gitignore`, `README.md`, `source-html/`) is preserved untouched. `source-html/` is read-only to the build script.

## URL structure

- `archives.mypenjustbroke.com/` → Main_Page (via `index.html`)
- `archives.mypenjustbroke.com/Main_Page` → same
- `archives.mypenjustbroke.com/<Title>` → individual page (GitHub Pages auto-strips `.html`)
- `archives.mypenjustbroke.com/Category:<Name>` → category page (these exist as `Category:<Name>.html` files in the dump)
- `archives.mypenjustbroke.com/pagefind/...` → search index (loaded by client-side search UI)

Special characters in titles (commas, ampersands, parentheses) are kept in filenames and URL-encoded in `href` values.

## Site shell

Each page has the same minimal style (matching the original scraper format):

- Sans-serif body, max-width 900px, light background (`#fafafa`), `#222` text
- Blue (`#3366cc`) links with `border-bottom` h1 of same color
- A small search box element injected at the top of `<body>` — single input, no advanced filters

No site-wide nav bar, no footer, no per-page metadata. The wiki was sparse; the mirror is sparse.

## Search

- **Pagefind** (https://pagefind.app), client-side static search
- Built once at end of `build.py`, ships as `~3-5MB` of JSON shards
- Injected UI on every page via the search box snippet
- No Pi dependency at runtime

## Hosting & DNS

### Repo
- Owner: `mypenjustbroke` (GitHub account)
- Name: `archives`
- Visibility: public (required for free GitHub Pages)
- Branch: `main`, Pages serves from `/`

### Files at repo root (committed)
```
archives/
├── CNAME                 # one line: archives.mypenjustbroke.com
├── .gitignore            # source-html/, .DS_Store, .venv/, __pycache__/
├── README.md             # one-pager: what this is, how to rebuild
├── docs/superpowers/specs/2026-05-05-archives-mypenjustbroke-design.md
├── tools/
│   ├── build.py
│   ├── template.html
│   └── search-snippet.html
├── index.html            # transformed Main_Page (regenerated each build)
├── Main_Page.html        # transformed (regenerated each build)
├── <Title>.html × 1322   # transformed pages (regenerated each build)
├── pagefind/             # generated index (regenerated each build)
└── source-html/          # gitignored — local-only working copy of Pi dump
```

### DNS
At Squarespace, add one record:

- Type: `CNAME`
- Host: `archives`
- Points to: `mypenjustbroke.github.io.`
- TTL: default

Apex `mypenjustbroke.com` (Google Sites) and `outlines.mypenjustbroke.com` (GitHub Pages, separate repo) are unchanged.

### Pages enable
After first push, enable Pages via API:
```
gh api -X POST repos/mypenjustbroke/archives/pages \
  -f 'source[branch]=main' -f 'source[path]=/'
```

HTTPS enforced via the Pages settings UI once cert provisions (5-15 min after DNS verifies).

## Edit policy & future updates

- **No public editing.** Static site.
- **Solo admin** — only the user can push to the repo.
- **Future updates** = re-run `build.py` after refreshing `source-html/` from the Pi (or adding hand-curated content the user wants preserved). Commit and push.
- The Pi's `wiki-updater` daemon will continue to scrape if `qwrky.dev` ever comes back, but in practice the source is dead and the scraper will idle.

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Pandoc-style conversion mistakes break a page's content | Medium | Spot-check 20-30 random transformed pages before deploy. Diff `<div class="mw-parser-output">` extraction against original via `lynx -dump` text comparison on a sample. |
| Title-with-special-chars 404s on GitHub Pages | Medium | Test 5-10 worst-case filenames (commas, ampersands, parentheses) before declaring done. |
| Cert provisioning stalls | Low | Standard waiting; Pages docs cover this. |
| Pi backup goes bad before we copy | Low (but irrecoverable if it does) | scp from Pi as Step 1; verify checksum match between Pi and Mac copies before doing anything else. |
| Pagefind index too large or slow on first load | Low | Corpus is small (31MB raw HTML). Pagefind typically yields ~10-20% of corpus size. Acceptable. |
| Transformed page renders wrong vs. original | Medium | Manual comparison of a sample of 10 wget-format pages, side-by-side, before bulk commit. |

## Out of scope (explicitly deferred)

- **Image recovery** via Wayback Machine or alternative archives. Possible future enhancement; not blocking v1.
- **Live MediaWiki** at any URL. Reconsidered if ever the user wants editable archive.
- **Better search UX** (filters, category browsing, advanced operators). Pagefind defaults are adequate for v1.
- **Pretty per-namespace handling** (Category:, Talk:, User:). Treated as plain pages for v1.
- **Custom 404 page**. Default GitHub Pages 404 acceptable; can add later.
- **Inbound link rewriting** for the user's Obsidian vault and published opinions, which still cite `qwrky.dev/mediawiki/index.php/...`. Tracked separately.

## Open questions

None. All decisions are made. (Self-review confirmed during spec write — see commit message for reviewer notes.)
