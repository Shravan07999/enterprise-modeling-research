# Enterprise Modeling Research Suite

Research tooling and evaluation datasets developed for master's thesis research on AI-assisted enterprise modeling.

The suite examines prompt engineering, query rewriting, hypothetical document embeddings (HyDE), and semantic prompt concatenation across two enterprise architecture standards: **4EM (For Enterprise Modeling)** and **ArchiMate 3.x**.

## Tools in this Repository

| Tool | Focus | Tech Stack | Ports |
|---|---|---|---|
| **[PrompTed](PrompTed/)** | Prompt management and iterative modeling workbench | FastAPI, SQLModel, Next.js 16 | Backend: `8000`<br>Frontend: `3000` |
| **[QRew](QRew/)** | Query rewriting pipeline for natural language requirements | FastAPI, Next.js 16, @xyflow/react | Backend: `8000` (or `8005`)<br>Frontend: `3000` (or `3005`) |
| **[HyDE](HyDE/)** | Retrieval-augmented generation with literature embeddings | FastAPI, ChromaDB, Next.js 16 | HyDE: `8010`<br>Telemetry: `8011`<br>Frontend: `3010` |
| **[4emPromptConcatenator](4emPromptConcatenator/)** | CLI pre-processor parsing complex scenario narratives | Python (`semantic-input-builder`) | CLI |

## Repository Layout

```
├── 4emPromptConcatenator/     # CLI pre-processor and scenario datasets
├── PrompTed/                  # Prompt chaining workbench and visualizer
├── QRew/                      # Query rewriting pipeline
├── HyDE/                      # HyDE retrieval pipeline and telemetry service
│   ├── DATA_ACQUISITION.md    # Guide for acquiring source literature
│   └── backend/data/          # Metamodel reference and sample data
├── Evals of Results/          # Evaluation workbooks and benchmark scenarios
└── .gitignore
```

## Default Ports

When running multiple tools locally:

- **PrompTed**: Backend on `http://localhost:8000`, Frontend on `http://localhost:3000`
- **QRew**: Backend on `http://localhost:8000` (or `8005`), Frontend on `http://localhost:3000` (or `3005`)
- **HyDE**: Engine on `http://localhost:8010`, Telemetry on `http://localhost:8011`, Frontend on `http://localhost:3010`

## Quickstart

### Prerequisites
- Python 3.12+
- Node.js 18+ (with npm)
- OpenAI API key with access to `gpt-4o` and `text-embedding-3-small`

### PrompTed
```bash
# Backend
cd PrompTed/backend
pip install -r requirements.txt
cp .env.template .env
python seed.py
uvicorn main:app --port 8000 --reload

# Frontend (separate terminal)
cd PrompTed/frontend
npm install
npm run dev
```

### QRew
```bash
# Backend
cd QRew/backend
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --port 8000 --reload

# Frontend (separate terminal)
cd QRew/frontend
npm install
npm run dev
```

### HyDE
```bash
cd HyDE
cp .env.example .env

# Ingest literature / reference data
cd backend/ingestion_service
pip install -r requirements.txt
python ingest.py
cd ../..

# Start HyDE engine, telemetry, and frontend together:
python run_system.py
```

### 4emPromptConcatenator
```bash
cd 4emPromptConcatenator/semantic-input-builder
pip install -e .
cp .env.example .env
semantic-input-builder -s scenarios/controlled_scenario_business_process_phase1.txt
```

## Evaluations and Benchmarks

The empirical evaluation of all four tools is located in [`Evals of Results/`](Evals of Results/):
- Six comparative Excel workbooks measuring latency, token throughput, syntactic validity (SVR), component/relationship precision and recall, and tool importability into BOC ADOxx (`.adl`) and Archi (`.archimate`).
- Controlled, organized, and tangled benchmark scenarios across 4EM Goal, Business Process, and General Model perspectives.
- Detailed metrics and workbook layout are documented in [`Evals of Results/README.md`](Evals of Results/README.md).

## Data & Literature Notice

Source literature textbooks are not bundled in this repository due to copyright restrictions. Instructions to ingest reference materials or test with synthetic data are provided in [`HyDE/DATA_ACQUISITION.md`](HyDE/DATA_ACQUISITION.md).
