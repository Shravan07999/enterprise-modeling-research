"""Unit tests for deterministic ID generation."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ids import element_id, relationship_id, diagram_id, folder_id


def test_element_id_deterministic():
    """Same inputs should produce same UUID."""
    id1 = element_id("model-123", "Test Process", "process")
    id2 = element_id("model-123", "Test Process", "process")
    assert id1 == id2, "UUIDv5 should be deterministic"


def test_element_id_unique_per_name():
    """Different names should produce different UUIDs."""
    id1 = element_id("model-123", "Process A", "process")
    id2 = element_id("model-123", "Process B", "process")
    assert id1 != id2, "Different names should produce different UUIDs"


def test_element_id_unique_per_type():
    """Same name, different type should produce different UUIDs."""
    id1 = element_id("model-123", "Test", "process")
    id2 = element_id("model-123", "Test", "goal")
    assert id1 != id2, "Different types should produce different UUIDs"


def test_relationship_id_deterministic():
    """Same inputs should produce same UUID."""
    id1 = relationship_id("model-123", "source-1", "target-1", "flows")
    id2 = relationship_id("model-123", "source-1", "target-1", "flows")
    assert id1 == id2, "UUIDv5 should be deterministic"


def test_diagram_id_deterministic():
    """Same inputs should produce same UUID."""
    id1 = diagram_id("model-123", "Main Diagram")
    id2 = diagram_id("model-123", "Main Diagram")
    assert id1 == id2, "UUIDv5 should be deterministic"


def test_folder_id_deterministic():
    """Same inputs should produce same UUID."""
    id1 = folder_id("model-123", "Business")
    id2 = folder_id("model-123", "Business")
    assert id1 == id2, "UUIDv5 should be deterministic"


def test_uuid_format():
    """Generated IDs should be valid XML NCName prefixed UUID format."""
    import uuid
    eid = element_id("model-123", "Test", "process")
    assert eid.startswith("id-")
    try:
        uuid.UUID(eid[3:])
    except ValueError:
        assert False, f"Invalid UUID format: {eid}"


if __name__ == "__main__":
    test_element_id_deterministic()
    test_element_id_unique_per_name()
    test_element_id_unique_per_type()
    test_relationship_id_deterministic()
    test_diagram_id_deterministic()
    test_folder_id_deterministic()
    test_uuid_format()
    print("All ID tests passed!")