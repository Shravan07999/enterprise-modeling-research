from dataclasses import dataclass, field
from semantic_input_builder.schemas import SemanticExtraction


@dataclass(slots=True)
class ValidationResult:
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_extraction(extraction: SemanticExtraction) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not extraction.components:
        errors.append("No components were extracted.")

    component_names: set[str] = set()
    component_names_lower: set[str] = set()
    component_ids: set[str] = set()

    for comp in extraction.components:
        name = comp.name.strip()
        comp_id = comp.id or "unknown"

        if not name:
            errors.append(f"Component '{comp_id}' has an empty or whitespace name.")
        elif name.lower() in component_names_lower:
            warnings.append(f"Duplicate component name detected: '{name}'.")
        else:
            component_names.add(name)
            component_names_lower.add(name.lower())

        if not comp.type.strip():
            errors.append(f"Component '{name or comp_id}' has an empty or whitespace type.")

        if comp.id:
            if comp.id in component_ids:
                warnings.append(f"Duplicate component ID detected: '{comp.id}'.")
            else:
                component_ids.add(comp.id)

    seen_relationships: set[tuple[str, str, str]] = set()

    for rel in extraction.relationships:
        source = rel.source.strip()
        target = rel.target.strip()
        rel_type = rel.type.strip()
        rel_id = rel.id or "unknown"

        if not source:
            errors.append(f"Relationship '{rel_id}' has an empty source.")
        elif source not in component_names:
            warnings.append(f"Relationship source '{source}' does not match any declared component name.")

        if not target:
            errors.append(f"Relationship '{rel_id}' has an empty target.")
        elif target not in component_names:
            warnings.append(f"Relationship target '{target}' does not match any declared component name.")

        if source and target and source.lower() == target.lower():
            warnings.append(f"Self-referencing relationship detected: '{source}' --[{rel_type}]--> '{target}'.")

        if not rel_type:
            errors.append(f"Relationship between '{source}' and '{target}' has an empty type.")

        rel_key = (source.lower(), rel_type.lower(), target.lower())
        if rel_key in seen_relationships:
            warnings.append(f"Duplicate relationship detected: '{source}' --[{rel_type}]--> '{target}'.")
        else:
            seen_relationships.add(rel_key)

    return ValidationResult(is_valid=(len(errors) == 0), errors=errors, warnings=warnings)
