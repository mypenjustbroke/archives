# archives.mypenjustbroke.com — Design Spec

**Date:** 2026-05-05
**Status:** Draft, pending user approval
**Author:** Walker Wambsganss (with Claude)

## Goal

Stand up a public, durable mirror of the SimDemocracy wiki at `archives.mypenjustbroke.com`. Source wiki at `qwrky.dev` has gone offline. The user has the full MediaWiki XML export (1333 pages, all namespaces incl. templates and categories, wikitext source). The Pi's HTML dump and DB are no longer needed as sources — the XML is authoritative.

Static site, no live wiki software at runtime, no ongoing server. Frozen snapshot dated 2026-05-05.

## Source data

`/Users/walkerwambsganss/Downloads/SimDemocracy+Archives-20260505192744.xml`

- 6.3 MB, MediaWiki 1.43 export, schema 0.11
- 1333 pages, one revision each (current state)
- Namespaces present: Main (0), Project space "SimDemocracy Archives" (4), File (6), Template (10), Category (14)
- Wikitext content, lossless
- **Media binaries not included.** All file references will render as broken-image placeholders by MediaWiki (clean visual: a styled "file not found" link, not a red-X).

## Non-goals

- Public editing or community contributions (read-only static)
- Recovery of dead media files
- Recreating MediaWiki features beyond what static HTML supports (no edit, no recent-changes)
- Mirroring any wiki content created after the snapshot timestamp
- Running live MediaWiki at runtime — it exists only during the local build

## Architecture

```
[ Mac (one-time, local) ]                                    [ GitHub Pages ]
                                                              mypenjustbroke/archives
  Docker compose:                                             ├ static HTML (1333+ pages)
    ├─ MediaWiki 1.43 (matches export version)                ├ skin assets (Vector)
    └─ MariaDB                                                ├ CNAME archives.mypenjustbroke.com
       │                                                      └ pagefind/ index
       ├ importDump.php   (XML → wikitext in DB)
       ├ rebuildall.php   (rebuild links, categories, search)
       ├ wget --mirror    (locally crawl every page → static HTML)
       └ post-process     (rewrite internal links, build Pagefind index)
                                                                   ▲
                                                                   │ git push
       output: ~/Documents/archives/site/    ─────────────────────┘
```

- **Build host**: Mac. Conversion is one-shot, idempotent, and reproducible.
- **Container stack**: Docker Compose with two services (MediaWiki + MariaDB). Spec'd in `docker-compose.yml` at the repo root. Volumes are local-only and torn down after build.
- **Skin**: MediaWiki Vector (default). Visually clean, well-supported, all assets resolve under wget mirroring.
- **Static output**: committed to repo root, served by GitHub Pages.
- **DNS**: single `CNAME` at Squarespace, `archives` → `mypenjustbroke.github.io.`. Apex Google Sites and `outlines.` Pages are unchanged.

## Build pipeline

Single Python orchestration script (`tools/build.py`) drives everything. Idempotent — safe to re-run. Steps:

### 1. Spin up the wiki container

```
docker compose up -d
```

`docker-compose.yml` defines:
- `mariadb:10.11` with persistent volume `./.docker/db/`
- `mediawiki:1.43` with mounted `LocalSettings.php` enabling required maintenance scripts and the Vector skin

Wait for MediaWiki to be ready (poll `http://localhost:8080/api.php?action=siteinfo` until 200).

### 2. Import the XML dump

Inside the container:
```
php maintenance/importDump.php < /import/SimDemocracy-Archives.xml
php maintenance/rebuildall.php
```

`rebuildall.php` rebuilds the links table, recent changes, and search index — without it, internal `[[wikilinks]]` won't resolve correctly in rendered HTML.

### 3. Mirror the local wiki

```
wget --mirror \
     --page-requisites \
     --convert-links \
     --adjust-extension \
     --no-parent \
     --no-host-directories \
     --execute robots=off \
     --directory-prefix=site/ \
     http://localhost:8080/wiki/Main_Page
```

Plus follow-up wgets for each non-Main namespace root (Special:AllPages enumeration, Categories, Templates) so nothing is missed by the link-following crawl.

### 4. Post-process (`tools/postprocess.py`)

UI stripping uses defense-in-depth: `LocalSettings.php` disables interactive features at the MediaWiki layer (so wget never captures most of them), and post-process catches any remnants. Specifically:

- **Strip MediaWiki UI artifacts** that don't make sense in a frozen static archive: edit links (`?action=edit`), watch links, history tabs, Special:RecentChanges sidebar items, login/account-creation links. Talk-page tabs are kept (talk pages exist in namespace 1, valuable as discussion record).
- **Strip broken file links**: `<a href="...File:...">` for files we know are missing → leave plain text.
- **Inject site notice**: a single banner at the top of every page reading "Archive of the SimDemocracy wiki, snapshot 2026-05-05. Read-only." (style matches the Vector skin).
- **Build Pagefind index** (`pagefind --site site/`): client-side search, ships as `~3-5 MB` of JSON. UI snippet injected into a sidebar element on every page.

### 5. Tear down

```
docker compose down
```

Database volume retained at `.docker/db/` (gitignored) so re-running the build is fast (skip import if XML hasn't changed).

## URL structure

MediaWiki + wget produces URLs of the form `/wiki/<Title>` (with the leading `wiki/` from the MediaWiki article path). Pages, categories, and templates all live under there:

- `/wiki/Main_Page`
- `/wiki/Abuse_of_Process_Act_2025`
- `/wiki/Category:Legislation`
- `/wiki/Template:Stub`

The site root `/` redirects to `/wiki/Main_Page` via a generated `index.html` containing a `<meta http-equiv="refresh">`.

Special characters in titles (commas, ampersands, parentheses) are preserved as-is; wget URL-encodes them in `href` values during `--convert-links`.

## Site shell

Vector skin (MediaWiki default). Includes:
- Site logo (placeholder unless we add one — defaults to MediaWiki sunflower)
- Search box (top-right, native — but we'll replace it with the Pagefind UI)
- Page tabs (Article / Talk / Read / View source / Edit) — Edit/Source stripped during post-process
- Sidebar: Main page, Recent changes (stripped), Random page, Help (stripped)
- Footer: Privacy / About / Disclaimers (replaced with snapshot date + link to source)

Site notice added: read-only banner at top of every page.

## Search

- **Pagefind** (https://pagefind.app), client-side static search
- Replaces MediaWiki's built-in search box (which doesn't work statically)
- ~3-5 MB index, served from `/pagefind/`
- Native MediaWiki search box's `<form>` is replaced during post-process with the Pagefind UI element

## Hosting & DNS

### Repo
- Owner: `mypenjustbroke`
- Name: `archives`
- Visibility: public (required for free GitHub Pages)
- Branch: `main`, Pages serves from `/`

### Repo layout
```
~/Documents/archives/
├── CNAME                            # archives.mypenjustbroke.com
├── .gitignore                       # .docker/, *.xml, source files, .DS_Store, .venv/, __pycache__/, site/-internal-junk
├── README.md                        # rebuild instructions, snapshot notes
├── docs/superpowers/specs/2026-05-05-archives-mypenjustbroke-design.md
├── docker-compose.yml               # MediaWiki + MariaDB
├── LocalSettings.php                # MediaWiki config for build container
├── tools/
│   ├── build.py                     # orchestrator
│   ├── postprocess.py               # strip UI, inject notice, build pagefind
│   └── import.xml                   # symlink to the actual XML (gitignored)
├── index.html                       # redirect to /wiki/Main_Page
├── wiki/                            # mirrored static HTML, 1333+ files
│   ├── Main_Page
│   ├── Abuse_of_Process_Act_2025
│   ├── Category:Legislation
│   └── ...
├── load.php                         # MediaWiki CSS/JS resources (wget'd)
├── resources/                       # skin assets
└── pagefind/                        # generated search index
```

### DNS
At Squarespace, add one record:
- Type: `CNAME`
- Host: `archives`
- Points to: `mypenjustbroke.github.io.`
- TTL: default

### Pages enable
After first push:
```
gh api -X POST repos/mypenjustbroke/archives/pages \
  -f 'source[branch]=main' -f 'source[path]=/'
```

Enforce HTTPS via the Pages settings UI once the cert provisions.

## Edit policy & future updates

- **No public editing.** Static.
- **Solo admin** — only the user pushes to repo.
- **Future updates** = drop a fresh XML into `tools/import.xml`, run `python tools/build.py`, commit, push. Or hand-edit individual `wiki/*.html` files for one-off fixes (with the caveat that re-running the build clobbers them — anything hand-edited should be reflected in the post-process script instead).

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Docker MediaWiki version doesn't match XML schema (1.43 / 0.11) | High | Pin `mediawiki:1.43` image. Schema 0.11 is supported all the way back to 1.27, so even minor pinning slop is fine. |
| `wget --mirror` misses pages not linked from Main_Page | Medium | After the recursive mirror, run a second pass enumerating `Special:AllPages` per namespace (Main, Category, Template, Project) to ensure full coverage. Verify with `find site/wiki/ -name "*.html" \| wc -l` >= 1333. |
| MediaWiki UI elements (edit, watch, history) leak through to public site | Medium | Post-process strips them. Test on 5-10 pages before deploy. Also consider configuring `LocalSettings.php` to disable login/edit at the UI level so wget never captures those elements in the first place. |
| Pagefind UI styled inconsistently with Vector skin | Low | Tweak Pagefind UI CSS to match Vector colors. Cosmetic only. |
| Broken file links render ugly | Low | MediaWiki's missing-file placeholder is already visually clean ("Image of X — file not found" link). Better than the previous broken-`<img>` situation. |
| Repo size from skin assets | Low | Vector skin is small (<1MB). Pagefind index ~5MB. Total well within GitHub repo limits. |
| First-time wget against fresh MediaWiki picks up a "Welcome to the Wiki" install page | Low | Verify install is complete + XML imported before wget runs (build.py polls). |
| Title with `:` (e.g. `Category:Legislation`) breaks on some filesystems | Low (mac/linux/Pages OK) | Tested through GitHub Pages; works. macOS HFS+/APFS allow `:` in URLs (though display as `/` in Finder). |

## Out of scope (explicitly deferred)

- **Image recovery** via Wayback Machine. Possible future enhancement.
- **Live MediaWiki** at any URL. Reconsidered if user ever wants editable archive.
- **Better search UX** (advanced filters, scoped search). Pagefind defaults are adequate for v1.
- **Custom 404 page**. Default GitHub Pages 404 acceptable.
- **Inbound link rewriting** for the user's Obsidian vault and published opinions still citing `qwrky.dev`. Tracked separately.
- **Skin customization** beyond the read-only post-process. Vector default is fine.

## Open questions

None. All decisions are made.
