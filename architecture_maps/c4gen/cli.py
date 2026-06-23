"""``c4gen`` — generate Mermaid C4 data-flow docs from a structured model.

Hybrid pipeline:

    extract   witan-code graph  -> models/<name>.graph.yaml (+ .cycles.json)
    render    curated + graph    -> docs/.../architecture/*.md
    build     = extract then render

The curated model (``models/<name>.yaml``) holds nodes, async/code-derived
flows, and scenario narratives. The extractor refreshes the deterministic
cross-service slice. The renderer merges them (curated wins) and writes pages.
"""

from __future__ import annotations

import datetime
import json
import os
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
    # Strip the XML prolog/doctype so the <svg> inlines cleanly into HTML.
    i = svg.find("<svg")
    return svg[i:] if i != -1 else svg


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


@app.command
def render(name: str) -> None:
    """Render markdown pages for model ``name`` (uses an existing graph slice if present)."""
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

    out = DOCS_BASE / model.meta.primary_system / "architecture"
    out.mkdir(parents=True, exist_ok=True)

    # Render each C4-PlantUML diagram to an SVG file via Kroki. A mkdocs hook
    # (hooks/c4_inline.py) inlines these into the pages at build time.
    primary = model.system_of(model.meta.primary_system)
    diagrams = {
        "system-context": puml_mod.render_context_puml(
            model, {primary.name: "../container/"} if primary else None
        ),
        "container": puml_mod.render_container_puml(model),
    }
    for sc in model.scenarios:
        diagrams[f"flow-{sc.id}"] = puml_mod.render_dynamic_puml(model, sc.id)

    svg_dir = out / "_diagrams"
    svg_dir.mkdir(parents=True, exist_ok=True)
    for dname, src in diagrams.items():
        (svg_dir / f"{dname}.svg").write_text(_kroki_svg(src))

    written = {
        "index.md": pages_mod.page_index(model),
        "system-context.md": pages_mod.page_context(model),
        "container.md": pages_mod.page_container(model),
        "data-flows.md": pages_mod.page_data_flows(model),
        "dependencies-and-cycles.md": pages_mod.page_dependencies(model, cycles, candidates),
    }
    for fname, content in written.items():
        (out / fname).write_text(content)
    print(
        f"wrote {len(written)} pages + {len(diagrams)} SVGs to "
        f"{out.relative_to(REPO_ROOT)} (kroki: {KROKI_URL})"
    )


@app.command
def build(name: str) -> None:
    """Extract then render in one step."""
    extract(name)
    render(name)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
