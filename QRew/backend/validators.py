"""Validation pipeline for canonical model."""

from dataclasses import dataclass
from typing import List, Dict, Any
import jsonschema
import json

from config import CANONICAL_MODEL_SCHEMA


@dataclass
class ValidationResult:
    passed: bool
    errors: List[str]      # Structural - blocks export
    warnings: List[str]    # Semantic - export with warning


def validate_schema(model: Dict[str, Any]) -> List[str]:
    """Validate model against JSON Schema."""
    errors = []
    try:
        validator = jsonschema.Draft202012Validator(CANONICAL_MODEL_SCHEMA)
        for error in validator.iter_errors(model):
            path = " -> ".join(str(p) for p in error.absolute_path)
            errors.append(f"{path}: {error.message}")
    except Exception as e:
        errors.append(f"Schema validation error: {str(e)}")
    return errors


def validate_refs(model: Dict[str, Any]) -> List[str]:
    """Validate all relationship references point to existing elements."""
    errors = []
    element_ids = {e["id"] for e in model.get("elements", [])}

    for rel in model.get("relationships", []):
        if rel["sourceId"] not in element_ids:
            errors.append(f"Relationship {rel['id']}: sourceId {rel['sourceId']} not found")
        if rel["targetId"] not in element_ids:
            errors.append(f"Relationship {rel['id']}: targetId {rel['targetId']} not found")
    return errors


def validate_4em_semantics(model: Dict[str, Any]) -> List[str]:
    """4EM semantic validation (warnings only)."""
    warnings = []
    elements = model.get("elements", [])
    relationships = model.get("relationships", [])

    # Build lookup
    elements_by_id = {e["id"]: e for e in elements}
    processes = [e for e in elements if e.get("canonicalType") == "process"]
    goals = [e for e in elements if e.get("canonicalType") == "goal"]
    actors = [e for e in elements if e.get("canonicalType") in ("actor", "role", "org_unit")]

    # Every Process must have responsible_for from Actor/Role/OrgUnit
    for p in processes:
        has_owner = any(
            r.get("canonicalType") == "responsible_for" and r["targetId"] == p["id"]
            for r in relationships
        )
        if not has_owner:
            warnings.append(f"Process '{p.get('name', p['id'])}' lacks responsible Actor/Role")

    # Every Process must have input/output InformationSet
    for p in processes:
        has_io = any(
            r.get("canonicalType") in ("input", "output") and (r["sourceId"] == p["id"] or r["targetId"] == p["id"])
            for r in relationships
        )
        if not has_io:
            warnings.append(f"Process '{p.get('name', p['id'])}' has no Input/Output InformationSet")

    # Goals must connect to Processes via responsible_for chain
    for g in goals:
        connected = any(
            r.get("canonicalType") == "responsible_for" and r["sourceId"] == g["id"]
            for r in relationships
        )
        if not connected:
            warnings.append(f"Goal '{g.get('name', g['id'])}' not connected to any Process")

    # Submodel coverage
    submodels = {e.get("submodel") for e in elements if e.get("submodel")}
    required = {"goals", "processes", "actors", "technical"}
    for missing in required - submodels:
        warnings.append(f"Missing 4EM submodel: {missing}")

    return warnings


def validate_bpmn_semantics(model: Dict[str, Any]) -> List[str]:
    """BPMN semantic validation (warnings only)."""
    warnings = []
    elements = model.get("elements", [])

    has_start = any(e.get("frameworkType") == "StartEvent" for e in elements)
    has_end = any(e.get("frameworkType") == "EndEvent" for e in elements)

    if not has_start:
        warnings.append("No StartEvent found")
    if not has_end:
        warnings.append("No EndEvent found")

    return warnings


def validate_canonical(model: Dict[str, Any]) -> ValidationResult:
    """Full validation: schema + refs + semantic."""
    errors = []
    warnings = []

    if not model.get("elements"):
        errors.append("Model must contain at least one element")

    errors.extend(validate_schema(model))
    errors.extend(validate_refs(model))

    framework = model.get("framework", "")
    if framework == "4EM":
        warnings.extend(validate_4em_semantics(model))
    elif framework == "BPMN":
        warnings.extend(validate_bpmn_semantics(model))

    return ValidationResult(passed=len(errors) == 0, errors=errors, warnings=warnings)


def validate_adl_output(content: str) -> ValidationResult:
    """Validate generated ADL content."""
    errors = []
    warnings = []

    instance_count = content.count("INSTANCE")
    relation_count = content.count("RELATION")
    end_count = content.count("//END")

    checks = [
        ("VERSION <5.1>", "VERSION <5.1>" in content),
        ("MODEL declaration", "BUSINESS PROCESS MODEL" in content),
        ("INSTANCE/END balance", instance_count <= end_count),
    ]

    # Only check RELATION/END balance if there are RELATION blocks
    if relation_count > 0:
        checks.append(("RELATION/END balance", relation_count <= end_count))

    checks.append(("All elements have Position", "Position" in content))

    for name, check in checks:
        if not check:
            errors.append(f"ADL validation failed: {name}")

    return ValidationResult(passed=len(errors) == 0, errors=errors, warnings=warnings)


def validate_archimate_output(xml_bytes: bytes) -> ValidationResult:
    """Validate generated ArchiMate XML."""
    errors = []
    warnings = []

    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_bytes)

        # Check root element
        if root.tag != '{http://www.archimatetool.com/archimate}model':
            errors.append("Invalid root element")

        # Check namespaces - parse the raw XML string for namespace declarations
        xml_str = xml_bytes.decode('utf-8')
        if 'xmlns:archimate="http://www.archimatetool.com/archimate"' not in xml_str:
            errors.append("Missing archimate namespace")
        if 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' not in xml_str:
            errors.append("Missing xsi namespace")

        # Check unique IDs
        all_ids = []
        for elem in root.iter():
            if 'id' in elem.attrib:
                all_ids.append(elem.attrib['id'])
        if len(all_ids) != len(set(all_ids)):
            errors.append("Duplicate IDs found")

    except ET.ParseError as e:
        errors.append(f"XML parse error: {str(e)}")
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")

    return ValidationResult(passed=len(errors) == 0, errors=errors, warnings=warnings)