"""Load and navigate the allocation hierarchy dimension tree."""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import AllocationDimensionNode

_DEFAULT_DIMENSIONS_PATH = Path("config/allocation_dimensions.yaml")


def load_dimensions(
    config_path: Path | str = _DEFAULT_DIMENSIONS_PATH,
) -> dict[str, AllocationDimensionNode]:
    """Parse config/allocation_dimensions.yaml. Returns dict keyed by node key."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Allocation dimensions config not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)

    nodes: dict[str, AllocationDimensionNode] = {}
    for raw in doc.get("nodes", []):
        key = raw["key"]
        nodes[key] = AllocationDimensionNode(
            key=key,
            label=raw["label"],
            parent_key=raw.get("parent_key"),
            dimension_type=raw["dimension_type"],
            allocation_category_type=raw["allocation_category_type"],
            hierarchy_level=int(raw["hierarchy_level"]),
            children=tuple(raw.get("children", [])),
            replay_filter_mapping=dict(raw.get("replay_filter_mapping") or {}),
            replay_sophistication=raw.get("replay_sophistication", "NONE"),
        )

    return nodes


def get_ancestry_chain(
    node_key: str,
    all_nodes: dict[str, AllocationDimensionNode],
) -> list[AllocationDimensionNode]:
    """Return ordered list from root (Level 1) down to the given node (inclusive)."""
    chain: list[AllocationDimensionNode] = []
    current_key: str | None = node_key
    while current_key is not None:
        node = all_nodes.get(current_key)
        if node is None:
            break
        chain.append(node)
        current_key = node.parent_key
    chain.reverse()
    return chain


def compute_pct_of_total(
    node_key: str,
    pct_of_parent_map: dict[str, float],
    all_nodes: dict[str, AllocationDimensionNode],
) -> float:
    """Calculate target_pct_of_total as product of pct_of_parent across ancestry chain."""
    chain = get_ancestry_chain(node_key, all_nodes)
    result = 1.0
    for node in chain:
        pct = pct_of_parent_map.get(node.key)
        if pct is None:
            return 0.0
        result *= pct / 100.0
    return round(result * 100.0, 6)


def get_sibling_keys(
    node_key: str,
    all_nodes: dict[str, AllocationDimensionNode],
) -> list[str]:
    """Return all sibling keys (same parent, excluding self)."""
    node = all_nodes.get(node_key)
    if node is None or node.parent_key is None:
        return []
    parent = all_nodes.get(node.parent_key)
    if parent is None:
        return []
    return [k for k in parent.children if k != node_key]


def get_nodes_by_asset_class(
    all_nodes: dict[str, AllocationDimensionNode],
    asset_class: str,
) -> list[AllocationDimensionNode]:
    """Return all nodes belonging to the given asset class (e.g. 'EQUITY')."""
    return [n for n in all_nodes.values() if n.allocation_category_type == asset_class]


def get_level1_keys(all_nodes: dict[str, AllocationDimensionNode]) -> list[str]:
    """Return all Level 1 (asset class) node keys."""
    return [k for k, n in all_nodes.items() if n.hierarchy_level == 1]


def get_children(
    node_key: str,
    all_nodes: dict[str, AllocationDimensionNode],
) -> list[AllocationDimensionNode]:
    """Return direct child nodes of the given node."""
    node = all_nodes.get(node_key)
    if node is None:
        return []
    return [all_nodes[k] for k in node.children if k in all_nodes]


def get_leaf_nodes(all_nodes: dict[str, AllocationDimensionNode]) -> list[AllocationDimensionNode]:
    """Return all leaf nodes (nodes with no children)."""
    return [n for n in all_nodes.values() if n.is_leaf]
