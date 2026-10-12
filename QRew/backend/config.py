"""Static configuration, prompt templates, and schema definitions."""

# Framework domain rules
FRAMEWORK_KNOWLEDGE = {
    "BPMN": (
        "ArchiMate / Business Process Modeling Rules:\n"
        "- First, determine the MODEL TYPE from the user input:\n"
        "  (A) PROCESS FLOW: The input describes a sequence of tasks, steps, events, or activities "
        "with a logical order of execution (e.g., 'first do X, then Y, if Z then…').\n"
        "  (B) STRUCTURAL / ORGANIZATIONAL: The input describes compositions, aggregations, "
        "decompositions, or location assignments of actors, roles, and organizational units "
        "WITHOUT any process flow (e.g., 'Actor A is composed of B and C', 'Location X aggregates Actor Y').\n"
        "  (C) LAYERED ARCHITECTURE: The input describes elements spanning multiple ArchiMate layers "
        "(motivation, business, application, technology) with cross-layer relationships.\n"
        "\n"
        "- For PROCESS FLOW models: Start with a single start event, use sequence flows for "
        "logical order, use gateways for diverging/converging logic, and terminate at an end event.\n"
        "- For STRUCTURAL / ORGANIZATIONAL models: Model the exact hierarchy stated. Use "
        "composition, aggregation, and assignment relationships. Do NOT add start/end events "
        "or sequence flows.\n"
        "- For LAYERED ARCHITECTURE models: Include elements from all relevant layers and "
        "use appropriate cross-layer relationships (serving, realization, assignment).\n"
        "- Preserve the exact structural relationships stated by the user: composition means "
        "'is composed of', aggregation means 'aggregates', assignment means 'is assigned to'."
    ),
    "TOGAF": (
        "TOGAF ADM Phase-A Core Mapping:\n"
        "- Define the Architecture Vision, high-level business capabilities, and core stakeholders.\n"
        "- Map current state capabilities to desired target capabilities directly.\n"
        "- Define core business goals and align them to technical baseline requirements."
    ),
    "4EM": (
        "4EM (Enterprise Modeling) Syntax Rules:\n"
        "- Models must explicitly connect 4 distinct sub-models: Goals, Business Processes, Actors, and Technical Concepts.\n"
        "- Business processes must be triggered by an external event or linked directly to a defined corporate Goal.\n"
        "- Every process step must be explicitly owned by a defined Actor resource or Automated System component."
    ),
    "ZACHMAN": (
        "Zachman Framework Syntax Rules:\n"
        "- Models are organized as a 6x6 matrix: 6 rows (Scope, Business Model, System Model, Technology Model, Detailed Representations, Functioning Enterprise) x 6 columns (What, How, Where, Who, When, Why).\n"
        "- Each cell in the matrix is an atomic artifact that must align vertically across rows and horizontally across columns.\n"
        "- Row 1 (Scope) defines business context and external drivers; each subsequent row adds detail without contradicting higher rows.\n"
        "- The What column addresses data/inventory; How addresses function/process; Where addresses network/location; Who addresses people/responsibility; When addresses time/schedule; Why addresses motivation/strategy."
    ),
}


# Stage 1: Requirement translation prompt
STAGE_1_TEMPLATE = (
    "You are an expert Enterprise Architect specializing in mapping vague "
    "requirements to strict architectural frameworks.\n"
    "Your task is to rewrite the User Input into a highly descriptive, "
    "technically precise Architectural Query optimized for generation.\n"
    "\n"
    "Incorporate the following Framework Rules explicitly into your rewritten query:\n"
    "{framework_rules}\n"
    "\n"
    'User Input: "{user_input}"\n'
    "\n"
    "Output ONLY the rewritten, high-fidelity query. Do not include "
    "introductory text, conversational filler, or markdown formatting."
)

# Stage 2: Diagram synthesis prompt (Mermaid)
MERMAID_KEYWORDS = [
    "graph ", "flowchart ", "sequenceDiagram", "classDiagram",
    "stateDiagram", "erDiagram", "gantt", "pie", "gitGraph",
    "mindmap", "timeline", "block", "journey", "C4Context",
    "C4Container", "C4Component",
]

STAGE_2_TEMPLATE = (
    "You are an advanced systems engineering tool. Your task is to compile "
    "the following High-Fidelity Architectural Query into flawless visual "
    "diagram notation matching the framework syntax.\n"
    "\n"
    "Target Framework Concept: {framework_choice}\n"
    'Architectural Blueprint Query: "{rewritten_query}"\n'
    "\n"
    "Output instructions:\n"
    "1. Generate valid, error-free rendering code for the specific framework.\n"
    "2. Use Mermaid.js syntax. The first line MUST be a Mermaid diagram type "
    "keyword (e.g., `graph TD`, `flowchart LR`, `sequenceDiagram`, "
    "`classDiagram`, `stateDiagram-v2`, `erDiagram`, `gantt`, `pie`, "
    "`gitGraph`, `mindmap`, `timeline`, `block`, `journey`).\n"
    "3. For BPMN specifically:\n"
    "   - If the query describes a PROCESS FLOW (tasks, steps, events, gateways), "
    "use `flowchart LR` or `graph TD` with Start/End nodes and conditional branches.\n"
    "   - If the query describes an ORGANIZATIONAL STRUCTURE (actors composed of "
    "sub-actors, locations aggregating actors, decompositions — no process steps), "
    "use `graph TD` with subgraphs to represent containment/hierarchy. Use "
    "`-->|composition|` and `-->|aggregation|` edge labels. Do NOT add Start/End nodes.\n"
    "   - If the query describes a LAYERED ARCHITECTURE spanning multiple layers, "
    "use `graph TD` with subgraphs per layer (Motivation, Business, Application, Technology).\n"
    "4. Do NOT wrap your output in markdown code blocks. Only output the raw "
    "Mermaid code string.\n"
    "5. Output ONLY the raw structural code string. Do not include "
    "conversational remarks, explanations, or filler."
)


# Canonical schema definition
CANONICAL_MODEL_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://qrew.ai/schemas/canonical-model-v1.json",
    "title": "QRew Canonical Semantic Model",
    "type": "object",
    "required": ["framework", "metadata", "elements", "relationships"],
    "properties": {
        "framework": {"type": "string", "enum": ["4EM", "BPMN", "TOGAF", "ZACHMAN"]},
        "metadata": {
            "type": "object",
            "required": ["modelId", "name", "version", "createdAt", "toolVersion"],
            "properties": {
                "modelId": {"type": "string", "format": "uuid"},
                "name": {"type": "string", "maxLength": 200},
                "version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"},
                "createdAt": {"type": "string", "format": "date-time"},
                "toolVersion": {"type": "string"},
                "frameworkVersion": {"type": "string"},
                "sourceRunId": {"type": "string", "format": "uuid"}
            }
        },
        "elements": {"type": "array", "items": {"$ref": "#/$defs/element"}},
        "relationships": {"type": "array", "items": {"$ref": "#/$defs/relationship"}},
        "diagrams": {"type": "array", "items": {"$ref": "#/$defs/diagram"}},
        "folders": {"type": "array", "items": {"$ref": "#/$defs/folder"}},
        "extensions": {"type": "object"}
    },
    "$defs": {
        "element": {
            "type": "object",
            "required": ["id", "frameworkType", "canonicalType", "name", "layer", "submodel", "attributes"],
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "frameworkType": {"type": "string"},
                "canonicalType": {
                    "type": "string",
                    "enum": ["goal", "process", "actor", "org_unit", "role", "problem", "info_set", "product", "component", "feature", "tech_component", "concept", "attribute", "biz_actor", "biz_process", "biz_service", "biz_function", "biz_event", "biz_role", "biz_object", "app_component", "app_service", "app_function", "data_object", "artifact", "device", "node", "system_software", "tech_service", "tech_function", "tech_interface", "comm_network", "equipment", "facility", "junction", "grouping", "location", "driver", "stakeholder", "assessment", "principle", "requirement", "constraint", "outcome", "event", "gateway"]
                },
                "name": {"type": "string", "maxLength": 200},
                "description": {"type": ["string", "null"]},
                "layer": {"type": ["string", "null"], "enum": ["goals", "processes", "actors", "technical", "business", "application", "technology", "physical", "motivation", "implementation", None]},
                "submodel": {"type": ["string", "null"], "enum": ["goals", "processes", "actors", "technical", None]},
                "attributes": {"type": "object", "additionalProperties": True}
            }
        },
        "relationship": {
            "type": "object",
            "required": ["id", "sourceId", "targetId", "frameworkType", "canonicalType", "attributes"],
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "sourceId": {"type": "string", "format": "uuid"},
                "targetId": {"type": "string", "format": "uuid"},
                "frameworkType": {"type": "string"},
                "canonicalType": {
                    "type": "string",
                    "enum": ["part_of", "works_in", "refines", "hinders", "responsible_for", "decomposes_to", "input", "output", "composes", "offers", "supports", "includes", "triggers", "aggregates", "realizes", "serves", "flows", "assigns", "associates", "specializes", "access_read", "access_write", "access_rw"]
                },
                "name": {"type": ["string", "null"]},
                "description": {"type": ["string", "null"]},
                "attributes": {"type": "object", "additionalProperties": True}
            }
        },
        "diagram": {
            "type": "object",
            "required": ["id", "name", "type", "nodes", "connections"],
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "name": {"type": "string"},
                "type": {"type": "string"},
                "viewpoint": {"type": ["string", "null"]},
                "nodes": {"type": "array", "items": {"type": "object", "required": ["elementId", "x", "y", "width", "height"], "properties": {"elementId": {"type": "string", "format": "uuid"}, "x": {"type": "number"}, "y": {"type": "number"}, "width": {"type": "number", "minimum": 10}, "height": {"type": "number", "minimum": 10}}}},
                "connections": {"type": "array", "items": {"type": "object", "required": ["relationshipId", "waypoints"], "properties": {"relationshipId": {"type": "string", "format": "uuid"}, "waypoints": {"type": "array", "items": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}}}}}
            }
        },
        "folder": {
            "type": "object",
            "required": ["id", "name", "type", "elementIds"],
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "name": {"type": "string"},
                "type": {"type": "string", "enum": ["strategy", "business", "application", "technology", "motivation", "implementation_migration", "other", "relations"]},
                "elementIds": {"type": "array", "items": {"type": "string", "format": "uuid"}}
            }
        }
    }
}


# 4EM Stage 2b Prompt
ALLOWED_4EM_ELEMENT_TYPES = [
    "Goal", "Process", "Actor", "Organizational Unit", "Role", "Problem",
    "Information Set", "Unspecific/Product/Service", "Component", "Feature",
    "IS Technical Component", "Concept", "Attribute"
]

ALLOWED_4EM_RELATIONSHIP_TYPES = [
    "part of", "works in", "refined by (AND)", "Hinders", "is responsible for",
    "decomposed into", "Input", "Output", "consists of", "offers", "supports",
    "refined by", "included in"
]

STAGE_2B_TEMPLATE_4EM = (
    "You are a 4EM (Four Essential Model) modeling expert. Convert the query into a structured canonical model covering ALL FOUR 4EM sub-models.\n"
    "\n"
    "Framework: 4EM\n"
    'Query: "{rewritten_query}"\n'
    "\n"
    "=== CRITICAL RULE: YOU MUST COVER ALL FOUR 4EM SUB-MODELS ===\n"
    "1. GOALS sub-model (submodel='goals'): corporate Goals and Problems\n"
    "2. PROCESSES sub-model (submodel='processes'): Business Processes and their decomposition\n"
    "3. ACTORS sub-model (submodel='actors'): Actors, Organizational Units, Roles\n"
    "4. TECHNICAL sub-model (submodel='technical'): Information Sets, Products, Components, Features, IS Technical Components, Concepts, Attributes\n"
    "\n"
    "Allowed frameworkType values:\n"
    "- goals sub-model: Goal, Problem\n"
    "- processes sub-model: Process\n"
    "- actors sub-model: Actor, Organizational Unit, Role\n"
    "- technical sub-model: Information Set, Unspecific/Product/Service, Component, Feature, IS Technical Component, Concept, Attribute\n"
    "\n"
    "Allowed canonicalType values (map 1:1 from frameworkType):\n"
    "  Goal->goal, Problem->problem, Process->process, Actor->actor,\n"
    "  Organizational Unit->org_unit, Role->role, Information Set->info_set,\n"
    "  Unspecific/Product/Service->product, Component->component, Feature->feature,\n"
    "  IS Technical Component->tech_component, Concept->concept, Attribute->attribute\n"
    "\n"
    "Allowed relationship types (canonicalType):\n"
    "- part_of, works_in, refines, hinders, responsible_for, decomposes_to,\n"
    "  input, output, composes, offers, supports, includes\n"
    "\n"
    "=== MANDATORY RELATIONSHIP RULES (EVERY ELEMENT MUST BE CONNECTED) ===\n"
    "- EVERY element in the model MUST participate in at least ONE relationship. No element may be isolated.\n"
    "- Goal --refines--> Process (goal drives the process)\n"
    "- Goal --refines--> Goal (goal hierarchy)\n"
    "- Problem --hinders--> Goal (problem obstructs a goal)\n"
    "- Actor/Role/Organizational Unit --responsible_for--> Process\n"
    "- Actor/Role --works_in--> Organizational Unit\n"
    "- Process --decomposes_to--> Process (process decomposition)\n"
    "- Information Set --input--> Process\n"
    "- Process --output--> Information Set\n"
    "- IS Technical Component --supports--> Process\n"
    "- Product --composes--> Component (product consists of components)\n"
    "- Component --part_of--> Product / Component --part_of--> Component\n"
    "- Product --offers--> Feature\n"
    "- Concept --includes--> Information Set\n"
    "- Organizational Unit --part_of--> Organizational Unit (org hierarchy)\n"
    "\n"
    "=== MANDATORY EXAMPLE (follow this exact structure) ===\n"
    "{{\n"
    '  "elements": [\n'
    '    {{"id": "GEN-UUID", "frameworkType": "Goal", "canonicalType": "goal", "name": "Improve Order Efficiency", "description": "Corporate goal to streamline order processing", "layer": "goals", "submodel": "goals", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "Problem", "canonicalType": "problem", "name": "Slow Order Fulfillment", "description": "Orders take too long due to manual steps", "layer": "goals", "submodel": "goals", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "Process", "canonicalType": "process", "name": "Order Processing", "description": "End-to-end order lifecycle process", "layer": "processes", "submodel": "processes", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "Process", "canonicalType": "process", "name": "Payment Processing", "description": "Authorize and collect payment", "layer": "processes", "submodel": "processes", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "Actor", "canonicalType": "actor", "name": "Customer", "description": "End customer placing orders", "layer": "actors", "submodel": "actors", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "Role", "canonicalType": "role", "name": "Sales Team", "description": "Handles orders and inquiries", "layer": "actors", "submodel": "actors", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "Organizational Unit", "canonicalType": "org_unit", "name": "E-commerce Company", "description": "Company operating the platform", "layer": "actors", "submodel": "actors", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "Information Set", "canonicalType": "info_set", "name": "Order Data", "description": "Order records and statuses", "layer": "technical", "submodel": "technical", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "IS Technical Component", "canonicalType": "tech_component", "name": "E-commerce Platform", "description": "Online storefront system", "layer": "technical", "submodel": "technical", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "IS Technical Component", "canonicalType": "tech_component", "name": "Payment Gateway", "description": "Payment authorization system", "layer": "technical", "submodel": "technical", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "IS Technical Component", "canonicalType": "tech_component", "name": "ERP System", "description": "Enterprise resource planning system", "layer": "technical", "submodel": "technical", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "IS Technical Component", "canonicalType": "tech_component", "name": "Inventory Management System", "description": "Stock and inventory tracking system", "layer": "technical", "submodel": "technical", "attributes": {{}}}}\n'
    '  ],\n'
    '  "relationships": [\n'
    '    {{"id": "GEN-UUID", "sourceId": "Improve Order Efficiency", "targetId": "Order Processing", "frameworkType": "refined by (AND)", "canonicalType": "refines", "name": "", "description": "Goal drives the process", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Slow Order Fulfillment", "targetId": "Improve Order Efficiency", "frameworkType": "Hinders", "canonicalType": "hinders", "name": "", "description": "Problem obstructs the goal", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Order Processing", "targetId": "Payment Processing", "frameworkType": "decomposed into", "canonicalType": "decomposes_to", "name": "", "description": "Order processing decomposes into payment processing", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Sales Team", "targetId": "Order Processing", "frameworkType": "is responsible for", "canonicalType": "responsible_for", "name": "", "description": "Sales team owns order processing", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Sales Team", "targetId": "E-commerce Company", "frameworkType": "works in", "canonicalType": "works_in", "name": "", "description": "Sales team works in the company", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Customer", "targetId": "E-commerce Company", "frameworkType": "works in", "canonicalType": "works_in", "name": "", "description": "Customer interacts with the company", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Order Data", "targetId": "Order Processing", "frameworkType": "Input", "canonicalType": "input", "name": "", "description": "Order data feeds the process", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Order Processing", "targetId": "Order Data", "frameworkType": "Output", "canonicalType": "output", "name": "", "description": "Process produces order data", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "E-commerce Platform", "targetId": "Order Processing", "frameworkType": "supports", "canonicalType": "supports", "name": "", "description": "Platform supports the order process", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Payment Gateway", "targetId": "Payment Processing", "frameworkType": "supports", "canonicalType": "supports", "name": "", "description": "Payment gateway supports payment processing", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "ERP System", "targetId": "Order Processing", "frameworkType": "supports", "canonicalType": "supports", "name": "", "description": "ERP supports order processing", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Inventory Management System", "targetId": "Order Processing", "frameworkType": "supports", "canonicalType": "supports", "name": "", "description": "Inventory system supports order processing", "attributes": {{}}}}\n'
    '  ]\n'
    "}}\n"
    "\n"
    "=== MANDATORY REQUIREMENTS ===\n"
    "1. Generate AT LEAST 25-40 elements covering ALL FOUR sub-models (goals, processes, actors, technical)\n"
    "2. GOALS: minimum 2 Goals and 1 Problem — all with submodel='goals'\n"
    "If the query mentions these processes, you MUST include them as separate Process elements (submodel='processes'):\n"
    "- Product Management / Product Catalog Management\n"
    "- Order Processing / Order Management / Order Fulfillment\n"
    "- Payment Processing / Payment Authorization / Payment Collection\n"
    "- Inventory Management / Stock Management / Stock Check\n"
    "- Shipping / Logistics / Delivery / Fulfillment\n"
    "- Returns / Return Processing / Refund Processing\n"
    "- Customer Support / Complaint Handling / Inquiry Resolution\n"
    "- Supplier Management / Procurement\n"
    "\n"
    "=== EXPLICIT ACTOR/ROLE CHECKLIST ===\n"
    "If the query mentions these organizational units, you MUST include them as separate Actor/Role/Organizational Unit elements (submodel='actors'):\n"
    "- Customers (Actor)\n"
    "- Suppliers (Actor)\n"
    "- Sales Teams / Sales Department (Role)\n"
    "- Warehouse Staff / Warehouse Department (Role)\n"
    "- Finance Teams / Finance Department (Role)\n"
    "- Customer Support Teams (Role)\n"
    "- Logistics Teams (Role)\n"
    "- The company itself (Organizational Unit)\n"
    "\n"
    "=== EXPLICIT IT SYSTEM CHECKLIST ===\n"
    "If the query mentions these IT systems, you MUST include them as separate IS Technical Component elements (submodel='technical'):\n"
    "- E-commerce Platform / Online Platform\n"
    "- CRM System\n"
    "- ERP System\n"
    "- Payment Gateway\n"
    "- Inventory Management System\n"
)


# BPMN Stage 2b Prompt
ALLOWED_BPMN_ELEMENT_TYPES = [
    "StartEvent", "EndEvent", "Task", "UserTask", "ServiceTask", "ScriptTask", "BusinessRuleTask",
    "ExclusiveGateway", "ParallelGateway", "InclusiveGateway", "SequenceFlow", "MessageFlow",
    "DataObject", "DataStore", "Participant", "Lane"
]

ALLOWED_BPMN_RELATIONSHIP_TYPES = [
    "SequenceFlow", "MessageFlow", "DataInputAssociation", "DataOutputAssociation"
]

STAGE_2B_TEMPLATE_BPMN = (
    "You are an expert ArchiMate 3.2 Enterprise Architect. Convert the query into a rich, multi-layered canonical model.\n"
    "\n"
    "Framework: BPMN mapped to ArchiMate layers\n"
    'Query: "{rewritten_query}"\n'
    "\n"
    "=== DYNAMIC SCOPE INTERPRETATION ===\n"
    "Before generating the model, analyze the user's query to determine their intent:\n"
    "1. STRICT EXTRACTION MODE: If the user's query is highly specific, lists explicit elements, or explicitly constrains the scope (e.g., 'only the Business Layer', 'capture the organization structure'), you MUST act as a strict parser. Only create elements and relationships that are explicitly mentioned or directly implied by the text. DO NOT extrapolate missing layers or add filler elements. Only use the layers requested.\n"
    "2. EXTRAPOLATION MODE: If the query is high-level, conceptual, or asks for a general design across layers, you MUST extrapolate a full multi-layered architecture.\n"
    "\n"
    "=== EXTRAPOLATION MODE GUIDELINES (Ignore in Strict Extraction Mode) ===\n"
    "When in extrapolation mode, every business process model in ArchiMate MUST include elements from FOUR layers:\n"
    "1. MOTIVATION layer: Goals, drivers, stakeholders that justify the process\n"
    "2. BUSINESS layer: The process actors, steps, events, gateways, and services\n"
    "3. APPLICATION layer: The IT systems and applications that support the processes\n"
    "4. TECHNOLOGY layer: The infrastructure (servers, networks) supporting those applications\n"
    "\n"
    "Valid layer values: strategy | business | application | technology | physical | motivation | implementation_migration | other\n"
    "\n"
    "=== LAYER-TO-CANONICAL-TYPE MAPPING ===\n"
    "MOTIVATION layer elements use canonicalType:\n"
    "  goal, driver, stakeholder, assessment, principle, requirement, constraint, outcome\n"
    "\n"
    "BUSINESS layer elements use canonicalType:\n"
    "  biz_event (StartEvent/EndEvent)\n"
    "  biz_process (Task, UserTask, ServiceTask, ScriptTask, BusinessRuleTask)\n"
    "  biz_actor (Participant, Lane, BusinessActor)\n"
    "  biz_role (BusinessRole)\n"
    "  biz_service (BusinessService)\n"
    "  junction (ExclusiveGateway, ParallelGateway, InclusiveGateway)\n"
    "\n"
    "APPLICATION layer elements use canonicalType:\n"
    "  app_component (ApplicationComponent — the IT application itself)\n"
    "  app_service (ApplicationService — the service exposed by the app)\n"
    "  app_function (ApplicationFunction)\n"
    "  data_object (DataObject, DataStore)\n"
    "\n"
    "TECHNOLOGY layer elements use canonicalType:\n"
    "  node (Node — server)\n"
    "  device (Device — hardware)\n"
    "  system_software (SystemSoftware — OS, middleware, DBMS)\n"
    "  tech_service (TechnologyService)\n"
    "  comm_network (CommunicationNetwork)\n"
    "\n"
    "=== RELATIONSHIP TYPE MAPPINGS ===\n"
    "  composes — 'composed of', 'consists of', 'contains' (CompositionRelationship)\n"
    "  aggregates — 'aggregates', 'includes' (AggregationRelationship)\n"
    "  assigns — 'assigned to', 'allocated to', 'located at', 'hosts' (AssignmentRelationship)\n"
    "  serves — 'serves', 'supports', 'used by' (ServingRelationship)\n"
    "  realizes — 'realizes', 'fulfils', 'accomplishes' (RealizationRelationship)\n"
    "  flows — 'flows to', 'transfers to', 'sequence flow', 'sends data to' (FlowRelationship)\n"
    "  triggers — 'triggers', 'initiates', 'starts' (TriggeringRelationship)\n"
    "  associates — 'associated with', 'connected to' (AssociationRelationship)\n"
    "  specializes — 'specialized by', 'variant of', 'is a' (SpecializationRelationship)\n"
    "  access_read — 'accesses via read', 'reads' (AccessRelationship read)\n"
    "  access_write — 'accesses via write', 'writes' (AccessRelationship write)\n"
    "\n"
    "CRITICAL: If the query only describes an organization structure, functional decomposition, or technical structure, DO NOT hallucinate StartEvent/EndEvent dummy processes or dummy flows. Only model the exact elements and relationships stated.\n"
    "\n"
    "=== STRICT EXTRACTION EXAMPLE (Organization Structure) ===\n"
    "If query is: 'The Business Actor Arche is composed of Front Office and Back Office. Location Hamburg aggregates Front Office.'\n"
    "{{\n"
    '  "elements": [\n'
    '    {{"id": "GEN-UUID", "frameworkType": "BusinessActor", "canonicalType": "biz_actor", "name": "Arche", "description": "Arche business actor", "layer": "business", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "BusinessActor", "canonicalType": "biz_actor", "name": "Front Office", "description": "Front Office business actor", "layer": "business", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "BusinessActor", "canonicalType": "biz_actor", "name": "Back Office", "description": "Back Office business actor", "layer": "business", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "Location", "canonicalType": "location", "name": "Hamburg", "description": "Hamburg location", "layer": "business", "submodel": null, "attributes": {{}}}}\n'
    '  ],\n'
    '  "relationships": [\n'
    '    {{"id": "GEN-UUID", "sourceId": "Arche", "targetId": "Front Office", "frameworkType": "CompositionRelationship", "canonicalType": "composes", "name": "", "description": "Arche is composed of Front Office", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Arche", "targetId": "Back Office", "frameworkType": "CompositionRelationship", "canonicalType": "composes", "name": "", "description": "Arche is composed of Back Office", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Hamburg", "targetId": "Front Office", "frameworkType": "AggregationRelationship", "canonicalType": "aggregates", "name": "", "description": "Hamburg aggregates Front Office", "attributes": {{}}}}\n'
    '  ]\n'
    "}}\n"
    "\n"
    "=== MANDATORY MULTI-LAYER EXAMPLE (Use pattern when in Extrapolation Mode) ===\n"
    "{{\n"
    '  "elements": [\n'
    '    {{"id": "GEN-UUID", "frameworkType": "Goal", "canonicalType": "goal", "name": "Improve Order Efficiency", "description": "Corporate goal to streamline order processing", "layer": "motivation", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "Stakeholder", "canonicalType": "stakeholder", "name": "Customer", "description": "End customer placing the order", "layer": "motivation", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "Driver", "canonicalType": "driver", "name": "Competitive Pressure", "description": "Market pressure to deliver orders faster", "layer": "motivation", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "StartEvent", "canonicalType": "biz_event", "name": "Order Received", "description": "Customer places an order", "layer": "business", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "Task", "canonicalType": "biz_process", "name": "Validate Payment", "description": "Verify payment details and authorize charge", "layer": "business", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "ExclusiveGateway", "canonicalType": "junction", "name": "Payment Valid?", "description": "Decision: payment approved or rejected", "layer": "business", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "EndEvent", "canonicalType": "biz_event", "name": "Order Complete", "description": "Order successfully fulfilled", "layer": "business", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "BusinessService", "canonicalType": "biz_service", "name": "Payment Processing Service", "description": "Business service for payment processing", "layer": "business", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "ApplicationComponent", "canonicalType": "app_component", "name": "Payment Gateway Application", "description": "Software handling payment authorization", "layer": "application", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "ApplicationService", "canonicalType": "app_service", "name": "Payment Authorization API", "description": "REST API for authorizing payments", "layer": "application", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "ApplicationComponent", "canonicalType": "app_component", "name": "Order Management System", "description": "Application managing order lifecycle", "layer": "application", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "DataObject", "canonicalType": "data_object", "name": "Order Record", "description": "Persistent record of order status", "layer": "application", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "Node", "canonicalType": "node", "name": "Application Server", "description": "Server running application components", "layer": "technology", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "SystemSoftware", "canonicalType": "system_software", "name": "Database Server", "description": "DBMS persisting order and payment records", "layer": "technology", "submodel": null, "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "frameworkType": "CommunicationNetwork", "canonicalType": "comm_network", "name": "Enterprise Network", "description": "Network connecting all systems", "layer": "technology", "submodel": null, "attributes": {{}}}}\n'
    '  ],\n'
    '  "relationships": [\n'
    '    {{"id": "GEN-UUID", "sourceId": "Improve Order Efficiency", "targetId": "Validate Payment", "frameworkType": "TriggeringRelationship", "canonicalType": "triggers", "name": "", "description": "Goal motivates business process", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Customer", "targetId": "Order Received", "frameworkType": "AssociationRelationship", "canonicalType": "associates", "name": "", "description": "Stakeholder triggers start event", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Order Received", "targetId": "Validate Payment", "frameworkType": "SequenceFlow", "canonicalType": "flows", "name": "", "description": "", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Validate Payment", "targetId": "Payment Valid?", "frameworkType": "SequenceFlow", "canonicalType": "flows", "name": "", "description": "", "attributes": {{}}}},\n'
    '    {{ "id": "GEN-UUID", "sourceId": "Payment Valid?", "targetId": "Order Complete", "frameworkType": "SequenceFlow", "canonicalType": "flows", "name": "Approved", "description": "", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Payment Gateway Application", "targetId": "Payment Processing Service", "frameworkType": "RealizationRelationship", "canonicalType": "realizes", "name": "", "description": "App realizes business service", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Payment Authorization API", "targetId": "Validate Payment", "frameworkType": "ServingRelationship", "canonicalType": "serves", "name": "", "description": "App service supports business process", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Order Management System", "targetId": "Order Record", "frameworkType": "AggregationRelationship", "canonicalType": "aggregates", "name": "", "description": "Application manages data object", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Application Server", "targetId": "Payment Gateway Application", "frameworkType": "AssignmentRelationship", "canonicalType": "assigns", "name": "", "description": "Server hosts the application", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Application Server", "targetId": "Order Management System", "frameworkType": "AssignmentRelationship", "canonicalType": "assigns", "name": "", "description": "Server hosts the application", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Database Server", "targetId": "Order Record", "frameworkType": "AssignmentRelationship", "canonicalType": "assigns", "name": "", "description": "Database persists data", "attributes": {{}}}},\n'
    '    {{"id": "GEN-UUID", "sourceId": "Enterprise Network", "targetId": "Application Server", "frameworkType": "AssignmentRelationship", "canonicalType": "assigns", "name": "", "description": "Network connects infrastructure", "attributes": {{}}}}\n'
    '  ]\n'
    "}}\n"
    "\n"
    "=== GENERAL REQUIREMENTS (Apply to all modes) ===\n"
    "1. Use element NAMES exactly as sourceId/targetId values in relationships\n"
    "2. Every element must have a meaningful non-empty description\n"
    "3. submodel must be null for all BPMN elements\n"
    "4. Output ONLY valid JSON. No markdown, no explanations.\n"
    "\n"
    "=== EXTRAPOLATION MANDATES (Ignore in Strict Extraction Mode) ===\n"
    "- Generate AT LEAST 25-40 elements spanning ALL FOUR LAYERS (Motivation, Business, Application, Technology)\n"
    "- MOTIVATION: minimum 2 Goals, 2 Stakeholders, 1 Driver — all with layer='motivation'\n"
    "- BUSINESS: Create a SEPARATE element for EACH distinct process mentioned. Also create StartEvent/EndEvent for each major process flow.\n"
    "- APPLICATION: Create an ApplicationComponent for EACH IT system mentioned. Create ApplicationServices for key APIs. Create DataObjects for key business entities.\n"
    "- TECHNOLOGY: minimum 2 Nodes, 1 SystemSoftware, 1 CommunicationNetwork.\n"
    "- Cross-layer relationships are MANDATORY — connect every layer to adjacent layers.\n"
    "\n"
    "=== EXPLICIT PROCESS COVERAGE CHECKLIST ===\n"
    "If the query mentions these processes, you MUST include them as separate biz_process elements:\n"
    "- Product Management / Product Catalog Management\n"
    "- Order Processing / Order Management / Order Fulfillment\n"
    "- Payment Processing / Payment Authorization / Payment Collection\n"
    "- Inventory Management / Stock Management / Stock Check\n"
    "- Shipping / Logistics / Delivery / Fulfillment\n"
    "- Returns / Return Processing / Refund Processing\n"
    "- Customer Support / Complaint Handling / Inquiry Resolution\n"
    "- Supplier Management / Procurement\n"
    "\n"
    "=== EXPLICIT ACTOR/ROLE CHECKLIST ===\n"
    "If the query mentions these organizational units, you MUST include them as separate biz_actor/biz_role elements:\n"
    "- Customers (biz_actor, layer='business')\n"
    "- Suppliers (biz_actor, layer='business')\n"
    "- Sales Teams / Sales Department (biz_role, layer='business')\n"
    "- Warehouse Staff / Warehouse Department (biz_role, layer='business')\n"
    "- Finance Teams / Finance Department (biz_role, layer='business')\n"
    "- Customer Support Teams (biz_role, layer='business')\n"
    "- Logistics Teams (biz_role, layer='business')\n"
    "\n"
    "=== EXPLICIT APPLICATION SYSTEM CHECKLIST ===\n"
    "If the query mentions these IT systems, you MUST include them as separate app_component elements:\n"
    "- E-commerce Platform / Online Platform (app_component, layer='application')\n"
    "- CRM System (app_component, layer='application')\n"
    "- ERP System (app_component, layer='application')\n"
    "- Payment Gateway (app_component, layer='application')\n"
    "- Inventory Management System (app_component, layer='application')\n"
)


# Canonical type mappings
CANONICAL_TYPE_MAP_4EM = {
    "Goal": "goal",
    "Process": "process",
    "Actor": "actor",
    "Organizational Unit": "org_unit",
    "Role": "role",
    "Problem": "problem",
    "Information Set": "info_set",
    "Unspecific/Product/Service": "product",
    "Component": "component",
    "Feature": "feature",
    "IS Technical Component": "tech_component",
    "Concept": "concept",
    "Attribute": "attribute",
}

# 4EM frameworkType -> submodel
SUBMODEL_MAP_4EM = {
    "Goal": "goals",
    "Process": "processes",
    "Actor": "actors",
    "Organizational Unit": "actors",
    "Role": "actors",
    "Problem": "goals",
    "Information Set": "technical",
    "Unspecific/Product/Service": "technical",
    "Component": "technical",
    "Feature": "technical",
    "IS Technical Component": "technical",
    "Concept": "technical",
    "Attribute": "technical",
}

# 4EM canonical relationship types (using 4EM unified types)
CANONICAL_RELATIONSHIP_MAP_4EM = {
    "part of": "part_of",
    "works in": "works_in",
    "refined by (AND)": "refines",
    "Hinders": "hinders",
    "is responsible for": "responsible_for",
    "decomposed into": "decomposes_to",
    "Input": "input",
    "Output": "output",
    "consists of": "composes",
    "offers": "offers",
    "supports": "supports",
    "refined by": "refines",
    "included in": "includes",
}

# BPMN frameworkType -> canonicalType (unified canonical types)
CANONICAL_TYPE_MAP_BPMN = {
    # Strategy & Motivation layer
    "Goal": "goal",
    "Outcome": "outcome",
    "Principle": "principle",
    "Requirement": "requirement",
    "Constraint": "constraint",
    "Value": "value",
    "Stakeholder": "stakeholder",
    "Driver": "driver",
    "Assessment": "assessment",
    # Business layer
    "StartEvent": "biz_event",
    "EndEvent": "biz_event",
    "Task": "biz_process",
    "UserTask": "biz_process",
    "ServiceTask": "biz_process",
    "ScriptTask": "biz_process",
    "BusinessRuleTask": "biz_process",
    "ExclusiveGateway": "junction",
    "ParallelGateway": "junction",
    "InclusiveGateway": "junction",
    "SequenceFlow": "flows",
    "MessageFlow": "flows",
    "DataObject": "data_object",
    "DataStore": "data_object",
    "Participant": "biz_actor",
    "Lane": "biz_role",
    "BusinessService": "biz_service",
    # Application layer
    "ApplicationComponent": "app_component",
    "ApplicationService": "app_service",
    "ApplicationFunction": "app_function",
    # Technology layer
    "Node": "node",
    "Device": "device",
    "SystemSoftware": "system_software",
    "TechnologyService": "tech_service",
    "CommunicationNetwork": "comm_network",
    # Physical / Other layer
    "Location": "location",
    "Artifact": "artifact",
    "Equipment": "equipment",
    "Facility": "facility",
    # Additional BPMN/ArchiMate mappings
    "Pool": "biz_actor",
    "SubProcess": "biz_process",
    "ManualTask": "biz_process",
    "SendTask": "biz_process",
    "ReceiveTask": "biz_process",
    "CallActivity": "biz_process",
    "IntermediateEvent": "biz_event",
    "IntermediateCatchEvent": "biz_event",
    "IntermediateThrowEvent": "biz_event",
    "BoundaryEvent": "biz_event",
    "EventBasedGateway": "junction",
    "ComplexGateway": "junction",
    "Group": "grouping",
    "Grouping": "grouping",
    "TextAnnotation": "biz_object",
    "Association": "associates",
}
