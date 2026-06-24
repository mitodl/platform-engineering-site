"""Compose a SOA System Landscape from the per-system curated models.

The eight curated ``models/<system>.yaml`` files each describe one system in
detail (its containers, peers, and flows). This module *composes* them into a
single holistic, system-level view — the capstone of the architecture-maps epic.

How the composition works
-------------------------
1. **Internal systems** — the union of every ``kind: internal`` system across the
   models (the eight apps). These are the landscape's primary nodes.
2. **Cross-service edges** — for every model, each flow's endpoints are lifted to
   their *owning system* (a container resolves to its system via ``system_of``; a
   peer id is already a system id). Edges whose two ends are different systems are
   kept, then deduped to one per (source, target) direction. Sync/async is
   preserved (async if *any* underlying flow is async) and labels are aggregated.
3. **Id reconciliation** — peer references are not perfectly consistent across
   models (e.g. the data-platform model calls MIT Learn's video peer
   ``odl-video`` while that system's own model is ``odl-video-service``; mit-learn
   calls the platform ``data-platform``). ``_canonical_id`` reconciles these to
   one node per real system, preferring a ``repo`` URL match and falling back to a
   known id-alias table. Unresolved ids are reported, never silently double-drawn.
4. **Shared platform & externals** — a curated allow-list of the platform/identity
   and AI nodes that recur across models (APISIX, Keycloak, Vault, Open edX,
   LiteLLM, an LLM provider, Fastly) is included and grouped by domain, so the
   gateway/identity coupling is visible. All other per-model externals (payments,
   CRM, media vendors, ETL aggregates) are dropped to keep the view under the C4
   "~20 elements" guideline.
5. **Cycle detection** — runs over the aggregated system-level edge graph to
   surface SOA-wide dependency cycles.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .schema import Model, NodeKind, System

# The eight internal systems, in a deliberate left-to-right reading order
# (apps that mostly *produce* catalog data first, the discovery hub, then AI and
# the data platform). Used only for stable ordering; membership comes from the
# models' ``kind: internal`` union.
INTERNAL_ORDER = [
    "mitxonline",
    "mitxpro",
    "micromasters",
    "ocw-studio",
    "odl-video-service",
    "mit-learn",
    "learn-ai",
    "ol-data-platform",
]

# Shared platform / identity / AI systems that recur across models and are worth
# showing at landscape scale. Anything not listed here (payments, CRM, media
# vendors, per-app ETL aggregates) is collapsed out to keep the view readable.
# label -> domain group (becomes an Enterprise_Boundary in the diagram).
SHARED_NODES: dict[str, str] = {
    "apisix": "Platform & Identity",
    "keycloak": "Platform & Identity",
    "vault": "Platform & Identity",
    "openedx": "Course Delivery",
    "litellm": "AI",
    "openai": "AI",
    "fastly": "Edge",
}

# Domain grouping for the internal systems (Enterprise_Boundary in the diagram).
INTERNAL_GROUP: dict[str, str] = {
    "mitxonline": "Learning Apps",
    "mitxpro": "Learning Apps",
    "micromasters": "Learning Apps",
    "ocw-studio": "Learning Apps",
    "odl-video-service": "Learning Apps",
    "mit-learn": "Discovery",
    "learn-ai": "AI",
    "ol-data-platform": "Data Platform",
}

# Cross-model id aliases that ``repo``-matching cannot catch (the alias system has
# no repo, or a different repo than its canonical model). Checked after repo match.
ID_ALIASES: dict[str, str] = {
    "data-platform": "ol-data-platform",  # mit-learn's name for the platform
    "odl-video": "odl-video-service",  # data-platform's name for OVS
    "xpro": "mitxpro",  # defensive: xPRO short id
    "open-edx": "openedx",  # odl-video-service spelling vs mitxonline/mitxpro
    "edx-platform": "openedx",  # repo-derived id for Open edX
}

# Friendly display names + taglines for the shared nodes (the per-model
# descriptions vary; pick one concise canonical line for the landscape).
SHARED_DISPLAY: dict[str, tuple[str, str]] = {
    "apisix": ("APISIX Gateway", "Shared API gateway (OIDC via Keycloak)."),
    "keycloak": ("Keycloak (SSO)", "OAuth2/OIDC identity provider (realm olapps)."),
    "vault": ("HashiCorp Vault", "Secrets and dynamic DB credentials."),
    "openedx": ("Open edX", "Courseware/LMS (edx-platform) behind the apps."),
    "litellm": ("LiteLLM Proxy", "OpenAI-compatible LLM/embeddings proxy."),
    "openai": ("LLM Provider", "Backing model (OpenAI-compatible) behind LiteLLM."),
    "fastly": ("Fastly CDN", "Edge TLS/caching in front of the apps."),
}


@dataclass
class LandscapeNode:
    id: str  # canonical id
    name: str
    description: str
    internal: bool
    group: str
    repo: str | None = None


@dataclass
class LandscapeEdge:
    source: str  # canonical system id
    target: str
    sync: bool  # False if ANY underlying flow is async
    labels: set[str] = field(default_factory=set)
    models: set[str] = field(default_factory=set)

    def summary(self) -> str:
        """A short representative label: the distinct underlying flow labels."""
        labels = sorted(label for label in self.labels if label)
        if not labels:
            return ""
        if len(labels) <= 2:
            return "; ".join(labels)
        return f"{labels[0]}; {labels[1]} (+{len(labels) - 2} more)"


@dataclass
class Landscape:
    nodes: dict[str, LandscapeNode]
    edges: list[LandscapeEdge]
    cycles: list[list[str]]
    unresolved: list[tuple[str, str]]  # (model name, raw id) that could not resolve

    def node(self, node_id: str) -> LandscapeNode:
        return self.nodes[node_id]

    def internal_ids(self) -> list[str]:
        ids = [n.id for n in self.nodes.values() if n.internal]
        return sorted(ids, key=lambda x: (INTERNAL_ORDER.index(x) if x in INTERNAL_ORDER else 99, x))

    def groups(self) -> dict[str, list[str]]:
        """group label -> ordered node ids (internal groups first, then shared)."""
        out: dict[str, list[str]] = defaultdict(list)
        for nid in self.internal_ids():
            out[self.nodes[nid].group].append(nid)
        for nid, node in self.nodes.items():
            if not node.internal:
                out[node.group].append(nid)
        return dict(out)


def _repo_key(repo: str | None) -> str | None:
    """``https://github.com/mitodl/mit-learn/`` -> ``mitodl/mit-learn`` (slug)."""
    if not repo:
        return None
    parts = repo.rstrip("/").split("/")
    return "/".join(parts[-2:]).lower() if len(parts) >= 2 else repo.lower()


def compose(models: dict[str, Model]) -> Landscape:
    """Compose the per-system models into one System Landscape.

    ``models`` maps a model name (the file stem) to a validated ``Model``.
    """
    # Pass 1: learn the canonical id of every real internal system, indexed by
    # repo slug, so cross-model aliases (different ids, same repo) collapse to one.
    repo_to_canonical: dict[str, str] = {}
    internal_systems: dict[str, System] = {}
    for model in models.values():
        for system in model.systems:
            if system.kind != NodeKind.INTERNAL:
                continue
            internal_systems.setdefault(system.id, system)
            key = _repo_key(system.repo)
            if key:
                repo_to_canonical.setdefault(key, system.id)

    def canonical_id(system: System | None, raw_id: str) -> str:
        if raw_id in internal_systems:
            return raw_id
        key = _repo_key(system.repo if system else None)
        if key and key in repo_to_canonical:
            return repo_to_canonical[key]
        return ID_ALIASES.get(raw_id, raw_id)

    nodes: dict[str, LandscapeNode] = {}
    for sid, system in internal_systems.items():
        nodes[sid] = LandscapeNode(
            id=sid,
            name=system.name,
            description=system.description,
            internal=True,
            group=INTERNAL_GROUP.get(sid, "Other"),
            repo=system.repo,
        )
    for sid, group in SHARED_NODES.items():
        name, desc = SHARED_DISPLAY[sid]
        nodes[sid] = LandscapeNode(sid, name, desc, internal=False, group=group)

    def is_landscape_node(cid: str) -> bool:
        return cid in internal_systems or cid in SHARED_NODES

    edges: dict[tuple[str, str], LandscapeEdge] = {}
    unresolved: set[tuple[str, str]] = set()
    for name, model in models.items():
        actor_ids = {a.id for a in model.actors}
        for flow in model.flows:
            for end in (flow.source, flow.target):
                if end not in actor_ids and model.system_of(end) is None and not is_landscape_node(
                    ID_ALIASES.get(end, end)
                ):
                    unresolved.add((name, end))
            if flow.source in actor_ids or flow.target in actor_ids:
                continue
            src = canonical_id(model.system_of(flow.source), flow.source)
            tgt = canonical_id(model.system_of(flow.target), flow.target)
            if src == tgt or not (is_landscape_node(src) and is_landscape_node(tgt)):
                continue
            # Keep only edges that touch at least one internal system (drop e.g.
            # apisix -> keycloak: pure shared-infra plumbing, not SOA coupling).
            if src not in internal_systems and tgt not in internal_systems:
                continue
            edge = edges.get((src, tgt))
            if edge is None:
                edge = edges[(src, tgt)] = LandscapeEdge(src, tgt, sync=True)
            if not flow.sync:
                edge.sync = False
            if flow.label:
                edge.labels.add(flow.label.strip())
            edge.models.add(name)

    edge_list = sorted(edges.values(), key=lambda e: (e.source, e.target))
    # Cycle detection runs over OWNED internal systems only. Shared infra (the
    # gateway, identity, the LMS) sits in nearly every system's path, so including
    # it manufactures cycles that aren't harmful SOA coupling (e.g.
    # apisix→learn-ai→mit-learn→apisix). Restricting to internal↔internal edges
    # surfaces the real app-level cycles (e.g. micromasters↔mit-learn).
    internal_pairs = [
        (e.source, e.target)
        for e in edge_list
        if nodes[e.source].internal and nodes[e.target].internal
    ]
    cycles = _find_cycles(internal_pairs)
    return Landscape(nodes, edge_list, cycles, sorted(unresolved))


def _find_cycles(pairs: list[tuple[str, str]]) -> list[list[str]]:
    """Directed cycles among system ids in the aggregated edge set.

    Mirrors ``extract.find_cycles`` (same DFS + canonical-rotation dedupe) but
    operates on already-resolved (src, tgt) system-id pairs rather than the
    repo-keyed ``CrossEdge`` objects the deterministic extractor produces.
    """
    adj: dict[str, set[str]] = defaultdict(set)
    for src, tgt in pairs:
        adj[src].add(tgt)

    cycles: set[tuple[str, ...]] = set()

    def canonical(path: list[str]) -> tuple[str, ...]:
        i = path.index(min(path))
        return tuple(path[i:] + path[:i])

    visited_global: set[str] = set()

    def dfs(node: str, stack: list[str], on_stack: set[str]) -> None:
        for nxt in adj[node]:
            if nxt in on_stack:
                cyc = stack[stack.index(nxt):]
                if len(cyc) >= 2:
                    cycles.add(canonical(cyc))
            elif nxt not in visited_global:
                stack.append(nxt)
                on_stack.add(nxt)
                dfs(nxt, stack, on_stack)
                on_stack.discard(nxt)
                stack.pop()
        visited_global.add(node)

    for start in list(adj):
        if start not in visited_global:
            dfs(start, [start], {start})
    return [list(c) for c in sorted(cycles)]
