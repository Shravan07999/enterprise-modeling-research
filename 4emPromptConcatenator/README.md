# 4EM Prompt Concatenator

This directory contains the `semantic-input-builder` CLI package and evaluation scenario inputs.

The tool extracts enterprise entities and relationships from narrative case descriptions across 4EM perspectives (goals, business processes, concepts, actors/resources, technical components) and concatenates structured prompts for downstream ADL generation.

## Quickstart

```bash
cd semantic-input-builder
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -e .
cp .env.example .env
```

Add your `OPENAI_API_KEY` to `.env`.

Extract and assemble a scenario:
```bash
semantic-input-builder -s scenarios/controlled_scenario_business_process_phase1.txt
```

Dry-run without making API calls:
```bash
semantic-input-builder -s scenarios/controlled_scenario_business_process_phase1.txt --dry-run
```

See [semantic-input-builder/README.md](semantic-input-builder/README.md) for full CLI flags, supported model types, and test instructions.
