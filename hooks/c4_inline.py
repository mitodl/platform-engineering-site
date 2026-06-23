"""mkdocs hook: inline the C4 architecture SVGs at build time.

c4gen renders each C4-PlantUML diagram to an SVG file (via Kroki) and leaves a
``<!--c4-svg:PATH-->`` marker in the page. We replace that marker with the SVG
content AFTER markdown has run (so the SVG isn't mangled by the markdown
pipeline), wrapped in a ``.c4-box`` that docs/javascripts/c4-zoom.js turns into a
pan/zoom viewport. Drill-down links are native (PlantUML ``$link``).
"""

from __future__ import annotations

import re
from pathlib import Path

_MARKER = re.compile(r"<!--\s*c4-svg:([^>]+?)\s*-->")


def on_page_content(html: str, page=None, config=None, files=None) -> str:  # noqa: ARG001
    if "c4-svg:" not in html:
        return html
    docs_dir = Path(config["docs_dir"])

    def replace(match: re.Match) -> str:
        rel = match.group(1).strip()
        svg = docs_dir / rel
        if not svg.is_file():
            return f'<div class="c4-box">[missing diagram: {rel}]</div>'
        return f'<div class="c4-box">{svg.read_text(encoding="utf-8")}</div>'

    return _MARKER.sub(replace, html)
