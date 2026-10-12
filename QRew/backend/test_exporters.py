"""Unit tests for exporters."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exporters.adl import ADLExporter
from exporters.archimate import ArchiMateExporter
from exporters.factory import get_exporter


def test_adl_exporter_basic():
    """Test ADL exporter generates valid output."""
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
            {
                "id": "123e4567-e89b-12d3-a456-426614174003",
                "frameworkType": "Actor",
                "canonicalType": "actor",
                "name": "Test Actor",
                "description": "A test actor",
                "layer": "actors",
                "submodel": "actors",
                "attributes": {}
            },
        ],
        "relationships": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174004",
                "sourceId": "123e4567-e89b-12d3-a456-426614174001",
                "targetId": "123e4567-e89b-12d3-a456-426614174002",
                "frameworkType": "refined by (AND)",
                "canonicalType": "refines",
                "name": "Goal to Process",
                "description": "",
                "attributes": {}
            },
            {
                "id": "123e4567-e89b-12d3-a456-426614174005",
                "sourceId": "123e4567-e89b-12d3-a456-426614174003",
                "targetId": "123e4567-e89b-12d3-a456-426614174002",
                "frameworkType": "is responsible for",
                "canonicalType": "responsible_for",
                "name": "Actor to Process",
                "description": "",
                "attributes": {}
            }
        ],
        "diagrams": [],
        "folders": [],
        "extensions": {}
    }

    exporter = ADLExporter()
    output = exporter.export(model)

    assert isinstance(output, bytes)
    content = output.decode("utf-8")

    # Check required sections
    assert "VERSION <5.1>" in content
    assert "BUSINESS PROCESS MODEL" in content
    assert "INSTANCE <Test Goal> : <Goal>" in content
    assert "INSTANCE <Test Process> : <Process>" in content
    assert "INSTANCE <Test Actor> : <Actor>" in content
    assert "RELATION <4EM_Relation>" in content
    assert "refined by (AND)" in content
    assert "is responsible for" in content


def test_adl_exporter_wrong_framework():
    """Test ADL exporter rejects non-4EM framework."""
    model = {
        "framework": "BPMN",
        "metadata": {},
        "elements": [],
        "relationships": [],
        "diagrams": [],
        "folders": [],
        "extensions": {}
    }

    exporter = ADLExporter()
    try:
        exporter.export(model)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "4EM" in str(e)


def test_adl_exporter_contains_position():
    """Test ADL exporter includes Position attributes."""
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
        "relationships": [],
        "diagrams": [],
        "folders": [],
        "extensions": {}
    }

    exporter = ADLExporter()
    output = exporter.export(model)
    content = output.decode("utf-8")

    assert "Position" in content
    assert "NODE x:" in content


def test_archimate_exporter_basic():
    """Test ArchiMate exporter generates valid XML."""
    model = {
        "framework": "BPMN",
        "metadata": {
            "modelId": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Test Model",
            "version": "1.0.0",
            "createdAt": "2024-01-01T00:00:00Z",
            "toolVersion": "QRew-1.0",
            "frameworkVersion": "ArchiMate:3.2",
            "sourceRunId": "123e4567-e89b-12d3-a456-426614174000",
        },
        "elements": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "frameworkType": "Task",
                "canonicalType": "process",
                "name": "Business Process",
                "description": "A process",
                "layer": "business",
                "submodel": None,
                "attributes": {}
            },
            {
                "id": "123e4567-e89b-12d3-a456-426614174002",
                "frameworkType": "StartEvent",
                "canonicalType": "event",
                "name": "Start",
                "description": "Start event",
                "layer": "business",
                "submodel": None,
                "attributes": {}
            }
        ],
        "relationships": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174003",
                "sourceId": "123e4567-e89b-12d3-a456-426614174002",
                "targetId": "123e4567-e89b-12d3-a456-426614174001",
                "frameworkType": "SequenceFlow",
                "canonicalType": "flows",
                "name": "sequence",
                "description": "",
                "attributes": {}
            }
        ],
        "diagrams": [],
        "folders": [],
        "extensions": {}
    }

    exporter = ArchiMateExporter()
    output = exporter.export(model)

    assert isinstance(output, bytes)
    content = output.decode("utf-8")

    # Check XML structure
    assert '<?xml version="1.0" encoding="utf-8"?>' in content
    assert 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' in content
    assert 'xmlns:archimate="http://www.archimatetool.com/archimate"' in content
    assert 'archimate:model' in content
    assert 'archimate:BusinessProcess' in content
    assert 'archimate:BusinessEvent' in content
    assert 'archimate:FlowRelationship' in content


def test_archimate_exporter_wrong_framework():
    """Test ArchiMate exporter rejects non-BPMN framework."""
    model = {
        "framework": "4EM",
        "metadata": {},
        "elements": [],
        "relationships": [],
        "diagrams": [],
        "folders": [],
        "extensions": {}
    }

    exporter = ArchiMateExporter()
    try:
        exporter.export(model)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "BPMN" in str(e)


def test_factory_get_exporter():
    """Test factory returns correct exporter."""
    adl = get_exporter("adl")
    archi = get_exporter("archimate")

    assert isinstance(adl, ADLExporter)
    assert isinstance(archi, ArchiMateExporter)


def test_factory_invalid_format():
    """Test factory raises for invalid format."""
    try:
        get_exporter("invalid")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unknown export format" in str(e)


if __name__ == "__main__":
    test_adl_exporter_basic()
    test_adl_exporter_wrong_framework()
    test_adl_exporter_contains_position()
    test_archimate_exporter_basic()
    test_archimate_exporter_wrong_framework()
    test_factory_get_exporter()
    test_factory_invalid_format()
    print("All exporter tests passed!")