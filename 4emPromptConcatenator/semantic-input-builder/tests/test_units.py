from pathlib import Path
import pytest
from semantic_input_builder.model_registry import (
    get_display_name,
    infer_model_type_from_path,
    normalize_model_type,
    resolve_model_type,
)
from semantic_input_builder.schemas import Component, Relationship, SemanticExtraction
from semantic_input_builder.text_builder import (
    build_final_document,
    format_components_and_relationships,
)
from semantic_input_builder.validator import validate_extraction


@pytest.fixture
def bp_extraction() -> SemanticExtraction:
    return SemanticExtraction(
        model_type="business_process",
        components=[
            Component(name="Target Setting", type="Business Process"),
            Component(name="Customer Survey", type="Information Set"),
        ],
        relationships=[
            Relationship(
                source="Customer Survey",
                type="is input to",
                target="Target Setting",
            )
        ],
    )


# --- Model Registry ---

@pytest.mark.parametrize(
    ("alias", "expected"),
    [
        ("pm", "business_process"),
        ("arm", "actors_ressources"),
        ("actors-resources", "actors_ressources"),
        ("cm", "concept"),
        ("tkam", "technical_requirement"),
        ("general", "general_model"),
    ],
)
def test_alias_normalization(alias: str, expected: str) -> None:
    assert normalize_model_type(alias) == expected


@pytest.mark.parametrize(
    "model_key",
    [
        "business_process",
        "actors_ressources",
        "concept",
        "goal",
        "product",
        "technical_requirement",
        "general_model",
    ],
)
def test_resolve_explicit_model_type(model_key: str) -> None:
    assert resolve_model_type(explicit=model_key) == model_key


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("scenarios/controlled_scenario_business_process_phase1.txt", "business_process"),
        ("scenarios/actors_ressources_scenario.txt", "actors_ressources"),
        ("scenarios/sample_goal.txt", "goal"),
    ],
)
def test_infer_model_from_path(filename: str, expected: str) -> None:
    path = Path(filename)
    assert infer_model_type_from_path(path) == expected
    assert resolve_model_type(scenario_path=path) == expected


def test_invalid_model_type_raises() -> None:
    with pytest.raises(ValueError, match="Unknown model type"):
        resolve_model_type(explicit="non_existent_model")


def test_display_names() -> None:
    assert get_display_name("business_process") == "Business Process Model"
    assert get_display_name("technical_requirement") == "Technical Components and Requirements Model"


# --- Validation ---

def test_validation_pass(bp_extraction: SemanticExtraction) -> None:
    result = validate_extraction(bp_extraction)
    assert result.is_valid
    assert not result.errors
    assert not result.warnings


def test_validation_no_components() -> None:
    extraction = SemanticExtraction(model_type="business_process")
    result = validate_extraction(extraction)
    assert not result.is_valid
    assert any("No components were extracted" in e for e in result.errors)


def test_validation_warnings() -> None:
    extraction = SemanticExtraction(
        model_type="business_process",
        components=[
            Component(name="Process A", type="Business Process"),
            Component(name="Process A", type="Business Process"),
        ],
        relationships=[
            Relationship(source="Unknown Source", type="is input to", target="Process A"),
            Relationship(source="Process A", type="loops to", target="Process A"),
        ],
    )
    result = validate_extraction(extraction)
    assert result.is_valid
    assert any("Duplicate component name" in w for w in result.warnings)
    assert any("Unknown Source" in w for w in result.warnings)
    assert any("Self-referencing relationship" in w for w in result.warnings)


# --- Text Assembly ---

def test_format_graph(bp_extraction: SemanticExtraction) -> None:
    formatted = format_components_and_relationships(bp_extraction)
    assert "Components:\n- Target Setting\n- Customer Survey" in formatted
    assert "Relationships:\n- Customer Survey is input to Target Setting" in formatted


def test_document_section_order(bp_extraction: SemanticExtraction) -> None:
    preprompt = "Business Process Model pre-prompt."
    scenario = "The enterprise runs a target setting process."
    downstream = "You are a model generator. Produce ADL output."

    doc = build_final_document(
        preprompt=preprompt,
        scenario=scenario,
        extraction=bp_extraction,
        downstream_prompt=downstream,
    )

    assert doc.index(preprompt) < doc.index(scenario)
    assert doc.index(scenario) < doc.index("Components:\n- Target Setting")
    assert doc.index("Components:\n- Target Setting") < doc.index(downstream)
    assert "===" not in doc
