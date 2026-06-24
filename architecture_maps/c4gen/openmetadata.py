"""Deterministic extractor: OpenMetadata asset lineage -> model flow slice.

The *second* deterministic lineage source, parallel to the witan-code code-graph
bridge in ``extract.py``. Where the graph sees **runtime HTTP contracts** between
services, OpenMetadata sees **data lineage** in the OL data platform: the dbt /
warehouse transformations that pull each source system's tables into the lake and
join them across systems. Both halves emit the same intermediate
candidate-edge / ``Model``-slice shape so the renderer treats them identically —
unverified candidates surfaced on the Dependencies page, not drawn until curated.

How a lineage edge becomes a cross-service flow
-----------------------------------------------
The warehouse names every table ``<layer>__<source-system>__...`` (``raw__``,
``stg__``, ``int__``, ``marts__``, ``combined``...). The ``<source-system>`` token
(``mitlearn``, ``mitxonline``, ``micromasters``, ...) attributes a table to the
service whose data it carries. A lineage edge whose upstream and downstream tables
resolve to *different* source systems is a cross-system data flow inside the
platform (e.g. a ``marts__combined__*`` model joining ``int__mitxonline__*`` and
``int__micromasters__*``). Same-system edges (``raw -> stg -> int`` for one source)
are intra-platform plumbing and are not emitted as cross-service candidates.

Every emitted edge also flows *into* the synthetic ``ol-data-platform`` system
(the lake itself), so the Context view can show "service X feeds the data
platform" even when no cross-system join is involved.

Connection
----------
This talks to the OpenMetadata REST API the catalog MCP server fronts. Set
``C4GEN_OPENMETADATA_URL`` (e.g. ``https://catalog.example.edu``) and, if the
instance requires auth, ``C4GEN_OPENMETADATA_TOKEN`` (a JWT bot token). When the
server is unset or unreachable, extraction degrades gracefully: it logs a skip
and returns an empty slice, so ``render`` / the graph source keep working with no
OpenMetadata present.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from urllib import error, parse, request

# Source-system token (as it appears in warehouse table names) -> model system id.
# These mirror the system ids the curated models / witan-code graph already use,
# so OpenMetadata-derived edges line up with graph-derived ones on the same nodes.
SOURCE_SYSTEM_IDS: dict[str, str] = {
    "mitlearn": "mit-learn",
    "mitxonline": "mitxonline",
    "micromasters": "micromasters",
    "mitxpro": "mitxpro",
    "xpro": "mitxpro",
    "bootcamps": "bootcamps",
    "edxorg": "edxorg",
    "edx": "edxorg",
    "ocw": "ocw",
}

# The data platform itself, as a system node. Lineage edges terminate here so the
# Context view can show each service feeding the lake.
PLATFORM_SYSTEM_ID = "ol-data-platform"
PLATFORM_SYSTEM_NAME = "OL Data Platform"

# Warehouse layer prefixes, longest-first so ``raw`` doesn't shadow a longer token.
_LAYER_PREFIXES = ("raw", "stg", "staging", "int", "intermediate", "marts", "mart")
_NAME_RE = re.compile(r"^(?P<layer>[a-z]+)__(?P<source>[a-z0-9]+)__")


def _base_url() -> str | None:
    url = os.environ.get("C4GEN_OPENMETADATA_URL", "").strip().rstrip("/")
    return url or None


def source_system(table_name: str | None) -> str | None:
    """``stg__mitlearn__app__postgres__...`` -> ``mit-learn`` (model system id).

    Returns ``None`` for names that don't carry a recognized source token
    (``information_schema`` tables, ``combined_*`` reports without a source
    segment, unknown sources, or a missing/empty name) — the caller skips those.
    """
    if not table_name:
        return None
    m = _NAME_RE.match(table_name)
    if not m or m.group("layer") not in _LAYER_PREFIXES:
        return None
    return SOURCE_SYSTEM_IDS.get(m.group("source"))


@dataclass
class CatalogClient:
    """Thin OpenMetadata REST client (search + lineage), tolerant of an absent server."""

    base_url: str
    token: str | None = None
    timeout: int = 30

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{parse.urlencode(params)}"
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = request.Request(url, headers=headers, method="GET")  # noqa: S310 (trusted catalog URL)
        with request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))

    def reachable(self) -> bool:
        try:
            self._get("/api/v1/system/version")
            return True
        except (error.URLError, OSError, ValueError):
            return False

    def search_tables(self, query: str = "*", size: int = 1000) -> list[dict]:
        """Page through table-entity search hits (fqn + name), newest API shape."""
        out: list[dict] = []
        frm = 0
        while True:
            page = self._get(
                "/api/v1/search/query",
                {"q": query, "index": "table_search_index", "from": frm, "size": size},
            )
            if not isinstance(page, dict):
                break
            hits = (page.get("hits") or {}).get("hits", [])
            if not hits:
                break
            out.extend(h.get("_source", {}) for h in hits)
            frm += len(hits)
            if len(hits) < size:
                break
        return out

    def lineage(self, fqn: str, upstream: int = 3, downstream: int = 0) -> dict:
        """Lineage graph for a table by fully-qualified name."""
        return self._get(
            f"/api/v1/lineage/getLineage/table/name/{parse.quote(fqn, safe='')}",
            {"upstreamDepth": upstream, "downstreamDepth": downstream},
        )


def _asset_url(base_url: str, fqn: str) -> str:
    """Deep link into the OpenMetadata UI for a table fqn."""
    return f"{base_url}/table/{parse.quote(fqn, safe='')}"


@dataclass
class LineageEdge:
    """An aggregated cross-system lineage edge between two source systems.

    ``dst`` is the source system that the combining table belongs to, or the
    synthetic platform when the combining table is cross-cutting (a
    ``marts__combined__*`` model that carries no single source).
    """

    src: str  # upstream source-system id (where the data originates)
    dst: str  # downstream system id (the joiner, or the platform)
    lineage_kinds: set[str] = field(default_factory=set)  # DbtLineage / ViewLineage / ...
    sample_assets: list[str] = field(default_factory=list)  # combining-table fqns
    example_asset_fqn: str | None = None
    example_upstream_fqn: str | None = None


def cross_system_edges(client: CatalogClient, tables: list[dict]) -> list[LineageEdge]:
    """Walk lineage per table; emit an edge wherever 2+ source systems combine.

    For each table we collect the distinct source systems among *all* its upstream
    nodes (the full lineage subgraph, not just direct parents). When a single
    downstream table is fed by more than one source system — the signature of a
    cross-service join in the warehouse — we emit one directed edge per upstream
    system into the downstream table's system. A downstream table that carries no
    single source of its own (a ``combined`` mart) is attributed to the synthetic
    ``ol-data-platform`` system, so "service X feeds the platform" still shows.

    Tables fed by a single source (plain ``raw -> stg -> int`` plumbing) emit
    nothing: they are intra-service and not cross-service candidates.
    """
    by_id: dict[tuple[str, str], LineageEdge] = {}

    for tbl in tables:
        fqn = tbl.get("fullyQualifiedName")
        name = tbl.get("name", "")
        if not fqn:
            continue
        down_sys = source_system(name) or PLATFORM_SYSTEM_ID
        try:
            graph = client.lineage(fqn)
        except (error.URLError, OSError, ValueError):
            continue
        if not isinstance(graph, dict):
            continue

        nodes = list(graph.get("nodes") or [])
        entity = graph.get("entity") or {}
        kinds = {
            source
            for e in (graph.get("upstreamEdges") or [])
            if e and (source := (e.get("lineageDetails") or {}).get("source"))
        }
        # Distinct upstream source systems feeding this table (exclude itself).
        upstream: dict[str, str] = {}  # system id -> one example upstream fqn
        for n in nodes:
            if n.get("id") == entity.get("id"):
                continue
            sys = source_system(n.get("name", ""))
            if sys and sys != down_sys:
                upstream.setdefault(sys, n.get("fullyQualifiedName"))
        if len(upstream) < 2 and down_sys != PLATFORM_SYSTEM_ID:
            # Single-source (or no cross-source) feed into a service-owned table:
            # intra-service plumbing, not a cross-service candidate.
            continue
        for up_sys, up_fqn in upstream.items():
            key = (up_sys, down_sys)
            agg = by_id.get(key)
            if agg is None:
                agg = by_id[key] = LineageEdge(up_sys, down_sys)
            agg.lineage_kinds |= kinds
            if fqn not in agg.sample_assets:
                agg.sample_assets.append(fqn)
            if agg.example_asset_fqn is None:
                agg.example_asset_fqn = fqn
                agg.example_upstream_fqn = up_fqn
    return list(by_id.values())


def _ensure_system(systems: dict[str, dict], sid: str, name: str | None = None) -> None:
    systems.setdefault(
        sid,
        {"id": sid, "name": name or sid, "kind": "internal"},
    )


def build_flow_slice(base_url: str, edges: list[LineageEdge]) -> dict:
    """Turn cross-system lineage edges into a ``Model``-shaped dict (systems + flows).

    Mirrors ``extract.build_flow_slice``: emits bare system stubs (the curated
    model supplies prose) and one flow per cross-system lineage relation, tagged
    ``etl`` + ``cross-service`` + ``openmetadata-derived`` and carrying enough
    provenance (source/downstream asset fqn + catalog deep link) to trace it.
    """
    systems: dict[str, dict] = {}
    _ensure_system(systems, PLATFORM_SYSTEM_ID, PLATFORM_SYSTEM_NAME)

    flows: list[dict] = []
    for e in edges:
        _ensure_system(systems, e.src)
        _ensure_system(systems, e.dst)
        kinds = ", ".join(sorted(e.lineage_kinds)) or "lineage"
        n = len(e.sample_assets)
        flows.append(
            {
                "id": f"omd-{e.src}-to-{e.dst}-lineage",
                "source": e.src,
                "target": e.dst,
                "label": f"feeds {n} downstream table{'s' if n != 1 else ''}",
                "sync": False,  # warehouse transforms are batch/async by nature
                "protocol": "SQL",
                "data": f"e.g. {e.example_asset_fqn.split('.')[-1]}"
                if e.example_asset_fqn
                else "",
                "trigger": "etl: warehouse transform",
                "tags": ["cross-service", "etl", "openmetadata-derived"],
                "provenance": {
                    "derived_from": "openmetadata",
                    "contract_kind": "lineage",
                    "contract_key": kinds,
                    "asset_fqn": e.example_asset_fqn,
                    "asset_url": _asset_url(base_url, e.example_asset_fqn)
                    if e.example_asset_fqn
                    else None,
                },
            }
        )
    return {"systems": list(systems.values()), "flows": flows}


def extract_slice() -> dict:
    """Top-level entry: connect, walk lineage, return a flow slice (or empty if down).

    Returns ``{"systems": [], "flows": []}`` and prints a skip note when no
    OpenMetadata server is configured or it is unreachable — callers (the CLI)
    can merge an empty slice harmlessly.
    """
    base = _base_url()
    if base is None:
        print(
            "openmetadata: C4GEN_OPENMETADATA_URL not set — skipping lineage source.",
            file=sys.stderr,
        )
        return {"systems": [], "flows": []}
    client = CatalogClient(base, token=os.environ.get("C4GEN_OPENMETADATA_TOKEN") or None)
    if not client.reachable():
        print(
            f"openmetadata: catalog at {base} unreachable — skipping lineage source.",
            file=sys.stderr,
        )
        return {"systems": [], "flows": []}
    try:
        tables = client.search_tables()
    except error.HTTPError as exc:
        hint = (
            " (set C4GEN_OPENMETADATA_TOKEN to a JWT bot token)" if exc.code == 401 else ""
        )
        print(
            f"openmetadata: search failed ({exc.code} {exc.reason}){hint} — "
            "skipping lineage source.",
            file=sys.stderr,
        )
        return {"systems": [], "flows": []}
    except (error.URLError, OSError, ValueError) as exc:
        print(f"openmetadata: search failed ({exc}) — skipping lineage source.", file=sys.stderr)
        return {"systems": [], "flows": []}
    edges = cross_system_edges(client, tables)
    return build_flow_slice(base, edges)
