"""Deterministic UUIDv5 generation for canonical model."""

import uuid

MODEL_NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')


def element_id(model_id: str, name: str, elem_type: str) -> str:
    """Generate deterministic UUIDv5 for an element."""
    return f"id-{uuid.uuid5(MODEL_NAMESPACE, f'{model_id}:elem:{elem_type}:{name}')}"


def relationship_id(model_id: str, source_id: str, target_id: str, rel_type: str) -> str:
    """Generate deterministic UUIDv5 for a relationship."""
    return f"id-{uuid.uuid5(MODEL_NAMESPACE, f'{model_id}:rel:{rel_type}:{source_id}:{target_id}')}"


def diagram_id(model_id: str, name: str) -> str:
    """Generate deterministic UUIDv5 for a diagram."""
    return f"id-{uuid.uuid5(MODEL_NAMESPACE, f'{model_id}:diag:{name}')}"


def folder_id(model_id: str, name: str) -> str:
    """Generate deterministic UUIDv5 for a folder."""
    return f"id-{uuid.uuid5(MODEL_NAMESPACE, f'{model_id}:folder:{name}')}"