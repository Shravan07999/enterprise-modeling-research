import logging
from pathlib import Path
from semantic_input_builder.config import AppConfig, PromptMode
from semantic_input_builder.extractor import extract_semantics
from semantic_input_builder.file_loader import load_model_preprompt, load_prompt_by_mode, load_text_file
from semantic_input_builder.llm_client import BaseLLMClient, OpenAILLMClient
from semantic_input_builder.model_registry import get_display_name, resolve_model_type
from semantic_input_builder.schemas import SemanticExtraction
from semantic_input_builder.text_builder import build_final_document
from semantic_input_builder.validator import validate_extraction

logger = logging.getLogger("semantic_input_builder")


def run_pipeline(
    scenario_path: Path | str,
    model_type: str | None = None,
    output_path: Path | str | None = None,
    prompt_mode: PromptMode | None = None,
    save_extraction: bool = False,
    dry_run: bool = False,
    mock_extraction: SemanticExtraction | None = None,
    llm_client: BaseLLMClient | None = None,
    config: AppConfig | None = None,
) -> str:
    cfg = config or AppConfig()
    mode = prompt_mode or cfg.prompt_mode
    scenario_file = Path(scenario_path)

    resolved_type = resolve_model_type(explicit=model_type, scenario_path=scenario_file)
    logger.info("Using %s (%s)", resolved_type, get_display_name(resolved_type))

    scenario_text = load_text_file(scenario_file)
    preprompt_text = load_model_preprompt(cfg.prompts_dir, resolved_type)
    modeling_instructions = load_prompt_by_mode(cfg.prompts_dir, resolved_type, mode)

    if mock_extraction:
        logger.info("Using provided mock extraction data")
        extraction = mock_extraction
    elif dry_run:
        logger.info("Dry-run: skipping extraction")
        extraction = SemanticExtraction(model_type=resolved_type, components=[], relationships=[])
    else:
        client = llm_client or OpenAILLMClient(cfg)
        logger.info("Extracting semantics with %s...", cfg.llm_model)
        extraction = extract_semantics(
            llm_client=client,
            model_type=resolved_type,
            preprompt=preprompt_text,
            scenario=scenario_text,
        )

    validation = validate_extraction(extraction)
    for warning in validation.warnings:
        logger.warning("Semantic warning: %s", warning)
    for error in validation.errors:
        logger.error("Semantic validation error: %s", error)

    final_text = build_final_document(
        preprompt=preprompt_text,
        scenario=scenario_text,
        extraction=extraction,
        downstream_prompt=modeling_instructions,
    )

    base_name = scenario_file.stem
    if save_extraction and not dry_run:
        extractions_dir = cfg.output_dir / "extractions"
        extractions_dir.mkdir(parents=True, exist_ok=True)
        extraction_path = extractions_dir / f"{base_name}.json"
        extraction_path.write_text(extraction.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Saved extraction: %s", extraction_path)

    out_file = Path(output_path) if output_path else cfg.output_dir / "final_inputs" / f"{base_name}.txt"
    if not dry_run:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(final_text, encoding="utf-8")
        logger.info("Saved final document: %s", out_file)
    else:
        logger.info("[dry-run] Output generated in memory, skipped disk write")

    return final_text
