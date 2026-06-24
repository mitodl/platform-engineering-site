"""C4-PlantUML renderer (rendered to SVG via Kroki).

We render C4 diagrams with C4-PlantUML instead of Mermaid: its Graphviz layout
handles our hub-and-spoke graphs far better (no overlapping edge labels, wrapped
shape descriptions), it supports native clickable drill-down (`$link=`), and
dashed async edges. The diagrams are rendered to SVG at generation time by a
Kroki server (see cli.render), so the published pages need no client-side
diagram engine — only svg-pan-zoom for pan/zoom.

This module mirrors render.py (same model, same grouping/tagline conventions)
but emits C4-PlantUML text. The Mermaid renderer is kept for reference.
"""

from __future__ import annotations

from .landscape import Landscape
from .render import (
    _group_alias,
    _owner_id,
    _short,
    _tagline,
    alias,
    q,
)
from .schema import Flow, Model

ASYNC_COLOR = "#e8a33d"
# A relationship tag that draws async edges dashed + amber. Note: send the
# diagram to Kroki as text/plain (not form-encoded) or long diagrams overflow
# Kroki's form-field limit.
_ASYNC_TAG = f'AddRelTag("async", $lineStyle=DashedLine(), $lineColor="{ASYNC_COLOR}")'

_SHAPE_MACRO = {"container": "Container", "db": "ContainerDb", "queue": "ContainerQueue"}


def _title(text: str) -> str:
    # PlantUML title runs to end of line; keep it plain text.
    return " ".join((text or "").split())


def _rel(src: str, tgt: str, label: str, sync: bool) -> str:
    tag = "" if sync else ', $tags="async"'
    return f"Rel({src}, {tgt}, {q(_short(label, 50))}{tag})"


# --------------------------------------------------------------------------
# System Landscape (composed from every per-system model)
# --------------------------------------------------------------------------
def render_landscape_puml(landscape: Landscape, links: dict[str, str] | None = None) -> str:
    """Render the composed SOA System Landscape.

    Internal systems and the curated shared platform/AI nodes are drawn grouped by
    domain (``Enterprise_Boundary``); aggregated cross-service edges carry a
    representative label and keep sync/async styling. See ``landscape.compose``.
    """
    links = links or {}
    out = [
        "@startuml",
        "!include <C4/C4_Context>",
        _ASYNC_TAG,
        "title System Landscape - MIT Open Learning SOA",
    ]
    for group, node_ids in landscape.groups().items():
        out.append(f"Enterprise_Boundary({_group_alias(group)}, {q(group)}) {{")
        for nid in node_ids:
            node = landscape.node(nid)
            macro = "System" if node.internal else "System_Ext"
            link = links.get(nid)
            link_arg = f', $link="{link}"' if link else ""
            out.append(
                f"  {macro}({alias(nid)}, {q(node.name)}, {q(_tagline(node.description))}{link_arg})"
            )
        out.append("}")
    for edge in landscape.edges:
        out.append(_rel(alias(edge.source), alias(edge.target), edge.summary(), edge.sync))
    out.append("@enduml")
    return "\n".join(out)


# --------------------------------------------------------------------------
# System Context
# --------------------------------------------------------------------------
def render_context_puml(model: Model, links: dict[str, str] | None = None) -> str:
    links = links or {}
    out = [
        "@startuml",
        "!include <C4/C4_Context>",
        _ASYNC_TAG,
        f"title System Context - {_title(model.meta.name)}",
    ]

    groups: dict[str, list] = {}
    for s in model.systems:
        if s.kind == "external" and s.context_group:
            groups.setdefault(s.context_group, []).append(s)

    def ctx_node(system_id: str) -> str:
        s = next((x for x in model.systems if x.id == system_id), None)
        return _group_alias(s.context_group) if (s and s.context_group) else alias(system_id)

    used = {f.source for f in model.flows} | {f.target for f in model.flows}
    for actor in model.actors:
        if actor.id in used:
            out.append(f"Person({alias(actor.id)}, {q(actor.name)}, {q(_tagline(actor.description))})")
    for s in model.systems:
        if s.context_group:
            continue
        macro = "System" if s.kind == "internal" else "System_Ext"
        link = links.get(s.id)
        link_arg = f', $link="{link}"' if link else ""
        out.append(f"{macro}({alias(s.id)}, {q(s.name)}, {q(_tagline(s.description))}{link_arg})")
    for label, members in groups.items():
        names = ", ".join(m.name for m in members)
        out.append(f"System_Ext({_group_alias(label)}, {q(label)}, {q(_short(names, 48))})")

    seen: dict[tuple[str, str], Flow] = {}
    pairs: set[frozenset[str]] = set()
    for f in model.flows:
        src = ctx_node(_owner_id(model, f.source))
        tgt = ctx_node(_owner_id(model, f.target))
        if src == tgt:
            continue
        key = frozenset((src, tgt))
        if key in pairs:  # collapse opposite-direction duplicates at this level
            continue
        pairs.add(key)
        seen[(src, tgt)] = f
    for (src, tgt), f in seen.items():
        out.append(_rel(src, tgt, f.label, f.sync))
    out.append("@enduml")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Container
# --------------------------------------------------------------------------
def render_container_puml(model: Model, links: dict[str, str] | None = None) -> str:
    links = links or {}
    primary = next((s for s in model.systems if s.id == model.meta.primary_system), None)
    if primary is None:
        raise ValueError(f"primary_system {model.meta.primary_system!r} not in model")
    container_ids = {c.id for c in primary.containers}

    out = [
        "@startuml",
        "!include <C4/C4_Container>",
        _ASYNC_TAG,
        f"title Container diagram - {_title(primary.name)}",
    ]

    touch = _nodes_touching(model, container_ids | {primary.id})
    for actor in model.actors:
        if actor.id in touch:
            out.append(f"Person({alias(actor.id)}, {q(actor.name)}, {q(_tagline(actor.description))})")

    out.append(f"System_Boundary({alias(primary.id)}_b, {q(primary.name)}) {{")
    for c in primary.containers:
        macro = _SHAPE_MACRO[c.shape]
        link = links.get(c.id)
        link_arg = f', $link="{link}"' if link else ""
        out.append(
            f"  {macro}({alias(c.id)}, {q(c.name)}, {q(c.technology or '')}, "
            f"{q(_tagline(c.description))}{link_arg})"
        )
    out.append("}")

    for system in model.systems:
        if system.id == primary.id or system.id not in touch:
            continue
        link = links.get(system.id)
        link_arg = f', $link="{link}"' if link else ""
        out.append(
            f"System_Ext({alias(system.id)}, {q(system.name)}, "
            f"{q(_tagline(system.description))}{link_arg})"
        )

    entry = model.meta.api_container
    seen: set[tuple[str, str, str]] = set()
    for flow in model.flows:
        if not (
            _drawn(model, flow.source, container_ids, touch)
            and _drawn(model, flow.target, container_ids, touch)
        ):
            continue
        s = flow.source if flow.source in container_ids else _owner_id(model, flow.source)
        t = flow.target if flow.target in container_ids else _owner_id(model, flow.target)
        if entry:
            s = entry if s == primary.id else s
            t = entry if t == primary.id else t
        if s == t:
            continue
        key = (s, t, _short(flow.label, 50))
        if key in seen:
            continue
        seen.add(key)
        out.append(_rel(alias(s), alias(t), flow.label, flow.sync))
    out.append("@enduml")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Component (one per container that declares components)
# --------------------------------------------------------------------------
def render_component_puml(model: Model, container_id: str) -> str:
    """Zoom into one container's ``components`` (C4 Component level).

    Components are drawn inside a ``Container_Boundary``; their ``relationships``
    are drawn as edges to sibling components (intra-container) or out to adjacent
    containers / external systems, which are declared as the surrounding context.
    This is a projection over the same model — it never alters the other views.
    """
    container = model.container_of(container_id)
    if container is None:
        raise ValueError(f"no container {container_id!r}")
    if not container.components:
        raise ValueError(f"container {container_id!r} declares no components")

    component_ids = {comp.id for comp in container.components}
    # External targets a component points at that are not sibling components:
    # either another container in the model or an external system.
    neighbors: list[str] = []
    for comp in container.components:
        for rel in comp.relationships:
            if rel.target not in component_ids and rel.target not in neighbors:
                neighbors.append(rel.target)

    out = [
        "@startuml",
        "!include <C4/C4_Component>",
        _ASYNC_TAG,
        f"title Component diagram - {_title(container.name)}",
    ]

    for nid in neighbors:
        out.append(_declare_context_node(model, nid))

    boundary = f"{alias(container.id)}_b"
    out.append(f"Container_Boundary({boundary}, {q(container.name)}) {{")
    for comp in container.components:
        out.append(
            f"  Component({alias(comp.id)}, {q(comp.name)}, {q(comp.technology or '')}, "
            f"{q(_tagline(comp.description))})"
        )
    out.append("}")

    for comp in container.components:
        for rel in comp.relationships:
            label = rel.label
            if rel.technology:
                label = f"{label} [{rel.technology}]" if label else rel.technology
            out.append(_rel(alias(comp.id), alias(rel.target), label, rel.sync))
    out.append("@enduml")
    return "\n".join(out)


def _declare_context_node(model: Model, node_id: str) -> str:
    """Declare a neighbor of an expanded container: a sibling container keeps its
    shape; a system/actor is drawn as its Context-level box; anything unknown
    falls back to a generic external system so the edge still resolves."""
    for system in model.systems:
        for c in system.containers:
            if c.id == node_id:
                macro = _SHAPE_MACRO[c.shape]
                return (
                    f"{macro}({alias(c.id)}, {q(c.name)}, {q(c.technology or '')}, "
                    f"{q(_tagline(c.description))})"
                )
    return _declare_node(model, node_id)


# --------------------------------------------------------------------------
# Dynamic (one per scenario)
# --------------------------------------------------------------------------
def render_dynamic_puml(model: Model, scenario_id: str) -> str:
    scenario = next((s for s in model.scenarios if s.id == scenario_id), None)
    if scenario is None:
        raise ValueError(f"no scenario {scenario_id!r}")

    referenced: list[str] = []
    for step in scenario.steps:
        for nid in (step.source, step.target):
            if nid not in referenced:
                referenced.append(nid)

    out = [
        "@startuml",
        "!include <C4/C4_Dynamic>",
        _ASYNC_TAG,
        f"title {_title(scenario.title)}",
    ]
    for nid in referenced:
        out.append(_declare_node(model, nid))
    # C4-PlantUML Dynamic does not auto-number; prefix the step index.
    for i, step in enumerate(scenario.steps, 1):
        label = f"{i}. {step.label}"
        tag = "" if step.sync else ', $tags="async"'
        out.append(f"Rel({alias(step.source)}, {alias(step.target)}, {q(_short(label, 60))}{tag})")
    out.append("@enduml")
    return "\n".join(out)


# --------------------------------------------------------------------------
# helpers (shared shapes of render.py, adapted for PlantUML)
# --------------------------------------------------------------------------
def _nodes_touching(model: Model, ids: set[str]) -> set[str]:
    out: set[str] = set()
    for flow in model.flows:
        resolved = {
            flow.source: _owner_id(model, flow.source),
            flow.target: _owner_id(model, flow.target),
        }
        if {flow.source, flow.target} & ids or set(resolved.values()) & ids:
            for raw, owner in resolved.items():
                out.add(raw)
                out.add(owner)
    return out


def _drawn(model: Model, node_id: str, container_ids: set[str], touch: set[str]) -> bool:
    if node_id in container_ids:
        return True
    owner = _owner_id(model, node_id)
    return owner in touch or node_id in touch


def _declare_node(model: Model, node_id: str) -> str:
    for actor in model.actors:
        if actor.id == node_id:
            return f"Person({alias(actor.id)}, {q(actor.name)}, {q(_tagline(actor.description))})"
    for system in model.systems:
        if system.id == node_id:
            macro = "System" if system.kind == "internal" else "System_Ext"
            return f"{macro}({alias(system.id)}, {q(system.name)}, {q(_tagline(system.description))})"
        for c in system.containers:
            if c.id == node_id:
                macro = _SHAPE_MACRO[c.shape]
                return (
                    f"{macro}({alias(c.id)}, {q(c.name)}, {q(c.technology or '')}, "
                    f"{q(_tagline(c.description))})"
                )
    return f'System({alias(node_id)}, {q(node_id)}, "")'
