"""Markdown page assembly: wraps the C4 diagrams with prose, legends, and
provenance tables. Diagrams are C4-PlantUML rendered to SVG by Kroki at
generation time (see cli.render + puml.py); each page emits a ``.c4-box``
placeholder div that docs/javascripts/c4-zoom.js fills with the pre-rendered SVG.
"""

from __future__ import annotations

from .landscape import Landscape
from .render import ASYNC_COLOR, BANNER, SYNC_COLOR, _owner_id
from .schema import Flow, Model

_LEGEND = f"""
/// admonition | How to read these diagrams
    type: info

These are [C4 model](https://c4model.com/) diagrams (C4-PlantUML). Read them
top-down: **System Context** (the whole SOA) → **Container** (one system's
runtime units) → **Dynamic** (a single data flow, step by step).

* **People** are rounded boxes; **systems** and **containers** are
  rectangles; **databases** and **queues** have distinct shapes.
* Each arrow is a data flow labelled with *what* moves.
* <span style="color:{SYNC_COLOR}">**Solid arrows**</span> are
  **synchronous** (request/response, caller blocks).
* <span style="color:{ASYNC_COLOR}">**Amber dashed arrows**</span> are
  **asynchronous** (queued, scheduled, or event-driven — caller does not block).
* **Drag to pan, scroll to zoom.** Boxes with a link drill into the next level.
///
"""


def _diagram(model: Model, name: str) -> str:  # noqa: ARG001 (kept for signature stability)
    """A placeholder div that docs/javascripts/c4-zoom.js fills with the
    pre-rendered SVG (fetched from a sibling ``_diagrams/`` file) and turns into a
    pan/zoom viewport. Client-side injection of a static SVG keeps this
    independent of the static-site generator (works under zensical and mkdocs)."""
    return f'<div class="c4-box" data-c4-svg="../_diagrams/{name}.svg"></div>\n'


def _stamp(model: Model) -> str:
    bits = []
    if model.meta.generated_at:
        bits.append(f"Generated {model.meta.generated_at}")
    if model.meta.generator_version:
        bits.append(f"c4gen {model.meta.generator_version}")
    return f"_{' · '.join(bits)}_\n" if bits else ""


def _banner(model: Model) -> str:
    return BANNER.format(model=model.meta.primary_system)


def page_index(model: Model) -> str:
    # The infrastructure-references page is hand-authored, not generated; only
    # link to it for systems that actually have one (see Meta).
    # The component page is only generated when a container opts in by declaring
    # `components`; link to it from the index only when it exists.
    component_link = ""
    n = 5
    if model.containers_with_components():
        component_link = (
            f"\n{n}. [Components](component.md) — the code-level building blocks "
            "inside expanded containers."
        )
        n += 1
    infra_ref = (
        f"\n{n}. [Infrastructure references](infrastructure-references.md) — "
        "Pulumi, Concourse, and compose source-of-truth links (curated)."
        if model.meta.has_infrastructure_references
        else ""
    )
    return f"""{_banner(model)}# {model.meta.name} — Architecture & Data Flows

{_stamp(model)}
{model.meta.description}

This is a C4 view of **{model.meta.name}** within the MIT Open Learning SOA,
focused on **how data is created and propagated** — synchronous request paths
and asynchronous (queued, scheduled, event-driven) flows alike. Use it for
onboarding and as a holistic reference when realigning flows or hunting harmful
cycles and fragile linkages.
{_LEGEND}
## Contents

1. [System Context](system-context.md) — {model.meta.name} and the systems it exchanges data with.
2. [Containers](container.md) — the runtime units inside {model.meta.name}.
3. [Data Flows](data-flows.md) — key interactions, step by step (sync & async).
4. [Dependencies & Cycles](dependencies-and-cycles.md) — graph-derived coupling, cycles, fragile links.{component_link}{infra_ref}

## Keeping this current

These pages are **generated** from a structured model by
`architecture_maps/c4gen`. The cross-service edges are extracted deterministically
from the witan-code graph; node prose and scenarios are curated. See
[the generator README](https://github.com/mitodl/platform-engineering-site/tree/main/architecture_maps)
to regenerate after the system changes.
"""


def page_context(model: Model) -> str:
    externals = [s for s in model.systems if s.kind == "external"]
    rows = ["| System | Role |", "| --- | --- |"]
    for s in externals:
        rows.append(f"| **{s.name}** | {s.description} |")
    return f"""{_banner(model)}# System Context — {model.meta.name}

{_stamp(model)}
The widest view: **{model.meta.name}** and every external actor and system it
exchanges data with. Edges shown are **curated and code-verified**; raw
graph-derived candidates are listed under
[Dependencies & Cycles](dependencies-and-cycles.md).

/// admonition | Interactive
    type: tip

Drag to pan, scroll to zoom. **Click the {model.meta.name} box** to drill
into its [container view](container.md).
///

{_diagram(model, "system-context")}
## External systems & peers

{chr(10).join(rows)}
"""


def page_container(model: Model) -> str:
    primary = next((s for s in model.systems if s.id == model.meta.primary_system), None)
    if primary is None:
        raise ValueError(f"primary_system {model.meta.primary_system!r} not in model")
    rows = ["| Container | Technology | Responsibility |", "| --- | --- | --- |"]
    for c in primary.containers:
        rows.append(f"| **{c.name}** | {c.technology or ''} | {c.description} |")
    return f"""{_banner(model)}# Containers — {primary.name}

{_stamp(model)}
The runtime/deployable units inside **{primary.name}** and how data moves
between them and adjacent systems.

{_diagram(model, "container")}
## Containers

{chr(10).join(rows)}
"""


def page_component(model: Model) -> str:
    """One page covering every container that declares ``components`` — each as a
    section with its own C4 Component diagram and a responsibility table. Only
    emitted when at least one container is expanded to Component level."""
    expanded = model.containers_with_components()
    parts = [f"""{_banner(model)}# Components — {model.meta.name}

{_stamp(model)}
The innermost view: the **components** inside containers that have been expanded
to C4 Component level — the major code groupings within a deployable unit and how
they collaborate and reach out to adjacent containers and systems.
{_LEGEND}"""]
    for container in expanded:
        parts.append(f"## {container.name}\n")
        if container.description:
            parts.append(container.description + "\n")
        parts.append(_diagram(model, f"component-{container.id}"))
        rows = ["| Component | Technology | Responsibility |", "| --- | --- | --- |"]
        for comp in container.components:
            tech = (comp.technology or "").replace("\n", " ").replace("|", "\\|")
            desc = comp.description.replace("\n", " ").replace("|", "\\|")
            rows.append(f"| **{comp.name}** | {tech} | {desc} |")
        parts.append("\n".join(rows) + "\n")
    return "\n".join(parts)


def page_data_flows(model: Model) -> str:
    parts = [f"""{_banner(model)}# Data Flows — {model.meta.name}

{_stamp(model)}
Each scenario below replays one interaction as a C4 **Dynamic** diagram.
Amber steps are asynchronous (queued / scheduled / event-driven).
{_LEGEND}"""]
    for sc in model.scenarios:
        parts.append(f"## {sc.title}\n")
        if sc.description:
            parts.append(sc.description + "\n")
        parts.append(_diagram(model, f"flow-{sc.id}"))

    if model.etl_sources:
        parts.append("## Ingestion sources (ETL)\n")
        parts.append(
            "Every external source the `edx_content` / `default` Celery workers "
            "pull from, with transport and cadence. ⚠️ marks brittle linkages "
            "(HTML/token scrapes, hardcoded URLs).\n"
        )
        rows = ["| Source | Transport | Cadence | Data | Source of truth |",
                "| --- | --- | --- | --- | --- |"]
        for s in sorted(model.etl_sources, key=lambda x: x.name):
            warn = "⚠️ " if s.fragile else ""
            ref = ""
            if s.source_ref and s.source_ref.path:
                ref = f"`{s.source_ref.path}`"
            rows.append(
                f"| {warn}**{s.name}** | {s.transport} | {s.cadence} | {s.data} | {ref} |"
            )
        parts.append("\n".join(rows) + "\n")
    return "\n".join(parts)


def page_dependencies(model: Model, cycles: list[list[str]], candidates: list[Flow]) -> str:
    # curated cross-service edges actually drawn in the diagrams
    cross = [f for f in model.flows if "cross-service" in f.tags]
    # dependency matrix at system level (curated, verified)
    # Resolve container ids (e.g. celery-edx) up to their owning system (mit-learn)
    # so the matrix is system-to-system.
    deps: dict[str, set[str]] = {}
    for f in cross:
        src = _owner_id(model, f.source)
        tgt = _owner_id(model, f.target)
        if src != tgt:
            deps.setdefault(src, set()).add(tgt)
    matrix = ["| Depends on → | …on these systems |", "| --- | --- |"]
    for src in sorted(deps):
        matrix.append(f"| **{src}** | {', '.join(sorted(deps[src]))} |")
    matrix_md = "\n".join(matrix) if deps else "_No curated cross-service edges._"

    if cycles:
        cyc_lines = ["/// admonition | Dependency cycles detected", "    type: danger", ""]
        for c in cycles:
            cyc_lines.append(f"* `{ ' → '.join(c + [c[0]]) }`")
        cyc_lines.append("///")
        cyc_md = "\n".join(cyc_lines)
    else:
        cyc_md = (
            "/// admonition | No cycles\n    type: success\n\n"
            "No cross-service dependency cycles detected.\n///"
        )

    fragile = [f for f in model.flows if "fragile" in f.tags]
    frag_md = "\n".join(
        f"- **{f.source} → {f.target}**: {f.label} — {f.data}" for f in fragile
    ) or "_None flagged._"

    return f"""{_banner(model)}# Dependencies & Cycles — {model.meta.name}

{_stamp(model)}
Coupling between {model.meta.name} and the rest of the SOA. The **matrix** and
**cycles** below come from the deterministic witan-code graph extraction; the
**candidate edges** are raw graph findings that still need human confirmation.

## Cross-service dependency matrix (curated)

{matrix_md}

## Cycles

{cyc_md}

/// admonition | Interpreting graph candidates
    type: warning

Cross-repo edges are matched by normalized endpoint path. Two services that
both define e.g. `/api/v0/users/me/`, or a client checked into a repo for
**load testing**, produce *phantom* edges. Confirm each candidate against the
actual client/route code before treating it as a real runtime dependency.
///

## Candidate edges (graph-derived, unverified)

{_candidate_rows(candidates)}

## Fragile / noteworthy linkages

{frag_md}
"""


def _candidate_rows(candidates: list[Flow]) -> str:
    if not candidates:
        return "_None extracted._"
    rows = ["| Consumer → Provider | Contract sample | Source of truth |",
            "| --- | --- | --- |"]
    for f in sorted(candidates, key=lambda x: (x.source, x.target)):
        url = f.provenance.url()
        loc = f"[{f.provenance.path}]({url})" if url and f.provenance.path else (
            f"`{f.provenance.path}`" if f.provenance.path else "—"
        )
        rows.append(
            f"| {f.source} → {f.target} ({f.label}) | `{f.provenance.contract_key or ''}` | {loc} |"
        )
    return "\n".join(rows)


_LANDSCAPE_BANNER = (
    "<!-- GENERATED by architecture_maps/c4gen — do not hand-edit.\n"
    "     The System Landscape is COMPOSED from every architecture_maps/models/*.yaml.\n"
    "     Edit the per-system models, then (from the repo root, with a local Kroki\n"
    "     running) regenerate with:\n"
    "       uv run --directory architecture_maps --group c4gen python -m c4gen landscape\n"
    "     See architecture_maps/README.md. -->\n"
)


def page_landscape(landscape: Landscape, generated_at: str, version: str) -> str:
    """Render the composed SOA System Landscape page (diagram + SOA-wide summary)."""
    stamp = f"_Generated {generated_at} · c4gen {version}_\n"

    # System-level dependency matrix: each internal system → systems it calls.
    deps: dict[str, set[str]] = {}
    for edge in landscape.edges:
        if landscape.node(edge.source).internal:
            deps.setdefault(edge.source, set()).add(edge.target)
    matrix = ["| System | Depends on → |", "| --- | --- |"]
    for src in landscape.internal_ids():
        targets = sorted(deps.get(src, set()))
        matrix.append(f"| **{landscape.node(src).name}** | {', '.join(targets) or '—'} |")
    matrix_md = "\n".join(matrix)

    if landscape.cycles:
        cyc = ["/// admonition | SOA-wide dependency cycles", "    type: danger", ""]
        cyc += [f"* `{' → '.join(c + [c[0]])}`" for c in landscape.cycles]
        cyc.append("///")
        cyc_md = "\n".join(cyc)
    else:
        cyc_md = (
            "/// admonition | No cross-service cycles\n    type: success\n\n"
            "No directed cross-service dependency cycles detected across the SOA.\n///"
        )

    if landscape.unresolved:
        rows = "\n".join(
            f"- `{rid}` (referenced in **{model}**)" for model, rid in landscape.unresolved
        )
        unresolved_md = (
            "/// admonition | Unresolved peer references\n    type: warning\n\n"
            "Flow endpoints that did not resolve to a known landscape node "
            "(shown for transparency; not drawn):\n\n"
            f"{rows}\n///"
        )
    else:
        unresolved_md = (
            "/// admonition | Composition clean\n    type: success\n\n"
            "Every cross-service flow endpoint resolved to a known system or shared "
            "platform node.\n///"
        )

    n_internal = len(landscape.internal_ids())

    return f"""{_LANDSCAPE_BANNER}# SOA System Landscape — MIT Open Learning

{stamp}
The holistic, whole-system view: every mapped MIT Open Learning system and the
**cross-service data flows** between them, composed from the {n_internal} per-system
C4 models. Use it for onboarding and SOA-wide decisions — surfacing dependencies,
cycles, and the shared platform every system leans on. Each per-system guide drills
into containers and flows; this page is the map of maps.
{_LEGEND}
<div class="c4-box" data-c4-svg="../_diagrams/system-landscape.svg"></div>

## System dependency matrix

System-to-system coupling aggregated from the curated cross-service flows across
all models (container-level flows lifted to their owning system; deduped).

{matrix_md}

## Cross-service cycles

Computed over the owned internal systems only — shared gateway/identity/LMS infra
(APISIX, Keycloak, Open edX) sits in nearly every path and would manufacture
cycles that aren't harmful coupling.

{cyc_md}

## Shared platform & libraries

The apps share a common platform: **APISIX** (gateway, OIDC), **Keycloak** (SSO),
and **HashiCorp Vault** (secrets/credentials), with **Open edX** behind the
course-delivery apps. Shared Django/identity libraries — **ol-django** and
**ol-keycloak** — are used across systems (not drawn as nodes).

{unresolved_md}

## Keeping this current

This page is **composed** from `architecture_maps/models/*.yaml` by
`architecture_maps/c4gen`. Update a per-system model and regenerate with
`c4gen landscape`; CI fails if the committed page/diagram drift.
"""
