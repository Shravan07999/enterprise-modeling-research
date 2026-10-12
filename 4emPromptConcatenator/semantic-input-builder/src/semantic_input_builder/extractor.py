from semantic_input_builder.llm_client import BaseLLMClient
from semantic_input_builder.model_registry import get_display_name
from semantic_input_builder.schemas import SemanticExtraction

_EXTRACTION_SYSTEM_PROMPT = """\
You extract enterprise modeling components and relationships for a {model_display_name} in the 4EM framework.

Using the provided pre-prompt rules and scenario:
- Identify all domain entities and assign their valid 4EM component type.
- Identify all relationships between entities, preserving source, relation verb, and target direction.
- Do not output ADL serialization syntax.
- Return structured data matching the schema.
"""


def _build_extraction_messages(
    model_type: str,
    preprompt: str,
    scenario: str,
) -> list[dict[str, str]]:
    system_content = _EXTRACTION_SYSTEM_PROMPT.format(
        model_display_name=get_display_name(model_type)
    ).strip()

    user_content = (
        f"Pre-prompt guidelines:\n{preprompt.strip()}\n\n"
        f"Scenario:\n{scenario.strip()}\n\n"
        f"Extract the components and relationships for {get_display_name(model_type)}."
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def extract_semantics(
    llm_client: BaseLLMClient,
    model_type: str,
    preprompt: str,
    scenario: str,
    max_retries: int = 3,
) -> SemanticExtraction:
    messages = _build_extraction_messages(model_type, preprompt, scenario)
    last_error: Exception | None = None

    for _ in range(max_retries):
        try:
            result = llm_client.generate_structured(messages, SemanticExtraction)
            if isinstance(result, SemanticExtraction):
                result.model_type = model_type
                for idx, comp in enumerate(result.components, start=1):
                    comp.id = comp.id or f"C{idx}"
                for idx, rel in enumerate(result.relationships, start=1):
                    rel.id = rel.id or f"R{idx}"
                return result
        except Exception as err:
            last_error = err

    raise RuntimeError(
        f"Semantic extraction failed after {max_retries} attempts: {last_error}"
    )
