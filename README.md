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
