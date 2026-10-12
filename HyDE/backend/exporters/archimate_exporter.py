from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

from .exporter_utils import generate_uuid


@dataclass
class ArchElement:
    uid: str
    xsi_type: str
    name: str
    folder: str
    extra_attrs: dict = field(default_factory=dict)


@dataclass
class ArchRelation:
    uid: str
    xsi_type: str
    source: str
    target: str
    name: str = ""


_4EM_ARCH_MAP: dict[str, tuple[str, str]] = {
    "Goal":     ("archimate:Goal",             "Motivation"),
    "Process":  ("archimate:BusinessProcess",  "Business"),
    "Data":     ("archimate:DataObject",       "Application"),
    "Resource": ("archimate:BusinessActor",    "Business"),
}

_RELATION_MAP: dict[tuple[str, str], str] = {
    ("Goal",            "Goal"):           "archimate:InfluenceRelationship",
    ("Goal",            "BusinessProcess"):"archimate:TriggeringRelationship",
    ("BusinessProcess", "BusinessProcess"):"archimate:TriggeringRelationship",
    ("BusinessProcess", "DataObject"):     "archimate:AccessRelationship",
    ("DataObject",      "BusinessProcess"):"archimate:AccessRelationship",
    ("BusinessActor",   "BusinessProcess"):"archimate:AssignmentRelationship",
    ("BusinessActor",   "Goal"):           "archimate:AssignmentRelationship",
}

_BPMN_TAG_MAP: dict[str, tuple[str, str, dict]] = {
    "usertask":           ("archimate:BusinessProcess", "Business", {}),
    "servicetask":        ("archimate:BusinessProcess", "Business", {}),
    "sendtask":           ("archimate:BusinessProcess", "Business", {}),
    "receivetask":        ("archimate:BusinessProcess", "Business", {}),
    "manualtask":         ("archimate:BusinessProcess", "Business", {}),
    "businesstask":       ("archimate:BusinessProcess", "Business", {}),
    "scripttask":         ("archimate:BusinessProcess", "Business", {}),
    "task":               ("archimate:BusinessProcess", "Business", {}),
    "startevent":         ("archimate:BusinessEvent",    "Business", {}),
    "endevent":           ("archimate:BusinessEvent",    "Business", {}),
    "intermediateevent":  ("archimate:BusinessEvent",    "Business", {}),
    "boundaryevent":      ("archimate:BusinessEvent",    "Business", {}),
    "event":              ("archimate:BusinessEvent",    "Business", {}),
    "exclusivegateway":   ("archimate:Junction",         "Other",     {"type": "xor"}),
    "parallelgateway":    ("archimate:Junction",         "Other",     {"type": "and"}),
    "inclusivegateway":   ("archimate:Junction",         "Other",     {"type": "or"}),
    "eventbasedgateway":  ("archimate:Junction",         "Other",     {"type": "xor"}),
    "gateway":            ("archimate:Junction",         "Other",     {"type": "xor"}),
    "dataobject":         ("archimate:DataObject",       "Application", {}),
    "datastore":          ("archimate:DataObject",       "Application", {}),
    "lane":               ("archimate:BusinessActor",    "Business", {}),
    "pool":               ("archimate:BusinessActor",    "Business", {}),
    "group":              ("archimate:Grouping",         "Other",     {}),
    "textannotation":     ("archimate:Grouping",         "Other",     {}),
}

_BOX_W = 120
_BOX_H = 55
_GRID_COL_PX = 160
_GRID_ROW_PX = 90
_MARGIN_PX   = 24


def _arch_short(xsi_type: str) -> str:
    return xsi_type.split(":")[-1] if ":" in xsi_type else xsi_type


def _infer_rel_type(src: ArchElement, tgt: ArchElement) -> str:
    key = (_arch_short(src.xsi_type), _arch_short(tgt.xsi_type))
    return _RELATION_MAP.get(key, "archimate:AssociationRelationship")


def _infer_bpmn_rel_type(src: ArchElement, tgt: ArchElement, flow_name: str = "") -> str:
    src_short = _arch_short(src.xsi_type)
    tgt_short = _arch_short(tgt.xsi_type)
    
    if src_short == "Junction":
        return "archimate:TriggeringRelationship"
    
    if tgt_short == "Junction":
        return "archimate:TriggeringRelationship"
    
    key = (src_short, tgt_short)
    return _RELATION_MAP.get(key, "archimate:TriggeringRelationship")


def _parse_4em_json(blueprint: str) -> tuple[list[ArchElement], list[ArchRelation]]:
    raw_nodes: list[dict] = json.loads(blueprint)

    id_to_elem: dict[str, ArchElement] = {}
    elements: list[ArchElement] = []

    for node in raw_nodes:
        raw_type = node.get("type", "").strip()
        label    = node.get("label", "").strip()

        name = label.split(":", 1)[1].strip() if ":" in label else label

        xsi_type, folder = _4EM_ARCH_MAP.get(raw_type, ("archimate:BusinessObject", "Business"))

        uid = generate_uuid()
        elem = ArchElement(uid=uid, xsi_type=xsi_type, name=name, folder=folder)
        id_to_elem[node["id"]] = elem
        elements.append(elem)

    relations: list[ArchRelation] = []
    for node in raw_nodes:
        src = id_to_elem.get(node["id"])
        if src is None:
            continue
        for next_id in node.get("next", []):
            tgt = id_to_elem.get(next_id)
            if tgt is None:
                continue
            rel = ArchRelation(
                uid=generate_uuid(),
                xsi_type=_infer_rel_type(src, tgt),
                source=src.uid,
                target=tgt.uid,
            )
            relations.append(rel)

    return elements, relations


def _extract_bpmn_xml(text: str) -> Optional[str]:
    pattern = r"```\s*(?:xml|bpmn)\s*\n?([\s\S]*?)\n?```"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _parse_bpmn_xml_from_string(xml_str: str) -> tuple[list[ArchElement], list[ArchRelation]]:
    xml_str = xml_str.strip()

    ET.register_namespace('bpmn', 'http://www.omg.org/spec/BPMN/20100524/MODEL')
    ET.register_namespace('bpmndi', 'http://www.omg.org/spec/BPMN/20100524/DI')
    ET.register_namespace('dc', 'http://www.omg.org/spec/DD/20100524/DC')
    ET.register_namespace('di', 'http://www.omg.org/spec/DD/20100524/DI')

    try:
        root = ET.fromstring(xml_str)
    except Exception as e:
        raise ValueError(f"Failed to parse BPMN XML: {e}")

    elements = []
    relations = []
    id_to_uid = {}
    bpmn_id_counter = 0

    def get_or_create_bpmn_id(elem_id: Optional[str]) -> str:
        nonlocal bpmn_id_counter
        if elem_id:
            return elem_id
        bpmn_id_counter += 1
        return f"_synthetic_{bpmn_id_counter}"

    def get_local_tag(tag: str) -> str:
        if '}' in tag:
            return tag.split('}')[-1]
        if ':' in tag:
            return tag.split(':')[-1]
        return tag

    def map_bpmn_tag(tag: str) -> tuple[str, str, dict]:
        tag_lower = tag.lower()
        if tag_lower in _BPMN_TAG_MAP:
            return _BPMN_TAG_MAP[tag_lower]
        for suffix, (xsi_type, folder, extra) in [
            ("task", ("archimate:BusinessProcess", "Business", {})),
            ("event", ("archimate:BusinessEvent", "Business", {})),
            ("gateway", ("archimate:Junction", "Other", {"type": "or"})),
        ]:
            if tag_lower.endswith(suffix):
                return (xsi_type, folder, extra)
        return ("", "", {})

    for elem in root.iter():
        local_tag = get_local_tag(elem.tag)
        
        name = elem.get('name', local_tag)
        elem_id = elem.get('id')
        
        elem_id = get_or_create_bpmn_id(elem_id)
        
        xsi_type, folder, extra_attrs = map_bpmn_tag(local_tag)
        
        if xsi_type:
            uid = generate_uuid()
            id_to_uid[elem_id] = uid
            elements.append(ArchElement(
                uid=uid,
                xsi_type=xsi_type,
                name=name,
                folder=folder,
                extra_attrs=extra_attrs
            ))
    
    uid_to_elem = {e.uid: e for e in elements}
    
    for elem in root.iter():
        local_tag = get_local_tag(elem.tag)
        tag_lower = local_tag.lower()
            
        if tag_lower == 'sequenceflow':
            source_ref = elem.get('sourceRef')
            target_ref = elem.get('targetRef')
            name = elem.get('name', '')
            
            if source_ref and target_ref and source_ref in id_to_uid and target_ref in id_to_uid:
                src_uid = id_to_uid[source_ref]
                tgt_uid = id_to_uid[target_ref]
                src_elem = uid_to_elem[src_uid]
                tgt_elem = uid_to_elem[tgt_uid]
                rel_uid = generate_uuid()
                relations.append(ArchRelation(
                    uid=rel_uid,
                    xsi_type=_infer_bpmn_rel_type(src_elem, tgt_elem, name),
                    source=src_uid,
                    target=tgt_uid,
                    name=name
                ))

    return elements, relations


def _parse_bpmn_xml(final_output: str, stage1_blueprint: str) -> tuple[list[ArchElement], list[ArchRelation]]:
    xml_str = _extract_bpmn_xml(final_output)
    
    if not xml_str:
        xml_str = _extract_bpmn_xml(stage1_blueprint)
    
    if not xml_str:
        start = final_output.find("<bpmn:definitions")
        end = final_output.find("</bpmn:definitions>")
        if start != -1 and end != -1:
            xml_str = final_output[start:end+19]
        else:
            raise ValueError("No BPMN XML found in the output.")

    return _parse_bpmn_xml_from_string(xml_str)


def _parse_narrative_fallback(
    final_output: str,
) -> tuple[list[ArchElement], list[ArchRelation]]:
    narrative = final_output.split("```")[0]
    pattern   = r"\b([A-Z][a-z]+(?: [A-Z][a-z]+){1,4})\b"
    matches   = re.findall(pattern, narrative)

    unique = list(dict.fromkeys(matches))[:12]

    elements: list[ArchElement] = []
    for idx, name in enumerate(unique):
        xsi_type = "archimate:BusinessProcess" if idx < len(unique) // 2 else "archimate:BusinessObject"
        folder   = "Business"
        uid      = generate_uuid()
        elements.append(ArchElement(uid=uid, xsi_type=xsi_type, name=name, folder=folder))

    return elements, []


_FOLDER_TYPE = {
    "Strategy":                    "strategy",
    "Business":                    "business",
    "Application":                 "application",
    "Technology & Physical":       "technology",
    "Motivation":                  "motivation",
    "Implementation & Migration":  "implementation_migration",
    "Other":                       "other",
    "Relations":                   "relations",
}

_ALL_FOLDERS = [
    "Strategy",
    "Business",
    "Application",
    "Technology & Physical",
    "Motivation",
    "Implementation & Migration",
    "Other",
]


def _build_archimate_xml(
    elements: list[ArchElement],
    relations: list[ArchRelation],
    model_name: str,
) -> str:
    model_id = generate_uuid()
    model_attrs = {
        "xmlns:xsi":       "http://www.w3.org/2001/XMLSchema-instance",
        "xmlns:archimate": "http://www.archimatetool.com/archimate",
        "name":            model_name,
        "id":              model_id,
        "version":         "5.0.0",
    }
    root = ET.Element("archimate:model", model_attrs)

    folder_uids: dict[str, str] = {f: generate_uuid() for f in _ALL_FOLDERS}
    relations_folder_uid = generate_uuid()

    by_folder: dict[str, list[ArchElement]] = {f: [] for f in _ALL_FOLDERS}
    for elem in elements:
        target_folder = elem.folder if elem.folder in by_folder else "Other"
        by_folder[target_folder].append(elem)

    for folder_name in _ALL_FOLDERS:
        ftype = _FOLDER_TYPE[folder_name]
        fuid  = folder_uids[folder_name]
        folder_elem = ET.SubElement(root, "folder", {
            "name": folder_name,
            "id":   fuid,
            "type": ftype,
        })
        for arch_elem in by_folder[folder_name]:
            attrs = {
                "xsi:type": arch_elem.xsi_type,
                "name":     arch_elem.name,
                "id":       arch_elem.uid,
            }
            attrs.update(arch_elem.extra_attrs)
            ET.SubElement(folder_elem, "element", attrs)

    rel_folder = ET.SubElement(root, "folder", {
        "name": "Relations",
        "id":   relations_folder_uid,
        "type": "relations",
    })
    for rel in relations:
        rel_attrs = {
            "xsi:type": rel.xsi_type,
            "id":       rel.uid,
            "source":   rel.source,
            "target":   rel.target,
        }
        if rel.name:
            rel_attrs["name"] = rel.name
        ET.SubElement(rel_folder, "element", rel_attrs)

    views_folder_uid = generate_uuid()
    views_folder = ET.SubElement(root, "folder", {
        "name": "Views",
        "id":   views_folder_uid,
        "type": "diagrams",
    })

    diagram_id   = generate_uuid()
    diagram_elem = ET.SubElement(views_folder, "element", {
        "xsi:type": "archimate:ArchimateDiagramModel",
        "name":     model_name,
        "id":       diagram_id,
    })

    elem_to_child_uid: dict[str, str] = {arch_elem.uid: generate_uuid() for arch_elem in elements}

    rel_to_conn_uid: dict[str, str] = {}
    child_to_target_conns: dict[str, list[str]] = {}

    for rel in relations:
        src_child = elem_to_child_uid.get(rel.source)
        tgt_child = elem_to_child_uid.get(rel.target)
        if src_child and tgt_child:
            conn_uid = generate_uuid()
            rel_to_conn_uid[rel.uid] = conn_uid
            child_to_target_conns.setdefault(tgt_child, []).append(conn_uid)

    child_elems: dict[str, ET.Element] = {}

    cols = 4
    for idx, arch_elem in enumerate(elements):
        col = idx % cols
        row = idx // cols
        x = _MARGIN_PX + col * _GRID_COL_PX
        y = _MARGIN_PX + row * _GRID_ROW_PX

        child_uid = elem_to_child_uid[arch_elem.uid]
        attrs = {
            "xsi:type":         "archimate:DiagramObject",
            "id":               child_uid,
            "archimateElement": arch_elem.uid,
        }
        
        # Archi requires targetConnections on the receiving diagram object
        if child_uid in child_to_target_conns:
            attrs["targetConnections"] = " ".join(child_to_target_conns[child_uid])

        child = ET.SubElement(diagram_elem, "child", attrs)
        child_elems[child_uid] = child
        ET.SubElement(child, "bounds", {
            "x":      str(x),
            "y":      str(y),
            "width":  str(_BOX_W),
            "height": str(_BOX_H),
        })

    for rel in relations:
        src_child = elem_to_child_uid.get(rel.source)
        tgt_child = elem_to_child_uid.get(rel.target)
        conn_uid = rel_to_conn_uid.get(rel.uid)
        
        if not (src_child and tgt_child and conn_uid):
            continue

        src_child_elem = child_elems.get(src_child)
        if src_child_elem is not None:
            ET.SubElement(src_child_elem, "sourceConnection", {
                "xsi:type":            "archimate:Connection",
                "id":                  conn_uid,
                "source":              src_child,
                "target":              tgt_child,
                "archimateRelationship": rel.uid,
            })

    ET.indent(root, space="  ")
    xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=False)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_bytes}'


def _validate(
    elements: list[ArchElement],
    relations: list[ArchRelation],
) -> Optional[str]:
    if not elements:
        return "Archi export failed: no model elements could be extracted."

    ids = [e.uid for e in elements]
    if len(ids) != len(set(ids)):
        return "Archi export failed: duplicate element IDs."

    id_set = set(ids)
    for rel in relations:
        if rel.source not in id_set:
            return f"Archi export failed: relation source '{rel.source}' does not exist."
        if rel.target not in id_set:
            return f"Archi export failed: relation target '{rel.target}' does not exist."

    return None


def generate_archimate(
    stage1_blueprint: str,
    final_output: str,
    framework_selected: str,
    model_name: str = "hyde_model",
) -> tuple[str, Optional[str]]:
    elements: list[ArchElement]
    relations: list[ArchRelation]

    is_bpmn_framework = (framework_selected == "BPMN")

    try:
        elements, relations = _parse_bpmn_xml(final_output, stage1_blueprint)
    except Exception as exc:
        if is_bpmn_framework:
            return "", f"Archi export failed for BPMN framework: No valid BPMN XML found in LLM output. Expected a ```xml``` or ```bpmn``` markdown block containing <bpmn:definitions>..."
        else:
            try:
                elements, relations = _parse_narrative_fallback(final_output)
            except Exception as exc2:
                return "", f"Archi export failed: BPMN XML parsing failed ({exc}); narrative fallback also failed ({exc2})"

    if is_bpmn_framework and not elements:
        return "", "Archi export failed for BPMN framework: No BPMN elements could be extracted from the XML."

    error = _validate(elements, relations)
    if error:
        return "", error

    xml_content = _build_archimate_xml(elements, relations, model_name)

    try:
        xml_content.encode("utf-8")
    except UnicodeEncodeError as e:
        return "", f"Archimate file contains invalid UTF-8 characters: {e}"

    return xml_content, None
