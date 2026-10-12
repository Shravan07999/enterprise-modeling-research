from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from typing import Optional

from .exporter_utils import adl_escape, grid_position, safe_filename


@dataclass
class ADLElement:
    instance_id: str
    adl_type: str
    description: str
    index: int
    x: float
    y: float
    w: float = 6.0
    h: float = 1.5
    extra_attrs: dict = field(default_factory=dict)


@dataclass
class ADLRelation:
    from_id: str
    from_type: str
    to_id: str
    to_type: str
    rel_type: str
    positions: str = ""


_4EM_TYPE_MAP: dict[str, tuple[str, float, float]] = {
    "Goal":     ("Goal",             6.0, 1.5),
    "Process":  ("Process",          5.5, 1.2),
    "Data":     ("Information Set",  5.0, 1.5),
    "Resource": ("Role",             4.0, 1.5),
}

_RELATION_TYPE_MAP: dict[tuple[str, str], str] = {
    ("Goal",            "Goal"):            "refined by (AND)",
    ("Goal",            "Process"):         "supported by",
    ("Process",         "Process"):         "decomposed into",
    ("Process",         "Information Set"): "Output",
    ("Information Set", "Process"):         "Input",
    ("Role",            "Process"):         "is responsible for",
    ("Role",            "Goal"):            "is responsible for",
    ("Role",            "Information Set"): "manages",
}


def _infer_relation_type(src_type: str, tgt_type: str) -> str:
    return _RELATION_TYPE_MAP.get((src_type, tgt_type), "related to")


def _format_cm(val: float) -> str:
    r = round(val, 2)
    if r == int(r):
        return f"{int(r)}cm"
    s = f"{r:.2f}".rstrip("0").rstrip(".")
    return f"{s}cm"


def _org_unit_attrs(elem: ADLElement) -> list[tuple[str, any]]:
    return [
        ("Decomposition", ""),
        ("Attributes", None),
    ]


def _role_attrs(elem: ADLElement) -> list[tuple[str, any]]:
    return [
        ("Decomposition", ""),
        ("Attributes", None),
    ]


def _goal_attrs(elem: ADLElement) -> list[tuple[str, any]]:
    return [
        ("Criticality", "Low"),
        ("Priority", "Low"),
        ("Intermodel-Relations", None),
        ("Decomposition", ""),
        ("Defined by", ""),
        ("Attributes", None),
        ("Is the exact same as", ""),
        ("hidden_attribute", ""),
    ]


def _problem_attrs(elem: ADLElement) -> list[tuple[str, any]]:
    return [
        ("Intermodel-Relations", None),
        ("Decomposition", ""),
        ("Attributes", None),
        ("Defined by", ""),
        ("Priority", "Low"),
        ("Criticality", "Low"),
        ("type", "Problem"),
        ("Is the exact same as", ""),
        ("hidden_attribute", ""),
    ]


def _process_attrs(elem: ADLElement) -> list[tuple[str, any]]:
    return [
        ("Decomposed Process", ""),
        ("Intermodel-Relations", None),
        ("Decomposition", ""),
        ("Execution Time", 0),
        ("Complexity", 0),
        ("Type", ""),
        ("Attributes", None),
        ("Is the exact same as", ""),
        ("hidden_attribute", ""),
    ]


def _info_set_attrs(elem: ADLElement) -> list[tuple[str, any]]:
    return [
        ("Intermodel-Relations", None),
        ("Decomposition", ""),
    ]


def _concept_attrs(elem: ADLElement) -> list[tuple[str, any]]:
    return [
        ("Intermodel-Relations", None),
        ("Decomposition", ""),
    ]


_TYPE_EXTRA_ATTRS = {
    "Organizational Unit": _org_unit_attrs,
    "Role": _role_attrs,
    "Goal": _goal_attrs,
    "Problem": _problem_attrs,
    "Process": _process_attrs,
    "Information Set": _info_set_attrs,
    "Concept": _concept_attrs,
}

_4EM_LAYER_ORDER = [
    "Organizational Unit",
    "Role",
    "Goal",
    "Problem",
    "Process",
    "Information Set",
    "Unspecific/Product/Service",
    "Component",
    "Feature",
    "IS Technical Component",
    "Concept",
    "Attribute",
]

_4EM_LAYER_DISPLAY = {
    "Organizational Unit": "ORGANIZATIONAL UNITS",
    "Role": "ROLES",
    "Goal": "GOALS",
    "Problem": "PROBLEM",
    "Process": "PROCESSES",
    "Information Set": "INFORMATION SETS",
    "Unspecific/Product/Service": "PRODUCT",
    "Component": "COMPONENTS",
    "Feature": "FEATURES",
    "IS Technical Component": "IS TECHNICAL COMPONENTS",
    "Concept": "CONCEPT AND ATTRIBUTE",
    "Attribute": "ATTRIBUTES",
}


def _compute_relation_path(src_elem: ADLElement, tgt_elem: ADLElement) -> str:
    sx = src_elem.x + src_elem.w / 2.0
    sy = src_elem.y + src_elem.h / 2.0
    tx = tgt_elem.x + tgt_elem.w / 2.0
    ty = tgt_elem.y + tgt_elem.h / 2.0

    y_overlap = abs(sy - ty) < max(src_elem.h, tgt_elem.h) * 1.5
    x_overlap = abs(sx - tx) < max(src_elem.w, tgt_elem.w) * 1.5

    waypoints = []
    if y_overlap:
        mx = (sx + tx) / 2.0
        waypoints = [(sx, sy), (mx, sy), (mx, ty), (tx, ty)]
    elif x_overlap:
        my = (sy + ty) / 2.0
        waypoints = [(sx, sy), (sx, my), (tx, my), (tx, ty)]
    else:
        mx = (sx + tx) / 2.0
        waypoints = [(sx, sy), (mx, sy), (mx, ty), (tx, ty)]

    segments = []
    for i, (x, y) in enumerate(waypoints):
        segments.append(f"LINE x:{x:.1f}cm y:{y:.1f}cm w:0cm h:0cm index:{i+1}")
    return "; ".join(segments)


def _inject_mandatory_relations(raw_nodes: list[dict]) -> list[dict]:
    if not raw_nodes:
        return raw_nodes

    id_to_node = {n["id"]: n for n in raw_nodes}
    
    def _map_type(raw_type: str) -> str:
        return _4EM_TYPE_MAP.get(raw_type, ("Concept", 5.0, 1.5))[0]
    
    type_to_ids: dict[str, list[str]] = {}
    for n in raw_nodes:
        adl_type = _map_type(n.get("type", ""))
        type_to_ids.setdefault(adl_type, []).append(n["id"])

    def has_edge(src_adl_type: str, tgt_adl_type: str) -> bool:
        for n in raw_nodes:
            src_adl = _map_type(n.get("type", ""))
            if src_adl == src_adl_type:
                for next_id in n.get("next", []):
                    tgt = id_to_node.get(next_id)
                    if tgt and _map_type(tgt.get("type", "")) == tgt_adl_type:
                        return True
        return False

    if "Process" in type_to_ids and "Information Set" in type_to_ids:
        if not has_edge("Process", "Information Set"):
            src_id = type_to_ids["Process"][0]
            tgt_id = type_to_ids["Information Set"][0]
            id_to_node[src_id].setdefault("next", []).append(tgt_id)

    if "Role" in type_to_ids and "Process" in type_to_ids:
        if not has_edge("Role", "Process"):
            src_id = type_to_ids["Role"][0]
            tgt_id = type_to_ids["Process"][0]
            id_to_node[src_id].setdefault("next", []).append(tgt_id)

    if "Role" in type_to_ids and "Information Set" in type_to_ids:
        if not has_edge("Role", "Information Set"):
            src_id = type_to_ids["Role"][0]
            tgt_id = type_to_ids["Information Set"][0]
            id_to_node[src_id].setdefault("next", []).append(tgt_id)

    if "Role" in type_to_ids and "Goal" in type_to_ids:
        if not has_edge("Role", "Goal"):
            src_id = type_to_ids["Role"][0]
            tgt_id = type_to_ids["Goal"][0]
            id_to_node[src_id].setdefault("next", []).append(tgt_id)

    if "Goal" in type_to_ids and "Process" in type_to_ids:
        if not has_edge("Goal", "Process"):
            src_id = type_to_ids["Goal"][0]
            tgt_id = type_to_ids["Process"][0]
            id_to_node[src_id].setdefault("next", []).append(tgt_id)

    return [id_to_node[n["id"]] for n in raw_nodes]


def _check_relation_completeness(elements: list[ADLElement], relations: list[ADLRelation]) -> list[str]:
    warnings = []
    has_process = any(e.adl_type == "Process" for e in elements)
    has_info = any(e.adl_type == "Information Set" for e in elements)
    has_role = any(e.adl_type == "Role" for e in elements)
    has_goal = any(e.adl_type == "Goal" for e in elements)

    rel_types = {(r.from_type, r.to_type) for r in relations}

    if has_process and has_info and ("Process", "Information Set") not in rel_types:
        warnings.append("Missing expected relation: Process → Information Set (Output)")
    if has_role and has_process and ("Role", "Process") not in rel_types:
        warnings.append("Missing expected relation: Role → Process (is responsible for)")
    if has_role and has_info and ("Role", "Information Set") not in rel_types:
        warnings.append("Missing expected relation: Role → Information Set (manages)")
    if has_role and has_goal and ("Role", "Goal") not in rel_types:
        warnings.append("Missing expected relation: Role → Goal (is responsible for)")
    if has_goal and has_process and ("Goal", "Process") not in rel_types:
        warnings.append("Missing expected relation: Goal → Process (supported by)")

    return warnings


# 4EM semantic directions — source drives target, not the other way around.
_SEMANTIC_RELATIONS: dict[tuple[str, str], str] = {
    ("Goal",            "Process"):         "supported by",
    ("Goal",            "Goal"):            "refined by (AND)",
    ("Process",         "Process"):         "decomposed into",
    ("Process",         "Information Set"): "Output",
    ("Information Set", "Process"):         "Input",
    ("Role",            "Process"):         "is responsible for",
    ("Role",            "Goal"):            "is responsible for",
    ("Role",            "Information Set"): "manages",
}


def _get_semantic_relation(src_type: str, tgt_type: str) -> tuple[str, str, str] | None:
    if (src_type, tgt_type) in _SEMANTIC_RELATIONS:
        return (src_type, tgt_type, _SEMANTIC_RELATIONS[(src_type, tgt_type)])
    # Check reverse — LLM may have the direction flipped
    if (tgt_type, src_type) in _SEMANTIC_RELATIONS:
        return (tgt_type, src_type, _SEMANTIC_RELATIONS[(tgt_type, src_type)])
    return None


def _parse_4em_json(blueprint: str) -> tuple[list[ADLElement], list[ADLRelation]]:
    raw_nodes: list[dict] = json.loads(blueprint)

    id_to_elem: dict[str, ADLElement] = {}
    type_counters: dict[str, int] = {}
    elements: list[ADLElement] = []

    for node_idx, node in enumerate(raw_nodes):
        raw_type = node.get("type", "").strip()
        label    = node.get("label", "").strip()

        display_name = label.split(":", 1)[1].strip() if ":" in label else label

        adl_type, w, h = _4EM_TYPE_MAP.get(raw_type, ("Concept", 5.0, 1.5))

        type_counters[adl_type] = type_counters.get(adl_type, 0) + 1
        counter = type_counters[adl_type]
        instance_id = f"{adl_type} - {counter}"

        x, y = grid_position(node_idx, cols=3, col_w=8.0, row_h=2.5)

        elem = ADLElement(
            instance_id=instance_id,
            adl_type=adl_type,
            description=display_name,
            index=node_idx + 1,
            x=x, y=y, w=w, h=h,
        )
        id_to_elem[node["id"]] = elem
        elements.append(elem)

    relations: list[ADLRelation] = []
    seen_relations: set[tuple[str, str, str]] = set()
    for node in raw_nodes:
        src_elem = id_to_elem.get(node["id"])
        if src_elem is None:
            continue
        for next_id in node.get("next", []):
            tgt_elem = id_to_elem.get(next_id)
            if tgt_elem is None:
                continue
            
            semantic = _get_semantic_relation(src_elem.adl_type, tgt_elem.adl_type)
            
            if semantic:
                sem_src_type, sem_tgt_type, rel_type = semantic
                if sem_src_type == src_elem.adl_type and sem_tgt_type == tgt_elem.adl_type:
                    from_elem, to_elem = src_elem, tgt_elem
                else:
                    # Semantic direction is reversed from what the LLM produced
                    from_elem, to_elem = tgt_elem, src_elem
            else:
                from_elem, to_elem = src_elem, tgt_elem
                rel_type = "related to"
            
            rel_key = (from_elem.instance_id, to_elem.instance_id, rel_type)
            if rel_key in seen_relations:
                continue
            seen_relations.add(rel_key)
            
            relations.append(ADLRelation(
                from_id=from_elem.instance_id,
                from_type=from_elem.adl_type,
                to_id=to_elem.instance_id,
                to_type=to_elem.adl_type,
                rel_type=rel_type,
                positions="",
            ))

    return elements, relations


def _parse_narrative_fallback(
    final_output: str, framework: str
) -> tuple[list[ADLElement], list[ADLRelation]]:
    narrative = final_output.split("```")[0]

    pattern = r"\b([A-Z][a-z]+(?: [A-Z][a-z]+){1,4})\b"
    matches  = re.findall(pattern, narrative)

    unique = list(dict.fromkeys(matches))[:12]

    elements: list[ADLElement] = []
    type_counters: dict[str, int] = {}
    for idx, name in enumerate(unique):
        adl_type = "Process" if idx < len(unique) // 2 else "Concept"
        type_counters[adl_type] = type_counters.get(adl_type, 0) + 1
        counter = type_counters[adl_type]
        instance_id = f"{adl_type} - {counter}"
        x, y = grid_position(idx, cols=3, col_w=8.0, row_h=2.5)
        elements.append(ADLElement(
            instance_id=instance_id,
            adl_type=adl_type,
            description=name,
            index=idx + 1,
            x=x, y=y, w=5.5, h=1.2,
        ))

    return elements, []


def _render_instance(elem: ADLElement) -> str:
    parts: list[str] = []
    parts.append(f"INSTANCE <{elem.instance_id}> : <{elem.adl_type}>")

    pos = (
        f"NODE x:{_format_cm(elem.x)} y:{_format_cm(elem.y)} "
        f"w:{_format_cm(elem.w)} h:{_format_cm(elem.h)} index:{elem.index}"
    )
    parts.append(f'\tATTRIBUTE <Position>\n\tVALUE "{adl_escape(pos)}"')
    parts.append('\tATTRIBUTE <External tool coupling>\n\tVALUE ""')
    parts.append(f'\tATTRIBUTE <Description>\n\tVALUE "{adl_escape(elem.description)}"')

    extra_fn = _TYPE_EXTRA_ATTRS.get(elem.adl_type, _concept_attrs)
    for attr_name, attr_val in extra_fn(elem):
        if attr_val is None:
            parts.append(f'\tATTRIBUTE <{attr_name}>\n\tVALUE')
        elif isinstance(attr_val, int):
            parts.append(f'\tATTRIBUTE <{attr_name}>\n\tVALUE {attr_val}')
        else:
            parts.append(f'\tATTRIBUTE <{attr_name}>\n\tVALUE "{adl_escape(str(attr_val))}"')

    parts.append("//END")
    return "\n\n".join(parts)


def _render_relation(rel: ADLRelation) -> str:
    parts: list[str] = []
    header = (
        "RELATION <4EM_Relation>\n"
        f"\tFROM <{rel.from_id}> : <{rel.from_type}>\n"
        f"\tTO <{rel.to_id}> : <{rel.to_type}>"
    )
    parts.append(header)
    parts.append(f'\tATTRIBUTE <Positions>\n\tVALUE "{adl_escape(rel.positions)}"')
    parts.append(f'\tATTRIBUTE <Type>\n\tVALUE "{adl_escape(rel.rel_type)}"')
    parts.append('\tATTRIBUTE <Description>\n\tVALUE ""')
    parts.append("//END")
    return "\n\n".join(parts)


def _validate(
    elements: list[ADLElement],
    relations: list[ADLRelation],
    model_name: str,
) -> Optional[str]:
    ids = [e.instance_id for e in elements]
    if len(ids) != len(set(ids)):
        return "ADL validation failed: duplicate instance identifiers detected."

    id_set = set(ids)
    for rel in relations:
        if rel.from_id not in id_set:
            return f"ADL validation failed: relation source '{rel.from_id}' does not exist."
        if rel.to_id not in id_set:
            return f"ADL validation failed: relation target '{rel.to_id}' does not exist."

    if not elements:
        return "ADL validation failed: no model elements could be extracted."

    return None


def _extract_json_content(text: str) -> Optional[str]:
    pattern = r"```\s*json\s*\n?([\s\S]*?)\n?```"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        candidate = match.group(1).strip()
        if candidate.startswith("[") and candidate.endswith("]"):
            return candidate

    for cb in re.findall(r"```[a-zA-Z0-9_-]*\s*\n?([\s\S]*?)\n?```", text):
        cb = cb.strip()
        if cb.startswith("[") and cb.endswith("]"):
            try:
                json.loads(cb)
                return cb
            except Exception:
                pass

    # last resort: bare array anywhere in the text
    m = re.search(r"(\[\s*\{[\s\S]*\}\s*\])", text)
    if m:
        try:
            candidate = m.group(1).strip()
            json.loads(candidate)
            return candidate
        except Exception:
            pass

    return None


def _validate_4em_json_schema(nodes: list[dict]) -> Optional[str]:
    if not isinstance(nodes, list):
        return "Expected a JSON array of nodes."
    if not nodes:
        return "JSON array is empty."
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            return f"Node {i} is not an object."
        for field in ("id", "label", "type", "next"):
            if field not in node:
                return f"Node {i} missing required field: '{field}'"
        if not isinstance(node["next"], list):
            return f"Node {i} 'next' field must be an array."
    return None


def generate_adl(
    stage1_blueprint: str,
    final_output: str,
    framework_selected: str,
    model_name: str = "hyde_model",
) -> tuple[str, Optional[str]]:
    elements: list[ADLElement] = []
    relations: list[ADLRelation] = []

    json_str = _extract_json_content(final_output)

    if json_str:
        try:
            raw_nodes = json.loads(json_str)
            schema_error = _validate_4em_json_schema(raw_nodes)
            if not schema_error:
                raw_nodes = _inject_mandatory_relations(raw_nodes)
                elements, relations = _parse_4em_json(json.dumps(raw_nodes))
            else:
                elements, relations = _parse_narrative_fallback(final_output, framework_selected)
        except Exception:
            elements, relations = _parse_narrative_fallback(final_output, framework_selected)
    else:
        elements, relations = _parse_narrative_fallback(final_output, framework_selected)

    error = _validate(elements, relations, model_name)
    if error:
        return "", error

    warnings = _check_relation_completeness(elements, relations)
    if warnings:
        print("[ADL Export Warnings] " + "; ".join(warnings), file=sys.stderr)

    safe_name = adl_escape(model_name.replace("_", " "))
    lines: list[str] = [
        "//////////////////////////////////////////////////////////////",
        "//",
        "VERSION <5.1>",
        "",
        f"BUSINESS PROCESS MODEL <{safe_name}> : <4EM-Rostock Library_87_22_04_01>",
        "VERSION <>",
        "TYPE <4EM General Model>",
        "//",
    ]

    by_type: dict[str, list[ADLElement]] = {}
    for elem in elements:
        by_type.setdefault(elem.adl_type, []).append(elem)

    for adl_type in _4EM_LAYER_ORDER:
        elems = by_type.get(adl_type, [])
        if not elems:
            continue
        display_name = _4EM_LAYER_DISPLAY.get(adl_type, adl_type.upper() + "S")
        lines.append("//")
        lines.append("// --------------------------------------------------------------")
        lines.append(f"// {display_name}")
        lines.append("// --------------------------------------------------------------")
        for elem in elems:
            lines.append(_render_instance(elem))
            lines.append("")

    if relations:
        lines.append("//")
        lines.append("// --------------------------------------------------------------")
        lines.append("// RELATIONS")
        lines.append("// --------------------------------------------------------------")
        for rel in relations:
            lines.append(_render_relation(rel))
            lines.append("")

    # CRLF for native Windows ADOxx / 4EM Toolkit compatibility
    adl_content = "\r\n".join(lines)

    try:
        adl_content.encode("utf-8")
    except UnicodeEncodeError as e:
        return "", f"ADL file contains invalid UTF-8 characters: {e}"

    if "<PLACEHOLDER>" in adl_content or "{{" in adl_content:
        return "", "ADL file contains unresolved placeholders."

    return adl_content, None
