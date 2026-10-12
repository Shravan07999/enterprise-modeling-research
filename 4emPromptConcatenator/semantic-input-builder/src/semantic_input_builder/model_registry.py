from pathlib import Path

MODEL_TYPES: dict[str, dict[str, str]] = {
    "business_process": {
        "display_name": "Business Process Model",
        "description": "Enterprise processes, activities, workflows, and process interdependencies.",
    },
    "actors_ressources": {
        "display_name": "Actors and Resources Model",
        "description": "Actors, organizational units, and physical/intellectual resources.",
    },
    "concept": {
        "display_name": "Concept Model",
        "description": "Glossary, entities, terminology, and concept relationships.",
    },
    "goal": {
        "display_name": "Goal Model",
        "description": "Enterprise goals, problems, causes, constraints, and opportunities.",
    },
    "product": {
        "display_name": "Product and Service Model",
        "description": "Products, services, components, and distinguishing features.",
    },
    "technical_requirement": {
        "display_name": "Technical Components and Requirements Model",
        "description": "IT components, functional/non-functional requirements, and systems.",
    },
    "general_model": {
        "display_name": "4EM General Model",
        "description": "Multi-perspective enterprise overview integrating cross-domain components.",
    },
}

ALIAS_MAP: dict[str, str] = {
    "arm": "actors_ressources",
    "actors": "actors_ressources",
    "actors_resources": "actors_ressources",
    "resources": "actors_ressources",
    "pm": "business_process",
    "process": "business_process",
    "processes": "business_process",
    "cm": "concept",
    "concepts": "concept",
    "gm": "goal",
    "goals": "goal",
    "ps": "product",
    "products": "product",
    "product_service": "product",
    "tc": "technical_requirement",
    "tkam": "technical_requirement",
    "technical": "technical_requirement",
    "technical_requirements": "technical_requirement",
    "general": "general_model",
}

_PATH_INFERENCE_KEYS: tuple[str, ...] = (
    "technical_requirement",
    "technical_components",
    "business_process",
    "actors_ressources",
    "actors_resources",
    "general_model",
    "concept",
    "goal",
    "product",
)


def normalize_model_type(key: str) -> str | None:
    clean_key = key.strip().lower().replace("-", "_").replace(" ", "_")
    if clean_key in MODEL_TYPES:
        return clean_key
    return ALIAS_MAP.get(clean_key)


def infer_model_type_from_path(path: Path | str) -> str | None:
    stem = Path(path).stem.lower()

    for pattern in _PATH_INFERENCE_KEYS:
        if pattern in stem:
            return normalize_model_type(pattern)

    for part in stem.split("_"):
        resolved = normalize_model_type(part)
        if resolved:
            return resolved

    return None


def resolve_model_type(explicit: str | None = None, scenario_path: Path | str | None = None) -> str:
    if explicit:
        norm = normalize_model_type(explicit)
        if not norm:
            valid = ", ".join(MODEL_TYPES.keys())
            raise ValueError(f"Unknown model type '{explicit}'. Valid options: {valid}")
        return norm

    if scenario_path:
        inferred = infer_model_type_from_path(scenario_path)
        if inferred:
            return inferred

    valid = ", ".join(MODEL_TYPES.keys())
    raise ValueError(
        f"Could not infer model type from filename '{scenario_path}'. "
        f"Please supply an explicit --model-type. Valid options: {valid}"
    )


def get_display_name(model_type: str) -> str:
    norm = normalize_model_type(model_type)
    if norm and norm in MODEL_TYPES:
        return MODEL_TYPES[norm]["display_name"]
    return model_type
