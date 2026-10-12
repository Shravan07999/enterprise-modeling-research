"""Unit tests for layout algorithms."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from layout import generate_4em_layout, generate_archimate_layout, Position


def test_4em_layout_basic():
    """Test basic 4EM layout generation."""
    elements = [
        {"id": "elem-1", "name": "Goal A", "canonicalType": "goal", "submodel": "goals"},
        {"id": "elem-2", "name": "Process A", "canonicalType": "process", "submodel": "processes"},
        {"id": "elem-3", "name": "Actor A", "canonicalType": "actor", "submodel": "actors"},
        {"id": "elem-4", "name": "Component A", "canonicalType": "component", "submodel": "technical"},
    ]

    positions = generate_4em_layout(elements)

    assert len(positions) == 4
    assert "elem-1" in positions
    assert "elem-2" in positions
    assert "elem-3" in positions
    assert "elem-4" in positions


def test_4em_layout_column_assignment():
    """Test elements are assigned to correct columns."""
    elements = [
        {"id": "g1", "name": "Goal", "canonicalType": "goal", "submodel": "goals"},
        {"id": "p1", "name": "Process", "canonicalType": "process", "submodel": "processes"},
        {"id": "a1", "name": "Actor", "canonicalType": "actor", "submodel": "actors"},
        {"id": "t1", "name": "Tech", "canonicalType": "tech_component", "submodel": "technical"},
    ]

    positions = generate_4em_layout(elements)

    # Goals column 0: x ~ 1
    assert abs(positions["g1"].x - 1) < 0.1
    # Processes column 1: x ~ 8
    assert abs(positions["p1"].x - 8) < 0.1
    # Actors column 2: x ~ 15
    assert abs(positions["a1"].x - 15) < 0.1
    # Technical column 3: x ~ 22
    assert abs(positions["t1"].x - 22) < 0.1


def test_4em_layout_vertical_stacking():
    """Test elements in same submodel stack vertically."""
    elements = [
        {"id": "p1", "name": "Process A", "canonicalType": "process", "submodel": "processes"},
        {"id": "p2", "name": "Process B", "canonicalType": "process", "submodel": "processes"},
        {"id": "p3", "name": "Process C", "canonicalType": "process", "submodel": "processes"},
    ]

    positions = generate_4em_layout(elements)

    # Should stack vertically with ~2.5cm spacing
    assert abs(positions["p1"].y - 1) < 0.1
    assert abs(positions["p2"].y - 3.5) < 0.1
    assert abs(positions["p3"].y - 6) < 0.1


def test_4em_layout_deterministic():
    """Same elements should produce same layout."""
    elements = [
        {"id": "e1", "name": "Zebra", "canonicalType": "goal", "submodel": "goals"},
        {"id": "e2", "name": "Apple", "canonicalType": "goal", "submodel": "goals"},
    ]

    pos1 = generate_4em_layout(elements)
    pos2 = generate_4em_layout(elements)

    assert pos1["e1"].x == pos2["e1"].x
    assert pos1["e1"].y == pos2["e1"].y


def test_4em_layout_sorts_by_name():
    """Elements should be sorted by name within submodel."""
    elements = [
        {"id": "e1", "name": "Zebra", "canonicalType": "goal", "submodel": "goals"},
        {"id": "e2", "name": "Apple", "canonicalType": "goal", "submodel": "goals"},
    ]

    positions = generate_4em_layout(elements)

    # Apple should come first (lower y)
    assert positions["e2"].y < positions["e1"].y


def test_archimate_layout_basic():
    """Test basic ArchiMate layout generation."""
    elements = [
        {"id": "e1", "name": "Business Process", "canonicalType": "biz_process", "layer": "business"},
        {"id": "e2", "name": "App Service", "canonicalType": "app_service", "layer": "application"},
        {"id": "e3", "name": "Tech Node", "canonicalType": "node", "layer": "technology"},
    ]
    folders = []

    positions = generate_archimate_layout(elements, folders)

    assert len(positions) == 3


def test_archimate_layout_layer_columns():
    """Test process flow elements are assigned sequential depth positions."""
    elements = [
        {"id": "e1", "name": "Biz", "canonicalType": "biz_process", "layer": "business"},
        {"id": "e2", "name": "App", "canonicalType": "app_service", "layer": "application"},
        {"id": "e3", "name": "Tech", "canonicalType": "node", "layer": "technology"},
    ]
    relationships = [
        {"sourceId": "e1", "targetId": "e2", "canonicalType": "flows"},
        {"sourceId": "e2", "targetId": "e3", "canonicalType": "flows"},
    ]

    positions = generate_archimate_layout(elements, relationships)

    assert positions["e1"].x == 100
    assert positions["e2"].x == 320
    assert positions["e3"].x == 540


def test_archimate_layout_vertical_stacking():
    """Test elements at the same depth stack vertically with spacing."""
    elements = [
        {"id": "e1", "name": "A", "canonicalType": "biz_process", "layer": "business"},
        {"id": "e2", "name": "B", "canonicalType": "biz_process", "layer": "business"},
        {"id": "e3", "name": "C", "canonicalType": "biz_process", "layer": "business"},
    ]
    relationships = []

    positions = generate_archimate_layout(elements, relationships)

    assert positions["e1"].y == 100
    assert positions["e2"].y == 190
    assert positions["e3"].y == 280


if __name__ == "__main__":
    test_4em_layout_basic()
    test_4em_layout_column_assignment()
    test_4em_layout_vertical_stacking()
    test_4em_layout_deterministic()
    test_4em_layout_sorts_by_name()
    test_archimate_layout_basic()
    test_archimate_layout_layer_columns()
    test_archimate_layout_vertical_stacking()
    print("All layout tests passed!")