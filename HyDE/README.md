# HyDE for Enterprise Modeling

HyDE uses Hypothetical Document Embeddings to retrieve relevant domain literature when synthesizing enterprise models from natural language descriptions.

Given an input scenario, the engine generates a hypothetical model blueprint, embeds it via OpenAI `text-embedding-3-small`, retrieves matching contextual excerpts from a local Chroma vector database of 4EM literature, and passes that context to the final model synthesizer.

## Services

| Service | Directory | Port | Role |
|---|---|---|---|
| **HyDE Engine** | `backend/hyde_service/` | `8010` | FastAPI pipeline and LLM orchestration |
| **Telemetry Service** | `backend/telemetry_service/` | `8011` | Records pipeline latency, stages, and token counts |
| **Ingestion Pipeline** | `backend/ingestion_service/` | CLI | PDF parsing and Chroma vector store population |
| **Frontend** | `frontend/` | `3010` | Next.js 16 interactive UI and diagram visualizer |

## Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- OpenAI API key

### 1. Environment Configuration

```bash
cp .env.example .env
```
Edit `.env` and set your `OPENAI_API_KEY`.

### 2. Ingest the Literature / Knowledge Base

Before running HyDE, populate the Chroma vector store. (See [DATA_ACQUISITION.md](DATA_ACQUISITION.md) for how to obtain academic textbooks or use the included reference file):

```bash
cd backend/ingestion_service
pip install -r requirements.txt
python ingest.py
cd ../..
```

### 3. Install Service Dependencies

```bash
# HyDE Engine
cd backend/hyde_service
pip install -r requirements.txt

# Telemetry
cd ../telemetry_service
pip install -r requirements.txt

# Frontend
cd ../../frontend
npm install
cd ..
```

### 4. Running the System

HyDE provides a launcher script that starts the engine, telemetry service, and frontend together:

```bash
python run_system.py
```

This boots:
- Telemetry: `http://localhost:8011`
- HyDE Engine: `http://localhost:8010`
- Frontend: `http://localhost:3010`

Press `Ctrl+C` in that terminal to stop all services.

## Model Formats

Generated models export to:
- **BOC ADOxx** (`.adl`): 4EM metamodel
- **Archi** (`.archimate`): ArchiMate 3.x XML
- Interactive canvas diagrams (BPMN / Mermaid)
