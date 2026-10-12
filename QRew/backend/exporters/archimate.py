"""ArchiMate Exchange Format serializer."""

from typing import Dict, Any, List
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from exporters.base import BaseExporter
from layout import generate_archimate_layout
from ids import element_id, relationship_id, folder_id


class ArchiMateExporter(BaseExporter):
    """Serialize canonical model to ArchiMate Exchange Format (OpenGroup 3.2)."""

    # Canonical type to ArchiMate xsi:type
    ELEMENT_TYPE_MAP = {
        # Business layer
        "process":      "archimate:BusinessProcess",
        "actor":        "archimate:BusinessActor",
        "role":         "archimate:BusinessRole",
        "event":        "archimate:BusinessEvent",
        "function":     "archimate:BusinessFunction",
        "interaction":  "archimate:BusinessInteraction",
        "product":      "archimate:Product",
        "service":      "archimate:BusinessService",
        "interface":    "archimate:BusinessInterface",
        "object":       "archimate:BusinessObject",
        "contract":     "archimate:Contract",
        "representation": "archimate:Representation",
        "meaning":      "archimate:Meaning",
        "value":        "archimate:Value",
        # BPMN mappings
        "biz_actor":    "archimate:BusinessActor",
        "biz_role":     "archimate:BusinessRole",
        "biz_process":  "archimate:BusinessProcess",
        "biz_event":    "archimate:BusinessEvent",
        "biz_service":  "archimate:BusinessService",
        "biz_object":   "archimate:BusinessObject",
        "biz_function": "archimate:BusinessFunction",
        "junction":     "archimate:Junction",
        # Application layer
        "app_component": "archimate:ApplicationComponent",
        "app_service":   "archimate:ApplicationService",
        "app_function":  "archimate:ApplicationFunction",
        "data_object":   "archimate:DataObject",
        "artifact":      "archimate:Artifact",
        # Technology layer
        "device":        "archimate:Device",
        "node":          "archimate:Node",
        "system_software": "archimate:SystemSoftware",
        "tech_service":  "archimate:TechnologyService",
        "tech_function": "archimate:TechnologyFunction",
        "tech_interface": "archimate:TechnologyInterface",
        "comm_network":  "archimate:CommunicationNetwork",
        "equipment":     "archimate:Equipment",
        "facility":      "archimate:Facility",
        # Physical / Other
        "location":      "archimate:Location",
        "grouping":      "archimate:Grouping",
        "gateway":       "archimate:Junction",
        # Motivation layer
        "goal":          "archimate:Goal",
        "outcome":       "archimate:Outcome",
        "principle":     "archimate:Principle",
        "requirement":   "archimate:Requirement",
        "constraint":    "archimate:Constraint",
        "stakeholder":   "archimate:Stakeholder",
        "driver":        "archimate:Driver",
        "assessment":    "archimate:Assessment",
        "problem":       "archimate:Assessment",
        # 4EM mappings
        "org_unit":      "archimate:BusinessActor",
        "info_set":      "archimate:DataObject",
        "component":     "archimate:ApplicationComponent",
        "feature":       "archimate:BusinessService",
        "tech_component": "archimate:Node",
        "concept":       "archimate:BusinessObject",
        "attribute":     "archimate:DataObject",
    }

    # Canonical relationship to ArchiMate xsi:type
    RELATIONSHIP_TYPE_MAP = {
        "triggers": "archimate:TriggeringRelationship",
        "aggregates": "archimate:AggregationRelationship",
        "composes": "archimate:CompositionRelationship",
        "realizes": "archimate:RealizationRelationship",
        "serves": "archimate:ServingRelationship",
        "flows": "archimate:FlowRelationship",
        "assigns": "archimate:AssignmentRelationship",
        "associates": "archimate:AssociationRelationship",
        "specializes": "archimate:SpecializationRelationship",
        "access_read": "archimate:AccessRelationship",
        "access_write": "archimate:AccessRelationship",
        "access_rw": "archimate:AccessRelationship",
        "part_of": "archimate:AggregationRelationship",
        "works_in": "archimate:AssignmentRelationship",
        "refines": "archimate:SpecializationRelationship",
        "hinders": "archimate:AssociationRelationship",
        "responsible_for": "archimate:AssignmentRelationship",
        "decomposes_to": "archimate:CompositionRelationship",
        "input": "archimate:AccessRelationship",
        "output": "archimate:AccessRelationship",
        "composes": "archimate:CompositionRelationship",
        "offers": "archimate:ServingRelationship",
        "supports": "archimate:ServingRelationship",
        "includes": "archimate:AggregationRelationship",
    }

    # Access type mapping for AccessRelationship
    ACCESS_TYPE_MAP = {
        "access_read": "1",
        "access_write": "2",
        "access_rw": "3",
        "input": "1",
        "output": "2",
    }

    # Layer to folder type
    LAYER_FOLDER_MAP = {
        "strategy": "strategy",
        "business": "business",
        "application": "application",
        "technology": "technology",
        "physical": "technology",
        "motivation": "motivation",
        "implementation": "implementation_migration",
    }

    # Folder display names
    FOLDER_NAMES = {
        "strategy": "Strategy",
        "business": "Business",
        "application": "Application",
        "technology": "Technology & Physical",
        "motivation": "Motivation",
        "implementation_migration": "Implementation & Migration",
        "other": "Other",
        "relations": "Relations",
    }

    def export(self, model: Dict[str, Any]) -> bytes:
        if model.get("framework") != "BPMN":
            raise ValueError("ArchiMateExporter only supports BPMN framework")

        elements = model.get("elements", [])
        relationships = model.get("relationships", [])
        diagrams = model.get("diagrams", [])
        folders = model.get("folders", [])
        metadata = model.get("metadata", {})
        model_id = metadata.get("modelId", "")
        model_name = metadata.get("name", "ArchiMate Model")

        # Register namespaces
        ET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        ET.register_namespace('archimate', 'http://www.archimatetool.com/archimate')

        # Create root element (namespaces will be added by register_namespace)
        root = ET.Element(
            '{http://www.archimatetool.com/archimate}model',
            {
                'name': model_name,
                'id': model_id,
                'version': '5.0.0'
            }
        )

        # Group elements by layer/folder
        layer_elements: Dict[str, List[Dict]] = {}
        for elem in elements:
            archimate_type = self.ELEMENT_TYPE_MAP.get(elem.get("canonicalType", ""), "archimate:BusinessObject")
            
            # Archi strictly expects elements in specific folders based on their xsi:type
            if archimate_type.startswith("archimate:Business") or archimate_type in ["archimate:Product", "archimate:Contract", "archimate:Representation", "archimate:Meaning", "archimate:Value"]:
                folder_type = "business"
            elif archimate_type.startswith("archimate:Application") or archimate_type == "archimate:DataObject":
                folder_type = "application"
            elif archimate_type.startswith("archimate:Technology") or archimate_type in ["archimate:Node", "archimate:Device", "archimate:SystemSoftware", "archimate:CommunicationNetwork", "archimate:Path", "archimate:Artifact", "archimate:Equipment", "archimate:Facility", "archimate:DistributionNetwork", "archimate:Material"]:
                folder_type = "technology"
            elif archimate_type in ["archimate:Resource", "archimate:Capability", "archimate:CourseOfAction", "archimate:ValueStream"]:
                folder_type = "strategy"
            elif archimate_type in ["archimate:Stakeholder", "archimate:Driver", "archimate:Assessment", "archimate:Goal", "archimate:Outcome", "archimate:Principle", "archimate:Requirement", "archimate:Constraint", "archimate:Meaning", "archimate:Value"]:
                folder_type = "motivation"
            elif archimate_type in ["archimate:WorkPackage", "archimate:Deliverable", "archimate:ImplementationEvent", "archimate:Plateau", "archimate:Gap"]:
                folder_type = "implementation_migration"
            else:
                folder_type = "other"

            if folder_type not in layer_elements:
                layer_elements[folder_type] = []
            layer_elements[folder_type].append(elem)

        # Archi strictly expects all standard folders to be present
        standard_folders = [
            "strategy", "business", "application", "technology",
            "motivation", "implementation_migration", "other"
        ]
        
        folder_id_map = {}
        for folder_type in standard_folders:
            folder_name = self.FOLDER_NAMES.get(folder_type, folder_type.capitalize())
            if folder_type == "technology":
                folder_name = "Technology & Physical"
            elif folder_type == "implementation_migration":
                folder_name = "Implementation & Migration"
                
            fid = folder_id(model_id, folder_name)
            folder_id_map[folder_type] = fid

            # Folders use NO namespace prefix (just <folder>, not <archimate:folder>)
            folder_elem = ET.SubElement(root, 'folder', {
                'name': folder_name,
                'id': fid,
                'type': folder_type
            })

            # Add elements belonging to this folder if any
            if folder_type in layer_elements:
                for elem in layer_elements[folder_type]:
                    archimate_type = self.ELEMENT_TYPE_MAP.get(elem.get("canonicalType", ""), "archimate:BusinessObject")
                    # Elements use <element> (no namespace), not <archimate:element>
                    elem_elem = ET.SubElement(folder_elem, 'element', {
                        '{http://www.w3.org/2001/XMLSchema-instance}type': archimate_type,
                        'name': elem.get("name") or "",
                        'id': elem["id"]
                    })
                    if elem.get("description"):
                        doc_elem = ET.SubElement(elem_elem, 'documentation')
                        doc_elem.text = elem["description"]

        # Create Relations folder
        relations_fid = folder_id(model_id, "Relations")
        folder_id_map["relations"] = relations_fid
        relations_folder = ET.SubElement(root, 'folder', {
            'name': 'Relations',
            'id': relations_fid,
            'type': 'relations'
        })

        # Build element type lookup map for relationship validation
        element_types = {e["id"]: self.ELEMENT_TYPE_MAP.get(e.get("canonicalType", ""), "archimate:BusinessObject") for e in elements}

        for rel in relationships:
            archimate_rel_type = self.RELATIONSHIP_TYPE_MAP.get(rel.get("canonicalType", ""), "archimate:AssociationRelationship")
            source_type = element_types.get(rel.get("sourceId", ""))
            target_type = element_types.get(rel.get("targetId", ""))

            # ARCHIMATE 3.2 METAMODEL ENFORCEMENT:
            # Rather than blocking ALL cross-type structural relationships, use an
            # allowlist of valid pairs from the ArchiMate 3.2 specification.
            # Location can aggregate/compose any active structure element or node.
            # Grouping can aggregate anything. Same-type pairs are always valid.
            if archimate_rel_type in ("archimate:AggregationRelationship", "archimate:CompositionRelationship"):
                if source_type and target_type and source_type != target_type:
                    is_valid = self._is_valid_structural_pair(source_type, target_type)
                    if not is_valid:
                        archimate_rel_type = "archimate:AssociationRelationship"

            # Access relationships are only valid if targeting passive structure (DataObject, BusinessObject, Artifact, etc)
            if archimate_rel_type == "archimate:AccessRelationship" and target_type:
                if not target_type.endswith(("Object", "Artifact", "Representation", "Meaning", "Value", "Material")):
                    archimate_rel_type = "archimate:AssociationRelationship"

            # Relations also use <element> (no namespace)
            rel_elem = ET.SubElement(relations_folder, 'element', {
                '{http://www.w3.org/2001/XMLSchema-instance}type': archimate_rel_type,
                'name': rel.get("name") or "",
                'id': rel["id"],
                'source': rel["sourceId"],
                'target': rel["targetId"]
            })

            # Add accessType for AccessRelationship
            if archimate_rel_type == "archimate:AccessRelationship":
                access_type = self.ACCESS_TYPE_MAP.get(rel.get("canonicalType", ""), "1")
                rel_elem.set('accessType', access_type)

            if rel.get("description"):
                doc_elem = ET.SubElement(rel_elem, 'documentation')
                doc_elem.text = rel["description"]

        # Note: the "Other" folder for groupings/locations is now handled automatically
        # by the new folder_type mapping, so we don't need a separate pass for them.

        # Generate viewpoints/views from diagrams so Archi opens with a visual model view
        self._generate_viewpoints(root, model_id, elements, relationships)

        # Pretty-print XML
        rough_string = ET.tostring(root, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ", encoding="utf-8")

        # Remove extra blank lines
        lines = pretty_xml.decode("utf-8").split('\n')
        filtered = [line for line in lines if line.strip() or not line.startswith(' ')]
        return '\n'.join(filtered).encode('utf-8')

    def _generate_viewpoints(self, root: ET.Element, model_id: str, elements: List[Dict], relationships: List[Dict]):
        """Generate a single comprehensive view for the model to preserve all cross-layer relationships."""
        if not elements:
            return

        # Create Views folder
        views_folder_id = folder_id(model_id, "Views")
        views_folder = ET.SubElement(root, 'folder', {
            'name': 'Views',
            'id': views_folder_id,
            'type': 'diagrams'
        })

        # Create a single Main View for all elements
        view_id = element_id(model_id, "main_view", "view")
        view_elem = ET.SubElement(views_folder, 'element', {
            '{http://www.w3.org/2001/XMLSchema-instance}type': 'archimate:ArchimateDiagramModel',
            'name': 'Main View',
            'id': view_id,
            'viewpoint': 'layered'
        })

        # Pre-compute connection IDs and build target connection map
        # (Archi requires targetConnections on diagram objects to route line endpoints)
        conn_id_map = {}  # rel_id -> conn_id
        target_conn_map = {}  # element_id -> [conn_id, ...]
        elem_id_set = {e["id"] for e in elements}

        for rel in relationships:
            source_id = rel.get("sourceId")
            target_id = rel.get("targetId")
            if source_id in elem_id_set and target_id in elem_id_set:
                conn_id = element_id(model_id, f"{rel['id']}_conn", "connection")
                conn_id_map[rel["id"]] = conn_id
                if target_id not in target_conn_map:
                    target_conn_map[target_id] = []
                target_conn_map[target_id].append(conn_id)

        # Add node elements for all elements
        positions = generate_archimate_layout(elements, relationships)
        node_elements_map = {}
        elem_to_node_id = {}
        for elem in elements:
            node_id = element_id(model_id, f"{elem['id']}_node", "node")
            elem_to_node_id[elem["id"]] = node_id

            attrs = {
                '{http://www.w3.org/2001/XMLSchema-instance}type': 'archimate:DiagramObject',
                'id': node_id,
                'archimateElement': elem["id"]
            }
            # Add targetConnections attribute if this element is a target of any connection
            if elem["id"] in target_conn_map:
                attrs['targetConnections'] = ' '.join(target_conn_map[elem["id"]])

            node_elem = ET.SubElement(view_elem, 'child', attrs)
            node_elements_map[elem["id"]] = node_elem

            # Add bounds for layout
            pos = positions.get(elem["id"])
            if pos:
                ET.SubElement(node_elem, 'bounds', {
                    'x': str(int(pos.x)),
                    'y': str(int(pos.y)),
                    'width': str(int(pos.width)),
                    'height': str(int(pos.height))
                })

        # Add connection elements for all relationships
        for rel in relationships:
            source_id = rel.get("sourceId")
            target_id = rel.get("targetId")

            source_node_id = elem_to_node_id.get(source_id)
            target_node_id = elem_to_node_id.get(target_id)
            source_node_elem = node_elements_map.get(source_id)

            if source_node_elem is not None and target_node_id is not None and source_node_id is not None:
                conn_id = conn_id_map.get(rel["id"])
                if conn_id:
                    ET.SubElement(source_node_elem, 'sourceConnection', {
                        '{http://www.w3.org/2001/XMLSchema-instance}type': 'archimate:Connection',
                        'id': conn_id,
                        'source': source_node_id,
                        'target': target_node_id,
                        'archimateRelationship': rel["id"]
                    })

    @staticmethod
    def _is_valid_structural_pair(source_type: str, target_type: str) -> bool:
        """Check if a structural relationship (Aggregation/Composition) is valid
        between two ArchiMate element types per ArchiMate 3.2 metamodel.

        ArchiMate allows structural relationships between elements of the same
        layer/category, and additionally allows Location to aggregate/compose
        active structure elements from any layer.
        """
        # Grouping can aggregate/compose anything
        if source_type.endswith("Grouping"):
            return True

        # Location can aggregate/compose any active structure element or node
        if source_type == "archimate:Location":
            valid_location_targets = {
                "archimate:BusinessActor", "archimate:BusinessRole",
                "archimate:BusinessCollaboration", "archimate:BusinessInterface",
                "archimate:BusinessProcess", "archimate:BusinessFunction",
                "archimate:BusinessInteraction", "archimate:BusinessService",
                "archimate:ApplicationComponent", "archimate:ApplicationCollaboration",
                "archimate:ApplicationInterface", "archimate:ApplicationFunction",
                "archimate:ApplicationProcess", "archimate:ApplicationService",
                "archimate:Node", "archimate:Device", "archimate:SystemSoftware",
                "archimate:TechnologyCollaboration", "archimate:TechnologyInterface",
                "archimate:TechnologyFunction", "archimate:TechnologyProcess",
                "archimate:TechnologyService", "archimate:CommunicationNetwork",
                "archimate:Path", "archimate:Equipment", "archimate:Facility",
                "archimate:DistributionNetwork", "archimate:Material",
                "archimate:Location",  # Location can nest Locations
            }
            return target_type in valid_location_targets

        # Same layer check: extract the layer prefix from the xsi:type
        # e.g. "archimate:BusinessActor" -> "Business", "archimate:ApplicationComponent" -> "Application"
        def get_layer(t: str) -> str:
            name = t.split(':')[1] if ':' in t else t
            for prefix in ["Business", "Application", "Technology", "Physical"]:
                if name.startswith(prefix):
                    return prefix
            # Motivation, Strategy, Implementation layer types
            motivation_types = {"Stakeholder", "Driver", "Assessment", "Goal", "Outcome",
                               "Principle", "Requirement", "Constraint", "Meaning", "Value"}
            strategy_types = {"Resource", "Capability", "CourseOfAction", "ValueStream"}
            if name in motivation_types:
                return "Motivation"
            if name in strategy_types:
                return "Strategy"
            return "Other"

        src_layer = get_layer(source_type)
        tgt_layer = get_layer(target_type)

        # Same-layer structural relationships are valid
        if src_layer == tgt_layer:
            return True

        # Cross-layer structural relationships are generally not valid
        # (except Location which is handled above)
        return False