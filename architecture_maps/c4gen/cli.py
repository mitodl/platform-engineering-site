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
from . import landscape as landscape_mod
from . import pages as pages_mod
from . import puml as puml_mod
from .schema import Flow, Model

app = cyclopts.App(name="c4gen", help="Generate C4 data-flow docs (C4-PlantUML via Kroki).")

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = REPO_ROOT / "architecture_maps" / "models"
DOCS_BASE = REPO_ROOT / "docs" / "system_architecture"

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
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _known_system_ids() -> set[str]:
    """The canonical system ids = the curated model file stems (one per system)."""
    return {p.stem for p in MODELS_DIR.glob("*.yaml") if not p.name.endswith(".graph.yaml")}


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
        yaml.safe_dump(slice_, sort_keys=False, width=100), encoding="utf-8"
    )
    (MODELS_DIR / f"{name}.cycles.json").write_text(
        json.dumps(cycles, indent=2), encoding="utf-8"
    )
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
    cycles = json.loads(cycles_path.read_text(encoding="utf-8")) if cycles_path.exists() else []

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
    # $link drill-down, relative to each page's pretty URL under system_architecture/:
    #   context -> container (../container/) and known peer systems (../../<peer>/);
    #   a container box with a component view -> ../component/.
    primary = model.system_of(model.meta.primary_system)
    known = _known_system_ids()
    ctx_links: dict[str, str] = {}
    cont_links: dict[str, str] = {}
    if primary:
        ctx_links[primary.id] = "../container/"
        for cont in primary.containers:
            if cont.components:
                cont_links[cont.id] = "../component/"
    for s in model.systems:
        canon = landscape_mod.ID_ALIASES.get(s.id, s.id)
        if s.kind == "external" and canon in known and canon != model.meta.primary_system:
            if not s.context_group:
                ctx_links[s.id] = f"../../{canon}/"
            cont_links[s.id] = f"../../{canon}/"
    puml = {
        "system-context": puml_mod.render_context_puml(model, ctx_links),
        "container": puml_mod.render_container_puml(model, cont_links),
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

    out = DOCS_BASE / model.meta.primary_system
    out.mkdir(parents=True, exist_ok=True)
    svg_dir = out / "_diagrams"
    svg_dir.mkdir(parents=True, exist_ok=True)

    for dname, svg in svgs.items():
        (svg_dir / f"{dname}.svg").write_text(svg, encoding="utf-8")
    for fname, content in pages.items():
        (out / fname).write_text(content, encoding="utf-8")
    print(
        f"wrote {len(pages)} pages + {len(svgs)} SVGs to "
        f"{out.relative_to(REPO_ROOT)} (kroki: {KROKI_URL})"
    )


# Hand-authored (not generated) files that live alongside the generated docs and
# must NOT be flagged as orphans by the drift-check.
_CURATED_FILES = {"infrastructure-references.md"}


@app.command
def check(name: str) -> None:
    """Verify the committed docs for ``name`` match a fresh render (drift-check).

    Renders the model in memory and compares against the committed
    ``docs/system_architecture/<system>/`` tree: every expected page/SVG must
    exist and match (markdown with the time-varying ``generated_at`` stamp
    normalized; SVGs byte-for-byte), AND no *orphaned* generated artifact may
    linger — e.g. a ``component.md`` or ``flow-*.svg`` left behind after a
    component or scenario is removed. Hand-authored curated files
    (``_CURATED_FILES``) are exempt. Exits non-zero listing the offending files,
    so CI fails until an author regenerates and commits. Also doubles as render
    validation: a model that errors or a diagram that fails to produce a valid
    ``<svg>`` aborts the render.
    """
    model, pages, svgs = _build_outputs(name)
    out = DOCS_BASE / model.meta.primary_system

    stale: list[str] = []
    for fname, content in pages.items():
        path = out / fname
        rel = path.relative_to(REPO_ROOT)
        if not path.exists():
            stale.append(f"{rel} (missing — never generated)")
        elif _normalize_md(path.read_text(encoding="utf-8")) != _normalize_md(content):
            stale.append(f"{rel} (content differs)")
    for dname, svg in svgs.items():
        path = out / "_diagrams" / f"{dname}.svg"
        rel = path.relative_to(REPO_ROOT)
        if not path.exists():
            stale.append(f"{rel} (missing — never generated)")
        elif path.read_text(encoding="utf-8") != svg:
            stale.append(f"{rel} (content differs)")

    # Orphans: committed generated artifacts a fresh render no longer produces
    # (curated, hand-authored files are exempt).
    expected_md = set(pages) | _CURATED_FILES
    for path in sorted(out.glob("*.md")):
        if path.name not in expected_md:
            stale.append(f"{path.relative_to(REPO_ROOT)} (orphaned — no longer generated)")
    expected_svg = {f"{d}.svg" for d in svgs}
    for path in sorted((out / "_diagrams").glob("*.svg")):
        if path.name not in expected_svg:
            stale.append(f"{path.relative_to(REPO_ROOT)} (orphaned — no longer generated)")

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


LANDSCAPE_DIR = DOCS_BASE  # landscape.md lives at the System Architecture section root


def _build_landscape() -> tuple[str, str, landscape_mod.Landscape]:
    """Compose the SOA System Landscape from all curated models.

    Returns ``(page_markdown, svg, landscape)``. Renders in memory only — shared by
    ``landscape`` (which writes) and ``landscape --check`` (which diffs).
    """
    models: dict[str, Model] = {}
    for path in sorted(MODELS_DIR.glob("*.yaml")):
        if path.name.endswith(".graph.yaml"):
            continue  # generated slice, not a curated model
        models[path.stem] = Model.model_validate(_load_yaml(path))

    ls = landscape_mod.compose(models)
    generated_at = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M UTC")
    # Drill-down: each internal system box links to its overview page. From the
    # landscape pretty URL (system_architecture/landscape/) that is ../<sid>/.
    links = {sid: f"../{sid}/" for sid in ls.internal_ids()}
    svg = _kroki_svg(puml_mod.render_landscape_puml(ls, links))
    page = pages_mod.page_landscape(ls, generated_at, _version())
    return page, svg, ls


@app.command
def landscape(check: bool = False) -> None:
    """Compose + render the SOA System Landscape from every per-system model.

    Aggregates cross-service flows to the system level, reconciles cross-model ids,
    and runs SOA-wide cycle detection. With ``--check``, verify the committed page
    and SVG match a fresh render (drift-check) instead of writing them.
    """
    page, svg, ls = _build_landscape()
    page_path = LANDSCAPE_DIR / "landscape.md"
    svg_path = LANDSCAPE_DIR / "_diagrams" / "system-landscape.svg"

    if check:
        stale: list[str] = []
        for path, fresh, byte in ((page_path, page, False), (svg_path, svg, True)):
            rel = path.relative_to(REPO_ROOT)
            if not path.exists():
                stale.append(f"{rel} (missing — never generated)")
            elif (path.read_text(encoding="utf-8") if byte else _normalize_md(path.read_text(encoding="utf-8"))) != (
                fresh if byte else _normalize_md(fresh)
            ):
                stale.append(f"{rel} (content differs)")
        if stale:
            print("DRIFT: committed SOA System Landscape is stale vs a fresh render:")
            for s in stale:
                print(f"  - {s}")
            print(
                "\nRegenerate and commit:\n"
                "  uv run --directory architecture_maps --group c4gen python -m c4gen landscape"
            )
            sys.exit(1)
        print(
            f"OK: committed SOA System Landscape matches a fresh render "
            f"({len(ls.internal_ids())} systems, {len(ls.edges)} edges, "
            f"{len(ls.cycles)} cycles; kroki: {KROKI_URL})."
        )
        return

    (LANDSCAPE_DIR / "_diagrams").mkdir(parents=True, exist_ok=True)
    page_path.write_text(page, encoding="utf-8")
    svg_path.write_text(svg, encoding="utf-8")
    msg = (
        f"wrote SOA System Landscape ({len(ls.internal_ids())} systems, "
        f"{len(ls.edges)} cross-service edges, {len(ls.cycles)} cycles) to "
        f"{page_path.relative_to(REPO_ROOT)} (kroki: {KROKI_URL})"
    )
    if ls.unresolved:
        msg += f"\n  note: {len(ls.unresolved)} unresolved peer reference(s) — see page caveat"
    print(msg)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
