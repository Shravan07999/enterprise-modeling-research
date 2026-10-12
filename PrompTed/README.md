# PrompTed

An interactive prompt management and modeling workbench for enterprise architecture. PrompTed lets users construct multi-stage prompt pipelines, execute them against LLMs, visually inspect resulting diagrams, and export models directly to BOC ADOxx (`.adl`) and Archi (`.archimate`).

## Features

- **Multi-Framework Support**: Prompt templates and chaining for 4EM (Goals, Processes, Concepts, Actors/Resources, Technical Requirements) and ArchiMate 3.x (Business, Application, Technology layers).
- **Interactive Visualizer**: Dynamic blueprint rendering of generated components, properties, and relationships.
- **Export Engines**: Automatic graph layout and serialization to `.adl` (BOC ADOxx 4EM) and `.archimate` (Open Group ArchiMate exchange format) with syntax validation and graph repair.
- **Offline Simulation Mode**: If no `OPENAI_API_KEY` is provided, the backend falls back to deterministic simulation responses for local testing without incurring API costs.
- **Telemetry**: Tracks per-stage latency, token counts, and execution metrics.

## Technology Stack

- **Backend**: Python 3.12, FastAPI, SQLModel / SQLite, OpenAI API
- **Frontend**: Next.js 16 (App Router, React 19), TypeScript, Tailwind CSS

## Getting Started

### 1. Backend Setup

```bash
cd backend
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.template .env
```

Add your `OPENAI_API_KEY` to `.env` (optional; without a key, the backend runs in offline simulation mode).

Initialize and seed the database:
```bash
python seed.py
uvicorn main:app --reload --port 8000
```

API docs will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 2. Frontend Setup

In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Development Accounts

The seed script creates two test accounts (password for both is `password123`):
- `architect`: Runs scenarios, inspects blueprints, and exports `.adl` / `.archimate` models.
- `engineer`: Configures prompt templates and chains, inspects telemetry.

## Testing

Backend test suite:
```bash
cd backend
python -m pytest tests
```

Frontend typecheck:
```bash
cd frontend
npx tsc --noEmit
```

## Project Structure

```
PrompTed/
├── backend/
│   ├── main.py                  # FastAPI entrypoint
│   ├── database.py              # SQLite configuration
│   ├── models.py                # SQLModel schemas
│   ├── seed.py                  # Database seed script
│   ├── api/                     # Auth, prompts, chains, execution, export, analytics
│   ├── export_prompts/          # Distillation prompt templates
│   └── tests/                   # API and export unit tests
├── frontend/                    # Next.js 16 UI
├── reference_model.adl          # Example BOC ADOxx 4EM General Model
└── reference_model.archimate    # Example Archi ArchiMate model
```

## Contributors

- Shravan Navaneeth Kumar
- Mohammad Akmal Hassan
- Nour Aouadi
