# semantic-input-builder

Extracts domain entities and relationships from 4EM enterprise scenarios using a structured LLM call, then assembles a clean plain-text prompt for a downstream ADL generation tool.

## How it works

The pipeline runs in three stages:

1. **Extraction** — sends the scenario text to an OpenAI-compatible endpoint, constrained to return a structured `SemanticExtraction` JSON (components + relationships, no ADL syntax).
2. **Validation** — checks for empty names/types, dangling relationship endpoints, self-loops, and duplicates. Errors block output; warnings are logged.
3. **Assembly** — concatenates four sections into a single `.txt` file: pre-prompt → scenario → extracted graph → downstream modeling instructions.

Model type (e.g. `business_process`, `goal`) is inferred from the scenario filename or supplied explicitly via `--model-type`.

## Installation

```bash
pip install -e ".[dev]"
cp .env.example .env
```

Edit `.env` and set at minimum:

```
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
```

`LLM_BASE_URL` defaults to `https://api.openai.com/v1` but accepts any OpenAI-compatible endpoint.

## Usage

```bash
# Infer model type from filename, write to output/final_inputs/
semantic-input-builder -s scenarios/controlled_scenario_business_process_phase1.txt

# Explicit model type, custom output path
semantic-input-builder -s scenarios/my_scenario.txt -m business_process -o out.txt

# Skip the LLM call (useful for testing prompt files)
semantic-input-builder -s scenarios/my_scenario.txt --dry-run

# Save the intermediate extraction JSON alongside the final file
semantic-input-builder -s scenarios/my_scenario.txt --save-extraction

# All options
semantic-input-builder --help
```

Supported model types: `business_process`, `actors_ressources`, `concept`, `goal`, `product`, `technical_requirement`, `general_model`.

## Prompt modes

| Flag value | Appended to output |
|---|---|
| `semantic_only` (default) | `prompt_for_downstream.txt` — domain rules only, no ADL syntax |
| `full_prompt` | `prompt_original.txt` — includes ADL grammar examples |
| `none` | Nothing appended |

## Tests

```bash
pytest
```
