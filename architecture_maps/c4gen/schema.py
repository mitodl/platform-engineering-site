"""Structured intermediate model for the C4 data-flow maps.

This is the single source of truth a generation run reads. The deterministic
extractor (``extract.py``) refreshes the cross-repo *flow* edges from the
witan-code graph; humans/LLM refine the prose (descriptions, annotations,
scenario narratives). The renderer (``render.py``) projects this one model into
the three C4 levels we publish today — System Context, Container, and Dynamic —
without precluding a Component level later (see ``Container.components``).

Design notes
------------
* C4 levels are *projections* over one model, not separate documents. A System
  Context diagram collapses containers to their owning system; a Container
  diagram expands one system; a Dynamic diagram replays an ordered ``Scenario``.
* Every node carries a stable ``id`` used by flows and scenarios to refer to it.
* ``Flow.sync`` is the synchronous/asynchronous distinction the brief asks for.
  C4/Mermaid has no native async marker, so the renderer encodes it in the
  relationship's technology slot and the legend documents the convention.
* ``provenance`` records *how* an edge was learned (graph | code | infra |
  openmetadata) and, when from a deterministic source, the contract/asset that
  backs it — so a reader can trust and trace every line.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Base(BaseModel):
    # Reject unknown keys so YAML mistakes (e.g. an unquoted comma in an inline
    # map splitting a value into stray keys) fail loudly instead of silently
    # truncating a field.
    model_config = ConfigDict(extra="forbid")


class NodeKind(StrEnum):
    INTERNAL = "internal"  # a system we own / deploy
    EXTERNAL = "external"  # a third-party or peer system outside the detail scope


class Provenance(Base):
    """How a flow/node was discovered — drives trust and the "source of truth" link.

    ``derived_from`` reserves the vocabulary of deterministic sources:

    * ``graph`` — the witan-code cross-repo code graph (see ``extract.py``);
      ``contract_*`` and the ``repo``/``path``/``line`` ref back the edge.
    * ``openmetadata`` — table/asset lineage from the OpenMetadata catalog (see
      ``openmetadata.py``). The asset that backs the edge is carried as the
      ``asset_fqn`` (and ``asset_url`` deep-links into the catalog UI);
      ``contract_kind`` is ``lineage`` and ``contract_key`` names the lineage
      mechanism reported by OpenMetadata (e.g. ``DbtLineage``).
    * ``infra`` / ``code`` / ``manual`` — curated or infra-derived.
    """

    derived_from: Literal["graph", "openmetadata", "code", "infra", "manual"] = "manual"
    # When derived_from == "graph": the cross-repo contract backing this edge.
    # When derived_from == "openmetadata": contract_kind == "lineage" and
    # contract_key names the lineage source (DbtLineage / ViewLineage / ...).
    contract_kind: Literal["endpoint", "env_var", "service", "package", "lineage"] | None = None
    contract_key: str | None = None
    # A clickable source-of-truth location (repo-relative path + optional line).
    repo: str | None = None
    path: str | None = None
    line: int | None = None
    # OpenMetadata provenance: the catalog asset the edge was learned from and a
    # deep link into the catalog UI, so a reader can trace the lineage edge.
    asset_fqn: str | None = None
    asset_url: str | None = None

    def url(self) -> str | None:
        """A clickable source-of-truth URL: GitHub blob, or the catalog asset."""
        if self.asset_url:
            return self.asset_url
        if not (self.repo and self.path):
            return None
        base = self.repo.rstrip("/")
        suffix = f"#L{self.line}" if self.line else ""
        return f"{base}/blob/main/{self.path}{suffix}"


class SourceRef(Base):
    repo: str | None = None
    path: str | None = None


class Component(Base):
    """Reserved for a future Component-level (C4) projection. Unused by current views."""

    id: str
    name: str
    technology: str | None = None
    description: str = ""


class Container(Base):
    """A deployable/runtime unit inside an internal system (C4 Container)."""

    id: str
    name: str
    technology: str | None = None
    description: str = ""
    # ContainerDb / ContainerQueue render with distinct shapes in Mermaid C4.
    shape: Literal["container", "db", "queue"] = "container"
    source: SourceRef | None = None
    components: list[Component] = Field(default_factory=list)


class System(Base):
    """A C4 software system. Internal systems may be expanded into containers."""

    id: str
    name: str
    kind: NodeKind = NodeKind.EXTERNAL
    description: str = ""
    repo: str | None = None
    containers: list[Container] = Field(default_factory=list)
    # In the System Context view only, external systems sharing a context_group
    # are collapsed into one black box (keeps the Context under ~15 elements per
    # the C4 "stay under 20" rule). They stay individual in the Container view.
    context_group: str | None = None


class Actor(Base):
    id: str
    name: str
    description: str = ""


class Flow(Base):
    """A directed data flow between two nodes (actor / system / container id).

    The same flow can appear at multiple C4 levels: the renderer aggregates
    container-level flows up to their systems for the Context view.
    """

    id: str
    source: str
    target: str
    label: str = ""
    sync: bool = True  # True = synchronous request/response; False = asynchronous
    protocol: str | None = None  # HTTPS | GraphQL | S3 | Celery | SQL | SMTP | ...
    data: str = ""  # what information moves
    trigger: str | None = None  # "on request" | "beat: <name> every 120m" | "event: ..."
    tags: list[str] = Field(default_factory=list)  # etl | cross-service | auth | cycle | ...
    provenance: Provenance = Field(default_factory=Provenance)


class ScenarioStep(Base):
    source: str
    target: str
    label: str = ""
    sync: bool = True


class Scenario(Base):
    """An ordered interaction rendered as a C4 Dynamic diagram."""

    id: str
    title: str
    description: str = ""
    steps: list[ScenarioStep] = Field(default_factory=list)


class EtlSource(Base):
    """One external ingestion source, enumerated on the data-flows page."""

    name: str
    transport: str  # REST | REST OAuth2 | GraphQL | S3 | RSS | scrape | CSV | ...
    cadence: str = ""  # "daily 05:00" | "every 6h" | "webhook" | ...
    data: str = ""
    fragile: bool = False
    source_ref: SourceRef | None = None


class Meta(Base):
    name: str
    primary_system: str  # the system id the Container view expands
    description: str = ""
    # In the Container view, a cross-service flow that targets the primary system
    # as a whole is attributed to this entry container (where external HTTP lands).
    api_container: str | None = None
    # Whether a curated infrastructure-references.md exists for this system (it is
    # hand-authored, not generated). Drives the index page's link to it; default
    # off so a new system doesn't link to a page that does not exist yet.
    has_infrastructure_references: bool = False
    # Stamped by a generation run; kept out of the curated YAML to avoid churn.
    generated_at: str | None = None
    generator_version: str | None = None


class Model(Base):
    meta: Meta
    actors: list[Actor] = Field(default_factory=list)
    systems: list[System] = Field(default_factory=list)
    flows: list[Flow] = Field(default_factory=list)
    scenarios: list[Scenario] = Field(default_factory=list)
    etl_sources: list[EtlSource] = Field(default_factory=list)

    # --- lookup helpers -------------------------------------------------
    def system_of(self, node_id: str) -> System | None:
        """Return the system owning ``node_id`` (whether it is the system or a container)."""
        for system in self.systems:
            if system.id == node_id:
                return system
            if any(c.id == node_id for c in system.containers):
                return system
        return None

    def node_label(self, node_id: str) -> str:
        for actor in self.actors:
            if actor.id == node_id:
                return actor.name
        for system in self.systems:
            if system.id == node_id:
                return system.name
            for container in system.containers:
                if container.id == node_id:
                    return container.name
        return node_id
