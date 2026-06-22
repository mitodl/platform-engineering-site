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
from importlib import metadata
from pathlib import Path

import cyclopts
import yaml

from . import extract as extract_mod
from . import pages as pages_mod
from .schema import Flow, Model

app = cyclopts.App(name="c4gen", help="Generate Mermaid C4 data-flow docs from a model.")

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = REPO_ROOT / "architecture_maps" / "models"
DOCS_BASE = REPO_ROOT / "docs" / "application_specific_guides"


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
    written = {
        "index.md": pages_mod.page_index(model),
        "system-context.md": pages_mod.page_context(model),
        "container.md": pages_mod.page_container(model),
        "data-flows.md": pages_mod.page_data_flows(model),
        "dependencies-and-cycles.md": pages_mod.page_dependencies(model, cycles, candidates),
    }
    for fname, content in written.items():
        (out / fname).write_text(content)
    print(f"wrote {len(written)} pages to {out.relative_to(REPO_ROOT)}")


@app.command
def build(name: str) -> None:
    """Extract then render in one step."""
    extract(name)
    render(name)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
