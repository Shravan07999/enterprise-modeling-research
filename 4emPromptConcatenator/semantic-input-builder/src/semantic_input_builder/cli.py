from pathlib import Path
import click
from semantic_input_builder.config import PromptMode, get_config
from semantic_input_builder.logging_utils import setup_logging
from semantic_input_builder.model_registry import MODEL_TYPES
from semantic_input_builder.pipeline import run_pipeline


@click.command()
@click.option(
    "--scenario", "-s",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to the scenario text file.",
)
@click.option(
    "--model-type", "-m",
    default=None,
    type=click.Choice(list(MODEL_TYPES.keys()), case_sensitive=False),
    help="4EM model type (inferred from filename if omitted).",
)
@click.option(
    "--output", "-o",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output path for the generated text file.",
)
@click.option(
    "--prompt-mode", "-p",
    default="semantic_only",
    type=click.Choice(["semantic_only", "full_prompt", "none"], case_sensitive=False),
    help="Trailing prompt mode to include: semantic_only (default), full_prompt, or none.",
)
@click.option(
    "--save-extraction",
    is_flag=True,
    default=False,
    help="Save intermediate JSON extraction to disk.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run without calling the LLM or writing files to disk.",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose debug logging.",
)
def main(scenario, model_type, output, prompt_mode, save_extraction, dry_run, verbose):
    """Extract semantic components and compile an assembled prompt for 4EM ADL generation."""
    setup_logging(verbose=verbose)
    config = get_config()
    mode = PromptMode(prompt_mode)

    try:
        final_text = run_pipeline(
            scenario_path=scenario,
            model_type=model_type,
            output_path=output,
            prompt_mode=mode,
            save_extraction=save_extraction,
            dry_run=dry_run,
            config=config,
        )
        if dry_run:
            click.echo("\n--- Dry-Run Preview ---")
            click.echo(final_text[:600] + "\n... [truncated] ...")
    except Exception as exc:
        click.secho(f"Error: {exc}", fg="red", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()
