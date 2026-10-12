"""Pipeline orchestrator for query transformation and diagram synthesis."""

import uuid
import json
import os
import logging
from datetime import datetime, timezone
import re

logger = logging.getLogger(__name__)

from engine import QRewEngine
from config import (
    FRAMEWORK_KNOWLEDGE,
    STAGE_1_TEMPLATE,
    STAGE_2_TEMPLATE,
    MERMAID_KEYWORDS,
    CANONICAL_TYPE_MAP_4EM,
    SUBMODEL_MAP_4EM,
    CANONICAL_TYPE_MAP_BPMN,
    CANONICAL_RELATIONSHIP_MAP_4EM,
)
from ids import element_id, relationship_id, diagram_id, folder_id
from layout import generate_4em_layout, generate_archimate_layout
from validators import validate_canonical

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class QRewPipeline(QRewEngine):

    def transform_prompt(
        self, user_input: str, framework_choice: str
    ) -> tuple[str, dict]:
        if framework_choice not in FRAMEWORK_KNOWLEDGE:
            raise ValueError(f"Invalid framework choice: {framework_choice}")
        if not user_input or not user_input.strip():
            raise ValueError("user_input must be a non-empty string")

        rules = FRAMEWORK_KNOWLEDGE[framework_choice]
        prompt = STAGE_1_TEMPLATE.format(
            framework_rules=rules, user_input=user_input
        )

        text, latency, pt, ct = self._call_openai(prompt)

        metrics = {
            "stage_1_latency_seconds": latency,
            "stage_1_prompt_tokens": pt,
            "stage_1_completion_tokens": ct,
        }
        return text, metrics

    _RETRY_PROMPT = (
        "The previous response did not produce valid Mermaid syntax.\n"
        "Generate a valid Mermaid flowchart conforming to this format:\n\n"
        "graph TD\n"
        '    A[Start] --> B[Receive Application]\n'
        '    B --> C{Documents Complete?}\n'
        '    C -->|Yes| D[Process Application]\n'
        '    C -->|No| E[Request Missing Documents]\n'
        '    E --> F[Receive Documents]\n'
        '    F --> D\n'
        '    D --> G[Setup Workstation]\n'
        '    D --> H[Create Accounts]\n'
        '    G --> I[Orientation]\n'
        '    H --> I\n'
        '    I --> J[End]\n\n'
        "Target query:\n"
        '"{rewritten_query}"\n\n'
        "Output raw Mermaid code only."
    )

    @staticmethod
    def _extract_fallback_mermaid(raw: str) -> str:
        names = re.findall(r'name=["\']([^"\']+)["\']', raw)
        if not names:
            names = re.findall(r':([A-Z][A-Za-z ]+)', raw)
        if not names:
            names = ["Step 1", "Step 2", "Step 3"]
        lines = ["graph TD"]
        prev = "Start"
        node_id = 0
        for n in names:
            n = n.strip()
            if n.lower() in ("start", "end", "stop"):
                continue
            nid = f"N{node_id}"
            lines.append(f'    {nid}["{n}"]')
            lines.append(f"    {prev} --> {nid}")
            prev = nid
            node_id += 1
        lines.append(f"    {prev} --> End")
        return "\n".join(lines)

    @staticmethod
    def _is_mermaid(code: str) -> bool:
        first = code.strip().split("\n")[0]
        for kw in MERMAID_KEYWORDS:
            if first.startswith(kw) or code.strip().startswith(kw):
                return True
        return False

    def synthesize_model(
        self, rewritten_query: str, framework_choice: str
    ) -> tuple[str, dict]:
        if not rewritten_query or not rewritten_query.strip():
            raise ValueError("rewritten_query must be a non-empty string")

        prompt = STAGE_2_TEMPLATE.format(
            framework_choice=framework_choice, rewritten_query=rewritten_query
        )

        text, latency, pt, ct = self._call_openai(prompt)
        clean_code = self._strip_markdown_fences(text)

        total_latency = latency
        total_pt = pt
        total_ct = ct

        # Validate: output must be Mermaid syntax
        if not self._is_mermaid(clean_code):
            retry_prompt = self._RETRY_PROMPT.format(
                rewritten_query=rewritten_query,
            )
            text2, lat2, pt2, ct2 = self._call_openai(retry_prompt)
            clean_code = self._strip_markdown_fences(text2)
            total_latency += lat2
            total_pt += pt2 if pt2 > 0 else 0
            total_ct += ct2 if ct2 > 0 else 0

        # Final safety net: if STILL not Mermaid, build one from extracted names
        if not self._is_mermaid(clean_code):
            clean_code = self._extract_fallback_mermaid(text + "\n" + clean_code)

        metrics = {
            "stage_2_latency_seconds": total_latency,
            "stage_2_prompt_tokens": total_pt,
            "stage_2_completion_tokens": total_ct,
        }
        return clean_code, metrics

    def _post_process_canonical_model(self, raw_model: dict, framework: str, model_id: str) -> dict:
        """Post-process raw LLM output: assign UUIDs, deduplicate, add layout, defaults."""
        # Handle both formats: elements/relationships (expected) and nodes/edges (LLM actual output)
        elements = raw_model.get("elements", [])
        relationships = raw_model.get("relationships", [])
        
        # Handle LLM's nodes/edges format
        if not elements and "nodes" in raw_model:
            elements = raw_model.get("nodes", [])
        if not relationships:
            # Check multiple possible keys for relationships
            for key in ["edges", "relations", "relationships"]:
                if key in raw_model:
                    relationships = raw_model.get(key, [])
                    break

        # Normalize element fields: uuid -> id, add missing fields
        normalized_elements = []
        for elem in elements:
            normalized = {
                "id": elem.get("id") or elem.get("uuid", ""),
                "frameworkType": elem.get("frameworkType", ""),
                "canonicalType": elem.get("canonicalType", ""),
                "name": elem.get("name", ""),
                "description": elem.get("description", ""),
                "layer": elem.get("layer", ""),
                "submodel": elem.get("submodel", None),
                "attributes": elem.get("attributes", {})
            }
            normalized_elements.append(normalized)

        # Normalize relationship fields
        # Relationship canonicalType mapping - unified for all frameworks
        REL_CANONICAL_TYPE_MAP = {
            "flow": "flows",
            "sequence": "flows",
            "sequenceflow": "flows",
            "messageflow": "flows",
            "triggering": "triggers",
            "assignment": "assigns",
            "serving": "serves",
            "realization": "realizes",
            "access": "access_read",
            "composition": "composes",
            "aggregation": "aggregates",
            "specialization": "specializes",
            "association": "associates",
            # 4EM-specific (will be overridden by framework-specific map)
            "part of": "part_of",
            "works in": "works_in",
            "refined by (and)": "refines",
            "refined by (and)": "refines",
            "hinders": "hinders",
            "is responsible for": "responsible_for",
            "decomposed into": "decomposes_to",
            "decomposes into": "decomposes_to",
            "decomposition": "decomposes_to",
            "input": "input",
            "output": "output",
            "consists of": "composes",
            "offers": "offers",
            "supports": "supports",
            "support": "supports",
            "refined by": "refines",
            "included in": "includes",
            "is responsible for": "responsible_for",
            "responsibility": "responsible_for",
            "decomposition": "decomposes_to",
        }

        # Framework-specific relationship type maps
        FRAMEWORK_REL_MAPS = {
            "4EM": CANONICAL_RELATIONSHIP_MAP_4EM,
        }
        
        # Select the appropriate relationship map
        rel_map = FRAMEWORK_REL_MAPS.get(framework, REL_CANONICAL_TYPE_MAP)

        # Normalize relationship fields
        normalized_relationships = []
        for rel in relationships:
            raw_canonical = rel.get("canonicalType", "") or rel.get("type", "")
            # Map common type aliases to canonical types using framework-specific map
            canonical_type = rel_map.get(raw_canonical, raw_canonical)

            normalized = {
                "id": rel.get("id") or rel.get("uuid", ""),
                "sourceId": rel.get("sourceId") or rel.get("source", ""),
                "targetId": rel.get("targetId") or rel.get("target", ""),
                "frameworkType": rel.get("frameworkType", ""),
                "canonicalType": canonical_type,
                "name": rel.get("name", ""),
                "description": rel.get("description", ""),
                "attributes": rel.get("attributes", {})
            }
            normalized_relationships.append(normalized)

        elements = normalized_elements
        relationships = normalized_relationships

        # 1. Assign deterministic UUIDv5 to elements
        name_type_to_elem = {}
        for elem in elements:
            key = (elem.get("canonicalType", ""), elem.get("name", ""))
            if key in name_type_to_elem:
                # Duplicate - skip
                continue
            name_type_to_elem[key] = elem
            # Only assign UUID if not already a valid UUID
            if not elem.get("id") or elem.get("id") == "GEN-UUID":
                elem["id"] = element_id(model_id, elem.get("name", ""), elem.get("canonicalType", ""))

        # 2. Assign deterministic UUIDv5 to relationships
        seen_rels = set()
        valid_relationships = []
        
        # Build element list in order for sequential matching
        element_list = list(name_type_to_elem.values())
        
        for i, rel in enumerate(relationships):
            source_id = rel.get("sourceId", "")
            target_id = rel.get("targetId", "")
            canonical_type = rel.get("canonicalType", "")
            
            source_elem = None
            target_elem = None
            
            # Try to match by ID first
            source_elem = next((e for e in element_list if e.get("id") == source_id), None)
            target_elem = next((e for e in element_list if e.get("id") == target_id), None)
            
            # If not found by ID, try by name
            if not source_elem:
                source_elem = next((e for e in element_list if e.get("name") == source_id), None)
            if not target_elem:
                target_elem = next((e for e in element_list if e.get("name") == target_id), None)
            
            # If still not found (all GEN-UUID placeholders), match sequentially by index
            # Edge i connects element i to element i+1
            if not source_elem and i < len(element_list) - 1:
                source_elem = element_list[i]
            if not target_elem and i + 1 < len(element_list):
                target_elem = element_list[i + 1]
            
            if source_elem and target_elem:
                rel_key = (source_elem["id"], target_elem["id"], canonical_type)
                if rel_key in seen_rels:
                    continue
                seen_rels.add(rel_key)
                
                rel["id"] = relationship_id(model_id, source_elem["id"], target_elem["id"], canonical_type)
                rel["sourceId"] = source_elem["id"]
                rel["targetId"] = target_elem["id"]
                valid_relationships.append(rel)

        # FALLBACK: If LLM generated 0 valid relationships, create sequential flow
        if not valid_relationships and len(element_list) > 1:
            for i in range(len(element_list) - 1):
                source_elem = element_list[i]
                target_elem = element_list[i + 1]
                
                rel = {
                    "id": relationship_id(model_id, source_elem["id"], target_elem["id"], "flows"),
                    "sourceId": source_elem["id"],
                    "targetId": target_elem["id"],
                    "frameworkType": "SequenceFlow",
                    "canonicalType": "flows",
                    "name": "",
                    "description": f"Sequential flow from {source_elem.get('name')} to {target_elem.get('name')}",
                    "attributes": {}
                }
                valid_relationships.append(rel)

        # 3. Add framework-specific defaults
        VALID_CANONICAL_TYPES = {
            "goal", "process", "actor", "org_unit", "role", "problem",
            "info_set", "product", "component", "feature", "tech_component",
            "concept", "attribute",
            "biz_actor", "biz_process", "biz_service", "biz_function",
            "biz_event", "biz_role", "biz_object",
            "app_component", "app_service", "app_function",
            "data_object", "artifact", "device", "node", "system_software",
            "tech_service", "tech_function", "tech_interface", "comm_network",
            "equipment", "facility", "junction", "grouping", "location",
            "driver", "stakeholder", "assessment", "principle", "requirement",
            "constraint", "outcome", "event", "gateway",
        }

        for elem in name_type_to_elem.values():
            # Handle canonicalType mapping
            framework_type = elem.get("frameworkType", "")
            canonical_type = elem.get("canonicalType", "")
            
            # If canonicalType is not a valid unified type, try to map from frameworkType
            if canonical_type not in VALID_CANONICAL_TYPES:
                if framework == "4EM" and framework_type in CANONICAL_TYPE_MAP_4EM:
                    elem["canonicalType"] = CANONICAL_TYPE_MAP_4EM[framework_type]
                elif framework == "4EM" and canonical_type in CANONICAL_TYPE_MAP_4EM:
                    # Also check if the canonical_type itself is a key in the map (LLM put framework type in canonicalType field)
                    elem["canonicalType"] = CANONICAL_TYPE_MAP_4EM[canonical_type]
                elif framework == "BPMN" and framework_type in CANONICAL_TYPE_MAP_BPMN:
                    elem["canonicalType"] = CANONICAL_TYPE_MAP_BPMN[framework_type]
                # If still not valid, default to a reasonable type
                elif canonical_type == "event":
                    elem["canonicalType"] = "biz_event"
                elif canonical_type == "gateway":
                    elem["canonicalType"] = "junction"
                elif canonical_type == "process":
                    elem["canonicalType"] = "biz_process"
                elif canonical_type == "flow":
                    elem["canonicalType"] = "flows"
                else:
                    # Last-resort: unknown type -> 'grouping' (safe ArchiMate catch-all)
                    logger.warning(
                        f"Unknown canonicalType '{canonical_type}' for element "
                        f"'{elem.get('name')}' (frameworkType='{framework_type}'). "
                        f"Defaulting to 'grouping'."
                    )
                    elem["canonicalType"] = "grouping"
            
            VALID_LAYERS = {"goals", "processes", "actors", "technical",
                            "business", "application", "technology",
                            "physical", "motivation", "implementation"}

            if framework == "4EM":
                # First set submodel based on frameworkType OR existing submodel value
                framework_type = elem.get("frameworkType", "")
                submodel_value = elem.get("submodel", "")
                
                # Map submodel from frameworkType if present in map
                if framework_type in SUBMODEL_MAP_4EM:
                    elem["submodel"] = SUBMODEL_MAP_4EM[framework_type]
                # Also check if the submodel value itself is a key in the map (LLM may have put submodel name directly)
                elif submodel_value in SUBMODEL_MAP_4EM:
                    elem["submodel"] = SUBMODEL_MAP_4EM[submodel_value]
                # For 4EM, layer MUST come from submodel (goals, processes, actors, technical)
                # Ignore LLM's layer field
                elem["layer"] = elem.get("submodel")
            elif framework == "BPMN":
                # Validate layer against allowed enum; default to business
                if not elem.get("layer") or elem.get("layer") not in VALID_LAYERS:
                    elem["layer"] = "business"
                elem["submodel"] = None

            # Ensure description exists (required by schema)
            if not elem.get("description"):
                elem["description"] = ""

            # Ensure attributes dict exists
            if "attributes" not in elem:
                elem["attributes"] = {}

        # 4. Generate deterministic layout
        if framework == "4EM":
            positions = generate_4em_layout(list(name_type_to_elem.values()))
            for elem in name_type_to_elem.values():
                pos = positions.get(elem["id"])
                if pos:
                    elem["attributes"]["Position"] = f"NODE x:{pos.x:.1f}cm y:{pos.y:.1f}cm w:{pos.width:.1f}cm h:{pos.height:.1f}cm index:1"

        # Build processed model
        processed = {
            "framework": framework,
            "metadata": {
                "modelId": model_id,
                "name": raw_model.get("metadata", {}).get("name", f"{framework} Model"),
                "version": "1.0.0",
                "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "toolVersion": "QRew-1.0",
                "frameworkVersion": "4EM:5.1" if framework == "4EM" else "ArchiMate:3.2",
                "sourceRunId": raw_model.get("metadata", {}).get("sourceRunId", model_id),
            },
            "elements": list(name_type_to_elem.values()),
            "relationships": valid_relationships,
            "diagrams": raw_model.get("diagrams", []),
            "folders": raw_model.get("folders", []),
            "extensions": raw_model.get("extensions", {}),
        }

        return processed

    def _validate_canonical_model(self, model: dict, framework: str):
        """Validate canonical model, return warnings (never blocks)."""
        from validators import validate_canonical
        result = validate_canonical(model)
        return result.warnings

    def generate_canonical_model_pipeline(self, rewritten_query: str, framework_choice: str) -> tuple[dict, dict, list]:
        """Run Stage 2b: generate canonical model with validation."""
        if framework_choice not in ("4EM", "BPMN"):
            return None, {}, []

        model_id = str(uuid.uuid4())

        # Generate raw model from LLM
        raw_model, metrics = self.generate_canonical_model(rewritten_query, framework_choice)

        logger.debug("Raw model output: %s", raw_model)
        processed_model = self._post_process_canonical_model(raw_model, framework_choice, model_id)
        logger.debug("Processed canonical model: %s", processed_model)
        warnings = self._validate_canonical_model(processed_model, framework_choice)

        return processed_model, metrics, warnings

    def run_qrew_pipeline(
        self, user_input: str, framework_choice: str
    ) -> dict:
        run_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        try:
            rewritten_query, s1_metrics = self.transform_prompt(
                user_input, framework_choice
            )

            final_code, s2_metrics = self.synthesize_model(
                rewritten_query, framework_choice
            )

            canonical_model, s2b_metrics, canonical_warnings = self.generate_canonical_model_pipeline(
                rewritten_query, framework_choice
            )

            total_latency = (
                s1_metrics["stage_1_latency_seconds"]
                + s2_metrics["stage_2_latency_seconds"]
            )

            event_payload = {
                "run_id": run_id,
                "timestamp": timestamp,
                "pipeline_strategy": "QRew",
                "framework_target": framework_choice,
                "metrics": {
                    "stage_1_latency_seconds": s1_metrics[
                        "stage_1_latency_seconds"
                    ],
                    "stage_2_latency_seconds": s2_metrics[
                        "stage_2_latency_seconds"
                    ],
                    "total_latency_seconds": total_latency,
                    "stage_1_prompt_tokens": s1_metrics[
                        "stage_1_prompt_tokens"
                    ],
                    "stage_1_completion_tokens": s1_metrics[
                        "stage_1_completion_tokens"
                    ],
                    "stage_2_prompt_tokens": s2_metrics[
                        "stage_2_prompt_tokens"
                    ],
                    "stage_2_completion_tokens": s2_metrics[
                        "stage_2_completion_tokens"
                    ],
                },
                "traces": {
                    "original_raw_input": user_input,
                    "stage_1_rewritten_query": rewritten_query,
                    "final_generated_code": final_code,
                },
            }

            if canonical_model:
                event_payload["traces"]["canonical_model"] = canonical_model
                event_payload["metrics"]["stage_2b_latency_seconds"] = s2b_metrics.get("stage_2b_latency_seconds", 0)
                event_payload["metrics"]["stage_2b_prompt_tokens"] = s2b_metrics.get("stage_2b_prompt_tokens", 0)
                event_payload["metrics"]["stage_2b_completion_tokens"] = s2b_metrics.get("stage_2b_completion_tokens", 0)
                if canonical_warnings:
                    event_payload["traces"]["canonical_model_warnings"] = canonical_warnings

            if os.getenv("QREW_DEBUG_DUMP") == "1":
                event_path = os.path.join(_SCRIPT_DIR, "qrew_latest_event.json")
                output_path = os.path.join(_SCRIPT_DIR, "qrew_output_model.txt")
                with open(event_path, "w", encoding="utf-8") as f:
                    json.dump(event_payload, f, indent=2)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(final_code)

            return event_payload

        except Exception as e:
            if os.getenv("QREW_DEBUG_DUMP") == "1":
                event_path = os.path.join(_SCRIPT_DIR, "qrew_latest_event.json")
                error_payload = {
                    "run_id": run_id,
                    "timestamp": timestamp,
                    "pipeline_strategy": "QRew",
                    "framework_target": framework_choice,
                    "metrics": {
                        "stage_1_latency_seconds": -1.0,
                        "stage_2_latency_seconds": -1.0,
                        "total_latency_seconds": -1.0,
                        "stage_1_prompt_tokens": -1,
                        "stage_1_completion_tokens": -1,
                        "stage_2_prompt_tokens": -1,
                        "stage_2_completion_tokens": -1,
                    },
                    "traces": {
                        "original_raw_input": user_input,
                        "stage_1_rewritten_query": f"ERROR: {str(e)}",
                        "final_generated_code": "FAILED",
                    },
                }
                with open(event_path, "w", encoding="utf-8") as f:
                    json.dump(error_payload, f, indent=2)
            raise e
