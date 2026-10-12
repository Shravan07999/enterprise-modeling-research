import xml.etree.ElementTree as ET

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select

from api.export import router as export_router
from api.export import (
    _normalize_and_validate_adl,
    _serialize_adl,
    _normalize_and_validate_archimate,
    _serialize_archimate,
    _repair_adl,
    _repair_archimate,
    _validate_serialized_adl,
    _infer_adl_class,
    _infer_archimate_type,
    ExportException,
)
from database import get_session, _ensure_column
from models import ExportLog

# Isolated app instance (separate from test_api.py so overrides never clash)
sqlite_url = "sqlite:///database_export_test.db"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    # Apply lightweight migrations so stale test databases gain new columns
    _ensure_column(engine, "executionhistory", "metrics_json TEXT")
    _ensure_column(engine, "exportlog", "prompt_tokens INTEGER")
    _ensure_column(engine, "exportlog", "completion_tokens INTEGER")


def get_session_override():
    with Session(engine) as session:
        yield session


app = FastAPI()
app.include_router(export_router)
app.dependency_overrides[get_session] = get_session_override

client = TestClient(app)


def setup_module(module):
    create_db_and_tables()


VALID_ADL_MODEL = {
    "model_name": "4EM General Model - Test",
    "entities": [
        {"class": "Organizational Unit", "name": "The Company"},
        {"class": "Role", "name": "Product Owner"},
        {
            "class": "Goal",
            "name": "Energy Efficiency",
            "attributes": {"Criticality": "High", "Priority": "High"},
        },
        {"class": "Process", "name": "Product Innovation"},
        {"class": "Information Set", "name": "Customer Survey"},
    ],
    "relations": [
        {"type": "works in", "source": "Product Owner", "target": "The Company"},
        {"type": "is responsible for", "source": "Product Owner", "target": "Product Innovation"},
        {"type": "refined by (AND)", "source": "Energy Efficiency", "target": "Product Innovation"},
        {"type": "Input", "source": "Product Innovation", "target": "Customer Survey"},
    ],
}

VALID_ARCHIMATE_MODEL = {
    "model_name": "Arche 2",
    "elements": [
        {"type": "BusinessActor", "name": "Operations Manager", "layer": "Business"},
        {"type": "BusinessProcess", "name": "Pay", "layer": "Business"},
        {"type": "ApplicationComponent", "name": "Payment App", "layer": "Application"},
        {"type": "SystemSoftware", "name": "DB", "layer": "Technology"},
        {"type": "Goal", "name": "Efficient Ops", "layer": "Motivation"},
    ],
    "relationships": [
        {"type": "AssignmentRelationship", "source": "Operations Manager", "target": "Pay"},
        {"type": "ServingRelationship", "source": "Payment App", "target": "Pay"},
        {"type": "RealizationRelationship", "source": "DB", "target": "Payment App"},
        {"type": "RealizationRelationship", "source": "Pay", "target": "Efficient Ops"},
    ],
}

STEPS = [
    {
        "step": 1,
        "prompt_name": "Context Extraction & Normalization",
        "type": "GENERATION",
        "result": "actors: [Product Owner], goals: [Energy Efficiency]",
    },
    {
        "step": 2,
        "prompt_name": "4EM Goal Model",
        "type": "GENERATION",
        "result": "Goal hierarchy with refinements.",
    },
    {
        "step": 3,
        "prompt_name": "4EM Process Model",
        "type": "GENERATION",
        "result": "Processes and information sets.",
    },
]

# Returned by _llm_structured_json monkeypatches alongside the model payload.
FAKE_LLM_METRICS = {
    "latency_seconds": 1.25,
    "prompt_tokens": 1000,
    "completion_tokens": 500,
    "model": "gpt-4o",
}


# ---------------------------------------------------------------------------
# Serializer + validator unit tests
# ---------------------------------------------------------------------------


def test_adl_validation_accepts_valid_model():
    assert _normalize_and_validate_adl(VALID_ADL_MODEL) == []


def test_adl_validation_isolated_entity_is_non_blocking():
    model = {
        "entities": [
            {"class": "Goal", "name": "G1"},
            {"class": "Process", "name": "P1"},
            {"class": "Process", "name": "P2"},
        ],
        "relations": [{"type": "decomposed into", "source": "P1", "target": "P2"}],
    }
    assert _normalize_and_validate_adl(model) == []


def test_adl_validation_dangling_relation():
    model = {
        "entities": [{"class": "Goal", "name": "G1"}],
        "relations": [{"type": "refined by (AND)", "source": "G1", "target": "Ghost"}],
    }
    problems = _normalize_and_validate_adl(model)
    assert any("target not found" in p for p in problems)


def test_adl_validation_unknown_class_and_relation():
    model = {
        "entities": [{"class": "Unicorn", "name": "X"}, {"class": "Goal", "name": "G1"}],
        "relations": [{"type": "teleports to", "source": "X", "target": "G1"}],
    }
    problems = _normalize_and_validate_adl(model)
    assert any("Unknown 4EM class" in p for p in problems)
    assert any("Unknown 4EM relation type" in p for p in problems)


def test_adl_validation_duplicate_relation_pair():
    model = {
        "entities": [
            {"class": "Process", "name": "Product Innovation"},
            {"class": "Information Set", "name": "Customer Survey"},
        ],
        "relations": [
            {"type": "Input", "source": "Product Innovation", "target": "Customer Survey"},
            {"type": "Output", "source": "Product Innovation", "target": "Customer Survey"},
        ],
    }
    problems = _normalize_and_validate_adl(model)
    assert any("already related" in p and "Product Innovation" in p for p in problems)


def test_adl_validation_reversed_duplicate_relation_pair():
    model = {
        "entities": [
            {"class": "Process", "name": "Product Innovation"},
            {"class": "Information Set", "name": "Customer Survey"},
        ],
        "relations": [
            {"type": "Input", "source": "Product Innovation", "target": "Customer Survey"},
            {"type": "Output", "source": "Customer Survey", "target": "Product Innovation"},
        ],
    }
    problems = _normalize_and_validate_adl(model)
    assert any("already related" in p for p in problems)


def test_adl_serializer_golden_structure():
    text = _serialize_adl("Test", VALID_ADL_MODEL)
    assert "VERSION <5.1>" in text
    assert "TYPE <4EM General Model>" in text
    assert "BUSINESS PROCESS MODEL <" in text
    assert ": <4EM-Rostock Library_87_22_04_01>" in text
    assert text.count("INSTANCE <") == 5
    assert text.count("RELATION <4EM_Relation>") == 4
    assert text.count("//END") == 9  # 5 instances + 4 relations
    assert "NODE x:1cm y:1cm w:4cm h:1.5cm index:1" in text
    assert 'VALUE "refined by (AND)"' in text
    assert "\tATTRIBUTE <Criticality>\n\tVALUE \"High\"" in text


def test_adl_hidden_attribute_is_quoted():
    # Regression: hidden_attribute must render as "VALUE \"\"" (quoted empty string),
    # never as a bare "VALUE" line. The 4EM Toolkit parser rejects the latter with a
    # "syntax error" when opening an exported model (see the working reference_model.adl).
    text = _serialize_adl("Test", VALID_ADL_MODEL)
    assert "ATTRIBUTE <hidden_attribute>" in text
    assert "\tATTRIBUTE <hidden_attribute>\n\tVALUE \"\"" in text
    assert "\tATTRIBUTE <hidden_attribute>\n\tVALUE\n" not in text


def test_adl_numeric_attrs_are_quoted_for_word_values():
    # Regression: Execution Time / Complexity / Quantity must NEVER render as an
    # unquoted bare word (e.g. "VALUE Long"), which the 4EM Toolkit rejects with a
    # "syntax error". LLM-supplied words must be quoted: VALUE "Long".
    model = {
        "entities": [
            {
                "class": "Process",
                "name": "Product innovation process",
                "attributes": {"Execution Time": "Long", "Complexity": "High"},
            },
            {
                "class": "Component",
                "name": "Indoor Module",
                "attributes": {"Quantity": "many"},
            },
            {
                "class": "IS Technical Component",
                "name": "Database System",
                "attributes": {"Quantity": 3},
            },
        ],
        "relations": [],
    }
    text = _serialize_adl("Test", model)
    assert "\tATTRIBUTE <Execution Time>\n\tVALUE \"Long\"" in text
    assert "\tATTRIBUTE <Complexity>\n\tVALUE \"High\"" in text
    assert "\tATTRIBUTE <Quantity>\n\tVALUE \"many\"" in text
    assert "\tATTRIBUTE <Quantity>\n\tVALUE \"3\"" in text
    # No unquoted non-numeric value may ever appear.
    assert "\n\tVALUE Long" not in "\n" + text
    assert "\n\tVALUE High" not in "\n" + text
    assert "\n\tVALUE many" not in "\n" + text


def test_adl_numeric_attrs_default_to_quoted_zero():
    model = {
        "entities": [
            {"class": "Process", "name": "Some Process"},
            {"class": "Component", "name": "Some Component"},
        ],
        "relations": [],
    }
    text = _serialize_adl("Test", model)
    assert "\tATTRIBUTE <Execution Time>\n\tVALUE \"0\"" in text
    assert "\tATTRIBUTE <Complexity>\n\tVALUE \"0\"" in text
    assert "\tATTRIBUTE <Quantity>\n\tVALUE \"0\"" in text


def test_adl_full_class_sweep_has_no_unquoted_values():
    # Serialize one instance of EVERY 4EM class and assert the whole document only
    # uses the three valid VALUE forms (bare for empty attrs, quoted, or numeric).
    classes = [
        ("Organizational Unit", "OU"),
        ("Role", "Role X"),
        ("Goal", "Goal X"),
        ("Problem", "Problem X"),
        ("Process", "Process X"),
        ("Information Set", "Info Set"),
        ("Unspecific/Product/Service", "Product X"),
        ("Component", "Component X"),
        ("Feature", "Feature X"),
        ("IS Technical Component", "Tech X"),
        ("Concept", "Concept X"),
        ("Attribute", "Attribute X"),
    ]
    model = {
        "entities": [{"class": cls, "name": name} for cls, name in classes],
        "relations": [],
    }
    text = _serialize_adl("Test", model)
    assert not _validate_serialized_adl(text)
    # Belt and braces: scan lines for any bare-word VALUE directly.
    import re as _re

    for i, line in enumerate(text.splitlines()):
        if _re.match(r"^\s*VALUE\s+", line):
            tail = line.split("VALUE", 1)[1].strip()
            assert tail.startswith('"') or _re.match(r"^[+-]?(\d+(\.\d*)?|\.\d+)$", tail), (
                f"unquoted non-numeric VALUE at line {i + 1}: {line!r}"
            )


def test_validate_serialized_adl_rejects_unquoted_word():
    problems = _validate_serialized_adl(
        "\tATTRIBUTE <Execution Time>\n\tVALUE Long\n"
        "\tATTRIBUTE <Complexity>\n\tVALUE High\n"
    )
    assert any("unquoted non-numeric" in p and "Execution Time" in p for p in problems)
    # Quoted and numeric forms are accepted.
    assert not _validate_serialized_adl(
        "\tATTRIBUTE <Execution Time>\n\tVALUE \"Long\"\n"
        "\tATTRIBUTE <Complexity>\n\tVALUE 5\n"
        "\tATTRIBUTE <Attributes>\n\tVALUE\n"
    )



def test_archimate_validation_accepts_valid_model():
    assert _normalize_and_validate_archimate(VALID_ARCHIMATE_MODEL) == []


def test_archimate_validation_isolated_element_is_non_blocking():
    model = {
        "elements": [
            {"type": "BusinessActor", "name": "A"},
            {"type": "BusinessActor", "name": "B"},
            {"type": "Goal", "name": "G"},
        ],
        "relationships": [{"type": "AssignmentRelationship", "source": "A", "target": "B"}],
    }
    assert _normalize_and_validate_archimate(model) == []


def test_archimate_validation_unknown_types():
    model = {
        "elements": [{"type": "FluxCapacitor", "name": "A"}, {"type": "Goal", "name": "G"}],
        "relationships": [{"type": "WormholeRelationship", "source": "A", "target": "G"}],
    }
    problems = _normalize_and_validate_archimate(model)
    assert any("Unknown ArchiMate element type" in p for p in problems)
    assert any("Unknown ArchiMate relationship type" in p for p in problems)


def test_archimate_serializer_wellformed_with_integrity():
    text = _serialize_archimate("ArchiMate", VALID_ARCHIMATE_MODEL)
    root = ET.fromstring(text)  # raises if not well-formed

    defined = {}
    for e in root.iter():
        if "id" in e.attrib:
            defined[e.attrib["id"]] = e.tag
    assert len(defined) == len([e for e in root.iter() if "id" in e.attrib]), "Duplicate ids"

    # Every referenced id (source/target/archimateElement/archimateRelationship) must exist
    for e in root.iter():
        for key in ("source", "target", "archimateElement", "archimateRelationship"):
            if key in e.attrib:
                assert e.attrib[key] in defined, f"{key} {e.attrib[key]} is undefined"

    # Exactly the 4 model relationships, all as elements with a source
    relationships = [e for e in root.iter() if e.tag.endswith("element") and "source" in e.attrib]
    assert len(relationships) == 4

    # Views present: a single comprehensive blueprint view (no per-layer diagrams)
    assert "Enterprise Blueprint" in text
    assert 'viewpoint="layered"' in text
    assert text.count("ArchimateDiagramModel") == 1
    assert "Business Architecture" not in text and "Application Architecture" not in text
    assert "Technology &amp; Physical" in text
    assert text.count('xsi:type="archimate:') >= 5


# ---------------------------------------------------------------------------
# Self-healing repair tests
# ---------------------------------------------------------------------------


def test_repair_adl_autocreates_missing_entities():
    # LLM emitted relations whose targets (goals) are missing from the entities list.
    model = {
        "model_name": "Order Fulfilment",
        "entities": [
            {"class": "Process", "name": "Order Fulfilment Process"},
            {"class": "Information Set", "name": "Order Data"},
        ],
        "relations": [
            {"type": "supports", "source": "Streamline Order Placement", "target": "Order Fulfilment Process"},
            {"type": "supports", "source": "Optimize Order Processing", "target": "Order Fulfilment Process"},
            {"type": "Input", "source": "Order Fulfilment Process", "target": "Order Data"},
        ],
    }
    data, notes = _repair_adl(model)
    names = [e["name"] for e in data["entities"]]
    assert "Streamline Order Placement" in names
    assert "Optimize Order Processing" in names
    created = [n for n in notes if n.startswith("created missing")]
    assert len(created) == 2
    assert all("(Goal)" in n for n in created)
    assert _normalize_and_validate_adl(data) == []


def test_repair_adl_fuzzy_resolves_paraphrased_name():
    model = {
        "entities": [
            {"class": "Goal", "name": "Streamline Order Placement"},
            {"class": "Process", "name": "Order Fulfilment Process"},
        ],
        "relations": [{"type": "supports", "source": "Order Placement Streamlining", "target": "Order Fulfilment Process"}],
    }
    data, notes = _repair_adl(model)
    assert len(data["entities"]) == 2
    assert any("resolved to existing entity" in n for n in notes)
    assert _normalize_and_validate_adl(data) == []


def test_repair_adl_merges_duplicate_and_drops_self_loop():
    model = {
        "entities": [
            {"class": "Process", "name": "Product Innovation"},
            {"class": "Information Set", "name": "Customer Survey"},
        ],
        "relations": [
            {"type": "Input", "source": "Product Innovation", "target": "Customer Survey"},
            {"type": "Output", "source": "Product Innovation", "target": "Customer Survey"},
            {"type": "decomposed into", "source": "Product Innovation", "target": "Product Innovation"},
        ],
    }
    data, notes = _repair_adl(model)
    assert len(data["relations"]) == 1
    assert any("merged duplicate" in n for n in notes)
    assert any("self-loop" in n for n in notes)
    assert _normalize_and_validate_adl(data) == []


def test_repair_archimate_autocreates_missing_elements():
    model = {
        "model_name": "Arche",
        "elements": [
            {"type": "BusinessProcess", "name": "Pay", "layer": "Business"},
            {"type": "ApplicationComponent", "name": "Payment App", "layer": "Application"},
        ],
        "relationships": [
            {"type": "ServingRelationship", "source": "Payment App", "target": "Pay"},
            {"type": "RealizationRelationship", "source": "Payment Database", "target": "Payment App"},
        ],
    }
    data, notes = _repair_archimate(model)
    names = [e["name"] for e in data["elements"]]
    assert "Payment Database" in names
    created = [e for e in data["elements"] if e["name"] == "Payment Database"]
    assert created and created[0]["type"] == "Artifact"
    assert any("created missing" in n for n in notes)
    assert _normalize_and_validate_archimate(data) == []


def test_repair_archimate_drops_self_loop():
    model = {
        "elements": [{"type": "BusinessActor", "name": "A"}],
        "relationships": [{"type": "AssociationRelationship", "source": "A", "target": "A"}],
    }
    data, notes = _repair_archimate(model)
    assert data["relationships"] == []
    assert any("self-loop" in n for n in notes)


def test_infer_adl_class_priority():
    assert _infer_adl_class("supports", "source", None, "Reduce Costs") == "Goal"
    assert _infer_adl_class("Input", "target", "Process", "Orders") == "Information Set"
    assert _infer_adl_class("works in", "target", "Role", "Sales Department") == "Organizational Unit"
    assert _infer_adl_class("decomposed into", "source", "Process", "Something Else") == "Process"


def test_infer_archimate_type_priority():
    assert _infer_archimate_type("RealizationRelationship", "source", None, "Order Database") == "Artifact"
    assert _infer_archimate_type("ServingRelationship", "target", "ApplicationComponent", "Backoffice System") == "ApplicationComponent"


def test_export_adl_repairs_dangling_targets(monkeypatch):
    # Exact user scenario: relation targets (goals) not present in the entities list.
    dangling_model = {
        "model_name": "E-Commerce Optimisation",
        "entities": [
            {"class": "Process", "name": "Order Fulfilment Process"},
            {"class": "Information Set", "name": "Order Data"},
        ],
        "relations": [
            {"type": "supports", "source": "Streamline Order Placement", "target": "Order Fulfilment Process"},
            {"type": "supports", "source": "Optimize Order Processing", "target": "Order Fulfilment Process"},
            {"type": "supports", "source": "Reduce Costs", "target": "Order Fulfilment Process"},
            {"type": "Input", "source": "Order Fulfilment Process", "target": "Order Data"},
        ],
    }
    monkeypatch.setattr(
        "api.export._llm_structured_json", lambda system, user: (dangling_model, FAKE_LLM_METRICS)
    )
    response = client.post(
        "/export/adl", json={"chain_name": "4EM Repair", "steps": STEPS}
    )
    assert response.status_code == 200
    body = response.text
    assert body.count("INSTANCE <") == 5  # 2 original + 3 auto-created goals
    assert "Streamline Order Placement" in body
    assert "Optimize Order Processing" in body
    assert "Reduce Costs" in body

    logs = _export_logs()
    assert any(l.format == "adl" and l.status == "success" and l.entity_count == 5 for l in logs)


# ---------------------------------------------------------------------------
# Endpoint tests (LLM mocked)
# ---------------------------------------------------------------------------


def _export_logs():
    with Session(engine) as session:
        return session.exec(select(ExportLog).order_by(ExportLog.created_at.desc())).all()


def test_export_adl_success(monkeypatch):
    monkeypatch.setattr(
        "api.export._llm_structured_json",
        lambda system, user: (VALID_ADL_MODEL, FAKE_LLM_METRICS),
    )
    response = client.post(
        "/export/adl",
        json={"chain_name": "4EM Enterprise Alignment", "steps": STEPS, "history_id": 7},
    )
    assert response.status_code == 200
    assert "attachment; filename=" in response.headers["content-disposition"]
    assert "4em-enterprise-alignment-4EM-General-Model.adl" in response.headers["content-disposition"]
    body = response.text
    assert "VERSION <5.1>" in body

    logs = _export_logs()
    assert any(l.format == "adl" and l.status == "success" and l.entity_count == 5 and l.relation_count == 4 for l in logs)
    # Telemetry: distillation token usage must be recorded on the export log
    assert any(
        l.format == "adl" and l.status == "success"
        and l.prompt_tokens == FAKE_LLM_METRICS["prompt_tokens"]
        and l.completion_tokens == FAKE_LLM_METRICS["completion_tokens"]
        for l in logs
    )


def test_export_archimate_success(monkeypatch):
    monkeypatch.setattr(
        "api.export._llm_structured_json",
        lambda system, user: (VALID_ARCHIMATE_MODEL, FAKE_LLM_METRICS),
    )
    response = client.post(
        "/export/archimate",
        json={"chain_name": "ArchiMate Layering", "steps": STEPS, "history_id": 8},
    )
    assert response.status_code == 200
    assert response.headers["content-disposition"].endswith(".archimate\"")
    ET.fromstring(response.text)

    logs = _export_logs()
    assert any(l.format == "archimate" and l.status == "success" and l.entity_count == 5 for l in logs)


def test_export_adl_fails_loudly_without_key(monkeypatch):
    def raise_no_key(system, user):
        raise ExportException(503, "No valid OPENAI_API_KEY found")

    monkeypatch.setattr("api.export._llm_structured_json", raise_no_key)
    response = client.post(
        "/export/adl", json={"chain_name": "4EM", "steps": STEPS}
    )
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]

    logs = _export_logs()
    assert any(l.format == "adl" and l.status == "failed" and "OPENAI_API_KEY" in l.error for l in logs)


def test_export_adl_validation_failure_is_loud(monkeypatch):
    bad_model = {
        "entities": [{"class": "Goal", "name": "G1"}, {"class": "Goal", "name": "G2"}],
        "relations": [{"type": "refined by (AND)", "source": "G1", "target": "G1"}],
    }
    monkeypatch.setattr(
        "api.export._llm_structured_json", lambda system, user: (bad_model, FAKE_LLM_METRICS)
    )
    response = client.post(
        "/export/adl", json={"chain_name": "4EM", "steps": STEPS}
    )
    assert response.status_code == 422
    assert "failed validation" in response.json()["detail"]

    logs = _export_logs()
    assert any(l.format == "adl" and l.status == "failed" for l in logs)


def test_export_adl_duplicate_relations_auto_merged(monkeypatch):
    # The 4EM Toolkit rejects duplicate relation pairs, so the repair layer must merge them.
    duplicate_model = {
        "entities": [
            {"class": "Process", "name": "Product Innovation"},
            {"class": "Information Set", "name": "Customer Survey"},
        ],
        "relations": [
            {"type": "Input", "source": "Product Innovation", "target": "Customer Survey", "description": "reads survey"},
            {"type": "Output", "source": "Product Innovation", "target": "Customer Survey", "description": "writes survey"},
        ],
    }
    monkeypatch.setattr(
        "api.export._llm_structured_json", lambda system, user: (duplicate_model, FAKE_LLM_METRICS)
    )
    response = client.post(
        "/export/adl", json={"chain_name": "4EM", "steps": STEPS}
    )
    assert response.status_code == 200
    assert response.text.count("RELATION <4EM_Relation>") == 1
    assert "reads survey" in response.text and "writes survey" in response.text

    logs = _export_logs()
    assert any(l.format == "adl" and l.status == "success" and l.relation_count == 1 for l in logs)


def test_export_adl_no_step_content():
    response = client.post(
        "/export/adl",
        json={"chain_name": "4EM", "steps": [{"step": 1, "prompt_name": "Critic", "type": "CRITIC", "result": "ok"}]},
    )
    assert response.status_code == 422
    assert "No usable layer content" in response.json()["detail"]


def test_export_logs_endpoint_returns_telemetry():
    response = client.get("/export/logs?limit=50")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all("format" in row and "status" in row and "duration_ms" in row for row in data)
