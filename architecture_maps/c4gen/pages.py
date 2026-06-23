"""Markdown page assembly: wraps the C4 diagrams with prose, legends, and
provenance tables. Diagrams are C4-PlantUML rendered to SVG by Kroki at
generation time (see cli.render + puml.py); each page emits a ``.c4-box``
placeholder div that docs/javascripts/c4-zoom.js fills with the pre-rendered SVG.
"""

from __future__ import annotations

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
4. [Dependencies & Cycles](dependencies-and-cycles.md) — graph-derived coupling, cycles, fragile links.
5. [Infrastructure references](infrastructure-references.md) — Pulumi, Concourse, and compose source-of-truth links (curated).

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
