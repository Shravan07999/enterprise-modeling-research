import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Tuple, Set
from sqlmodel import Session, select
from database import get_session
from models import AuditLog, ExportLog, ExportLogRead
import json
import re
import os
import time
from uuid import uuid4
from dotenv import load_dotenv
import openai

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/export",
    tags=["export"],
)

_available_models = [
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
]

_max_tokens = {
    "gpt-4o": 16384,
    "gpt-4-turbo": 4096,
    "gpt-3.5-turbo": 4096,
}

_PROMPTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "export_prompts"
)


class ExportException(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class ExportStep(BaseModel):
    step: int = 1
    prompt_name: str = ""
    type: str = "GENERATION"
    result: str = ""


class ExportRequest(BaseModel):
    chain_name: str
    steps: List[ExportStep]
    history_id: Optional[int] = None
    inputs: Optional[Dict[str, Any]] = None


# 4EM General Model schema and layout definition

_ADL_CLASS_ATTRS = {
    "Organizational Unit": ["Position", "External tool coupling", "Description", "Decomposition", "Attributes"],
    "Role": ["Position", "External tool coupling", "Description", "Decomposition", "Attributes"],
    "Goal": ["Position", "External tool coupling", "Description", "Criticality", "Priority", "Intermodel-Relations", "Decomposition", "Defined by", "Attributes", "Is the exact same as", "hidden_attribute"],
    "Problem": ["Position", "External tool coupling", "Intermodel-Relations", "Decomposition", "Attributes", "Defined by", "Priority", "Criticality", "Description", "type", "Is the exact same as", "hidden_attribute"],
    "Process": ["Position", "External tool coupling", "Description", "Decomposed Process", "Intermodel-Relations", "Decomposition", "Execution Time", "Complexity", "Type", "Attributes", "Is the exact same as", "hidden_attribute"],
    "Information Set": ["Position", "External tool coupling", "Description", "Intermodel-Relations", "Decomposition"],
    "Unspecific/Product/Service": ["Position", "External tool coupling", "Specification", "Attribute", "Description", "Intermodel-Relations", "Decomposition"],
    "Component": ["Position", "External tool coupling", "Description", "Decomposition", "Quantity", "Location", "Intermodel-Relations"],
    "Feature": ["Position", "External tool coupling", "Description", "Attribute", "Intermodel-Relations", "Decomposition"],
    "IS Technical Component": ["Position", "External tool coupling", "Description", "Intermodel-Relations", "Decomposition", "Location", "Quantity", "Attributes"],
    "Concept": ["Position", "External tool coupling", "Description", "Intermodel-Relations", "Decomposition"],
    "Attribute": ["Position", "External tool coupling", "Description", "Intermodel-Relations", "Decomposition"],
}

_ADL_EMPTY_ATTRS = {"Attributes", "Intermodel-Relations", "Attribute"}
_ADL_NUMERIC_ATTRS = {"Execution Time", "Complexity", "Quantity"}

_ADL_SECTION_ORDER = [
    ("Organizational Unit", "ORGANIZATIONAL UNITS"),
    ("Role", "ROLES"),
    ("Goal", "GOALS"),
    ("Problem", "PROBLEM"),
    ("Process", "PROCESSES"),
    ("Information Set", "INFORMATION SETS"),
    ("Unspecific/Product/Service", "PRODUCT (Unspecific/Product/Service)"),
    ("Component", "COMPONENTS"),
    ("Feature", "FEATURES"),
    ("IS Technical Component", "TECHNICAL COMPONENTS"),
    ("Concept", "CONCEPTS"),
    ("Attribute", "ATTRIBUTES"),
]

_ADL_LAYOUT = {
    "Organizational Unit": {"x": 1.0, "y0": 1.0, "step": 2.0, "w": 4.0, "h": 1.5},
    "Role": {"x": 1.0, "y0": 6.0, "step": 2.0, "w": 4.0, "h": 1.5},
    "Goal": {"x": 1.0, "y0": 11.0, "step": 2.0, "w": 6.0, "h": 1.5},
    "Problem": {"x": 1.0, "y0": 17.5, "step": 2.0, "w": 6.0, "h": 1.5},
    "Process": {"x": 1.0, "y0": 20.0, "step": 2.0, "w": 5.5, "h": 1.2},
    "Information Set": {"x": 8.0, "y0": 6.0, "step": 2.0, "w": 5.0, "h": 1.5},
    "Unspecific/Product/Service": {"x": 14.0, "y0": 1.0, "step": 3.0, "w": 6.0, "h": 2.0},
    "Component": {"x": 14.0, "y0": 4.0, "step": 3.0, "w": 4.0, "h": 2.0},
    "Feature": {"x": 21.0, "y0": 1.0, "step": 2.0, "w": 4.0, "h": 1.5},
    "IS Technical Component": {"x": 21.0, "y0": 6.0, "step": 2.0, "w": 4.0, "h": 1.5},
    "Concept": {"x": 1.0, "y0": 29.0, "step": 2.0, "w": 5.0, "h": 1.5},
    "Attribute": {"x": 8.0, "y0": 29.0, "step": 2.0, "w": 4.0, "h": 1.5},
}

_ADL_CLASS_ALIASES = {
    "organizational unit": "Organizational Unit",
    "organization unit": "Organizational Unit",
    "org unit": "Organizational Unit",
    "organisation": "Organizational Unit",
    "organisational": "Organizational Unit",
    "organizational": "Organizational Unit",
    "actor": "Role",
    "role": "Role",
    "stakeholder": "Role",
    "person": "Role",
    "goal": "Goal",
    "objective": "Goal",
    "problem": "Problem",
    "weakness": "Problem",
    "process": "Process",
    "business process": "Process",
    "activity": "Process",
    "workflow": "Process",
    "task": "Process",
    "information set": "Information Set",
    "infoset": "Information Set",
    "information": "Information Set",
    "unspecific/product/service": "Unspecific/Product/Service",
    "unspecific product/service": "Unspecific/Product/Service",
    "product/service": "Unspecific/Product/Service",
    "product": "Unspecific/Product/Service",
    "service": "Unspecific/Product/Service",
    "component": "Component",
    "feature": "Feature",
    "is technical component": "IS Technical Component",
    "technical component": "IS Technical Component",
    "technology component": "IS Technical Component",
    "system": "IS Technical Component",
    "concept": "Concept",
    "attribute": "Attribute",
}

_ADL_RELATION_ALIASES = {
    "part of": "part of",
    "is part of": "part of",
    "part-of": "part of",
    "works in": "works in",
    "work in": "works in",
    "works at": "works in",
    "refined by (and)": "refined by (AND)",
    "refined by and": "refined by (AND)",
    "refined by (or)": "refined by (OR)",
    "refined by or": "refined by (OR)",
    "refined by": "refined by",
    "hinders": "Hinders",
    "hinders goal": "Hinders",
    "supports": "supports",
    "support": "supports",
    "is responsible for": "is responsible for",
    "responsible for": "is responsible for",
    "decomposed into": "decomposed into",
    "decomposes into": "decomposed into",
    "decomposition": "decomposed into",
    "input": "Input",
    "output": "Output",
    "consists of": "consists of",
    "consist of": "consists of",
    "contains": "consists of",
    "offers": "offers",
    "offer": "offers",
    "included in": "included in",
    "is included in": "included in",
    "includes": "included in",
    "is similar to": "is similar to",
}


def _fmt(v):
    return f"{v:g}"


def _adl_value(v):
    s = str(v).strip().replace("\n", " ").replace("\r", " ")
    return s.replace('"', "'")


def _adl_resolve_attr(cls, attr, attrs):
    if attr in ("Criticality", "Priority"):
        return _adl_value(attrs.get(attr, "Low"))
    if attr in ("Execution Time", "Complexity", "Quantity"):
        # Coerce to a plain, always-valid string so no unexpected type (None/bool/float)
        # can ever leak into the serialized VALUE line.
        v = attrs.get(attr, 0)
        if v is None:
            return 0
        if isinstance(v, bool):
            return int(v)
        return v
    if attr == "type":
        if cls == "Problem":
            return "Problem"
        return _adl_value(attrs.get("Type", ""))
    return _adl_value(attrs.get(attr, ""))


def _normalize_adl_class(value):
    key = str(value).strip().lower()
    if key in _ADL_CLASS_ALIASES:
        return _ADL_CLASS_ALIASES[key]
    if str(value).strip() in _ADL_CLASS_ATTRS:
        return str(value).strip()
    return None


def _normalize_adl_relation(value):
    return _ADL_RELATION_ALIASES.get(str(value).strip().lower())


def _render_adl_instance(cls, entity):
    label = entity["_label"]
    pos = entity["_pos"]
    attrs = entity.get("attributes") or {}
    description = entity.get("description") or entity["name"]
    lines = [f"INSTANCE <{label}> : <{cls}>", ""]
    for attr in _ADL_CLASS_ATTRS.get(cls, _ADL_CLASS_ATTRS["Role"]):
        if attr == "Position":
            lines.append("\tATTRIBUTE <Position>")
            lines.append(f'\tVALUE "{pos}"')
        elif attr == "Description":
            lines.append("\tATTRIBUTE <Description>")
            lines.append(f'\tVALUE "{_adl_value(description)}"')
        elif attr in _ADL_EMPTY_ATTRS:
            lines.append(f"\tATTRIBUTE <{attr}>")
            lines.append("\tVALUE")
        else:
            lines.append(f"\tATTRIBUTE <{attr}>")
            lines.append(f'\tVALUE "{_adl_resolve_attr(cls, attr, attrs)}"')
        lines.append("")
    lines.append("//END")
    return "\n".join(lines)


def _render_adl_relation(rel_type, src_label, src_cls, tgt_label, tgt_cls, description=""):
    return "\n".join(
        [
            "RELATION <4EM_Relation>",
            f"\tFROM <{src_label}> : <{src_cls}>",
            f"\tTO <{tgt_label}> : <{tgt_cls}>",
            "",
            "\tATTRIBUTE <Positions>",
            '\tVALUE ""',
            "",
            "\tATTRIBUTE <Type>",
            f'\tVALUE "{_adl_value(rel_type)}"',
            "",
            "\tATTRIBUTE <Description>",
            f'\tVALUE "{_adl_value(description)}"',
            "",
            "//END",
        ]
    )


def _normalize_and_validate_adl(data):
    problems = []
    if not isinstance(data, dict):
        return ["Response was not a JSON object"]
    entities = data.get("entities")
    relations = data.get("relations")
    if not isinstance(entities, list) or not entities:
        problems.append("'entities' list is missing or empty")
    if not isinstance(relations, list) or not relations:
        problems.append("'relations' list is missing or empty")
    if problems:
        return problems

    names = {}
    for ent in entities:
        cls = _normalize_adl_class(ent.get("class", ""))
        if cls is None:
            problems.append(f"Unknown 4EM class: {ent.get('class')!r}")
            continue
        ent["class"] = cls
        ent["name"] = str(ent.get("name", "")).strip()
        if not ent["name"]:
            problems.append("Entity with empty name")
        ent["description"] = str(ent.get("description") or ent["name"])
        if not isinstance(ent.get("attributes"), dict):
            ent["attributes"] = {}
        key = ent["name"].lower()
        if key in names:
            problems.append(f"Duplicate entity name: {ent['name']!r}")
        names[key] = ent

    for rel in relations:
        rt = _normalize_adl_relation(rel.get("type", ""))
        if rt is None:
            problems.append(f"Unknown 4EM relation type: {rel.get('type')!r}")
        else:
            rel["type"] = rt
        s = str(rel.get("source", "")).strip()
        t = str(rel.get("target", "")).strip()
        rel["source"] = s
        rel["target"] = t
        if s.lower() not in names:
            problems.append(f"Relation source not found among entities: {s!r}")
        if t.lower() not in names:
            problems.append(f"Relation target not found among entities: {t!r}")
        if s and s.lower() == t.lower():
            problems.append(f"Self-loop relation on {s!r}")

    # The 4EM Toolkit stores at most ONE relation between any two instances
    # (import error "Instances are already related!"), regardless of relation type or
    # direction. Enforce uniqueness on the unordered pair to guarantee a valid import.
    seen_pairs = set()
    for rel in relations:
        pair = frozenset((rel["source"].lower(), rel["target"].lower()))
        if pair in seen_pairs:
            problems.append(
                f"Duplicate relation: '{rel['source']}' and '{rel['target']}' are already "
                "related. Each pair of 4EM instances can have at most one relation, even "
                "with different types or directions (e.g. both an Input and an Output "
                "between the same Process and Information Set). Merge them into a single "
                "relation and summarize the full exchange in its 'description'."
            )
        seen_pairs.add(pair)

    return problems


def _serialize_adl(chain_name, model):
    entities = model["entities"]
    relations = model["relations"]
    model_name = _adl_value(model.get("model_name") or f"4EM General Model - {chain_name}")

    header = (
        "//////////////////////////////////////////////////////////////\n"
        "//\n"
        "VERSION <5.1>\n"
        "\n"
        f"BUSINESS PROCESS MODEL <{model_name}> : <4EM-Rostock Library_87_22_04_01>\n"
        "VERSION <>\n"
        "TYPE <4EM General Model>"
    )

    seq = 0
    label_map = {}
    by_class = {}
    cursors = {cls: cfg["y0"] for cls, cfg in _ADL_LAYOUT.items()}
    for ent in entities:
        cls = ent["class"]
        seq += 1
        cfg = _ADL_LAYOUT.get(cls, _ADL_LAYOUT["Role"])
        ent["_label"] = f"{cls} - {seq}"
        ent["_pos"] = (
            f"NODE x:{_fmt(cfg['x'])}cm y:{_fmt(cursors[cls])}cm "
            f"w:{_fmt(cfg['w'])}cm h:{_fmt(cfg['h'])}cm index:{seq}"
        )
        cursors[cls] += cfg["step"]
        label_map[ent["name"].lower()] = (ent["_label"], cls)
        by_class.setdefault(cls, []).append(ent)

    parts = [header]
    banner = "// " + "-" * 62
    for cls, title in _ADL_SECTION_ORDER:
        if cls not in by_class:
            continue
        parts.append("//\n" + banner + "\n" + f"// {title}\n" + banner)
        for ent in by_class[cls]:
            parts.append(_render_adl_instance(cls, ent))

    if relations:
        parts.append("//\n" + banner + "\n" + "// RELATIONS\n" + banner)
        for rel in relations:
            s_label, s_cls = label_map.get(rel["source"].lower(), (rel["source"], "Role"))
            t_label, t_cls = label_map.get(rel["target"].lower(), (rel["target"], "Role"))
            parts.append(
                _render_adl_relation(
                    rel["type"], s_label, s_cls, t_label, t_cls, rel.get("description") or ""
                )
            )

    return "\n\n".join(p.rstrip() for p in parts) + "\n"


def _validate_serialized_adl(text):
    """Safety net: guarantee the serialized ADL never contains an invalid VALUE line.

    The 4EM Toolkit rejects every value form except:
      - a bare ``VALUE`` (no argument) -- only valid after an empty-set attribute,
      - a quoted ``VALUE "..."``, or
      - a numeric literal (``VALUE 0`` / ``VALUE 0.5``).
    An unquoted bare word (e.g. ``VALUE Long``) is a syntax error. The serializer
    fixes this by construction, but this guard makes any future regression fail
    loudly at export time instead of producing a file the toolkit cannot import.
    """
    problems = []
    attr_names = set()
    attr_names.update(_ADL_EMPTY_ATTRS)
    attr_names.update(_ADL_NUMERIC_ATTRS)
    attr_names.update(
        {
            "Position", "External tool coupling", "Description", "Decomposition",
            "Decomposed Process", "Defined by", "Specification", "Location",
            "Is the exact same as", "Type", "type", "Criticality", "Priority",
            "hidden_attribute", "Positions",
        }
    )
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^\s*ATTRIBUTE <(.+)>$", lines[i])
        if m:
            attr = m.group(1)
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            vm = re.match(r"^\s*VALUE(?:\s+(.*))?$", next_line)
            if vm:
                value_part = (vm.group(1) or "").strip()
                if not value_part:
                    if attr not in _ADL_EMPTY_ATTRS:
                        problems.append(
                            f"bare VALUE (no argument) after ATTRIBUTE <{attr}> -- "
                            "only the empty-set attributes may carry a bare VALUE"
                        )
                elif not (value_part.startswith('"') and value_part.endswith('"')):
                    if not re.match(r"^[+-]?(\d+(\.\d*)?|\.\d+)$", value_part):
                        problems.append(
                            f"unquoted non-numeric VALUE '{value_part}' after "
                            f"ATTRIBUTE <{attr}> -- must be quoted or numeric"
                        )
            i += 1
        i += 1
    return problems


# ---------------------------------------------------------------------------
# ArchiMate: element/relationship whitelists (mirrors reference .archimate)
# ---------------------------------------------------------------------------

_ARCHIMATE_ELEMENT_TYPES = {
    "BusinessActor", "BusinessRole", "BusinessProcess", "BusinessFunction",
    "BusinessService", "BusinessObject", "BusinessInterface", "BusinessCollaboration",
    "BusinessEvent", "Product", "Contract",
    "ApplicationComponent", "ApplicationService", "ApplicationFunction",
    "ApplicationProcess", "ApplicationInterface", "ApplicationCollaboration",
    "DataObject",
    "Node", "Device", "SystemSoftware", "TechnologyService", "TechnologyFunction",
    "TechnologyProcess", "TechnologyInterface", "TechnologyCollaboration", "Artifact",
    "CommunicationNetwork", "TechnologyEvent",
    "Goal", "Requirement", "Constraint", "Driver", "Assessment", "Value", "Outcome",
    "Principle", "Meaning",
    "Resource", "Capability", "ValueStream", "CourseOfAction",
    "WorkPackage", "Deliverable", "ImplementationEvent",
    "Junction", "Grouping", "Location", "Stakeholder",
}

_ARCHIMATE_ELEMENT_ALIASES = {
    "actor": "BusinessActor",
    "business actor": "BusinessActor",
    "role": "BusinessRole",
    "business role": "BusinessRole",
    "process": "BusinessProcess",
    "business process": "BusinessProcess",
    "function": "BusinessFunction",
    "business function": "BusinessFunction",
    "service": "BusinessService",
    "business service": "BusinessService",
    "business object": "BusinessObject",
    "event": "BusinessEvent",
    "application component": "ApplicationComponent",
    "app component": "ApplicationComponent",
    "application": "ApplicationComponent",
    "app": "ApplicationComponent",
    "software": "ApplicationComponent",
    "application service": "ApplicationService",
    "application process": "ApplicationProcess",
    "application function": "ApplicationFunction",
    "application interface": "ApplicationInterface",
    "application data object": "DataObject",
    "data object": "DataObject",
    "data": "DataObject",
    "system": "ApplicationComponent",
    "system software": "SystemSoftware",
    "software system": "SystemSoftware",
    "node": "Node",
    "device": "Device",
    "hardware": "Device",
    "server": "Node",
    "network": "CommunicationNetwork",
    "database": "Artifact",
    "artifact": "Artifact",
    "technology": "TechnologyService",
    "technology service": "TechnologyService",
    "technology function": "TechnologyFunction",
    "goal": "Goal",
    "requirement": "Requirement",
    "constraint": "Constraint",
    "driver": "Driver",
    "assessment": "Assessment",
    "value": "Value",
    "outcome": "Outcome",
    "principle": "Principle",
    "meaning": "Meaning",
    "resource": "Resource",
    "capability": "Capability",
    "value stream": "ValueStream",
    "valuestream": "ValueStream",
    "course of action": "CourseOfAction",
    "courseofaction": "CourseOfAction",
    "work package": "WorkPackage",
    "workpackage": "WorkPackage",
    "deliverable": "Deliverable",
    "implementation event": "ImplementationEvent",
    "grouping": "Grouping",
    "junction": "Junction",
    "location": "Location",
    "stakeholder": "Stakeholder",
    "product": "Product",
    "contract": "Contract",
}

_ARCHIMATE_REL_ALIASES = {
    "association": "AssociationRelationship",
    "associationrelationship": "AssociationRelationship",
    "composition": "CompositionRelationship",
    "compositionrelationship": "CompositionRelationship",
    "composes": "CompositionRelationship",
    "consists of": "CompositionRelationship",
    "consist of": "CompositionRelationship",
    "aggregation": "AggregationRelationship",
    "aggregationrelationship": "AggregationRelationship",
    "aggregates": "AggregationRelationship",
    "part of": "AggregationRelationship",
    "assignment": "AssignmentRelationship",
    "assignmentrelationship": "AssignmentRelationship",
    "assigned to": "AssignmentRelationship",
    "assignedto": "AssignmentRelationship",
    "realization": "RealizationRelationship",
    "realizationrelationship": "RealizationRelationship",
    "realizes": "RealizationRelationship",
    "realised by": "RealizationRelationship",
    "realized by": "RealizationRelationship",
    "realises": "RealizationRelationship",
    "serving": "ServingRelationship",
    "servingrelationship": "ServingRelationship",
    "serves": "ServingRelationship",
    "triggering": "TriggeringRelationship",
    "triggeringrelationship": "TriggeringRelationship",
    "triggers": "TriggeringRelationship",
    "flow": "FlowRelationship",
    "flowrelationship": "FlowRelationship",
    "flows": "FlowRelationship",
    "access": "AccessRelationship",
    "accessrelationship": "AccessRelationship",
    "accesses": "AccessRelationship",
    "specialization": "SpecializationRelationship",
    "specializationrelationship": "SpecializationRelationship",
    "specializes": "SpecializationRelationship",
    "specialises": "SpecializationRelationship",
    "influence": "InfluenceRelationship",
    "influencerelationship": "InfluenceRelationship",
    "influences": "InfluenceRelationship",
    "used by": "UsedByRelationship",
    "usedbyrelationship": "UsedByRelationship",
    "uses": "UsedByRelationship",
    "information flow": "InformationFlowRelationship",
    "informationflowrelationship": "InformationFlowRelationship",
}

_LAYER_ALIASES = {
    "business": "Business",
    "application": "Application",
    "technology": "Technology",
    "infrastructure": "Technology",
    "physical": "Technology",
    "strategy": "Strategy",
    "motivation": "Motivation",
    "implementation": "Implementation & Migration",
    "implementation & migration": "Implementation & Migration",
    "implementation and migration": "Implementation & Migration",
    "other": "Other",
}

_BUSINESS_TYPES = {"BusinessActor", "BusinessRole", "BusinessProcess", "BusinessFunction", "BusinessService", "BusinessObject", "BusinessInterface", "BusinessCollaboration", "BusinessEvent", "Product", "Contract", "Meaning", "Value", "Stakeholder"}
_APPLICATION_TYPES = {"ApplicationComponent", "ApplicationService", "ApplicationFunction", "ApplicationProcess", "ApplicationInterface", "ApplicationCollaboration", "DataObject"}
_TECHNOLOGY_TYPES = {"Node", "Device", "SystemSoftware", "TechnologyService", "TechnologyFunction", "TechnologyProcess", "TechnologyInterface", "TechnologyCollaboration", "Artifact", "CommunicationNetwork", "TechnologyEvent"}
_MOTIVATION_TYPES = {"Goal", "Requirement", "Constraint", "Driver", "Assessment", "Outcome", "Principle"}
_STRATEGY_TYPES = {"Resource", "Capability", "ValueStream", "CourseOfAction"}
_IMPL_TYPES = {"WorkPackage", "Deliverable", "ImplementationEvent"}

_LAYER_ORDER = ["Business", "Application", "Technology", "Strategy", "Motivation", "Implementation & Migration", "Other"]


def _default_layer(el_type):
    if el_type in _BUSINESS_TYPES:
        return "Business"
    if el_type in _APPLICATION_TYPES:
        return "Application"
    if el_type in _TECHNOLOGY_TYPES:
        return "Technology"
    if el_type in _MOTIVATION_TYPES:
        return "Motivation"
    if el_type in _STRATEGY_TYPES:
        return "Strategy"
    if el_type in _IMPL_TYPES:
        return "Implementation & Migration"
    return "Other"


def _normalize_layer(value):
    return _LAYER_ALIASES.get(str(value).strip().lower())


def _normalize_archimate_type(value):
    v = str(value).strip()
    if v in _ARCHIMATE_ELEMENT_TYPES:
        return v
    return _ARCHIMATE_ELEMENT_ALIASES.get(v.lower())


def _normalize_archimate_rel(value):
    return _ARCHIMATE_REL_ALIASES.get(str(value).strip().lower())


def _normalize_and_validate_archimate(data):
    problems = []
    if not isinstance(data, dict):
        return ["Response was not a JSON object"]
    elements = data.get("elements")
    relationships = data.get("relationships")
    if not isinstance(elements, list) or not elements:
        problems.append("'elements' list is missing or empty")
    if not isinstance(relationships, list) or not relationships:
        problems.append("'relationships' list is missing or empty")
    if problems:
        return problems

    name_map = {}
    for el in elements:
        t = _normalize_archimate_type(el.get("type", ""))
        if t is None:
            problems.append(f"Unknown ArchiMate element type: {el.get('type')!r}")
            continue
        el["type"] = t
        el["name"] = str(el.get("name", "")).strip()
        if not el["name"]:
            problems.append("Element with empty name")
        layer = _normalize_layer(el.get("layer", ""))
        el["layer"] = layer if layer else _default_layer(t)
        key = el["name"].lower()
        if key in name_map:
            problems.append(f"Duplicate element name: {el['name']!r}")
        name_map[key] = el

    for rel in relationships:
        rt = _normalize_archimate_rel(rel.get("type", ""))
        if rt is None:
            problems.append(f"Unknown ArchiMate relationship type: {rel.get('type')!r}")
        else:
            rel["type"] = rt
        s = str(rel.get("source", "")).strip()
        t = str(rel.get("target", "")).strip()
        rel["source"] = s
        rel["target"] = t
        if s.lower() not in name_map:
            problems.append(f"Relationship source not found among elements: {s!r}")
        if t.lower() not in name_map:
            problems.append(f"Relationship target not found among elements: {t!r}")
        if s and s.lower() == t.lower():
            problems.append(f"Self-loop relationship on {s!r}")

    return problems


# ---------------------------------------------------------------------------
# Self-healing repair: LLM consistency errors are fixed generically instead of
# failing the whole export. Repairs are surfaced as notes (console + AuditLog).
# ---------------------------------------------------------------------------

# Class inference for a single 4EM relation endpoint, keyed by (relation, side).
_ADL_RELATION_ENDPOINT_HINTS = {
    ("refined by (AND)", "source"): "Goal",
    ("refined by (AND)", "target"): "Goal",
    ("refined by (OR)", "source"): "Goal",
    ("refined by (OR)", "target"): "Goal",
    ("refined by", "source"): "Goal",
    ("refined by", "target"): "Goal",
    ("Hinders", "source"): "Problem",
    ("Hinders", "target"): "Goal",
    ("supports", "source"): "Goal",
    ("supports", "target"): "Goal",
    ("is responsible for", "source"): "Role",
    ("is responsible for", "target"): "Goal",
    ("works in", "source"): "Role",
    ("works in", "target"): "Organizational Unit",
    ("decomposed into", "source"): "Process",
    ("decomposed into", "target"): "Process",
    ("Input", "source"): "Process",
    ("Input", "target"): "Information Set",
    ("Output", "source"): "Process",
    ("Output", "target"): "Information Set",
    ("consists of", "source"): "Information Set",
    ("consists of", "target"): "Attribute",
    ("offers", "source"): "Unspecific/Product/Service",
    ("offers", "target"): "Feature",
}


def _norm_key(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value).strip().lower()).strip()


def _class_from_name_keywords(low, aliases):
    tokens = set(low.split())
    for key in sorted(aliases, key=lambda k: -len(k)):
        key_tokens = key.split()
        if len(key_tokens) > 1:
            if " " + key + " " in " " + low + " ":
                return aliases[key]
        elif key in tokens:
            return aliases[key]
    return None


def _fuzzy_entity_match(raw, by_key):
    target = set(_norm_key(raw).split())
    if not target:
        return None
    best, best_score = None, 0.0
    for key, ent in by_key.items():
        tokens = set(key.split())
        if not tokens:
            continue
        overlap = len(target & tokens) / min(len(target), len(tokens))
        if overlap > best_score:
            best, best_score = key, overlap
    if best_score >= 0.6:
        return best
    return None


def _adl_pair_semantics(rel_type, side, other_cls):
    if rel_type in ("Input", "Output"):
        return "Information Set" if other_cls == "Process" else "Process"
    if rel_type == "works in":
        return "Organizational Unit" if other_cls == "Role" else "Role"
    if rel_type == "is responsible for":
        return "Role" if other_cls in ("Goal", "Process") else "Goal"
    if rel_type == "decomposed into":
        return other_cls
    if rel_type == "consists of":
        return "Attribute" if other_cls == "Information Set" and side == "target" else "Information Set"
    if rel_type == "offers":
        return "Feature" if other_cls == "Unspecific/Product/Service" and side == "target" else "Unspecific/Product/Service"
    if rel_type == "Hinders":
        return "Problem" if side == "source" else "Goal"
    if rel_type in ("refined by", "refined by (AND)", "refined by (OR)"):
        return "Goal"
    if rel_type == "supports":
        if other_cls == "Process":
            return "Goal" if side == "source" else "IS Technical Component"
        return "Goal"
    if rel_type in ("included in", "is similar to", "part of"):
        return other_cls
    return None


def _infer_adl_class(rel_type, side, other_cls, name):
    low = _norm_key(name)
    mapped = _class_from_name_keywords(low, _ADL_CLASS_ALIASES)
    if mapped:
        return mapped
    if other_cls:
        inferred = _adl_pair_semantics(rel_type, side, other_cls)
        if inferred:
            return inferred
    hint = _ADL_RELATION_ENDPOINT_HINTS.get((rel_type, side))
    if hint:
        return hint
    return "Unspecific/Product/Service"


def _infer_archimate_type(rel_type, side, other_type, name):
    low = _norm_key(name)
    mapped = _class_from_name_keywords(low, _ARCHIMATE_ELEMENT_ALIASES)
    if mapped:
        return mapped
    if other_type:
        return other_type
    return "BusinessObject"


def _repair_adl(data):
    notes = []
    if not isinstance(data, dict):
        return data, notes
    entities = data.get("entities")
    relations = data.get("relations")
    if not isinstance(entities, list) or not isinstance(relations, list):
        return data, notes

    by_key = {}
    for ent in entities:
        if not isinstance(ent, dict):
            continue
        cls = _normalize_adl_class(ent.get("class", ""))
        if cls is None:
            continue
        ent["class"] = cls
        ent["name"] = str(ent.get("name", "")).strip()
        ent["description"] = str(ent.get("description") or ent["name"])
        if not isinstance(ent.get("attributes"), dict):
            ent["attributes"] = {}
        key = _norm_key(ent["name"])
        if ent["name"] and key:
            by_key.setdefault(key, ent)

    def resolve(raw, side, other_cls, rel_type):
        key = _norm_key(raw)
        if key in by_key:
            return by_key[key], False
        match = _fuzzy_entity_match(raw, by_key)
        if match is not None:
            notes.append(
                f"relation {side} '{raw}' resolved to existing entity '{by_key[match]['name']}'"
            )
            return by_key[match], False
        cls = _infer_adl_class(rel_type, side, other_cls, raw)
        ent = {"class": cls, "name": raw, "description": raw, "attributes": {}}
        entities.append(ent)
        by_key.setdefault(_norm_key(raw), ent)
        notes.append(f"created missing {side} entity '{raw}' ({cls})")
        return ent, True

    for rel in relations:
        if not isinstance(rel, dict):
            continue
        rt = _normalize_adl_relation(rel.get("type", ""))
        if rt is None:
            continue
        rel["type"] = rt
        s = str(rel.get("source", "")).strip()
        t = str(rel.get("target", "")).strip()
        if not s or not t:
            notes.append(f"dropped relation with missing {'source' if not s else 'target'}")
            rel["_drop"] = True
            continue
        s_ent, _ = resolve(s, "source", None, rt)
        t_ent, _ = resolve(t, "target", s_ent["class"], rt)
        rel["source"] = s_ent["name"]
        rel["target"] = t_ent["name"]
        if not isinstance(rel.get("description"), str):
            rel["description"] = ""
        if rel["source"].lower() == rel["target"].lower():
            notes.append(f"dropped self-loop relation on '{rel['source']}'")
            rel["_drop"] = True

    # The 4EM Toolkit allows at most ONE relation per unordered instance pair.
    seen_pairs = {}
    for rel in relations:
        if rel.get("_drop"):
            continue
        pair = tuple(sorted((rel["source"].lower(), rel["target"].lower())))
        if pair in seen_pairs:
            first = seen_pairs[pair]
            desc = (first.get("description") or "").strip()
            extra = (rel.get("description") or "").strip()
            first["description"] = f"{desc}; {extra}".strip("; ")
            rel["_drop"] = True
            notes.append(
                f"merged duplicate relation between '{rel['source']}' and '{rel['target']}' "
                f"({rel['type']}) into a single relation"
            )
        else:
            seen_pairs[pair] = rel

    relations[:] = [rel for rel in relations if not rel.get("_drop")]
    for rel in relations:
        rel.pop("_drop", None)

    touched = set()
    for rel in relations:
        touched.add(rel["source"].lower())
        touched.add(rel["target"].lower())
    for ent in entities:
        if isinstance(ent, dict) and ent.get("name") and ent["name"].lower() not in touched:
            notes.append(f"entity '{ent['name']}' has no relationships (kept as-is)")

    return data, notes


def _repair_archimate(data):
    notes = []
    if not isinstance(data, dict):
        return data, notes
    elements = data.get("elements")
    relationships = data.get("relationships")
    if not isinstance(elements, list) or not isinstance(relationships, list):
        return data, notes

    by_key = {}
    for el in elements:
        if not isinstance(el, dict):
            continue
        t = _normalize_archimate_type(el.get("type", ""))
        if t is None:
            continue
        el["type"] = t
        el["name"] = str(el.get("name", "")).strip()
        layer = _normalize_layer(el.get("layer", ""))
        el["layer"] = layer if layer else _default_layer(t)
        key = _norm_key(el["name"])
        if el["name"] and key:
            by_key.setdefault(key, el)

    def resolve(raw, side, other_type, rel_type):
        key = _norm_key(raw)
        if key in by_key:
            return by_key[key], False
        match = _fuzzy_entity_match(raw, by_key)
        if match is not None:
            notes.append(
                f"relationship {side} '{raw}' resolved to existing element '{by_key[match]['name']}'"
            )
            return by_key[match], False
        t = _infer_archimate_type(rel_type, side, other_type, raw)
        el = {"type": t, "name": raw, "layer": _default_layer(t)}
        elements.append(el)
        by_key.setdefault(_norm_key(raw), el)
        notes.append(f"created missing {side} element '{raw}' ({t})")
        return el, True

    for rel in relationships:
        if not isinstance(rel, dict):
            continue
        rt = _normalize_archimate_rel(rel.get("type", ""))
        if rt is None:
            continue
        rel["type"] = rt
        s = str(rel.get("source", "")).strip()
        t = str(rel.get("target", "")).strip()
        if not s or not t:
            notes.append(f"dropped relationship with missing {'source' if not s else 'target'}")
            rel["_drop"] = True
            continue
        s_el, _ = resolve(s, "source", None, rt)
        t_el, _ = resolve(t, "target", s_el["type"], rt)
        rel["source"] = s_el["name"]
        rel["target"] = t_el["name"]
        if rel["source"].lower() == rel["target"].lower():
            notes.append(f"dropped self-loop relationship on '{rel['source']}'")
            rel["_drop"] = True

    relationships[:] = [rel for rel in relationships if not rel.get("_drop")]
    for rel in relationships:
        rel.pop("_drop", None)

    touched = set()
    for rel in relationships:
        touched.add(rel["source"].lower())
        touched.add(rel["target"].lower())
    for el in elements:
        if isinstance(el, dict) and el.get("name") and el["name"].lower() not in touched:
            notes.append(f"element '{el['name']}' has no relationships (kept as-is)")

    return data, notes


def _xml_escape(v):
    s = str(v)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _serialize_archimate(chain_name, model):
    model_name = model.get("model_name") or chain_name
    elements = model["elements"]
    relationships = model["relationships"]

    model_id = "id-" + uuid4().hex
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append(
        f'<archimate:model xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        f'xmlns:archimate="http://www.archimatetool.com/archimate" '
        f'name="{_xml_escape(model_name)}" id="{model_id}" version="5.0.0">'
    )

    for el in elements:
        el["_id"] = "id-" + uuid4().hex
    name_to_id = {el["name"].lower(): el["_id"] for el in elements}
    for rel in relationships:
        rel["_id"] = "id-" + uuid4().hex
        rel["_source_id"] = name_to_id.get(rel["source"].lower())
        rel["_target_id"] = name_to_id.get(rel["target"].lower())

    folders = {
        "strategy": ("Strategy", []),
        "business": ("Business", []),
        "application": ("Application", []),
        "technology": ("Technology & Physical", []),
        "motivation": ("Motivation", []),
        "implementation_migration": ("Implementation & Migration", []),
        "other": ("Other", []),
    }
    layer_to_folder = {
        "Strategy": "strategy",
        "Business": "business",
        "Application": "application",
        "Technology": "technology",
        "Motivation": "motivation",
        "Implementation & Migration": "implementation_migration",
        "Other": "other",
    }
    for el in elements:
        folders[layer_to_folder.get(el["layer"], "other")][1].append(el)

    for fkey, (fname, fels) in folders.items():
        fid = "id-" + uuid4().hex
        if not fels:
            lines.append(f'  <folder name="{_xml_escape(fname)}" id="{fid}" type="{fkey}"/>')
        else:
            lines.append(f'  <folder name="{_xml_escape(fname)}" id="{fid}" type="{fkey}">')
            for el in fels:
                lines.append(
                    f'    <element xsi:type="archimate:{el["type"]}" name="{_xml_escape(el["name"])}" id="{el["_id"]}"/>'
                )
            lines.append("  </folder>")

    rel_fid = "id-" + uuid4().hex
    lines.append(f'  <folder name="Relations" id="{rel_fid}" type="relations">')
    for rel in relationships:
        lines.append(
            f'    <element xsi:type="archimate:{rel["type"]}" id="{rel["_id"]}" '
            f'source="{rel["_source_id"]}" target="{rel["_target_id"]}"/>'
        )
    lines.append("  </folder>")

    # Single comprehensive view: all elements from ALL layers, with ALL
    # relationships (including cross-layer) drawn as connections.
    views_fid = "id-" + uuid4().hex
    lines.append(f'  <folder name="Views" id="{views_fid}" type="diagrams">')

    # Comprehensive "Enterprise Blueprint" view: all elements from ALL layers, with ALL
    # relationships (including cross-layer) drawn as connections.
    all_dob_ids = {el["_id"]: "id-" + uuid4().hex for el in elements}
    for rel in relationships:
        rel["_bp_conn_id"] = "id-" + uuid4().hex
    bp_targets = {}
    for rel in relationships:
        bp_targets.setdefault(rel["_target_id"], []).append(rel["_bp_conn_id"])
    by_layer = {}
    for el in elements:
        by_layer.setdefault(el["layer"], []).append(el)
    layer_index = {layer: i for i, layer in enumerate(_LAYER_ORDER)}

    blueprint_id = "id-" + uuid4().hex
    lines.append(
        f'    <element xsi:type="archimate:ArchimateDiagramModel" '
        f'name="Enterprise Blueprint" id="{blueprint_id}" viewpoint="layered">'
    )
    for layer in _LAYER_ORDER:
        for i, el in enumerate(by_layer.get(layer, [])):
            did = all_dob_ids[el["_id"]]
            x = 24 + i * 140
            y = 24 + layer_index[layer] * 100
            tgt = bp_targets.get(el["_id"], [])
            tgt_attr = f' targetConnections="{" ".join(tgt)}"' if tgt else ""
            lines.append(
                f'      <child xsi:type="archimate:DiagramObject" id="{did}" '
                f'fontColor="#000000" lineColor="#000000" fillColor="#ffb973" '
                f'archimateElement="{el["_id"]}" textPosition="1"{tgt_attr}>'
            )
            lines.append(f'        <bounds x="{x}" y="{y}" width="120" height="55"/>')
            for rel in relationships:
                if rel["_source_id"] == el["_id"]:
                    lines.append(
                        f'        <sourceConnection xsi:type="archimate:Connection" '
                        f'id="{rel["_bp_conn_id"]}" source="{did}" '
                        f'target="{all_dob_ids[rel["_target_id"]]}" archimateRelationship="{rel["_id"]}"/>'
                    )
            lines.append("      </child>")
    lines.append("    </element>")
    lines.append("  </folder>")

    lines.append(
        f"  <purpose>Exported from the Enterprise Modelling Tool. Generated model: "
        f"{_xml_escape(model_name)}</purpose>"
    )
    lines.append("</archimate:model>")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# LLM distillation + shared helpers
# ---------------------------------------------------------------------------


def _extract_json(text):
    if not text:
        return None
    text = re.sub(r"^```(?:json)?\s*", "", str(text).strip())
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except Exception:
                    return None
    return None


def _llm_structured_json(system, user):
    load_dotenv(override=True)
    key = os.getenv("OPENAI_API_KEY")
    if not key or "your_key_here" in key:
        raise ExportException(
            503,
            "Export requires an LLM to structure the model, but no valid OPENAI_API_KEY "
            "was found in the environment. Please configure OPENAI_API_KEY and retry.",
        )
    client = openai.OpenAI(api_key=key.strip())
    last_error = ""
    for model_name in _available_models:
        try:
            logger.debug("Attempting distillation model: %s", model_name)
            start = time.perf_counter()
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.1,
                top_p=0.95,
                max_tokens=_max_tokens.get(model_name, 8192),
            )
            latency_seconds = round(time.perf_counter() - start, 3)
            if not response.choices or not response.choices[0].message.content:
                logger.warning("Model %s returned empty response content", model_name)
                continue
            data = _extract_json(response.choices[0].message.content)
            if data is None:
                raise ValueError("response did not contain valid JSON")

            usage = getattr(response, "usage", None)
            llm_metrics = {
                "latency_seconds": latency_seconds,
                "prompt_tokens": (
                    usage.prompt_tokens
                    if usage is not None and usage.prompt_tokens is not None
                    else -1
                ),
                "completion_tokens": (
                    usage.completion_tokens
                    if usage is not None and usage.completion_tokens is not None
                    else -1
                ),
                "model": model_name,
            }
            logger.info(
                "Model %s distillation succeeded in %.2fs (%s in / %s out tokens)",
                model_name,
                latency_seconds,
                llm_metrics["prompt_tokens"],
                llm_metrics["completion_tokens"],
            )
            return data, llm_metrics
        except Exception as e:
            last_error = str(e)
            logger.warning("Distillation model %s failed: %s", model_name, last_error)
            continue
    raise ExportException(
        502,
        "All models failed to produce a structured model. Last error: " + str(last_error),
    )


def _distill_model(system, user, validate_fn, repair_fn):
    notes = []
    last_problems = []
    llm_metrics = {
        "latency_seconds": 0.0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "model": None,
    }
    for attempt in range(2):
        prompt = user
        if attempt > 0 and last_problems:
            prompt = (
                user
                + "\n\nYour previous output failed validation. Fix these issues:\n- "
                + "\n- ".join(last_problems)
                + "\n\nOutput a corrected JSON object following the exact schema. Return ONLY valid JSON."
            )
        data, call_metrics = _llm_structured_json(system, prompt)
        llm_metrics["latency_seconds"] += call_metrics.get("latency_seconds") or 0.0
        llm_metrics["prompt_tokens"] += max(call_metrics.get("prompt_tokens") or 0, 0)
        llm_metrics["completion_tokens"] += max(
            call_metrics.get("completion_tokens") or 0, 0
        )
        llm_metrics["model"] = call_metrics.get("model")
        problems = validate_fn(data)
        if not problems:
            return data, notes, llm_metrics
        last_problems = problems
        logger.debug("Validation attempt %d failed: %s", attempt + 1, problems)
        data, repair_notes = repair_fn(data)
        for note in repair_notes:
            logger.debug("Graph repair applied: %s", note)
        notes.extend(repair_notes)
        problems = validate_fn(data)
        if not problems:
            logger.info("Model validated after auto-repair (%d modifications)", len(repair_notes))
            return data, notes, llm_metrics
        last_problems = problems
    raise ExportException(
        422,
        "Generated model failed validation after retries:\n"
        + "\n".join(f"- {p}" for p in last_problems),
    )


def _steps_to_context(steps):
    parts = []
    for s in steps:
        low = (s.prompt_name or "").lower()
        if "critic" in low or s.type == "CRITIC":
            continue
        parts.append(f"### Step {s.step}: {s.prompt_name}\n{s.result}")
    return "\n\n".join(parts)


def _slugify(name):
    s = re.sub(r"[^A-Za-z0-9]+", "-", str(name)).strip("-").lower()
    return s or "model"


def _read_prompt(filename):
    path = os.path.join(_PROMPTS_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return f.read()


def _record_telemetry(
    session,
    fmt,
    chain_name,
    status,
    error=None,
    entity_count=None,
    relation_count=None,
    duration_ms=None,
    history_id=None,
    notes=None,
    prompt_tokens=None,
    completion_tokens=None,
):
    log = ExportLog(
        user_id=1,
        format=fmt,
        chain_name=chain_name,
        history_id=history_id,
        status=status,
        error=error,
        entity_count=entity_count,
        relation_count=relation_count,
        duration_ms=duration_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    session.add(log)

    base = "Exported 4EM General Model" if fmt == "adl" else "Exported ArchiMate Model"
    action = f"{base} (Failed)" if status == "failed" else base
    audit = AuditLog(
        user_id=1,
        action=action,
        target_type="export",
        target_id=history_id or 0,
        details=json.dumps(
            {
                "format": fmt,
                "status": status,
                "error": error,
                "entity_count": entity_count,
                "relation_count": relation_count,
                "duration_ms": duration_ms,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "notes": notes or [],
            }
        ),
    )
    session.add(audit)
    session.commit()


def _build_user_prompt(request: ExportRequest, steps_text: str) -> str:
    parts = [f"Chain: {request.chain_name}"]
    if request.inputs:
        parts.append("Enterprise scenario inputs:\n" + json.dumps(request.inputs, indent=2))
    parts.append("Generated layers:\n" + steps_text)
    return "\n\n".join(parts)


# Exporter endpoints


@router.post("/adl")
def export_adl(request: ExportRequest, session: Session = Depends(get_session)):
    start = time.time()
    fmt = "adl"
    llm_metrics = {"latency_seconds": 0.0, "prompt_tokens": None, "completion_tokens": None}
    try:
        steps_text = _steps_to_context(request.steps)
        if not steps_text.strip():
            raise ExportException(422, "No usable layer content found in the provided steps.")
        model, notes, llm_metrics = _distill_model(
            _read_prompt("adl_general_model.txt"),
            _build_user_prompt(request, steps_text),
            _normalize_and_validate_adl,
            _repair_adl,
        )
        adl_text = _serialize_adl(request.chain_name, model)
        invalid_lines = _validate_serialized_adl(adl_text)
        if invalid_lines:
            raise ExportException(
                422, "Internal ADL validation failed: " + " | ".join(invalid_lines)
            )
        entity_count = len(model["entities"])
        relation_count = len(model["relations"])
        _record_telemetry(
            session,
            fmt,
            request.chain_name,
            "success",
            entity_count=entity_count,
            relation_count=relation_count,
            duration_ms=int((time.time() - start) * 1000),
            history_id=request.history_id,
            notes=notes,
            prompt_tokens=llm_metrics["prompt_tokens"],
            completion_tokens=llm_metrics["completion_tokens"],
        )
        slug = _slugify(request.chain_name)
        return Response(
            content=adl_text.encode("utf-8"),
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="{slug}-4EM-General-Model.adl"'
            },
        )
    except ExportException as e:
        _record_telemetry(
            session,
            fmt,
            request.chain_name,
            "failed",
            error=str(e.message),
            duration_ms=int((time.time() - start) * 1000),
            history_id=request.history_id,
        )
        raise HTTPException(status_code=e.status_code, detail=str(e.message))
    except Exception as e:
        _record_telemetry(
            session,
            fmt,
            request.chain_name,
            "failed",
            error=repr(e),
            duration_ms=int((time.time() - start) * 1000),
            history_id=request.history_id,
        )
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@router.post("/archimate")
def export_archimate(request: ExportRequest, session: Session = Depends(get_session)):
    start = time.time()
    fmt = "archimate"
    llm_metrics = {"latency_seconds": 0.0, "prompt_tokens": None, "completion_tokens": None}
    try:
        steps_text = _steps_to_context(request.steps)
        if not steps_text.strip():
            raise ExportException(422, "No usable layer content found in the provided steps.")
        model, notes, llm_metrics = _distill_model(
            _read_prompt("archimate_distill.txt"),
            _build_user_prompt(request, steps_text),
            _normalize_and_validate_archimate,
            _repair_archimate,
        )
        xml_text = _serialize_archimate(request.chain_name, model)
        entity_count = len(model["elements"])
        relation_count = len(model["relationships"])
        _record_telemetry(
            session,
            fmt,
            request.chain_name,
            "success",
            entity_count=entity_count,
            relation_count=relation_count,
            duration_ms=int((time.time() - start) * 1000),
            history_id=request.history_id,
            notes=notes,
            prompt_tokens=llm_metrics["prompt_tokens"],
            completion_tokens=llm_metrics["completion_tokens"],
        )
        slug = _slugify(request.chain_name)
        return Response(
            content=xml_text.encode("utf-8"),
            media_type="application/xml",
            headers={
                "Content-Disposition": f'attachment; filename="{slug}.archimate"'
            },
        )
    except ExportException as e:
        _record_telemetry(
            session,
            fmt,
            request.chain_name,
            "failed",
            error=str(e.message),
            duration_ms=int((time.time() - start) * 1000),
            history_id=request.history_id,
        )
        raise HTTPException(status_code=e.status_code, detail=str(e.message))
    except Exception as e:
        _record_telemetry(
            session,
            fmt,
            request.chain_name,
            "failed",
            error=repr(e),
            duration_ms=int((time.time() - start) * 1000),
            history_id=request.history_id,
        )
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@router.get("/logs", response_model=List[ExportLogRead])
def get_export_logs(limit: int = 50, session: Session = Depends(get_session)):
    statement = select(ExportLog).order_by(ExportLog.created_at.desc()).limit(limit)
    return session.exec(statement).all()
