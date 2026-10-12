"""4EM ADL serializer."""

from typing import Dict, Any, List
from exporters.base import BaseExporter
from layout import generate_4em_layout, format_4em_position
from ids import element_id, relationship_id


class ADLExporter(BaseExporter):
    """Serialize canonical model to 4EM ADL format (v5.1)."""

    # Section order from reference model
    SECTION_ORDER = [
        "Organizational Unit",
        "Role",
        "Actor",
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

    # Map canonical types to their proper 4EM framework types (not all "Actor")
    CANONICAL_TO_ADL_TYPE = {
        "org_unit": "Organizational Unit",
        "role": "Role",
        "actor": "Actor",
        "goal": "Goal",
        "problem": "Problem",
        "process": "Process",
        "info_set": "Information Set",
        "product": "Unspecific/Product/Service",
        "component": "Component",
        "feature": "Feature",
        "tech_component": "IS Technical Component",
        "concept": "Concept",
        "attribute": "Attribute",
        # BPMN types that might appear
        "biz_actor": "Actor",
        "biz_role": "Role",
        "biz_process": "Process",
        "biz_object": "Information Set",
        "biz_event": "Problem",
        "biz_service": "Feature",
        "biz_function": "Process",
        "app_component": "IS Technical Component",
        "app_service": "Feature",
        "app_function": "Process",
        "data_object": "Information Set",
    }

    # Canonical type to ADL framework type (4EM types)
    TYPE_MAP = {
        "org_unit": "Organizational Unit",
        "role": "Role",
        "goal": "Goal",
        "problem": "Problem",
        "process": "Process",
        "info_set": "Information Set",
        "product": "Unspecific/Product/Service",
        "component": "Component",
        "feature": "Feature",
        "tech_component": "IS Technical Component",
        "concept": "Concept",
        "attribute": "Attribute",
        # Actor types
        "actor": "Actor",
        "org_unit": "Organizational Unit",
        "role": "Role",
        "biz_actor": "Actor",
        "biz_role": "Role",
    }

    # Canonical relationship to 4EM ADL relationship type
    RELATION_TYPE_MAP = {
        "part_of": "part of",
        "works_in": "works in",
        "refines": "refined by (AND)",
        "hinders": "Hinders",
        "responsible_for": "is responsible for",
        "decomposes_to": "decomposed into",
        "input": "Input",
        "output": "Output",
        "composes": "consists of",
        "offers": "offers",
        "supports": "supports",
        "includes": "included in",
    }

    # Required attributes per ADL type (from reference model)
    REQUIRED_ATTRIBUTES = {
        "Goal": [
            "Criticality", "Priority", "Intermodel-Relations", "Decomposition",
            "Defined by", "Is the exact same as", "hidden_attribute"
        ],
        "Process": [
            "Decomposed Process", "Intermodel-Relations", "Decomposition",
            "Execution Time", "Complexity", "Type", "Is the exact same as", "hidden_attribute"
        ],
        "Problem": [
            "Intermodel-Relations", "Decomposition", "Attributes", "Defined by",
            "Priority", "Criticality", "type", "Is the exact same as", "hidden_attribute"
        ],
        "Actor": [
            "Decomposition", "Attributes"
        ],
        "Organizational Unit": [
            "Decomposition", "Attributes"
        ],
        "Role": [
            "Decomposition", "Attributes"
        ],
        "Information Set": [
            "Intermodel-Relations", "Decomposition"
        ],
        "Unspecific/Product/Service": [
            "Specification", "Attribute", "Intermodel-Relations", "Decomposition"
        ],
        "Component": [
            "Decomposition", "Quantity", "Location", "Intermodel-Relations"
        ],
        "Feature": [
            "Attribute", "Intermodel-Relations", "Decomposition"
        ],
        "IS Technical Component": [
            "Intermodel-Relations", "Decomposition", "Location", "Quantity", "Attributes"
        ],
        "Concept": [
            "Intermodel-Relations", "Decomposition"
        ],
        "Attribute": [
            "Intermodel-Relations", "Decomposition"
        ],
    }

    # Default values for required attributes
    DEFAULT_ATTRIBUTES = {
        "Criticality": "Low",
        "Priority": "Low",
        "Intermodel-Relations": "",
        "Decomposition": "",
        "Defined by": "",
        "Is the exact same as": "",
        "hidden_attribute": "",
        "Decomposed Process": "",
        "Execution Time": "0",
        "Complexity": "0",
        "Type": "",
        "Attributes": "",
        "Specification": "Product",
        "Attribute": "",
        "Quantity": "0",
        "Location": "",
    }

    def export(self, model: Dict[str, Any]) -> bytes:
        if model.get("framework") != "4EM":
            raise ValueError("ADLExporter only supports 4EM framework")

        elements = model.get("elements", [])
        relationships = model.get("relationships", [])
        metadata = model.get("metadata", {})
        model_id = metadata.get("modelId", "")
        model_name = metadata.get("name", "4EM Model")

        # Generate deterministic positions using 4EM layout
        positions = generate_4em_layout(elements)

        # Group elements by ADL section
        sections: Dict[str, List[Dict]] = {}
        for elem in elements:
            canonical_type = elem.get("canonicalType", "")
            adl_type = self.CANONICAL_TO_ADL_TYPE.get(canonical_type, canonical_type)
            if adl_type not in sections:
                sections[adl_type] = []
            sections[adl_type].append(elem)

        # Build ADL content
        lines = []

        # Header (from reference)
        lines.append("//////////////////////////////////////////////////////////////")
        lines.append("//")
        lines.append("VERSION <5.1>")
        lines.append("")
        lines.append(f'BUSINESS PROCESS MODEL <{model_name}> : <4EM-Rostock Library_87_22_04_01>')
        lines.append("VERSION <>")
        lines.append("TYPE <4EM General Model>")
        lines.append("//")

        # INSTANCE blocks per section (in SECTION_ORDER)
        for section_name in self.SECTION_ORDER:
            if section_name not in sections:
                continue

            # Section comment pluralization (match reference model)
            section_comment_map = {
                "Organizational Unit": "ORGANIZATIONAL UNITS",
                "Role": "ROLES",
                "Actor": "ACTORS",
                "Goal": "GOALS",
                "Problem": "PROBLEMS",
                "Process": "PROCESSES",
                "Information Set": "INFORMATION SETS",
                "Unspecific/Product/Service": "UNSPECIFIC/PRODUCT/SERVICE",
                "Component": "COMPONENTS",
                "Feature": "FEATURES",
                "IS Technical Component": "IS TECHNICAL COMPONENTS",
                "Concept": "CONCEPTS",
                "Attribute": "ATTRIBUTES",
            }
            comment_name = section_comment_map.get(section_name, section_name.upper() + "S")

            lines.append(f"//")
            lines.append(f"// ──────────────────────────────────────────────────────────────")
            lines.append(f"// {comment_name}")
            lines.append(f"// ──────────────────────────────────────────────────────────────")

            section_elements = sections[section_name]
            index = 1
            for elem in section_elements:
                pos = positions.get(elem["id"])
                if pos:
                    pos_str = format_4em_position(pos, index)
                else:
                    pos_str = f"NODE x:1cm y:1cm w:4cm h:1.5cm index:{index}"

                # Use section_name directly (already the correct ADL type)
                lines.append(f'INSTANCE <{elem["name"]}> : <{section_name}>')
                lines.append("")
                lines.append(f'\tATTRIBUTE <Position>')
                lines.append(f'\tVALUE "{pos_str}"')
                lines.append("")
                lines.append(f'\tATTRIBUTE <External tool coupling>')
                lines.append(f'\tVALUE ""')
                lines.append("")
                lines.append(f'\tATTRIBUTE <Description>')
                lines.append(f'\tVALUE "{elem.get("description", "")}"')
                lines.append("")

                # Required attributes for this type
                required_attrs = self.REQUIRED_ATTRIBUTES.get(section_name, [])
                for attr_name in required_attrs:
                    lines.append(f'\tATTRIBUTE <{attr_name}>')
                    value = elem.get("attributes", {}).get(attr_name, self.DEFAULT_ATTRIBUTES.get(attr_name, ""))
                    lines.append(f'\tVALUE "{value}"')
                    lines.append("")

                lines.append("//END")
                lines.append("")
                index += 1

        # RELATION blocks
        lines.append("//")
        lines.append("// ──────────────────────────────────────────────────────────────")
        lines.append("// RELATIONS")
        lines.append("// ──────────────────────────────────────────────────────────────")

        # Validate and fix relationship directions for 4EM semantics
        validated_relationships = self._validate_and_fix_relationships(relationships, elements)

        for rel in validated_relationships:
            canonical_type = rel.get("canonicalType", "")
            framework_type = self.RELATION_TYPE_MAP.get(canonical_type, canonical_type)

            source_elem = next((e for e in elements if e["id"] == rel["sourceId"]), None)
            target_elem = next((e for e in elements if e["id"] == rel["targetId"]), None)

            if not source_elem or not target_elem:
                continue

            source_adl_type = self.CANONICAL_TO_ADL_TYPE.get(source_elem.get("canonicalType", ""), source_elem.get("canonicalType", ""))
            target_adl_type = self.CANONICAL_TO_ADL_TYPE.get(target_elem.get("canonicalType", ""), target_elem.get("canonicalType", ""))

            lines.append(f'RELATION <4EM_Relation>')
            lines.append(f'\tFROM <{source_elem["name"]}> : <{source_adl_type}>')
            lines.append(f'\tTO <{target_elem["name"]}> : <{target_adl_type}>')
            lines.append("")
            lines.append(f'\tATTRIBUTE <Positions>')
            lines.append(f'\tVALUE ""')
            lines.append("")
            lines.append(f'\tATTRIBUTE <Type>')
            lines.append(f'\tVALUE "{framework_type}"')
            lines.append("")
            lines.append(f'\tATTRIBUTE <Description>')
            lines.append(f'\tVALUE "{rel.get("description", "")}"')
            lines.append("")
            lines.append("//END")
            lines.append("")

        return "\n".join(lines).encode("utf-8")

    def _validate_and_fix_relationships(self, relationships: List[Dict], elements: List[Dict]) -> List[Dict]:
        """Validate and fix relationship directions for 4EM semantics."""
        element_map = {e["id"]: e for e in elements}
        valid_rels = []

        for rel in relationships:
            source_id = rel.get("sourceId")
            target_id = rel.get("targetId")
            canonical_type = rel.get("canonicalType", "")

            source = element_map.get(source_id)
            target = element_map.get(target_id)

            if not source or not target:
                continue

            source_type = source.get("canonicalType", "")
            target_type = target.get("canonicalType", "")

            # Validate and potentially fix direction based on 4EM rules
            corrected_rel = self._correct_relationship_direction(source, target, canonical_type, rel)
            if corrected_rel:
                valid_rels.append(corrected_rel)

        return valid_rels

    def _correct_relationship_direction(self, source: Dict, target: Dict, canonical_type: str, rel: Dict) -> Dict:
        """Correct relationship direction based on 4EM semantics."""
        source_type = source.get("canonicalType", "")
        target_type = target.get("canonicalType", "")

        # 4EM relationship direction rules:
        # - refines: Goal -> Process, Goal -> Goal
        # - responsible_for: Actor/OrgUnit/Role -> Process
        # - input: InformationSet -> Process
        # - output: Process -> InformationSet
        # - works_in: Actor/Role -> OrganizationalUnit
        # - supports: TechComponent -> Process
        # - part_of: OrgUnit -> OrgUnit, Component -> Product/Component
        # - decomposes_to: Process -> Process
        # - hinders: Problem -> Goal
        # - composes: Product -> Component, Component -> Component
        # - offers: Product -> Feature
        # - includes: Concept -> InformationSet

        # Define expected directions (source_type, target_type) for each relationship type
        expected_directions = {
            "refines": [("goal", "process"), ("goal", "goal")],
            "responsible_for": [("actor", "process"), ("org_unit", "process"), ("role", "process")],
            "input": [("info_set", "process")],
            "output": [("process", "info_set")],
            "works_in": [("actor", "org_unit"), ("role", "org_unit")],
            "supports": [("tech_component", "process")],
            "part_of": [("org_unit", "org_unit"), ("component", "product"), ("component", "component")],
            "decomposes_to": [("process", "process")],
            "hinders": [("problem", "goal")],
            "composes": [("product", "component"), ("component", "component")],
            "offers": [("product", "feature")],
            "includes": [("concept", "info_set")],
        }

        # Check if current direction is valid for this canonical_type
        allowed = expected_directions.get(canonical_type, [])
        if (source_type, target_type) in allowed:
            return rel

        # Try reverse direction for the SAME relationship type
        reverse_allowed = [(t, s) for s, t in allowed]
        if (source_type, target_type) in reverse_allowed:
            corrected = rel.copy()
            corrected["sourceId"] = rel["targetId"]
            corrected["targetId"] = rel["sourceId"]
            corrected["description"] = f"Corrected direction: {source.get('name')} {canonical_type} {target.get('name')}"
            return corrected

        # If direction doesn't match for this canonical_type, find a canonical_type
        # that IS valid for this (source_type, target_type) pair
        for rel_type, directions in expected_directions.items():
            if (source_type, target_type) in directions:
                corrected = rel.copy()
                corrected["canonicalType"] = rel_type
                corrected["description"] = f"Inferred relationship type: {rel_type} ({source.get('name')} -> {target.get('name')})"
                return corrected
            # Also check reverse
            reverse_dirs = [(t, s) for s, t in directions]
            if (source_type, target_type) in reverse_dirs:
                corrected = rel.copy()
                corrected["canonicalType"] = rel_type
                corrected["sourceId"] = rel["targetId"]
                corrected["targetId"] = rel["sourceId"]
                corrected["description"] = f"Inferred and corrected: {rel_type} ({target.get('name')} -> {source.get('name')})"
                return corrected

        # If we still can't determine, keep original (don't filter out)
        return rel

    def _infer_relationship_type(self, source_type: str, target_type: str) -> str:
        """Infer the correct 4EM relationship type based on element types."""
        # Map of (source_type, target_type) -> relationship_type
        type_to_relation = {
            ("goal", "process"): "refines",
            ("actor", "process"): "responsible_for",
            ("org_unit", "process"): "responsible_for",
            ("role", "process"): "responsible_for",
            ("info_set", "process"): "input",
            ("process", "info_set"): "output",
            ("actor", "org_unit"): "works_in",
            ("role", "org_unit"): "works_in",
            ("tech_component", "process"): "supports",
            ("org_unit", "org_unit"): "part_of",
            ("component", "product"): "part_of",
            ("component", "component"): "part_of",
            ("goal", "goal"): "refines",
            ("problem", "goal"): "hinders",
            ("product", "component"): "composes",
            ("component", "component"): "part_of",
            ("product", "feature"): "offers",
            ("concept", "info_set"): "includes",
            ("process", "process"): "decomposes_to",
            # Additional inference rules for common LLM mistakes:
            ("process", "actor"): "responsible_for",  # Reverse of responsible_for
            ("process", "org_unit"): "responsible_for",  # Reverse of responsible_for
            ("process", "role"): "responsible_for",  # Reverse of responsible_for
            # Actor -> TechComponent often means TechComponent -> Process (supports)
            ("actor", "tech_component"): "supports",
            # TechComponent -> InfoSet often means InfoSet -> Process (input) or Process -> InfoSet (output)
            ("tech_component", "info_set"): "input",
            # Actor -> Actor: no valid 4EM relationship
            # Goal -> Actor: no valid 4EM relationship
            # Process -> TechComponent: could be supports (if Process is source, TechComponent supports it)
            ("process", "tech_component"): "supports",
        }
        return type_to_relation.get((source_type, target_type), "")

    def _canonical_to_framework_type(self, canonical_type: str) -> str:
        """Convert canonical relationship type to framework type for ADL output."""
        reverse_map = {
            "refines": "refined by (AND)",
            "responsible_for": "is responsible for",
            "input": "Input",
            "output": "Output",
            "works_in": "works in",
            "supports": "supports",
            "part_of": "part of",
            "decomposes_to": "decomposed into",
            "refines_goal": "refined by (AND)",
            "hinders": "Hinders",
            "composes": "consists of",
            "offers": "offers",
            "includes": "included in",
        }
        return reverse_map.get(canonical_type, canonical_type)

    def _is_valid_relationship(self, source: Dict, target: Dict, canonical_type: str) -> bool:
        """Check if relationship direction is valid for 4EM."""
        source_type = source.get("canonicalType", "")
        target_type = target.get("canonicalType", "")

        expected_directions = {
            "refines": [("goal", "process")],
            "responsible_for": [("actor", "process"), ("org_unit", "process"), ("role", "process")],
            "input": [("info_set", "process")],
            "output": [("process", "info_set")],
            "works_in": [("actor", "org_unit"), ("role", "org_unit")],
            "supports": [("tech_component", "process")],
            "part_of": [("org_unit", "org_unit"), ("component", "product"), ("component", "component")],
            "decomposes_to": [("process", "process")],
            "refines_goal": [("goal", "goal")],
            "hinders": [("problem", "goal")],
            "composes": [("product", "component"), ("component", "component")],
            "offers": [("product", "feature")],
            "includes": [("concept", "info_set")],
        }

        allowed = expected_directions.get(canonical_type, [])
        return (source_type, target_type) in allowed


# Re-export the format_4em_position function to ensure it's available
def format_4em_position(pos, index: int) -> str:
    """Format Position as ADL POSITION attribute string."""
    return f"NODE x:{pos.x:.1f}cm y:{pos.y:.1f}cm w:{pos.width:.1f}cm h:{pos.height:.1f}cm index:{index}"