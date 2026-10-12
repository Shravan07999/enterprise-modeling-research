# QRew

QRew (Query Rewriter) reformulates ambiguous natural-language enterprise scenarios into structured modeling specifications for 4EM (Goals and Business Processes) and ArchiMate 3.x. Models can be visualized on an interactive canvas and exported directly to BOC ADOxx (`.adl`) and Archi (`.archimate`).

## Technology Stack

- **Backend**: Python 3.12, FastAPI, SQLModel / SQLite, OpenAI API (`gpt-4o`)
- **Frontend**: Next.js 16 (React 19), `@xyflow/react`, `bpmn-js`, Mermaid, Tailwind CSS

## Getting Started

### 1. Backend

```bash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Add your `OPENAI_API_KEY` to `.env`.

Start the backend:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

API docs will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 2. Frontend

In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```

The frontend runs at [http://localhost:3000](http://localhost:3000).

> Note: If running alongside PrompTed (which also defaults to port 3000), launch QRew frontend with:
> ```bash
> npm run dev -- -p 3005
> ```
> and update `NEXT_PUBLIC_API_URL` to match your backend port if running on a non-default port.

## Output Formats

- **BOC ADOxx** (`.adl`): Importable into ADOxx 4EM modeling environments.
- **Archi** (`.archimate`): Open Group ArchiMate XML exchange format.
- Interactive canvas rendering using React Flow and BPMN.js.
