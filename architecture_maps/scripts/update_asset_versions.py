#!/usr/bin/env python3
"""Stamp/verify cache-busting ``?v=<sha256[:8]>`` fingerprints on the C4 docs JS.

The C4 diagram JS (``docs/javascripts/*.js``) is referenced from ``mkdocs.yml``'s
``extra_javascript`` by a stable filename, so a change is served stale by the
browser/CDN until the TTL lapses or someone purges. Appending a content-hash
query (``?v=...``) makes each change a new URL that is fetched fresh.

Usage (from the repo root):
    python architecture_maps/scripts/update_asset_versions.py           # rewrite ?v= in place
    python architecture_maps/scripts/update_asset_versions.py --check   # CI: exit 1 if any stale

Zero third-party deps so CI can run it with a bare ``python3``.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MKDOCS = REPO_ROOT / "mkdocs.yml"
DOCS_DIR = REPO_ROOT / "docs"

# Matches an extra_javascript list entry pointing at a local javascripts/*.js
# asset, with an optional existing ?v=<hash>. Quote-agnostic, trailing space ok.
_ENTRY = re.compile(
    r'(?P<lead>-\s*(?P<q>["\']?))(?P<path>javascripts/\S+?\.js)'
    r'(?:\?v=(?P<ver>[0-9a-f]+))?(?P<tail>(?P=q)[ \t]*)$',
    re.MULTILINE,
)


def _fingerprint(asset_path: str) -> str:
    f = DOCS_DIR / asset_path
    if not f.is_file():
        raise FileNotFoundError(f"referenced asset not found: {f.relative_to(REPO_ROOT)}")
    return hashlib.sha256(f.read_bytes()).hexdigest()[:8]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="verify committed ?v= matches each asset's content hash; exit 1 if not",
    )
    args = ap.parse_args()

    text = MKDOCS.read_text(encoding="utf-8")
    stale: list[str] = []

    def repl(m: re.Match[str]) -> str:
        want = _fingerprint(m.group("path"))
        have = m.group("ver")
        if have != want:
            stale.append(f"{m.group('path')}: committed v={have or '(none)'} expected v={want}")
        return f"{m.group('lead')}{m.group('path')}?v={want}{m.group('tail')}"

    if not _ENTRY.search(text):
        print("no local javascripts/*.js entries found in mkdocs.yml extra_javascript", file=sys.stderr)
        return 1

    try:
        updated = _ENTRY.sub(repl, text)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.check:
        if stale:
            print("STALE asset cache-bust fingerprints (regenerate with this script, no --check):")
            for s in stale:
                print(f"  - {s}")
            return 1
        print("OK: all extra_javascript ?v= fingerprints match their file content.")
        return 0

    if updated != text:
        MKDOCS.write_text(updated, encoding="utf-8")
        print("Updated cache-bust fingerprints:")
        for s in stale:
            print(f"  - {s}")
    else:
        print("No changes — fingerprints already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
