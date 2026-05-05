#!/usr/bin/env python3
"""
Build orchestrator for archives.mypenjustbroke.com.

Phases:
  1. up       — start Docker stack, wait for MariaDB healthy
  2. init     — bootstrap MediaWiki schema (idempotent), wait for MW HTTP
  3. import   — importDump.php + rebuildall.php
  4. mirror   — wget --mirror against local MediaWiki
  5. post     — postprocess.py mutations on mirrored HTML
  6. pagefind — build search index
  7. down     — tear down Docker stack

Usage:
  python3 tools/build.py                # run all phases
  python3 tools/build.py --skip up      # skip starting Docker (assume running)
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
            capture_output=True, text=True, cwd=REPO,
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


def schema_present() -> bool:
    r = subprocess.run(
        ["docker", "compose", "exec", "-T", "db",
         "mariadb", "-u", "wikiuser", "-pwikipass", "my_wiki",
         "-N", "-B", "-e", "SHOW TABLES LIKE 'site_stats'"],
        capture_output=True, text=True, cwd=REPO,
    )
    return r.returncode == 0 and "site_stats" in r.stdout


def phase_up() -> None:
    run(["docker", "compose", "up", "-d"])
    wait_for_db()


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
