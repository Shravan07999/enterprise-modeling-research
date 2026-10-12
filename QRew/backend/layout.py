"""Deterministic layout algorithms for 4EM and ArchiMate."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Position:
    x: float
    y: float
    width: float
    height: float


SUBMODEL_COLUMNS = {
    "goals": 0,
    "processes": 1,
    "actors": 2,
    "technical": 3,
}

TYPE_DIMENSIONS_4EM = {
    "goal": (6, 1.5),
    "problem": (6, 1.5),
    "process": (5.5, 1.2),
    "actor": (4, 1.5),
    "role": (4, 1.5),
    "org_unit": (4, 1.5),
    "info_set": (5, 1.5),
    "product": (6, 2),
    "component": (4, 2),
    "feature": (4, 1.5),
    "tech_component": (4, 1.5),
    "concept": (5, 1.5),
    "attribute": (4, 1.5),
}

LAYER_COLUMNS = {
    "business": 100,
    "application": 500,
    "technology": 900,
    "physical": 900,
    "motivation": 100,
    "implementation": 1300,
}


def generate_4em_layout(elements: List[dict]) -> Dict[str, Position]:
    """Generate ADL POSITION attributes for 4EM elements.

    Columns per submodel (from reference):
    - Col 0 (x=1cm): Goals, Problems
    - Col 1 (x=8cm): Processes
    - Col 2 (x=15cm): Actors, Roles, OrgUnits, Information Sets
    - Col 3 (x=22cm): Products, Components, Features, Tech Components, Concepts, Attributes

    Vertical stack within each column, sorted by name for determinism.
    """
    positions = {}
    row_counters: Dict[str, int] = {k: 0 for k in SUBMODEL_COLUMNS}

    # Sort by submodel order, then by name
    sorted_elements = sorted(
        elements,
        key=lambda e: (
            list(SUBMODEL_COLUMNS.keys()).index(e.get("submodel", "")) if e.get("submodel") in SUBMODEL_COLUMNS else 99,
            e.get("name", "")
        )
    )

    for elem in sorted_elements:
        submodel = elem.get("submodel")
        canonical_type = elem.get("canonicalType", "")

        if submodel not in SUBMODEL_COLUMNS:
            continue

        col = SUBMODEL_COLUMNS[submodel]
        row = row_counters[submodel]

        width, height = TYPE_DIMENSIONS_4EM.get(canonical_type, (4, 1.5))

        # Reference uses: x=1cm for col 0, x=8cm for col 1, x=14cm for col 2, x=21cm for col 3
        # Column spacing ~7cm
        x = 1 + col * 7
        y = 1 + row * 2.5

        positions[elem["id"]] = Position(x=x, y=y, width=width, height=height)
        row_counters[submodel] += 1

    return positions


def generate_archimate_layout(elements: List[dict], relationships: List[dict]) -> Dict[str, Position]:
    """Generate ArchiMate view node positions.

    Dispatches to a tree layout for hierarchical/structural models (composition,
    aggregation) or a DAG layout for process flow models (flows, triggers).
    """
    # Classify: is this predominantly a tree/hierarchy or a process flow?
    structural_types = {"composes", "aggregates", "assigns"}
    flow_types = {"flows", "triggers"}

    structural_count = sum(
        1 for r in relationships if r.get("canonicalType", "") in structural_types
    )
    flow_count = sum(
        1 for r in relationships if r.get("canonicalType", "") in flow_types
    )

    if structural_count > flow_count and structural_count > 0:
        return _tree_layout(elements, relationships)
    else:
        return _dag_layout(elements, relationships)


def _tree_layout(elements: List[dict], relationships: List[dict]) -> Dict[str, Position]:
    """Hierarchical tree layout for structural models (composition/aggregation).

    Roots are placed at the top; children are centered below their parent.
    """
    positions: Dict[str, Position] = {}
    element_ids = {e["id"] for e in elements}
    element_name_map = {e["id"]: e.get("name", e["id"]) for e in elements}

    # Build parent→children adjacency from structural relationships
    structural_types = {"composes", "aggregates", "assigns"}
    children: Dict[str, List[str]] = {e_id: [] for e_id in element_ids}
    has_parent: set = set()

    for rel in relationships:
        if rel.get("canonicalType", "") in structural_types:
            src = rel.get("sourceId")
            tgt = rel.get("targetId")
            if src in element_ids and tgt in element_ids:
                children[src].append(tgt)
                has_parent.add(tgt)

    # Sort children by name for deterministic layout
    for parent_id in children:
        children[parent_id].sort(key=lambda eid: element_name_map.get(eid, eid))

    # Roots = elements that have children but no parent (in structural rels)
    roots = [eid for eid in element_ids if eid not in has_parent and children[eid]]

    # Also include isolated elements (no structural relationships at all)
    connected = has_parent | {eid for eid in element_ids if children[eid]}
    isolated = [eid for eid in element_ids if eid not in connected]

    # If no roots found (all elements have parents somehow), pick first element
    if not roots and element_ids:
        roots = sorted(element_ids, key=lambda eid: element_name_map.get(eid, eid))[:1]

    # Sort roots by name for determinism
    roots.sort(key=lambda eid: element_name_map.get(eid, eid))

    # BFS to compute depth and subtree width for each node
    node_width = 160  # px per node box
    node_height = 65
    h_gap = 40  # horizontal gap between siblings
    v_gap = 100  # vertical gap between levels

    def subtree_width(node_id: str, visited: set) -> int:
        """Calculate how many leaf-level slots this subtree occupies."""
        if node_id in visited:
            return 1
        visited.add(node_id)
        child_list = children.get(node_id, [])
        if not child_list:
            return 1
        return sum(subtree_width(c, visited) for c in child_list)

    def place_tree(node_id: str, x_start: float, y: float, visited: set):
        """Recursively place a subtree starting at x_start, y."""
        if node_id in visited:
            return
        visited.add(node_id)
        child_list = children.get(node_id, [])
        total_slots = subtree_width(node_id, set())
        total_width = total_slots * (node_width + h_gap) - h_gap

        # Center this node over its subtree
        node_x = x_start + total_width / 2 - node_width / 2
        positions[node_id] = Position(x=node_x, y=y, width=node_width, height=node_height)

        if child_list:
            child_x = x_start
            for child_id in child_list:
                child_slots = subtree_width(child_id, set())
                child_total_w = child_slots * (node_width + h_gap) - h_gap
                place_tree(child_id, child_x, y + node_height + v_gap, visited)
                child_x += child_total_w + h_gap

    # Place each root tree side by side
    visited: set = set()
    x_cursor = 50.0  # starting x position
    for root_id in roots:
        total_slots = subtree_width(root_id, set())
        place_tree(root_id, x_cursor, 50.0, visited)
        total_width = total_slots * (node_width + h_gap) - h_gap
        x_cursor += total_width + 100  # gap between root trees

    # Place isolated elements in a row below all trees
    if isolated:
        max_y = max((p.y + p.height for p in positions.values()), default=50) + v_gap
        isolated.sort(key=lambda eid: element_name_map.get(eid, eid))
        ix = 50.0
        for eid in isolated:
            positions[eid] = Position(x=ix, y=max_y, width=node_width, height=node_height)
            ix += node_width + h_gap

    return positions


def _dag_layout(elements: List[dict], relationships: List[dict]) -> Dict[str, Position]:
    """DAG BFS layout for process flow models (original algorithm)."""
    positions: Dict[str, Position] = {}

    element_ids = {e["id"] for e in elements}
    # Build adjacency list
    adj: Dict[str, List[str]] = {e_id: [] for e_id in element_ids}
    in_degree: Dict[str, int] = {e_id: 0 for e_id in element_ids}

    for rel in relationships:
        src = rel.get("sourceId")
        tgt = rel.get("targetId")
        if src in element_ids and tgt in element_ids:
            adj[src].append(tgt)
            in_degree[tgt] += 1

    # Find roots (in_degree == 0)
    roots = [e_id for e_id in element_ids if in_degree[e_id] == 0]
    if not roots and element_ids:
        roots = [next(iter(element_ids))]

    # BFS to assign depths
    depths: Dict[str, int] = {}
    queue = [(root, 0) for root in roots]
    visited: set = set()

    while queue:
        node, depth = queue.pop(0)
        if node not in depths or depths[node] < depth:
            depths[node] = depth

        if node not in visited:
            visited.add(node)
            for neighbor in adj[node]:
                queue.append((neighbor, depth + 1))

    # Any disconnected nodes get depth 0
    for e_id in element_ids:
        if e_id not in depths:
            depths[e_id] = 0

    # Group by depth to assign Y coordinates
    depth_groups: Dict[int, List[str]] = {}
    for node, depth in depths.items():
        if depth not in depth_groups:
            depth_groups[depth] = []
        depth_groups[depth].append(node)

    # Assign coordinates: x based on depth, y based on index within depth group
    for depth, nodes in depth_groups.items():
        nodes.sort()
        x = 100 + depth * 220
        y = 100
        for node in nodes:
            width, height = 140, 55
            positions[node] = Position(x=x, y=y, width=width, height=height)
            y += 90  # vertical spacing for nodes at the same depth

    return positions


def format_4em_position(pos: Position, index: int) -> str:
    """Format Position as ADL POSITION attribute string."""
    return f"NODE x:{pos.x:.1f}cm y:{pos.y:.1f}cm w:{pos.width:.1f}cm h:{pos.height:.1f}cm index:{index}"