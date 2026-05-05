# archives.mypenjustbroke.com Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a frozen-snapshot static mirror of the SimDemocracy wiki at `archives.mypenjustbroke.com` from the user-supplied 6.3 MB MediaWiki XML export.

**Architecture:** One-shot local build on Mac — Docker Compose stands up MediaWiki 1.43 + MariaDB, imports XML, then `wget --mirror` produces clean static HTML. Output is post-processed (UI stripping, site notice, Pagefind injection) and pushed to GitHub Pages.

**Tech Stack:** Docker Compose, MediaWiki 1.43, MariaDB 10.11, Python 3 (orchestrator + post-processor), wget, Pagefind, GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-05-05-archives-mypenjustbroke-design.md`

**Working directory:** `~/Documents/archives/`

---

## File Structure

```
~/Documents/archives/
├── CNAME                            # Custom domain for Pages
├── README.md                        # How to rebuild the site
├── .gitignore                       # already exists; extended in Task 1
├── docker-compose.yml               # MediaWiki + MariaDB stack
├── LocalSettings.php                # MediaWiki config (read-only, no edit UI)
├── docs/
│   ├── superpowers/specs/2026-05-05-archives-mypenjustbroke-design.md
│   └── superpowers/plans/2026-05-05-archives-mypenjustbroke.md (this file)
├── tools/
│   ├── build.py                     # Orchestrator: container → import → mirror → post → pagefind
│   ├── postprocess.py               # HTML mutation: strip UI, inject notice, swap search box
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_postprocess.py      # Unit tests for postprocess functions
│   │   └── fixtures/                # Sample HTML fragments for tests
│   └── import.xml                   # symlink → ~/Downloads/SimDemocracy+Archives-*.xml (gitignored)
├── index.html                       # Generated redirect to /wiki/Main_Page (regenerated each build)
├── wiki/                            # wget output: ~1333 HTML pages (regenerated each build)
├── load.php                         # MediaWiki CSS/JS bundles (wget'd, regenerated each build)
├── resources/                       # Skin assets (regenerated each build)
└── pagefind/                        # Pagefind index (regenerated each build)
```

**Responsibilities:**
- `build.py` — orchestrates phases; idempotent; logs each step
- `postprocess.py` — pure HTML transforms, fully unit-tested
- `docker-compose.yml` — pinned versions, deterministic env
- `LocalSettings.php` — disables interactive features at the MW layer (defense in depth with postprocess)
- `tests/` — unit tests for postprocess functions only; container/wget/pagefind verified via integration smoke checks in `build.py`

---

## Task 1: Bootstrap repo files

**Files:**
- Create: `~/Documents/archives/CNAME`
- Create: `~/Documents/archives/README.md`
- Modify: `~/Documents/archives/.gitignore`

- [ ] **Step 1: Create CNAME**

```bash
echo 'archives.mypenjustbroke.com' > ~/Documents/archives/CNAME
```

- [ ] **Step 2: Create README**

Write to `~/Documents/archives/README.md`:

```markdown
# archives.mypenjustbroke.com

Frozen-snapshot static mirror of the SimDemocracy wiki, built from the
2026-05-05 MediaWiki XML export. Source wiki at qwrky.dev is offline.

## Rebuild

Requires Docker Desktop, Python 3.11+, wget, and the
[Pagefind](https://pagefind.app) binary (`brew install pagefind`).

```
ln -sf ~/Downloads/SimDemocracy+Archives-20260505192744.xml tools/import.xml
python3 tools/build.py
```

Output is committed to repo root and served by GitHub Pages.

## Layout

See `docs/superpowers/specs/2026-05-05-archives-mypenjustbroke-design.md`.
```

- [ ] **Step 3: Extend .gitignore**

Append to `~/Documents/archives/.gitignore` (file already has DS_Store, source-html, .venv, __pycache__, *.pyc):

```
.docker/
tools/import.xml
tools/tests/__pycache__/
*.xml
```

- [ ] **Step 4: Commit**

```bash
cd ~/Documents/archives && git add CNAME README.md .gitignore && \
  git -c user.email=wwambsganss@gmail.com -c user.name=mypenjustbroke \
      commit -m "Bootstrap repo files (CNAME, README, gitignore)"
```

---

## Task 2: Define Docker Compose stack

**Files:**
- Create: `~/Documents/archives/docker-compose.yml`
- Create: `~/Documents/archives/LocalSettings.php`

- [ ] **Step 1: Write docker-compose.yml**

Write to `~/Documents/archives/docker-compose.yml`:

```yaml
services:
  db:
    image: mariadb:10.11
    restart: "no"
    environment:
      MARIADB_DATABASE: my_wiki
      MARIADB_USER: wikiuser
      MARIADB_PASSWORD: wikipass
      MARIADB_ROOT_PASSWORD: rootpass
    volumes:
      - ./.docker/db:/var/lib/mysql
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 5s
      retries: 30

  mediawiki:
    image: mediawiki:1.43
    restart: "no"
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8080:80"
    volumes:
      - ./LocalSettings.php:/var/www/html/LocalSettings.php:ro
      - ./tools/import.xml:/import/SimDemocracy-Archives.xml:ro
      - ./.docker/mw-images:/var/www/html/images
```

- [ ] **Step 2: Write LocalSettings.php**

Write to `~/Documents/archives/LocalSettings.php` (read-only public-facing config; the import scripts run as CLI bypassing these permission gates):

```php
<?php
if ( !defined( 'MEDIAWIKI' ) ) { exit; }

$wgSitename = "SimDemocracy Archives";
$wgMetaNamespace = "SimDemocracy_Archives";

$wgScriptPath = "";
$wgArticlePath = "/wiki/$1";
$wgUsePathInfo = true;
$wgServer = "http://localhost:8080";

$wgEnableUploads = false;
$wgUseInstantCommons = false;

$wgDBtype = "mysql";
$wgDBserver = "db";
$wgDBname = "my_wiki";
$wgDBuser = "wikiuser";
$wgDBpassword = "wikipass";
$wgDBTableOptions = "ENGINE=InnoDB, DEFAULT CHARSET=binary";

$wgSecretKey = "buildtime-only-not-public-1f7a3e9c2b4d6a8e0f1c3a5b7d9e1f3a";
$wgUpgradeKey = "buildtime-only-not-public-2e8b4f0d3c5a7b9e1d3f5a7c9b1d3e5a";

$wgLanguageCode = "en-GB";
$wgDefaultSkin = "vector";

# --- Read-only public mode ---
# CLI maintenance scripts (importDump, rebuildall) bypass these gates,
# so this is safe for the import phase.
$wgGroupPermissions['*']['edit']            = false;
$wgGroupPermissions['*']['createaccount']   = false;
$wgGroupPermissions['*']['createpage']      = false;
$wgGroupPermissions['*']['createtalk']      = false;
$wgGroupPermissions['*']['writeapi']        = false;
$wgGroupPermissions['*']['upload']          = false;
$wgGroupPermissions['*']['move']            = false;
$wgGroupPermissions['user']['edit']         = false;
$wgGroupPermissions['user']['createaccount']= false;
$wgGroupPermissions['user']['createpage']   = false;
$wgGroupPermissions['user']['upload']       = false;

$wgRightsPage = "";
$wgRightsUrl  = "";
$wgRightsText = "Snapshot of the SimDemocracy Archives, 2026-05-05.";
$wgRightsIcon = "";

# Suppress diagnostics in rendered HTML
$wgShowExceptionDetails = false;
$wgShowDBErrorBacktrace = false;
$wgShowSQLErrors        = false;
```

- [ ] **Step 3: Symlink the XML import file**

```bash
cd ~/Documents/archives && \
  ln -sf ~/Downloads/SimDemocracy+Archives-20260505192744.xml tools/import.xml && \
  ls -la tools/import.xml
```

Expected: `tools/import.xml -> /Users/walkerwambsganss/Downloads/SimDemocracy+Archives-20260505192744.xml`

- [ ] **Step 4: Verify Docker stack starts**

```bash
cd ~/Documents/archives && docker compose up -d && \
  sleep 30 && \
  curl -fsS http://localhost:8080/api.php?action=siteinfo&format=json | head -c 300
```

Expected: JSON response containing `"sitename":"SimDemocracy Archives"`.

If the response is the install wizard, MediaWiki ran without LocalSettings — re-check the volume mount.

- [ ] **Step 5: Tear down for now**

```bash
cd ~/Documents/archives && docker compose down
```

- [ ] **Step 6: Commit**

```bash
cd ~/Documents/archives && git add docker-compose.yml LocalSettings.php && \
  git -c user.email=wwambsganss@gmail.com -c user.name=mypenjustbroke \
      commit -m "Add Docker Compose stack and MediaWiki LocalSettings.php"
```

---

## Task 3: Bootstrap build.py orchestrator

**Files:**
- Create: `~/Documents/archives/tools/build.py`

- [ ] **Step 1: Write build.py skeleton**

Write to `~/Documents/archives/tools/build.py`:

```python
#!/usr/bin/env python3
"""
Build orchestrator for archives.mypenjustbroke.com.

Phases:
  1. up       — start Docker stack, wait for MediaWiki ready
  2. import   — importDump.php + rebuildall.php
  3. mirror   — wget --mirror against local MediaWiki
  4. post     — postprocess.py mutations on mirrored HTML
  5. pagefind — build search index
  6. down     — tear down Docker stack

Usage:
  python3 tools/build.py                # run all phases
  python3 tools/build.py --skip-up      # skip starting Docker (assume running)
  python3 tools/build.py --only post    # run only the post phase
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MW_URL = "http://localhost:8080"
# `init` runs MediaWiki install.php once per fresh DB to create schema.
# An empty MariaDB has no MW tables; without init, every API call 500s.
ALL_PHASES = ["up", "init", "import", "mirror", "post", "pagefind", "down"]


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd or REPO, check=check)


def wait_for_db(timeout: int = 60) -> None:
    """Block until MariaDB reports healthy (compose healthcheck)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = subprocess.run(
            ["docker", "compose", "ps", "--format", "json", "db"],
            capture_output=True, text=True,
        )
        if '"Health":"healthy"' in r.stdout or '"healthy"' in r.stdout:
            print("MariaDB healthy")
            return
        time.sleep(2)
    raise SystemExit(f"MariaDB did not become healthy within {timeout}s")


def wait_for_mediawiki(timeout: int = 120) -> None:
    deadline = time.time() + timeout
    url = f"{MW_URL}/api.php?action=query&meta=siteinfo&format=json"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200:
                    data = json.loads(r.read())
                    name = data.get("query", {}).get("general", {}).get("sitename", "")
                    if name:
                        print(f"MediaWiki ready: {name}")
                        return
        except Exception:
            pass
        time.sleep(2)
    raise SystemExit(f"MediaWiki did not become ready within {timeout}s")


def phase_up() -> None:
    run(["docker", "compose", "up", "-d"])
    wait_for_db()


def phase_init() -> None:
    raise NotImplementedError("Task 4")


def phase_import() -> None:
    raise NotImplementedError("Task 4")


def phase_mirror() -> None:
    raise NotImplementedError("Task 5")


def phase_post() -> None:
    raise NotImplementedError("Task 7-12")


def phase_pagefind() -> None:
    raise NotImplementedError("Task 13")


def phase_down() -> None:
    run(["docker", "compose", "down"])


PHASES = {
    "up": phase_up,
    "init": phase_init,
    "import": phase_import,
    "mirror": phase_mirror,
    "post": phase_post,
    "pagefind": phase_pagefind,
    "down": phase_down,
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--only", choices=ALL_PHASES, help="run only one phase")
    p.add_argument("--skip", action="append", default=[], choices=ALL_PHASES,
                   help="skip a phase (repeatable)")
    args = p.parse_args()

    phases = [args.only] if args.only else [ph for ph in ALL_PHASES if ph not in args.skip]
    for ph in phases:
        print(f"\n=== Phase: {ph} ===")
        PHASES[ph]()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make executable**

```bash
chmod +x ~/Documents/archives/tools/build.py
```

- [ ] **Step 3: Smoke test the `up` and `down` phases**

```bash
cd ~/Documents/archives && python3 tools/build.py --only up
```

Expected: Docker starts, then "MariaDB healthy". (MW HTTP isn't checked here because schema isn't yet present on a fresh DB — `init` phase in Task 4 runs install.php to create it. If `.docker/db/` already has tables from a previous build, MW will respond, but we don't assert that.)

```bash
cd ~/Documents/archives && python3 tools/build.py --only down
```

Expected: containers stop.

- [ ] **Step 4: Commit**

```bash
cd ~/Documents/archives && git add tools/build.py && \
  git -c user.email=wwambsganss@gmail.com -c user.name=mypenjustbroke \
      commit -m "Bootstrap build.py orchestrator (up/down phases working)"
```

---

## Task 4: Implement init + import phases

**Files:**
- Modify: `~/Documents/archives/tools/build.py`

**Why init exists:** A fresh MariaDB has the `my_wiki` database but no MediaWiki tables. Without bootstrap, MW returns 500 on every request and `importDump` fails. `init` runs `install.php` once to create the schema. It's idempotent — if `site_stats` table already exists, it's a no-op.

**Why a separate install container:** the running `mediawiki` service has our `LocalSettings.php` mounted read-only, and `install.php` refuses to run when it sees an existing `LocalSettings.php`. We sidestep this by running install in a fresh `mediawiki:1.43` container that joins the same Docker network, talks to the same DB, and writes its (unused) generated config to `/tmp/`.

- [ ] **Step 1: Add `schema_present` and replace `phase_init` body**

In `tools/build.py`, add `schema_present` near `wait_for_db` and replace the `phase_init` stub:

```python
def schema_present() -> bool:
    r = subprocess.run(
        ["docker", "compose", "exec", "-T", "db",
         "mariadb", "-u", "wikiuser", "-pwikipass", "my_wiki",
         "-N", "-B", "-e", "SHOW TABLES LIKE 'site_stats'"],
        capture_output=True, text=True,
    )
    return r.returncode == 0 and "site_stats" in r.stdout


def phase_init() -> None:
    if schema_present():
        print("MediaWiki schema already present, skipping install")
        wait_for_mediawiki()
        return
    print("Bootstrapping MediaWiki schema (one-shot install container)")
    run([
        "docker", "run", "--rm", "--network=archives_default",
        "mediawiki:1.43",
        "php", "/var/www/html/maintenance/run.php", "install",
        "--dbtype=mysql", "--dbserver=db", "--dbname=my_wiki",
        "--dbuser=wikiuser", "--dbpass=wikipass",
        "--installdbuser=wikiuser", "--installdbpass=wikipass",
        "--pass=adminpass1234buildonly",
        "--scriptpath=", "--server=http://localhost:8080",
        "--confpath=/tmp", "--skins=Vector",
        "SimDemocracy Archives", "Admin",
    ])
    wait_for_mediawiki()
```

- [ ] **Step 2: Replace `phase_import` body**

In `tools/build.py`, replace the `phase_import` function with:

```python
def phase_import() -> None:
    # importDump.php reads from STDIN inside the container.
    run(["docker", "compose", "exec", "-T", "mediawiki",
         "bash", "-c",
         "php maintenance/run.php importDump --no-updates < /import/SimDemocracy-Archives.xml"])
    run(["docker", "compose", "exec", "mediawiki",
         "php", "maintenance/run.php", "rebuildall"])
    # rebuildall refreshes links but not site statistics; do that explicitly
    # so siteinfo and Special:Statistics show real counts.
    run(["docker", "compose", "exec", "mediawiki",
         "php", "maintenance/run.php", "initSiteStats", "--update"])
    verify_import()


def verify_import() -> None:
    # Source of truth: count rows in the page table directly. The MediaWiki
    # statistics counter only reflects pages with content links and lags
    # bulk imports; the raw page count is what we actually mirrored.
    r = subprocess.run(
        ["docker", "compose", "exec", "-T", "db",
         "mariadb", "-u", "wikiuser", "-pwikipass", "my_wiki",
         "-N", "-B", "-e", "SELECT COUNT(*) FROM page"],
        capture_output=True, text=True, cwd=REPO, check=True,
    )
    pages = int(r.stdout.strip())
    print(f"Page count after import: {pages}")
    if pages < 1300:
        raise SystemExit(f"Expected >= 1300 pages, got {pages}. Import may have failed.")
```

- [ ] **Step 3: Run init then import**

```bash
cd ~/Documents/archives && \
  python3 tools/build.py --only up && \
  python3 tools/build.py --only init && \
  python3 tools/build.py --only import
```

Expected:
- init: "Bootstrapping MediaWiki schema..." → install.php prints "done" lines → "MediaWiki ready: SimDemocracy Archives"
- (re-running init is a no-op: "MediaWiki schema already present, skipping install")
- importDump: "Done!" with per-page progress
- rebuildall: "Refreshing redirects table" / "Rebuilding recentchanges" / "Refreshing links table"
- "Page count after import: 1333" (1300+ asserted)

If it fails on `php maintenance/run.php importDump`, the older command form is `php maintenance/importDump.php`. MediaWiki 1.43 uses `run.php`; older fallback included for resilience.

- [ ] **Step 4: Commit**

```bash
cd ~/Documents/archives && git add tools/build.py && \
  git -c user.email=wwambsganss@gmail.com -c user.name=mypenjustbroke \
      commit -m "Implement init + import phases (schema bootstrap, importDump, rebuildall)"
```

---

## Task 5: Implement mirror phase

**Files:**
- Modify: `~/Documents/archives/tools/build.py`

- [ ] **Step 1: Replace `phase_mirror` body**

In `tools/build.py`, replace the `phase_mirror` function with:

```python
def enumerate_titles_via_api() -> list[str]:
    """List every page title across content namespaces using MediaWiki's API."""
    titles: list[str] = []
    for ns in [0, 4, 6, 10, 14]:  # Main, Project, File, Template, Category
        cont = ""
        while True:
            url = (f"{MW_URL}/api.php?action=query&list=allpages&aplimit=500"
                   f"&apnamespace={ns}&format=json{cont}")
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read())
            for p in data.get("query", {}).get("allpages", []):
                titles.append(p["title"])
            if "continue" in data:
                apcontinue = data["continue"].get("apcontinue", "")
                cont = f"&apcontinue={urllib.parse.quote(apcontinue)}"
            else:
                break
    return titles


def phase_mirror() -> None:
    site = REPO / "site_tmp"
    if site.exists():
        shutil.rmtree(site)
    site.mkdir()

    # Initial recursive mirror from Main_Page; --convert-links makes refs relative.
    run([
        "wget", "--mirror", "--page-requisites", "--convert-links",
        "--adjust-extension", "--no-parent", "--no-host-directories",
        "--execute", "robots=off",
        "--directory-prefix", str(site),
        f"{MW_URL}/wiki/Main_Page",
    ])

    # Coverage pass: enumerate every title via API and explicitly fetch any not
    # caught by the recursive crawl (orphans, less-linked categories, templates).
    titles = enumerate_titles_via_api()
    print(f"API enumerated {len(titles)} titles")
    urls_file = site / "_urls.txt"
    with urls_file.open("w") as f:
        for t in titles:
            f.write(f"{MW_URL}/wiki/{urllib.parse.quote(t.replace(' ', '_'))}\n")
    run([
        "wget", "--input-file", str(urls_file),
        "--page-requisites", "--convert-links",
        "--adjust-extension", "--no-host-directories",
        "--execute", "robots=off",
        "-N",  # only download if newer (skip the ones we already have)
        "--directory-prefix", str(site),
    ])
    urls_file.unlink()

    # Replace the existing mirror in repo root (preserve docs/, tools/, etc).
    for d in ("wiki", "load.php", "resources", "skins"):
        target = REPO / d
        src = site / d
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        if src.exists():
            shutil.move(str(src), str(target))
    # Move any top-level files (e.g. index.html from the crawl)
    for f in site.iterdir():
        if f.is_file():
            shutil.move(str(f), str(REPO / f.name))
    shutil.rmtree(site)

    # Coverage check
    page_count = sum(1 for _ in (REPO / "wiki").rglob("*.html"))
    print(f"Mirrored HTML files in /wiki: {page_count}")
    if page_count < 1300:
        raise SystemExit(f"Mirror coverage too low: {page_count} pages")
```

- [ ] **Step 2: Run mirror phase**

```bash
cd ~/Documents/archives && python3 tools/build.py --only mirror
```

Expected:
- wget chatter for Main_Page recursive crawl (several minutes for 1333 pages)
- "API enumerated 1333 titles"
- Second wget pass picking up any missed titles (mostly cache hits)
- "Mirrored HTML files in /wiki: 1333" or higher (categories/templates produce additional files)

- [ ] **Step 3: Spot-check a few mirrored pages**

```bash
ls ~/Documents/archives/wiki/ | head -5
open ~/Documents/archives/wiki/Main_Page.html
open ~/Documents/archives/wiki/Abuse_of_Process_Act_2025.html
```

Expected: pages render with Vector skin, internal links work (because `--convert-links` made them relative), tables/refs intact.

- [ ] **Step 4: Commit**

```bash
cd ~/Documents/archives && git add tools/build.py && \
  git -c user.email=wwambsganss@gmail.com -c user.name=mypenjustbroke \
      commit -m "Implement mirror phase: wget recursive + API-driven coverage pass"
```

---

## Task 6: Set up postprocess test scaffolding

**Files:**
- Create: `~/Documents/archives/tools/tests/__init__.py`
- Create: `~/Documents/archives/tools/tests/test_postprocess.py`
- Create: `~/Documents/archives/tools/postprocess.py`

- [ ] **Step 1: Install BeautifulSoup**

```bash
python3 -m pip install --user beautifulsoup4 lxml pytest
```

- [ ] **Step 2: Create empty `tools/tests/__init__.py`**

```bash
touch ~/Documents/archives/tools/tests/__init__.py
```

- [ ] **Step 3: Create postprocess.py stub**

Write to `~/Documents/archives/tools/postprocess.py`:

```python
"""HTML mutation pipeline applied to wget-mirrored MediaWiki output."""
from __future__ import annotations
from bs4 import BeautifulSoup


def transform(html: str) -> str:
    """Apply all mutations and return the modified HTML string."""
    soup = BeautifulSoup(html, "lxml")
    strip_edit_links(soup)
    strip_history_and_action_tabs(soup)
    strip_login_and_account_links(soup)
    strip_special_recentchanges_link(soup)
    inject_site_notice(soup)
    swap_search_box_for_pagefind(soup)
    return str(soup)


def strip_edit_links(soup: BeautifulSoup) -> None:
    raise NotImplementedError("Task 7")


def strip_history_and_action_tabs(soup: BeautifulSoup) -> None:
    raise NotImplementedError("Task 8")


def strip_login_and_account_links(soup: BeautifulSoup) -> None:
    raise NotImplementedError("Task 9")


def strip_special_recentchanges_link(soup: BeautifulSoup) -> None:
    raise NotImplementedError("Task 9")


def inject_site_notice(soup: BeautifulSoup) -> None:
    raise NotImplementedError("Task 10")


def swap_search_box_for_pagefind(soup: BeautifulSoup) -> None:
    raise NotImplementedError("Task 11")
```

- [ ] **Step 4: Create test file with imports**

Write to `~/Documents/archives/tools/tests/test_postprocess.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bs4 import BeautifulSoup
import postprocess


def soup_from(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")
```

- [ ] **Step 5: Verify pytest collects but skips empty file**

```bash
cd ~/Documents/archives && python3 -m pytest tools/tests/ -v
```

Expected: "no tests ran" — the test file is collected but contains no `test_*` functions yet.

- [ ] **Step 6: Commit**

```bash
cd ~/Documents/archives && \
  git add tools/postprocess.py tools/tests/__init__.py tools/tests/test_postprocess.py && \
  git -c user.email=wwambsganss@gmail.com -c user.name=mypenjustbroke \
      commit -m "Scaffold postprocess module and test harness"
```

---

## Task 7: Implement strip_edit_links (TDD)

**Files:**
- Modify: `~/Documents/archives/tools/tests/test_postprocess.py`
- Modify: `~/Documents/archives/tools/postprocess.py`

- [ ] **Step 1: Write the failing test**

Append to `~/Documents/archives/tools/tests/test_postprocess.py`:

```python
def test_strip_edit_links_removes_action_edit_anchors():
    html = '''
    <ul>
      <li id="ca-edit"><a href="/wiki/Foo?action=edit"><span>Edit</span></a></li>
      <li id="ca-ve-edit"><a href="/wiki/Foo?veaction=edit"><span>Edit</span></a></li>
      <li id="ca-view"><a href="/wiki/Foo">Read</a></li>
    </ul>
    '''
    soup = soup_from(html)
    postprocess.strip_edit_links(soup)
    assert soup.find(id="ca-edit") is None
    assert soup.find(id="ca-ve-edit") is None
    assert soup.find(id="ca-view") is not None  # Read tab kept


def test_strip_edit_links_removes_section_edit_brackets():
    html = '''
    <h2>
      <span class="mw-headline" id="Section">Section</span>
      <span class="mw-editsection">
        <span class="mw-editsection-bracket">[</span>
        <a href="/wiki/Foo?action=edit&section=1">edit</a>
        <span class="mw-editsection-bracket">]</span>
      </span>
    </h2>
    '''
    soup = soup_from(html)
    postprocess.strip_edit_links(soup)
    assert soup.find(class_="mw-editsection") is None
    assert soup.find(class_="mw-headline") is not None  # heading kept
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ~/Documents/archives && python3 -m pytest tools/tests/test_postprocess.py::test_strip_edit_links_removes_action_edit_anchors -v
```

Expected: FAIL with `NotImplementedError: Task 7`.

- [ ] **Step 3: Implement**

In `tools/postprocess.py`, replace the `strip_edit_links` body:

```python
def strip_edit_links(soup: BeautifulSoup) -> None:
    # Tab UI: <li id="ca-edit">, <li id="ca-ve-edit">
    for li_id in ("ca-edit", "ca-ve-edit"):
        for el in soup.find_all(id=li_id):
            el.decompose()
    # Per-section [edit] brackets
    for el in soup.find_all(class_="mw-editsection"):
        el.decompose()
```

- [ ] **Step 4: Run tests**

```bash
cd ~/Documents/archives && python3 -m pytest tools/tests/test_postprocess.py -v
```

Expected: both new tests PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/archives && git add tools/tests/test_postprocess.py tools/postprocess.py && \
  git -c user.email=wwambsganss@gmail.com -c user.name=mypenjustbroke \
      commit -m "Implement strip_edit_links (postprocess)"
```

---

## Task 8: Implement strip_history_and_action_tabs (TDD)

**Files:**
- Modify: `~/Documents/archives/tools/tests/test_postprocess.py`
- Modify: `~/Documents/archives/tools/postprocess.py`

- [ ] **Step 1: Write the failing test**

Append to `tools/tests/test_postprocess.py`:

```python
def test_strip_history_and_action_tabs_removes_known_ids():
    html = '''
    <ul>
      <li id="ca-history"><a>History</a></li>
      <li id="ca-watch"><a>Watch</a></li>
      <li id="ca-unwatch"><a>Unwatch</a></li>
      <li id="ca-move"><a>Move</a></li>
      <li id="ca-delete"><a>Delete</a></li>
      <li id="ca-protect"><a>Protect</a></li>
      <li id="ca-purge"><a>Purge</a></li>
      <li id="ca-view"><a>Read</a></li>
      <li id="ca-talk"><a>Talk</a></li>
    </ul>
    '''
    soup = soup_from(html)
    postprocess.strip_history_and_action_tabs(soup)
    for stripped in ("ca-history", "ca-watch", "ca-unwatch", "ca-move",
                     "ca-delete", "ca-protect", "ca-purge"):
        assert soup.find(id=stripped) is None, f"{stripped} should be removed"
    # Read and Talk tabs are kept
    assert soup.find(id="ca-view") is not None
    assert soup.find(id="ca-talk") is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ~/Documents/archives && python3 -m pytest tools/tests/test_postprocess.py::test_strip_history_and_action_tabs_removes_known_ids -v
```

Expected: FAIL with `NotImplementedError: Task 8`.

- [ ] **Step 3: Implement**

In `tools/postprocess.py`, replace the `strip_history_and_action_tabs` body:

```python
def strip_history_and_action_tabs(soup: BeautifulSoup) -> None:
    for li_id in ("ca-history", "ca-watch", "ca-unwatch", "ca-move",
                  "ca-delete", "ca-protect", "ca-purge"):
        for el in soup.find_all(id=li_id):
            el.decompose()
```

- [ ] **Step 4: Run tests**

```bash
cd ~/Documents/archives && python3 -m pytest tools/tests/test_postprocess.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/archives && git add tools/tests/test_postprocess.py tools/postprocess.py && \
  git -c user.email=wwambsganss@gmail.com -c user.name=mypenjustbroke \
      commit -m "Implement strip_history_and_action_tabs (postprocess)"
```

---

## Task 9: Implement strip_login + strip_special_recentchanges (TDD)

**Files:**
- Modify: `~/Documents/archives/tools/tests/test_postprocess.py`
- Modify: `~/Documents/archives/tools/postprocess.py`

- [ ] **Step 1: Write the failing tests**

Append to `tools/tests/test_postprocess.py`:

```python
def test_strip_login_and_account_links_removes_personal_tools():
    html = '''
    <ul id="p-personal-tools">
      <li id="pt-anonuserpage">Not logged in</li>
      <li id="pt-anontalk"><a>Talk for this IP</a></li>
      <li id="pt-anoncontribs"><a>Contributions</a></li>
      <li id="pt-createaccount"><a>Create account</a></li>
      <li id="pt-login"><a>Log in</a></li>
    </ul>
    '''
    soup = soup_from(html)
    postprocess.strip_login_and_account_links(soup)
    for stripped in ("pt-anonuserpage", "pt-anontalk", "pt-anoncontribs",
                     "pt-createaccount", "pt-login"):
        assert soup.find(id=stripped) is None, f"{stripped} should be removed"


def test_strip_special_recentchanges_link_removes_sidebar_entry():
    html = '''
    <ul>
      <li id="n-mainpage-description"><a href="/wiki/Main_Page">Main page</a></li>
      <li id="n-recentchanges"><a href="/wiki/Special:RecentChanges">Recent changes</a></li>
      <li id="n-randompage"><a href="/wiki/Special:Random">Random</a></li>
      <li id="n-help-mediawiki"><a href="https://www.mediawiki.org/">Help</a></li>
    </ul>
    '''
    soup = soup_from(html)
    postprocess.strip_special_recentchanges_link(soup)
    assert soup.find(id="n-recentchanges") is None
    assert soup.find(id="n-help-mediawiki") is None  # also strip MW external help
    assert soup.find(id="n-mainpage-description") is not None
    assert soup.find(id="n-randompage") is None  # Random page is meaningless on a static archive
```

- [ ] **Step 2: Run tests, expect failure**

```bash
cd ~/Documents/archives && python3 -m pytest tools/tests/test_postprocess.py::test_strip_login_and_account_links_removes_personal_tools tools/tests/test_postprocess.py::test_strip_special_recentchanges_link_removes_sidebar_entry -v
```

Expected: both FAIL with `NotImplementedError: Task 9`.

- [ ] **Step 3: Implement both functions**

In `tools/postprocess.py`, replace the two stubs:

```python
def strip_login_and_account_links(soup: BeautifulSoup) -> None:
    for li_id in ("pt-anonuserpage", "pt-anontalk", "pt-anoncontribs",
                  "pt-createaccount", "pt-login", "pt-userpage", "pt-mytalk",
                  "pt-preferences", "pt-watchlist", "pt-mycontris",
                  "pt-logout"):
        for el in soup.find_all(id=li_id):
            el.decompose()


def strip_special_recentchanges_link(soup: BeautifulSoup) -> None:
    for li_id in ("n-recentchanges", "n-help-mediawiki", "n-randompage",
                  "n-portal", "n-currentevents"):
        for el in soup.find_all(id=li_id):
            el.decompose()
```

- [ ] **Step 4: Run tests**

```bash
cd ~/Documents/archives && python3 -m pytest tools/tests/test_postprocess.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/archives && git add tools/tests/test_postprocess.py tools/postprocess.py && \
  git -c user.email=wwambsganss@gmail.com -c user.name=mypenjustbroke \
      commit -m "Implement strip_login_and_account_links + strip_special_recentchanges_link"
```

---

## Task 10: Implement inject_site_notice (TDD)

**Files:**
- Modify: `~/Documents/archives/tools/tests/test_postprocess.py`
- Modify: `~/Documents/archives/tools/postprocess.py`

- [ ] **Step 1: Write the failing test**

Append to `tools/tests/test_postprocess.py`:

```python
def test_inject_site_notice_adds_banner_at_top_of_content():
    html = '''
    <html><body>
      <div id="content" class="mw-body" role="main">
        <h1 id="firstHeading">Foo</h1>
        <div id="bodyContent">...</div>
      </div>
    </body></html>
    '''
    soup = soup_from(html)
    postprocess.inject_site_notice(soup)
    notice = soup.find(id="archives-notice")
    assert notice is not None, "site notice div not injected"
    assert "snapshot" in notice.get_text().lower()
    # Notice must come BEFORE the firstHeading
    h1 = soup.find(id="firstHeading")
    siblings_before_h1 = []
    for sib in h1.previous_siblings:
        if hasattr(sib, "get") and sib.get("id"):
            siblings_before_h1.append(sib.get("id"))
    assert "archives-notice" in siblings_before_h1


def test_inject_site_notice_idempotent():
    html = '<div id="content"><h1 id="firstHeading">X</h1></div>'
    soup = soup_from(html)
    postprocess.inject_site_notice(soup)
    postprocess.inject_site_notice(soup)
    assert len(soup.find_all(id="archives-notice")) == 1
```

- [ ] **Step 2: Run tests, expect failure**

```bash
cd ~/Documents/archives && python3 -m pytest tools/tests/test_postprocess.py::test_inject_site_notice_adds_banner_at_top_of_content tools/tests/test_postprocess.py::test_inject_site_notice_idempotent -v
```

Expected: both FAIL.

- [ ] **Step 3: Implement**

In `tools/postprocess.py`, replace the `inject_site_notice` body:

```python
SITE_NOTICE_HTML = (
    '<div id="archives-notice" '
    'style="background:#fff8dc;border:1px solid #d4c876;'
    'padding:8px 12px;margin:0 0 12px 0;font-size:90%;border-radius:3px;">'
    'Frozen snapshot of the SimDemocracy Archives, captured 2026-05-05. '
    'Read-only mirror; no edit, no live updates. '
    '<a href="https://mypenjustbroke.com">mypenjustbroke.com</a>'
    '</div>'
)


def inject_site_notice(soup: BeautifulSoup) -> None:
    if soup.find(id="archives-notice"):
        return  # idempotent
    h1 = soup.find(id="firstHeading")
    if h1 is None:
        return
    notice = BeautifulSoup(SITE_NOTICE_HTML, "lxml").body.next  # extract the div
    h1.insert_before(notice)
```

- [ ] **Step 4: Run tests**

```bash
cd ~/Documents/archives && python3 -m pytest tools/tests/test_postprocess.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/archives && git add tools/tests/test_postprocess.py tools/postprocess.py && \
  git -c user.email=wwambsganss@gmail.com -c user.name=mypenjustbroke \
      commit -m "Implement inject_site_notice (postprocess)"
```

---

## Task 11: Implement swap_search_box_for_pagefind (TDD)

**Files:**
- Modify: `~/Documents/archives/tools/tests/test_postprocess.py`
- Modify: `~/Documents/archives/tools/postprocess.py`

- [ ] **Step 1: Write the failing test**

Append to `tools/tests/test_postprocess.py`:

```python
def test_swap_search_box_for_pagefind_replaces_native_form():
    html = '''
    <html><head></head><body>
      <form action="/wiki/Special:Search" id="searchform">
        <input id="searchInput" type="search" name="search">
        <input type="submit" name="go" value="Go">
      </form>
    </body></html>
    '''
    soup = soup_from(html)
    postprocess.swap_search_box_for_pagefind(soup)
    assert soup.find(id="searchform") is None
    assert soup.find(id="archives-search") is not None
    head = soup.find("head")
    # Pagefind UI assets injected in head
    css = head.find("link", href=lambda h: h and "/pagefind/pagefind-ui.css" in h)
    js = head.find("script", src=lambda s: s and "/pagefind/pagefind-ui.js" in s)
    assert css is not None
    assert js is not None
```

- [ ] **Step 2: Run test, expect failure**

```bash
cd ~/Documents/archives && python3 -m pytest tools/tests/test_postprocess.py::test_swap_search_box_for_pagefind_replaces_native_form -v
```

Expected: FAIL.

- [ ] **Step 3: Implement**

In `tools/postprocess.py`, replace the `swap_search_box_for_pagefind` body:

```python
PAGEFIND_PLACEHOLDER_HTML = (
    '<div id="archives-search" style="margin:6px 0;"></div>'
)
PAGEFIND_INIT_SCRIPT = (
    '<script>'
    'window.addEventListener("DOMContentLoaded",function(){'
    'new PagefindUI({element:"#archives-search",showSubResults:true});'
    '});'
    '</script>'
)


def swap_search_box_for_pagefind(soup: BeautifulSoup) -> None:
    form = soup.find(id="searchform")
    if form is not None:
        placeholder = BeautifulSoup(PAGEFIND_PLACEHOLDER_HTML, "lxml").body.next
        form.replace_with(placeholder)
    head = soup.find("head")
    if head is not None:
        if not head.find("link", href=lambda h: h and "/pagefind/pagefind-ui.css" in h):
            link = soup.new_tag("link", rel="stylesheet", href="/pagefind/pagefind-ui.css")
            head.append(link)
        if not head.find("script", src=lambda s: s and "/pagefind/pagefind-ui.js" in s):
            script = soup.new_tag("script", src="/pagefind/pagefind-ui.js")
            head.append(script)
            init = BeautifulSoup(PAGEFIND_INIT_SCRIPT, "lxml").body.next
            head.append(init)
```

- [ ] **Step 4: Run tests**

```bash
cd ~/Documents/archives && python3 -m pytest tools/tests/test_postprocess.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/archives && git add tools/tests/test_postprocess.py tools/postprocess.py && \
  git -c user.email=wwambsganss@gmail.com -c user.name=mypenjustbroke \
      commit -m "Implement swap_search_box_for_pagefind (postprocess)"
```

---

## Task 12: Wire postprocess into build.py

**Files:**
- Modify: `~/Documents/archives/tools/build.py`

- [ ] **Step 1: Replace `phase_post` body**

In `tools/build.py`, replace `phase_post`:

```python
def phase_post() -> None:
    sys.path.insert(0, str(REPO / "tools"))
    import postprocess  # noqa
    wiki_dir = REPO / "wiki"
    if not wiki_dir.exists():
        raise SystemExit("wiki/ does not exist; run mirror phase first")
    count = 0
    for f in wiki_dir.rglob("*.html"):
        html = f.read_text(encoding="utf-8")
        new = postprocess.transform(html)
        if new != html:
            f.write_text(new, encoding="utf-8")
            count += 1
    print(f"Postprocessed {count} files")

    # Generate /index.html redirect to /wiki/Main_Page
    index = REPO / "index.html"
    index.write_text(
        '<!DOCTYPE html>\n'
        '<html><head>'
        '<meta charset="utf-8">'
        '<meta http-equiv="refresh" content="0;url=/wiki/Main_Page">'
        '<link rel="canonical" href="/wiki/Main_Page">'
        '<title>SimDemocracy Archives</title>'
        '</head><body>'
        '<p>Redirecting to <a href="/wiki/Main_Page">Main Page</a>...</p>'
        '</body></html>\n',
        encoding="utf-8",
    )
    print(f"Wrote {index}")
```

- [ ] **Step 2: Run postprocess on the existing mirrored output**

```bash
cd ~/Documents/archives && python3 tools/build.py --only post
```

Expected:
- "Postprocessed N files" where N >= 1300
- "Wrote /Users/.../index.html"

- [ ] **Step 3: Spot-check a postprocessed page**

```bash
open ~/Documents/archives/wiki/Main_Page.html
```

Expected:
- Yellow "Frozen snapshot…" notice at top
- Search box has been replaced with the Pagefind placeholder div
- Edit / History / Watch tabs are gone
- Page tabs only show Read and Talk
- Main page sidebar lacks Recent changes / Random / Help
- Tables, refs, internal links all working

- [ ] **Step 4: Commit**

```bash
cd ~/Documents/archives && git add tools/build.py && \
  git -c user.email=wwambsganss@gmail.com -c user.name=mypenjustbroke \
      commit -m "Wire postprocess into build.py + generate index.html redirect"
```

---

## Task 13: Build Pagefind index

**Files:**
- Modify: `~/Documents/archives/tools/build.py`

- [ ] **Step 1: Install Pagefind**

```bash
brew install pagefind
pagefind --version
```

Expected: a version like `pagefind 1.x.x`.

- [ ] **Step 2: Replace `phase_pagefind` body**

In `tools/build.py`, replace `phase_pagefind`:

```python
def phase_pagefind() -> None:
    pagefind_dir = REPO / "pagefind"
    if pagefind_dir.exists():
        shutil.rmtree(pagefind_dir)
    run(["pagefind", "--site", str(REPO), "--output-path", str(pagefind_dir)])
    if not (pagefind_dir / "pagefind.js").exists() and not (pagefind_dir / "pagefind-ui.js").exists():
        raise SystemExit("Pagefind output missing expected files")
    print(f"Pagefind index built at {pagefind_dir}")
```

- [ ] **Step 3: Run pagefind phase**

```bash
cd ~/Documents/archives && python3 tools/build.py --only pagefind
```

Expected:
- Pagefind output: "Indexed N pages" where N >= 1300
- "Pagefind index built at /Users/.../pagefind"

- [ ] **Step 4: Smoke-test search locally**

```bash
cd ~/Documents/archives && python3 -m http.server 8000 &
sleep 1
open http://localhost:8000/wiki/Main_Page.html
```

In the browser, type a known term (e.g. "Abuse of Process") in the Pagefind search box. Expected: a results dropdown appears with relevant pages.

```bash
kill %1   # stop the test server
```

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/archives && git add tools/build.py && \
  git -c user.email=wwambsganss@gmail.com -c user.name=mypenjustbroke \
      commit -m "Add pagefind phase to build.py"
```

---

## Task 14: Full end-to-end build verification

**Files:** none (verification only)

- [ ] **Step 1: Tear down the running stack and clean intermediate state**

```bash
cd ~/Documents/archives && docker compose down -v
rm -rf ~/Documents/archives/.docker ~/Documents/archives/wiki ~/Documents/archives/load.php ~/Documents/archives/resources ~/Documents/archives/skins ~/Documents/archives/pagefind ~/Documents/archives/index.html
```

- [ ] **Step 2: Run the full pipeline**

```bash
cd ~/Documents/archives && python3 tools/build.py
```

Expected: each phase logs its progress; total runtime ~5-15 min depending on Mac and network.

- [ ] **Step 3: Verify output**

```bash
ls ~/Documents/archives/wiki/ | wc -l
ls ~/Documents/archives/pagefind/
test -f ~/Documents/archives/index.html && echo "index OK" || echo "index MISSING"
```

Expected:
- ≥ 1300 pages in `wiki/`
- `pagefind/` contains `pagefind-ui.js`, `pagefind-ui.css`, `pagefind.js`, fragment shards
- "index OK"

- [ ] **Step 4: Stage all build output for commit**

```bash
cd ~/Documents/archives && git add -A && git status
```

Verify: only build artifacts (wiki/, pagefind/, index.html, load.php, resources/, skins/) and the tools/ + docker config. **Confirm `.docker/` and `tools/import.xml` are NOT staged** (they should be gitignored).

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/archives && \
  git -c user.email=wwambsganss@gmail.com -c user.name=mypenjustbroke \
      commit -m "Generate site: 1333 pages, Vector skin, Pagefind index"
```

---

## Task 15: Create GitHub repo and push

**Files:** none (deploy only)

- [ ] **Step 1: Switch gh to mypenjustbroke account**

```bash
gh auth switch --user mypenjustbroke && gh auth status
```

Expected: active account is `mypenjustbroke`.

- [ ] **Step 2: Create the repo and push**

```bash
cd ~/Documents/archives && \
  gh repo create mypenjustbroke/archives --public \
    --source . --push \
    --description "Frozen snapshot of the SimDemocracy wiki, 2026-05-05"
```

Expected: "Created repository mypenjustbroke/archives on GitHub", followed by a push.

- [ ] **Step 3: Enable GitHub Pages via API**

```bash
gh api -X POST repos/mypenjustbroke/archives/pages \
  -f 'source[branch]=main' -f 'source[path]=/'
```

Expected: JSON response with `"cname":"archives.mypenjustbroke.com"` and `"html_url"`.

---

## Task 16: User action — add CNAME at Squarespace

**Files:** none (manual user action)

- [ ] **Step 1: User adds DNS record**

Walker, log into Squarespace DNS settings for `mypenjustbroke.com` and add:

| Field | Value |
|---|---|
| Type | `CNAME` |
| Host | `archives` |
| Points to | `mypenjustbroke.github.io.` (with trailing dot) |
| TTL | default |

**Do not modify any existing records** — Google Sites apex and `outlines.` Pages depend on them.

- [ ] **Step 2: Verify propagation**

```bash
dig archives.mypenjustbroke.com CNAME +short
dig archives.mypenjustbroke.com @8.8.8.8 +short
```

Expected (may take 1-15 min after adding):
- First: `mypenjustbroke.github.io.`
- Second: that plus the Pages IPs `185.199.108-111.153`

If the response is empty, wait 5 min and retry — DNS propagation is the variable here.

- [ ] **Step 3: User enables HTTPS in Pages settings**

Walker, open `https://github.com/mypenjustbroke/archives/settings/pages` and:
1. Wait for the "DNS check" badge to turn green (cert provisioning, ~5-15 min after DNS verifies)
2. Tick "Enforce HTTPS"

(This step cannot be reliably done via API — it's a manual click.)

---

## Task 17: Live-site smoke test

**Files:** none (verification only)

- [ ] **Step 1: Probe the public site**

```bash
curl -sI https://archives.mypenjustbroke.com/ | head -3
curl -sI https://archives.mypenjustbroke.com/wiki/Main_Page | head -3
curl -sI https://archives.mypenjustbroke.com/wiki/Abuse_of_Process_Act_2025 | head -3
curl -sI 'https://archives.mypenjustbroke.com/wiki/Category:Legislation' | head -3
curl -sI 'https://archives.mypenjustbroke.com/wiki/SD_v_Notcommunist366,_Creative,_%26_Acool_2025_Crim_103' | head -3
```

Expected: `HTTP/2 200` (or `301` from `/` to `/wiki/Main_Page`) for each. The last one tests special-character handling (commas + ampersand).

- [ ] **Step 2: Browser smoke test**

```bash
open https://archives.mypenjustbroke.com/
```

Verify in the browser:
- Redirect lands on Main_Page
- Frozen-snapshot notice visible at top
- Vector skin renders correctly (logo, sidebar, content layout)
- Pagefind search works: type "judiciary", get results
- Click an internal wikilink — navigates correctly
- Click a Category link — category member listing appears
- Click a Talk tab on a page that has one — talk page loads
- No Edit / Watch / History tabs visible
- No "Create account / Log in" links

- [ ] **Step 3: Confirm pagefind index size is reasonable**

```bash
du -sh ~/Documents/archives/pagefind/
```

Expected: under 10 MB. (If much larger, may want to tune Pagefind config later — not blocking v1.)

- [ ] **Step 4: Tag the snapshot**

```bash
cd ~/Documents/archives && git tag -a snapshot-2026-05-05 -m "First public release: SimDemocracy Archives mirror" && \
  git push origin snapshot-2026-05-05
```

- [ ] **Step 5: Switch gh back to walker-pltfrm if user wants**

```bash
gh auth switch --user walker-pltfrm
```

Skip this step if user wants `mypenjustbroke` to remain the active account.

---

## Done criteria

- `https://archives.mypenjustbroke.com/` resolves and serves Main_Page over HTTPS
- All 1333 pages mirrored, postprocessed, indexed
- Search works on the live site
- Internal wikilinks, categories, templates render correctly
- No editing/login UI visible to public
- Snapshot tagged in git, repo public on GitHub
