"""``c4gen`` — generate C4 data-flow docs (C4-PlantUML, rendered to SVG by Kroki).

Hybrid pipeline:

    extract   witan-code graph  -> models/<name>.graph.yaml (+ .cycles.json)
    render    curated + graph    -> docs/.../architecture/*.md + _diagrams/*.svg
    build     = extract then render

The curated model (``models/<name>.yaml``) holds nodes, async/code-derived
flows, and scenario narratives. The extractor refreshes the deterministic
cross-service slice. The renderer merges them (curated wins), renders each
diagram to SVG via Kroki (see ``puml.py``), and writes the pages.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sys
from importlib import metadata
from pathlib import Path
from urllib import error, request

import cyclopts
import yaml

from . import extract as extract_mod
from . import pages as pages_mod
from . import puml as puml_mod
from .schema import Flow, Model

app = cyclopts.App(name="c4gen", help="Generate C4 data-flow docs (C4-PlantUML via Kroki).")

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = REPO_ROOT / "architecture_maps" / "models"
DOCS_BASE = REPO_ROOT / "docs" / "application_specific_guides"

# Kroki renders the C4-PlantUML source to SVG at generation time. Default to the
# local container (see architecture_maps/docker-compose.yml); override in CI.
KROKI_URL = os.environ.get("C4GEN_KROKI_URL", "http://localhost:8000").rstrip("/")


def _kroki_svg(puml: str) -> str:
    """Render C4-PlantUML to an inline-ready SVG string via Kroki."""
    url = f"{KROKI_URL}/c4plantuml/svg"
    req = request.Request(
        url, data=puml.encode("utf-8"), headers={"Content-Type": "text/plain"}, method="POST"
    )
    try:
        with request.urlopen(req, timeout=30) as resp:  # noqa: S310 (trusted local URL)
            svg = resp.read().decode("utf-8")
    except error.URLError as exc:
        raise RuntimeError(
            f"Kroki render failed at {url}: {exc}. Start it with "
            "`docker compose -f architecture_maps/docker-compose.yml up -d kroki` "
            "or set C4GEN_KROKI_URL."
        ) from exc
    # Strip the XML prolog/doctype so the <svg> inlines cleanly into HTML. A 200
    # with no <svg> means Kroki returned something unexpected — fail loudly rather
    # than write a bogus .svg file.
    i = svg.find("<svg")
    if i == -1:
        raise RuntimeError(f"Kroki returned a non-SVG response from {url}: {svg[:200]!r}")
    return svg[i:]


def _version() -> str:
    try:
        return metadata.version("platform-engineering-site")
    except metadata.PackageNotFoundError:
        return "dev"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def _merge_systems(curated: dict, slice_: dict) -> dict:
    """Add any graph-only systems as stubs so candidate edges have a node to name.

    Only *systems* are merged. Graph-derived *flows* are deliberately NOT drawn in
    the diagrams — they are unverified candidates (endpoint-key collisions and
    load-testing clients produce phantom edges). They are surfaced instead as an
    evidence table on the dependencies page, and they feed cycle detection.
    """
    merged = json.loads(json.dumps(curated))  # deep copy
    sys_by_id = {s["id"]: s for s in merged.setdefault("systems", [])}
    for s in slice_.get("systems", []):
        if s["id"] not in sys_by_id:
            merged["systems"].append(s)
    return merged


@app.command
def extract(name: str) -> None:
    """Refresh the deterministic cross-service slice for model ``name`` from the graph."""
    rows = extract_mod.load_bindings()
    contracts = extract_mod.group_contracts(rows)
    edges = extract_mod.cross_repo_edges(contracts, kinds=("endpoint",))
    cycles = extract_mod.find_cycles(edges)
    slice_ = extract_mod.build_flow_slice(edges)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    (MODELS_DIR / f"{name}.graph.yaml").write_text(
        yaml.safe_dump(slice_, sort_keys=False, width=100)
    )
    (MODELS_DIR / f"{name}.cycles.json").write_text(json.dumps(cycles, indent=2))
    print(f"extracted {len(slice_['flows'])} cross-service flows, {len(cycles)} cycles")


# The per-page provenance stamp (pages.py `_stamp`) embeds `meta.generated_at`,
# which is the current wall-clock time at render. It is the ONLY non-deterministic
# byte in the generated output, so drift detection must ignore it when comparing
# markdown. SVGs are deterministic for a fixed model + Kroki image, so they are
# compared byte-for-byte.
_STAMP_RE = re.compile(r"^_Generated .*·.*_$", re.MULTILINE)


def _normalize_md(text: str) -> str:
    """Drop the generated-at provenance line so drift compares meaningful content."""
    return _STAMP_RE.sub("_Generated <stamp>_", text)


def _build_outputs(name: str) -> tuple[Model, dict[str, str], dict[str, str]]:
    """Render model ``name`` to in-memory outputs without touching the docs tree.

    Returns ``(model, pages, svgs)`` where ``pages`` maps page filename -> markdown
    and ``svgs`` maps diagram name -> SVG string. Shared by ``render`` (which writes
    them) and ``check`` (which diffs them against the committed tree). The
    ``generated_at`` stamp is set here; callers that care about drift normalize it.
    """
    curated = _load_yaml(MODELS_DIR / f"{name}.yaml")
    slice_path = MODELS_DIR / f"{name}.graph.yaml"
    slice_ = _load_yaml(slice_path) if slice_path.exists() else {}
    cycles_path = MODELS_DIR / f"{name}.cycles.json"
    cycles = json.loads(cycles_path.read_text()) if cycles_path.exists() else []

    merged = _merge_systems(curated, slice_)
    merged.setdefault("meta", {})["generated_at"] = (
        datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M UTC")
    )
    merged["meta"]["generator_version"] = _version()
    model = Model.model_validate(merged)

    # Graph-derived candidate edges (evidence, not drawn) — validated for table use.
    candidates = [Flow.model_validate(f) for f in slice_.get("flows", [])]

    # Render each C4-PlantUML diagram to an SVG via Kroki. Each page emits a
    # `.c4-box` placeholder that docs/javascripts/c4-zoom.js fills with the SVG.
    primary = model.system_of(model.meta.primary_system)
    puml = {
        "system-context": puml_mod.render_context_puml(
            model, {primary.name: "../container/"} if primary else None
        ),
        "container": puml_mod.render_container_puml(model),
    }
    for sc in model.scenarios:
        puml[f"flow-{sc.id}"] = puml_mod.render_dynamic_puml(model, sc.id)
    # Component view: only for containers that opt in by declaring `components`.
    # When none do (true for every model today) nothing is emitted and the page
    # is skipped, so the no-components path stays graceful.
    expanded = model.containers_with_components()
    for container in expanded:
        puml[f"component-{container.id}"] = puml_mod.render_component_puml(
            model, container.id
        )
    svgs = {dname: _kroki_svg(src) for dname, src in puml.items()}

    pages = {
        "index.md": pages_mod.page_index(model),
        "system-context.md": pages_mod.page_context(model),
        "container.md": pages_mod.page_container(model),
        "data-flows.md": pages_mod.page_data_flows(model),
        "dependencies-and-cycles.md": pages_mod.page_dependencies(model, cycles, candidates),
    }
    if expanded:
        pages["component.md"] = pages_mod.page_component(model)
    return model, pages, svgs


@app.command
def render(name: str) -> None:
    """Render markdown pages for model ``name`` (uses an existing graph slice if present)."""
    model, pages, svgs = _build_outputs(name)

    out = DOCS_BASE / model.meta.primary_system / "architecture"
    out.mkdir(parents=True, exist_ok=True)
    svg_dir = out / "_diagrams"
    svg_dir.mkdir(parents=True, exist_ok=True)

    for dname, svg in svgs.items():
        (svg_dir / f"{dname}.svg").write_text(svg)
    for fname, content in pages.items():
        (out / fname).write_text(content)
    print(
        f"wrote {len(pages)} pages + {len(svgs)} SVGs to "
        f"{out.relative_to(REPO_ROOT)} (kroki: {KROKI_URL})"
    )


@app.command
def check(name: str) -> None:
    """Verify the committed pages/SVGs for ``name`` match a fresh render (drift-check).

    Renders the model in memory and compares against the committed
    ``docs/.../architecture/`` tree. Markdown is compared with the (time-varying)
    ``generated_at`` stamp normalized away; SVGs are compared byte-for-byte (they
    are deterministic for a fixed model + Kroki image). Exits non-zero — listing
    the stale/missing files — if anything differs, so CI fails until an author
    regenerates and commits. Also doubles as render validation: a model that errors
    or a diagram that fails to produce a valid ``<svg>`` aborts the render.
    """
    model, pages, svgs = _build_outputs(name)
    out = DOCS_BASE / model.meta.primary_system / "architecture"

    stale: list[str] = []
    for fname, content in pages.items():
        path = out / fname
        rel = path.relative_to(REPO_ROOT)
        if not path.exists():
            stale.append(f"{rel} (missing — never generated)")
        elif _normalize_md(path.read_text()) != _normalize_md(content):
            stale.append(f"{rel} (content differs)")
    for dname, svg in svgs.items():
        path = out / "_diagrams" / f"{dname}.svg"
        rel = path.relative_to(REPO_ROOT)
        if not path.exists():
            stale.append(f"{rel} (missing — never generated)")
        elif path.read_text() != svg:
            stale.append(f"{rel} (content differs)")

    if stale:
        print(f"DRIFT: committed docs for {name!r} are stale vs a fresh render:")
        for s in stale:
            print(f"  - {s}")
        print(
            "\nRegenerate and commit:\n"
            f"  uv run --directory architecture_maps --group c4gen python -m c4gen render {name}"
        )
        sys.exit(1)
    print(f"OK: committed docs for {name!r} match a fresh render ({len(pages)} pages, "
          f"{len(svgs)} SVGs; kroki: {KROKI_URL}).")


@app.command
def build(name: str) -> None:
    """Extract then render in one step."""
    extract(name)
    render(name)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
