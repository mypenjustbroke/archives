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
