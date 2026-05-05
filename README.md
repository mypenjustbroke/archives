# archives.mypenjustbroke.com

Frozen-snapshot static mirror of the SimDemocracy wiki, built from the
2026-05-05 MediaWiki XML export. Source wiki at qwrky.dev is offline.

## Rebuild

Prereqs: Docker (we use [colima](https://github.com/abiosoft/colima): `brew install colima docker docker-compose && colima start`), Python 3.11+, wget, [Pagefind](https://pagefind.app) (`brew install pagefind`).

One-time setup:

```sh
python3 -m venv .venv
.venv/bin/pip install beautifulsoup4 lxml pytest
ln -sf ~/Downloads/SimDemocracy+Archives-20260505192744.xml tools/import.xml
```

Build:

```sh
.venv/bin/python tools/build.py
```

Phases run in order: `up` → `init` → `import` → `mirror` → `post` → `pagefind` → `down`. Each is independently invocable: `.venv/bin/python tools/build.py --only post`. The `init` phase is idempotent — it skips MediaWiki install if the schema already exists in `.docker/db/`.

Output (`wiki/`, `pagefind/`, `index.html`, `load.php?...` files, `resources/`) is committed to repo root and served by GitHub Pages.

## Tests

```sh
.venv/bin/pytest tools/tests/ -v
```

## Layout

See `docs/superpowers/specs/2026-05-05-archives-mypenjustbroke-design.md`.
