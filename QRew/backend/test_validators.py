"""Unit tests for validators."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import validate_canonical, validate_adl_output, validate_archimate_output


def test_validate_canonical_valid_4em():
    """Test validation passes for valid 4EM model."""
    model = {
        "framework": "4EM",
        "metadata": {
            "modelId": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Test Model",
            "version": "1.0.0",
            "createdAt": "2024-01-01T00:00:00Z",
            "toolVersion": "QRew-1.0",
            "frameworkVersion": "4EM:5.1",
            "sourceRunId": "123e4567-e89b-12d3-a456-426614174000",
        },
        "elements": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "frameworkType": "Goal",
                "canonicalType": "goal",
                "name": "Test Goal",
                "description": "A test goal",
                "layer": "goals",
                "submodel": "goals",
                "attributes": {}
            },
            {
                "id": "123e4567-e89b-12d3-a456-426614174002",
                "frameworkType": "Process",
                "canonicalType": "process",
                "name": "Test Process",
                "description": "A test process",
                "layer": "processes",
                "submodel": "processes",
                "attributes": {}
            },
        ],
        "relationships": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174003",
                "sourceId": "123e4567-e89b-12d3-a456-426614174001",
                "targetId": "123e4567-e89b-12d3-a456-426614174002",
                "frameworkType": "is responsible for",
                "canonicalType": "responsible_for",
                "name": "Goal to Process",
                "description": "",
                "attributes": {}
            }
        ],
        "diagrams": [],
        "folders": [],
        "extensions": {}
    }

    result = validate_canonical(model)
    assert result.passed, f"Validation should pass: {result.errors}"
    assert len(result.errors) == 0


def test_validate_canonical_invalid_framework():
    """Test validation fails for invalid framework."""
    model = {
        "framework": "INVALID",
        "metadata": {},
        "elements": [],
        "relationships": [],
        "diagrams": [],
        "folders": [],
        "extensions": {}
    }

    result = validate_canonical(model)
    assert not result.passed
    assert any("framework" in e for e in result.errors)


def test_validate_canonical_missing_elements():
    """Test validation fails for empty elements."""
    model = {
        "framework": "4EM",
        "metadata": {
            "modelId": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Test",
            "version": "1.0.0",
            "createdAt": "2024-01-01T00:00:00Z",
            "toolVersion": "QRew-1.0",
            "frameworkVersion": "4EM:5.1",
            "sourceRunId": "123e4567-e89b-12d3-a456-426614174000",
        },
        "elements": [],
        "relationships": [],
        "diagrams": [],
        "folders": [],
        "extensions": {}
    }

    result = validate_canonical(model)
    assert not result.passed
    assert any("element" in e.lower() for e in result.errors)


def test_validate_canonical_bad_refs():
    """Test validation fails for invalid relationship references."""
    model = {
        "framework": "4EM",
        "metadata": {
            "modelId": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Test",
            "version": "1.0.0",
            "createdAt": "2024-01-01T00:00:00Z",
            "toolVersion": "QRew-1.0",
            "frameworkVersion": "4EM:5.1",
            "sourceRunId": "123e4567-e89b-12d3-a456-426614174000",
        },
        "elements": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "frameworkType": "Goal",
                "canonicalType": "goal",
                "name": "Goal",
                "description": "",
                "layer": "goals",
                "submodel": "goals",
                "attributes": {}
            }
        ],
        "relationships": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174002",
                "sourceId": "non-existent",
                "targetId": "123e4567-e89b-12d3-a456-426614174001",
                "frameworkType": "test",
                "canonicalType": "flows",
                "name": "Rel",
                "description": "",
                "attributes": {}
            }
        ],
        "diagrams": [],
        "folders": [],
        "extensions": {}
    }

    result = validate_canonical(model)
    assert not result.passed
    assert any("sourceId" in e or "targetId" in e for e in result.errors)


def test_validate_4em_semantics_warnings():
    """Test 4EM semantic validation produces warnings."""
    model = {
        "framework": "4EM",
        "metadata": {
            "modelId": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Test",
            "version": "1.0.0",
            "createdAt": "2024-01-01T00:00:00Z",
            "toolVersion": "QRew-1.0",
            "frameworkVersion": "4EM:5.1",
            "sourceRunId": "123e4567-e89b-12d3-a456-426614174000",
        },
        "elements": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "frameworkType": "Process",
                "canonicalType": "process",
                "name": "Lonely Process",
                "description": "",
                "layer": "processes",
                "submodel": "processes",
                "attributes": {}
            }
        ],
        "relationships": [],
        "diagrams": [],
        "folders": [],
        "extensions": {}
    }

    result = validate_canonical(model)
    # Should pass structurally but have warnings
    assert result.passed
    assert any("responsible" in w for w in result.warnings)
    assert any("Input/Output" in w for w in result.warnings)


def test_validate_adl_output_valid():
    """Test ADL validation passes for valid content."""
    content = """VERSION <5.1>

BUSINESS PROCESS MODEL <Test> : <4EM-Rostock Library_87_22_04_01>
VERSION <>
TYPE <4EM General Model>
//
INSTANCE <Goal> : <Goal>
	ATTRIBUTE <Position>
	VALUE "NODE x:1cm y:1cm w:4cm h:1.5cm index:1"
	ATTRIBUTE <External tool coupling>
	VALUE ""
	ATTRIBUTE <Description>
	VALUE "Test"
	ATTRIBUTE <Criticality>
	VALUE "Low"
	ATTRIBUTE <Priority>
	VALUE "Low"
	ATTRIBUTE <Intermodel-Relations>
	VALUE ""
	ATTRIBUTE <Decomposition>
	VALUE ""
	ATTRIBUTE <Defined by>
	VALUE ""
	ATTRIBUTE <Is the exact same as>
	VALUE ""
	ATTRIBUTE <hidden_attribute>
	VALUE ""
//END
"""
    result = validate_adl_output(content)
    assert result.passed, f"ADL validation should pass: {result.errors}"


def test_validate_adl_output_missing_version():
    """Test ADL validation fails for missing version."""
    content = "INSTANCE <Test> : <Goal> //END"
    result = validate_adl_output(content)
    assert not result.passed


if __name__ == "__main__":
    test_validate_canonical_valid_4em()
    test_validate_canonical_invalid_framework()
    test_validate_canonical_missing_elements()
    test_validate_canonical_bad_refs()
    test_validate_4em_semantics_warnings()
    test_validate_adl_output_valid()
    test_validate_adl_output_missing_version()
    print("All validator tests passed!")