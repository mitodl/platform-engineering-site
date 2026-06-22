"""Deterministic extractor: witan-code cross-repo graph -> model flow slice.

Reads the shared witan-code *bridge* store (the same data the ``witan-code deps``
command and the ``code_interface_*`` MCP tools expose) and emits the cross-repo
*runtime* data-flow edges as a ``Model`` slice, plus a cycle report. This is the
deterministic half of the hybrid process: re-running it refreshes every edge that
is a real cross-repo contract, so diagrams cannot silently drift from the code.

Only ``endpoint`` and ``service`` contracts become data-flow edges:

* ``endpoint`` — repo A's client code calls an HTTP route repo B serves
  (A depends on B; data flows on request). These are the synchronous SOA edges.
* ``service`` — an infra repo *deploys* another repo (provisioning, not runtime
  data flow); kept as a tagged edge so the Context view can show ownership.

``env_var`` and ``package`` contracts are deployment/build coupling, not runtime
data flows, so they are summarized in the cycle/echo report but not drawn as flows.

The extractor never invents node prose. It emits systems as bare stubs
(id + name + repo); the curated model supplies descriptions, and the renderer
merges curated-over-generated.
"""

from __future__ import annotations

import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


def _ensure_witan_importable() -> None:
    """Make ``witan_code`` importable even when this runs under the site's venv.

    witan-code is installed as a local ``uv`` tool, not a PyPI dep of this repo.
    Anyone running the extractor already has it installed (it owns the graph), so
    we locate that tool venv's site-packages and add it to ``sys.path``.
    """
    try:
        import witan_code  # noqa: F401

        return
    except ImportError:
        pass
    try:
        base = subprocess.run(
            ["uv", "tool", "dir"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:  # pragma: no cover
        raise RuntimeError(
            "witan_code is not importable and `uv tool dir` failed; install witan-code "
            "(`uv tool install witan-code`) before running the extractor."
        ) from exc
    hits = list(Path(base).glob("witan-code/lib/python*/site-packages"))
    if not hits:
        raise RuntimeError(
            "Could not find the witan-code tool venv; install it with "
            "`uv tool install witan-code`."
        )
    sys.path.insert(0, str(hits[0]))
    import witan_code  # noqa: F401


def short_repo(repo: str) -> str:
    """``https://github.com/mitodl/mit-learn`` -> ``mitodl/mit-learn``."""
    repo = repo.rstrip("/")
    parts = repo.split("/")
    return "/".join(parts[-2:]) if len(parts) >= 2 else repo


def system_id(repo: str) -> str:
    """Repo URI -> stable system id used across the model (``mit-learn``)."""
    return short_repo(repo).split("/")[-1]


def load_bindings() -> list[dict]:
    """Read every cross-repo binding row from the witan-code bridge store."""
    _ensure_witan_importable()
    from witan_code import config as cfg_module
    from witan_code import store as store_module
    from witan_code.graph import OmnigraphClient

    cfg = cfg_module.load()
    store = store_module.bridge_store(cfg)
    if not store.exists():
        raise RuntimeError(
            "No witan-code bridge store yet — run `witan-code index` in the repos first."
        )
    client = OmnigraphClient(str(store), cfg.queries_dir)
    return client.read("bridge.gq", "all_bindings", {})


@dataclass
class Contract:
    kind: str
    key: str
    key_norm: str
    providers: set[str] = field(default_factory=set)  # repo URIs
    consumers: set[str] = field(default_factory=set)
    # one example source ref per consumer repo, for the "source of truth" link
    consumer_ref: dict[str, dict] = field(default_factory=dict)


def group_contracts(rows: list[dict]) -> dict[tuple[str, str], Contract]:
    groups: dict[tuple[str, str], Contract] = {}
    for b in rows:
        key = (b["kind"], b["key_norm"])
        c = groups.get(key)
        if c is None:
            c = groups[key] = Contract(b["kind"], b.get("key", b["key_norm"]), b["key_norm"])
        if b["role"] == "provider":
            c.providers.add(b["repo"])
        else:
            c.consumers.add(b["repo"])
            c.consumer_ref.setdefault(
                b["repo"], {"path": b.get("file"), "line": b.get("line")}
            )
    return groups


@dataclass
class CrossEdge:
    """An aggregated A-depends-on-B edge with its backing contracts."""

    src: str  # consumer repo URI
    dst: str  # provider repo URI
    kind: str
    keys: list[str] = field(default_factory=list)
    example_ref: dict | None = None


def cross_repo_edges(
    contracts: dict[tuple[str, str], Contract],
    kinds: tuple[str, ...] = ("endpoint",),
) -> list[CrossEdge]:
    """Aggregate per-contract bindings into directed cross-repo edges of the given kinds."""
    agg: dict[tuple[str, str, str], CrossEdge] = {}
    for c in contracts.values():
        if c.kind not in kinds:
            continue
        for prov in c.providers:
            for cons in c.consumers:
                if cons == prov:
                    continue
                k = (cons, prov, c.kind)
                edge = agg.get(k)
                if edge is None:
                    edge = agg[k] = CrossEdge(cons, prov, c.kind)
                edge.keys.append(c.key)
                if edge.example_ref is None:
                    edge.example_ref = c.consumer_ref.get(cons)
    return list(agg.values())


def find_cycles(edges: list[CrossEdge]) -> list[list[str]]:
    """Find directed cycles among systems (by id) in the cross-repo edge set."""
    adj: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        adj[system_id(e.src)].add(system_id(e.dst))

    cycles: set[tuple[str, ...]] = set()

    def canonical(path: list[str]) -> tuple[str, ...]:
        # rotate so the lexicographically smallest node leads — dedupes rotations
        i = path.index(min(path))
        return tuple(path[i:] + path[:i])

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
        # mark fully-explored (black) on backtrack so the outer loop and other
        # branches skip it — keeps detection at O(V + E) instead of O(V^2).
        visited_global.add(node)

    visited_global: set[str] = set()
    for start in list(adj):
        if start not in visited_global:
            dfs(start, [start], {start})
    return [list(c) for c in sorted(cycles)]


def build_flow_slice(edges: list[CrossEdge]) -> dict:
    """Turn cross-repo edges into a serializable ``Model``-shaped dict (systems + flows)."""
    systems: dict[str, dict] = {}

    def ensure_system(repo: str) -> str:
        sid = system_id(repo)
        systems.setdefault(
            sid,
            {
                "id": sid,
                "name": short_repo(repo),
                "kind": "internal" if "mitodl/" in repo else "external",
                "repo": repo,
            },
        )
        return sid

    flows: list[dict] = []
    for e in edges:
        src = ensure_system(e.src)
        dst = ensure_system(e.dst)
        ref = e.example_ref or {}
        n = len(e.keys)
        sample = ", ".join(sorted(set(e.keys))[:3])
        flows.append(
            {
                "id": f"graph-{src}-to-{dst}-{e.kind}",
                "source": src,
                "target": dst,
                "label": f"calls {n} endpoint{'s' if n != 1 else ''}",
                "sync": e.kind == "endpoint",
                "protocol": "HTTPS" if e.kind == "endpoint" else e.kind,
                "data": f"e.g. {sample}" if sample else "",
                "trigger": "on request",
                "tags": ["cross-service", "graph-derived"],
                "provenance": {
                    "derived_from": "graph",
                    "contract_kind": e.kind,
                    "contract_key": sample,
                    "repo": e.src,
                    "path": ref.get("path"),
                    "line": ref.get("line"),
                },
            }
        )
    return {"systems": list(systems.values()), "flows": flows}
