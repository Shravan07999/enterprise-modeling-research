# Evaluation Datasets and Metrics

Empirical evaluation data, benchmark scenario prompts, and comparative evaluation sheets for the four tools: PrompTed, QRew, HyDE, and 4emPromptConcatenator.

## Contents

```
Evals of Results/
├── Evaluation Metrics - PrompTed 4EM.xlsx
├── Evaluation Metrics - PrompTed Archimate.xlsx
├── Evaluation Metrics - QRew 4EM.xlsx
├── Evaluation Metrics - QRew Archimate.xlsx
├── Evaluation Metrics - HyDE 4EM.xlsx
├── Evaluation Metrics - HyDE Archimate.xlsx
├── 4EM prompts and results/
│   ├── BusinessProcess/
│   ├── Goal/
│   └── TangledGeneralModel/
└── Archimate prompts/
```

## Evaluation Workbooks

Each workbook records test runs across 6 sheets comparing tool performance under 4EM and ArchiMate:
- `QRew ArchiMate`
- `PrompTed Archimate`
- `HyDE Archimate`
- `PrompTed 4EM`
- `QRew 4EM`
- `HyDE 4EM`

### Metrics Measured

- **Latency**: Stage 1 (pre-processing / retrieval / rewriting) and Stage 2 (model generation) response time in seconds.
- **Token Consumption**: Tokens consumed per stage, throughput (tokens/second), and orchestration overhead ratio (`Stage 1 Tokens / Total Tokens`).
- **Metamodel Correctness**: Syntactic Validity Rate (SVR), measuring strict compliance with target metamodel grammar.
- **Model Quality**: Precision and recall for components (entities) and structural relationships against ground-truth blueprints.
- **Tool Importability**: Verification that generated `.adl` files import cleanly into BOC ADOxx and `.archimate` files open without syntax warnings in Archi.

## Benchmark Scenarios

- **`4EM prompts and results/`**: Case scenarios organized by perspective (Goal, Business Process) and narrative difficulty (Controlled, Organized, Tangled). `TangledGeneralModel/` contains uncurated case studies requiring multi-perspective model synthesis.
- **`Archimate prompts/`**: Scenarios spanning ArchiMate 3.x Business, Application, and Technology layers.
