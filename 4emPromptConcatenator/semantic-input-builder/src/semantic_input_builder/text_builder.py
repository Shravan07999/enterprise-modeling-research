from semantic_input_builder.schemas import SemanticExtraction


def _format_graph(extraction: SemanticExtraction) -> str:
    comp_lines = ["Components:"]
    if extraction.components:
        for comp in extraction.components:
            comp_lines.append(f"- {comp.name.strip()}")
    else:
        comp_lines.append("- None")

    rel_lines = ["\nRelationships:"]
    if extraction.relationships:
        for rel in extraction.relationships:
            rel_lines.append(
                f"- {rel.source.strip()} {rel.type.strip()} {rel.target.strip()}"
            )
    else:
        rel_lines.append("- None")

    return "\n".join(comp_lines) + "\n" + "\n".join(rel_lines)


def build_final_document(
    preprompt: str,
    scenario: str,
    extraction: SemanticExtraction,
    downstream_prompt: str,
) -> str:
    sections = [
        preprompt.strip(),
        scenario.strip(),
        _format_graph(extraction).strip(),
        downstream_prompt.strip(),
    ]
    return "\n\n".join(s for s in sections if s) + "\n"


# kept for any callers that haven't migrated yet
format_components_and_relationships = _format_graph
