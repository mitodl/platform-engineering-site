# architecture_maps — C4 data-flow maps for the MIT Open Learning SOA

A **repeatable, hybrid** process for generating and maintaining
[C4 model](https://c4model.com/) data-flow documentation from a structured model.
The output lands in the docs site under
`docs/application_specific_guides/<system>/architecture/`.

Diagrams are **C4-PlantUML rendered to SVG by [Kroki](https://kroki.io/)** at
generation time (we moved off Mermaid C4 — its Graphviz layout handles our
hub-and-spoke graphs far better: no overlapping edge labels, wrapped shape
descriptions, dashed async edges, and native clickable drill-down via `$link`).
The SVGs are written to a sibling `_diagrams/` directory and committed;
`docs/javascripts/c4-zoom.js` fetches and injects them client-side (independent
of the static-site generator — works under zensical and mkdocs) and layers on
svg-pan-zoom. Rendering happens locally against a Kroki container, so the
published site has no external render dependency.

The first system mapped is **MIT Learn**; the process is designed to fan out to
the rest of the SOA (one model file per system).

## Why hybrid?

Two halves, each playing to its strength:

| Half | What it does | Why |
| --- | --- | --- |
| **Deterministic** (`extract.py` + `openmetadata.py`) | Two lineage sources emit cross-service edge *candidates* + a cycle report: the **witan-code** cross-repo code graph (runtime HTTP contracts) and the **OpenMetadata** catalog (warehouse/dbt data lineage). | Edges come from real code contracts and real data lineage, refresh on demand, and can run in CI. No drift. |
| **Curated** (`models/<system>.yaml`) | Humans/LLM author node prose, the verified flows actually drawn, async/ETL flows, and scenario narratives. | Neither source sees everything (the code graph misses ETL/events; lineage misses sync request paths) and both produce *phantom* edges (shared endpoint paths, load-testing clients, name-prefix mis-attribution). Curation confirms and enriches. |

The two deterministic sources are complementary: the **code graph** captures
synchronous service-to-service HTTP calls; **OpenMetadata lineage** captures the
asynchronous data-platform flows (each service's tables landing in the lake and
being joined across systems in dbt). Pick one or merge both with
`--source {graph,openmetadata,both}` on `extract`/`build`. Candidates carry
`provenance.derived_from` (`graph` | `openmetadata`) so a reader can tell — and
trace — where each came from; graph edges link the consumer source file, lineage
edges link the catalog asset.

The renderer merges them — **curated edges are drawn; raw graph edges appear only
as labelled candidates** on the Dependencies page, with a caveat to confirm each.

## Layout

```
architecture_maps/
  c4gen/
    schema.py    # the structured model (pydantic): systems, containers, flows, scenarios, etl_sources
    extract.py   # deterministic: witan-code bridge -> cross-service candidates + cycles
    openmetadata.py # deterministic: OpenMetadata catalog lineage -> cross-service candidates
    puml.py      # model -> C4-PlantUML (Context / Container / Dynamic)
    render.py    # shared rendering helpers (alias/quote/tagline/owner resolution)
    pages.py     # markdown page assembly (legend, tables, provenance, diagram placeholders)
    cli.py       # cyclopts CLI: extract / render (-> Kroki SVGs) / build
  docker-compose.yml  # local Kroki for rendering
  models/
    <system>.yaml          # CURATED model (source of truth for prose + verified flows)
    <system>.graph.yaml    # GENERATED graph slice (do not hand-edit)
    <system>.cycles.json   # GENERATED cycle report (do not hand-edit)
```

## Usage

Run these **from the repo root** (the `--directory architecture_maps` flag makes
`python -m c4gen` resolve regardless of where you are). **Rendering needs a local
Kroki server** (it turns the C4-PlantUML into SVG):

```bash
docker compose -f architecture_maps/docker-compose.yml up -d kroki   # renderer on :8000

# the common case — re-render docs + SVGs from the committed model (no witan-code):
uv run --directory architecture_maps --group c4gen python -m c4gen render mit-learn
```

The other two commands are for **authoring** and additionally need the
**witan-code** graph (below):

```bash
uv run --directory architecture_maps --group c4gen python -m c4gen extract mit-learn  # graph slice + cycles
uv run --directory architecture_maps --group c4gen python -m c4gen build mit-learn    # extract + render
```

`extract` (and therefore `build`) defaults to the **witan-code** graph source,
which requires the witan-code tool installed (`uv tool install witan-code`) with
an indexed graph — it reads the shared bridge store the
[`witan-code deps`](https://github.com/mitodl/agent-kit) command uses. If the
repos aren't indexed, run `witan-code index <repo>` first. A non-authoring
contributor who only changed a model usually just needs `render` + Kroki.

To pull the **OpenMetadata** data-lineage source instead of (or alongside) the
graph, set `C4GEN_OPENMETADATA_URL` to the catalog base URL (e.g.
`https://data.ol.mit.edu`) and `C4GEN_OPENMETADATA_TOKEN` to a JWT bot token,
then pass `--source openmetadata` or `--source both`:

```bash
export C4GEN_OPENMETADATA_URL=https://data.ol.mit.edu C4GEN_OPENMETADATA_TOKEN=...
uv run --directory architecture_maps --group c4gen python -m c4gen extract mit-learn --source both
```

OpenMetadata attributes each warehouse table to a source system via its
`<layer>__<source>__…` name prefix and emits a candidate edge wherever a single
downstream table is fed by more than one source system (a cross-service join), or
a cross-cutting `combined` model feeds the synthetic `ol-data-platform` node.
When the catalog is unset or unreachable the source degrades to an empty slice,
so `--source both` never breaks a graph-only run.

> Note: `extract` writes the *combined* slice to `models/<system>.graph.yaml`.
> Running `--source openmetadata` alone overwrites the graph slice (and vice
> versa); use `--source both` to refresh both at once.

The generated pages carry a "do not hand-edit" banner; the only files you edit by
hand are `models/<system>.yaml` and the curated
`.../architecture/infrastructure-references.md`.

## The update loop (when the system changes)

1. **Re-index** the changed repos in witan-code (or rely on the team's indexer).
2. `python -m c4gen extract <system>` — refresh candidates + cycles.
3. Review `models/<system>.cycles.json` and the new candidate edges. Confirm real
   ones into `models/<system>.yaml` as curated flows; ignore phantoms.
4. Update node prose / async flows / scenarios in the model as needed.
5. `python -m c4gen render <system>` and commit the diff.

### Optional LLM/skill assist

Steps 3–4 are where an LLM helps most: point an agent (with the witan-code MCP
tools) at the new candidates and the changed code and have it propose model
edits. The deterministic extractor keeps it honest; the model diff stays
reviewable. This is the "combination" path — deterministic edges, LLM-assisted
curation.

## Adding another system

1. Create `models/<system>.yaml` (copy `mit-learn.yaml` as a template). Set
   `meta.primary_system` and `meta.api_container`.
2. Define actors, the primary system's containers, peer/external systems, flows,
   and scenarios. Lean on `witan-code deps --repo <system>` and the
   `code_interface_*` MCP tools to seed cross-service edges.
3. `python -m c4gen build <system>`, then add the new pages to `mkdocs.yml` nav.

## Conventions

- **Sync vs async**: a flow's `sync: false` renders with an `async ·` technology
  label and an amber line. This is the data-flow distinction the maps exist for.
- **Component level**: not emitted yet, but `Container.components` is reserved so
  a Component view can be added without reshaping the model.
- **Provenance**: every graph candidate carries the consumer file it came from;
  curated flows should cite a `source_ref` / `data` path where practical.
