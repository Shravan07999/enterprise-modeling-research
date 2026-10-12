import json
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlmodel import Session

sys.path.append(str(Path(__file__).resolve().parent.parent))
from database.db import HydeInteraction, get_session, init_db
from exporters.adl_exporter import generate_adl
from exporters.archimate_exporter import generate_archimate
from exporters.exporter_utils import safe_filename

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

@asynccontextmanager
async def lifespan(application: FastAPI):
    init_db()
    yield

app = FastAPI(title="HyDE Engine Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Must use the same model as ingest.py — vectors live in the same space.
CHROMA_DB_PATH = str(Path(__file__).resolve().parent.parent / "chroma_db")
COLLECTION_NAME = "hyde_collection"
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

TELEMETRY_URL = "http://127.0.0.1:8011/log"

class ProcessRequest(BaseModel):
    user_query: str
    framework_selected: str

class ProcessResponse(BaseModel):
    id: int
    final_output: str
    retrieved_source_pages: list[str] = []
    stage1_prompt: str | None = None
    stage1_semantic_narrative: str | None = None
    stage1_blueprint: str | None = None
    stage2_query: str | None = None
    stage2_chunk_count: int | None = None
    stage3_prompt: str | None = None

async def log_telemetry(stage_name: str, latency_ms: float, token_count: int):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                TELEMETRY_URL,
                json={
                    "stage_name": stage_name,
                    "latency_ms": latency_ms,
                    "token_count": token_count,
                },
                timeout=2.0
            )
        except Exception as e:
            print(f"Failed to log telemetry to {TELEMETRY_URL}: {e}")

@app.post("/process-hyde", response_model=ProcessResponse)
async def process_hyde(req: ProcessRequest, session: Session = Depends(get_session)):
    
    # Clear stale telemetry so the sidebar starts fresh
    async with httpx.AsyncClient() as client:
        try:
            await client.delete("http://127.0.0.1:8011/metrics", timeout=2.0)
        except Exception:
            pass

    interaction = HydeInteraction(
        framework_selected=req.framework_selected,
        user_query=req.user_query,
        retrieved_source_pages=[],
        final_output=""
    )

    # Stage 1: Pseudo-Model Generator
    start_time = time.perf_counter()
    stage1_prompt = (
        f"You are an expert enterprise architect specializing in {req.framework_selected}.\n"
        f"User Query: {req.user_query}\n\n"
        "Output a clean JSON object with EXACTLY two keys:\n"
        "1. \"semantic_narrative\": A dense, text-only explanation of the architectural rules optimized for vector retrieval.\n"
        "2. \"hypothetical_blueprint\": The raw structural notation, code, or syntax."
    )
    
    completion1 = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": stage1_prompt}],
        response_format={"type": "json_object"}
    )
    stage1_latency = (time.perf_counter() - start_time) * 1000
    stage1_tokens = completion1.usage.total_tokens if completion1.usage else 0
    await log_telemetry("pseudo_model_generator", stage1_latency, stage1_tokens)
    
    try:
        content1 = completion1.choices[0].message.content or "{}"
        stage1_output = json.loads(content1)
        semantic_narrative = stage1_output.get("semantic_narrative", "")
        hypothetical_blueprint_raw = stage1_output.get("hypothetical_blueprint", "")
        # gpt-4o occasionally returns a nested dict rather than a string
        if isinstance(hypothetical_blueprint_raw, (dict, list)):
            hypothetical_blueprint = json.dumps(hypothetical_blueprint_raw, indent=2)
        else:
            hypothetical_blueprint = str(hypothetical_blueprint_raw)
    except (json.JSONDecodeError, TypeError, AttributeError):
        raise HTTPException(status_code=500, detail="Stage 1 LLM output was not valid JSON.")

    interaction.stage1_prompt = stage1_prompt
    interaction.stage1_semantic_narrative = semantic_narrative
    interaction.stage1_blueprint = hypothetical_blueprint

    # Stage 2: Vector Retrieval
    start_time = time.perf_counter()
    
    retrieved_texts = []
    source_pages = []
    try:
        vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            persist_directory=CHROMA_DB_PATH,
            embedding_function=embeddings_model,
        )
        results = vectorstore.similarity_search(query=semantic_narrative, k=5)
        for doc in results:
            retrieved_texts.append(doc.page_content)
            source = doc.metadata.get("source", "unknown")
            page = doc.metadata.get("page", "unknown")
            source_pages.append(f"{source} - Page {page}")
    except Exception as e:
        print(f"Vector retrieval failed (collection may be empty): {e}")

    stage2_latency = (time.perf_counter() - start_time) * 1000
    await log_telemetry("vector_retrieval", stage2_latency, 0)
    
    interaction.retrieved_source_pages = source_pages
    interaction.stage2_query = semantic_narrative
    interaction.stage2_chunk_count = len(retrieved_texts)

    # Stage 3: Context Synthesizer
    start_time = time.perf_counter()
    
    context_str = "\n\n".join(retrieved_texts) if retrieved_texts else "No context found."
    
    framework_data = {
        "TOGAF": {
            "overview": (
                "FRAMEWORK OVERVIEW:\n"
                "- TOGAF (The Open Group Architecture Framework): Organizes enterprise architecture into four domains:\n"
                "  1. Business Architecture (strategy, governance, organization, business processes, actors, roles)\n"
                "  2. Data Architecture (logical/physical data assets, data entities, data stores, information flows)\n"
                "  3. Application Architecture (application components, application services, interfaces, integrations)\n"
                "  4. Technology Architecture (infrastructure, platforms, networks, hardware, middleware)\n"
                "The ADM guides through phases A-H: Architecture Vision, Business Architecture, Information Systems,\n"
                "Technology Architecture, Migration Planning, Implementation Governance, Change Management.\n"
                "ABBs are reusable specs; SBBs are implementation components.\n\n"
            ),
            "syntax": (
                "You MUST output a PlantUML Component Diagram wrapped in ```plantuml. Start with @startuml.\n"
                "Organize into packages for the four domains (Business, Data, Application, Technology).\n"
                "Decompose the query into ABBs/SBBs inside each domain. Connect: Business → Application → Data,\n"
                "Application runs on Technology. Use only: [component], (interface), package, [database], rectangle.\n"
                "Do NOT use actor, class, or usecase. End with @enduml."
            )
        },
        "Zachman": {
            "overview": (
                "FRAMEWORK OVERVIEW:\n"
                "- Zachman Framework: An enterprise architecture ontology organized as a 6x6 matrix.\n"
                "Six rows (Perspectives): Planner (Scope/Context), Owner (Business Model),\n"
                "Designer (System Model), Builder (Technology Model), Subcontractor (Detailed Repr.),\n"
                "Enterprise (Functioning System). Six columns (Interrogatives): What (Data), How (Function),\n"
                "Where (Network), Who (People), When (Time), Why (Motivation). Each cell is a unique view.\n\n"
            ),
            "syntax": (
                "You MUST output Mermaid flowchart syntax wrapped in ```mermaid. Start with 'flowchart TD'.\n"
                "Use subgraph blocks for each perspective row: Planner, Owner, Designer, Builder, Subcontractor, Enterprise.\n"
                "Use simple subgraph titles — do NOT use parentheses or brackets in subgraph names.\n"
                "Within each subgraph, add nodes with the format: ID[Interrogative: Description]\n"
                "Always use square brackets [ ] for nodes — never use parentheses ( ) in node labels.\n"
                "Connect related cells across rows with arrows (e.g., PWhat --> OWhat).\n"
                "End each subgraph block with 'end' on its own line."
            )
        },
        "4EM": {
            "overview": (
                "FRAMEWORK OVERVIEW:\n"
                "- 4EM (Four Element Method): Models enterprises using exactly four element types:\n"
                "Goals (objectives, vision, targets), Processes (activities, workflows, functions),\n"
                "Data (information, documents, knowledge), Resources (actors, systems, tools).\n"
                "Relationships: Goals drive Processes, Processes consume/produce Data,\n"
                "Resources execute Processes, Resources manage Data.\n\n"
            ),
            "syntax": (
                "You MUST output a JSON node-edge tree wrapped in ```json.\n"
                "Format: [{\"id\": \"1\", \"label\": \"Type: Name\", \"type\": \"Goal|Process|Data|Resource\",\n"
                "\"next\": [\"2\"]}]. Generate 8-15 nodes. Follow relationship rules from FRAMEWORK OVERVIEW.\n"
                "Example: [{\"id\": \"1\", \"label\": \"Goal: Reduce Churn\", \"type\": \"Goal\", \"next\": [\"2\"]},\n"
                "{\"id\": \"2\", \"label\": \"Process: Handle Tickets\", \"type\": \"Process\", \"next\": [\"3\",\"4\"]},\n"
                "{\"id\": \"3\", \"label\": \"Data: Ticket DB\", \"type\": \"Data\", \"next\": []},\n"
                "{\"id\": \"4\", \"label\": \"Resource: Support Team\", \"type\": \"Resource\", \"next\": []}]."
            )
        },
        "BPMN": {
            "overview": (
                "FRAMEWORK OVERVIEW:\n"
                "- BPMN 2.0 (Business Process Model and Notation): Standard for business process modeling.\n"
                "Core flow elements: Events (Start, Intermediate, End), Activities (Tasks, SubProcesses),\n"
                "Gateways (Exclusive/XOR, Parallel/AND, Inclusive/OR). Connecting objects: Sequence Flows,\n"
                "Message Flows, Associations. Swimlanes: Pools (participants), Lanes (roles/departments).\n"
                "Artifacts: Data Objects, Groups, Text Annotations. Processes flow: Start → Activities →\n"
                "Gateways for decisions/parallelism → End.\n\n"
            ),
            "syntax": (
                "You MUST output a complete, valid BPMN 2.0 XML document wrapped in ```xml.\n"
                "Do not use pseudo-XML like <BPMN_DIAGRAM>. Use proper namespaces\n"
                "(<bpmn:definitions>, <bpmn:process>, <bpmn:startEvent>).\n"
                "Do NOT use generic <bpmn:Event> or <bpmn:Task> — use specific types:\n"
                "<bpmn:startEvent>, <bpmn:endEvent>, <bpmn:userTask>, <bpmn:serviceTask>,\n"
                "<bpmn:exclusiveGateway>, <bpmn:parallelGateway>.\n"
                "Keep the process completely flat. Do NOT use <bpmn:subProcess>, pools, or groups.\n"
                "Do NOT include <bpmndi:BPMNDiagram>; the frontend generates layout coordinates dynamically."
            )
        }
    }

    fd = framework_data.get(req.framework_selected)
    framework_overview = fd["overview"] if fd else ""
    diagram_syntax = fd["syntax"] if fd else ""

    stage3_prompt = (
        f"You are an expert enterprise architect specializing in {req.framework_selected}.\n\n"
        f"Original User Query: {req.user_query}\n\n"
        f"Hypothetical Blueprint (for structural reference):\n{hypothetical_blueprint}\n\n"
        f"Retrieved Reference Context:\n{context_str}\n\n"
        "CRITICAL CONSTRAINT: If the retrieved reference context is empty or falls short of context metrics matching the user prompt, "
        "you MUST explicitly respond with: 'Information Not Found in Reference Manuals' rather than fabricating enterprise framework configurations.\n\n"
        f"{framework_overview}"
        "BACKEND FORMATTING DIRECTIVE: Separate your response into clear sections: a comprehensive narrative answer "
        "followed by the required diagram syntax wrapped inside standard markdown blocks.\n\n"
        "DIAGRAM SYNTAX MAPPING (CRITICAL):\n"
        f"{diagram_syntax}\n"
    )
    
    interaction.stage3_prompt = stage3_prompt

    completion3 = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": stage3_prompt}],
        max_tokens=4096,
    )
    
    stage3_latency = (time.perf_counter() - start_time) * 1000
    stage3_tokens = completion3.usage.total_tokens if completion3.usage else 0
    await log_telemetry("context_synthesizer", stage3_latency, stage3_tokens)
    
    final_output = completion3.choices[0].message.content or ""
    
    interaction.final_output = final_output
    session.add(interaction)
    session.commit()
    session.refresh(interaction)
    
    return ProcessResponse(
        id=interaction.id,
        final_output=interaction.final_output,
        retrieved_source_pages=interaction.retrieved_source_pages,
        stage1_prompt=interaction.stage1_prompt,
        stage1_semantic_narrative=interaction.stage1_semantic_narrative,
        stage1_blueprint=interaction.stage1_blueprint,
        stage2_query=interaction.stage2_query,
        stage2_chunk_count=interaction.stage2_chunk_count,
        stage3_prompt=interaction.stage3_prompt,
    )


@app.get("/render-plantuml")
async def render_plantuml(encoded: str):
    url = f"https://www.plantuml.com/plantuml/svg/{encoded}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=15.0)
        resp.raise_for_status()
        return Response(content=resp.text, media_type="image/svg+xml")


class ExportRequest(BaseModel):
    framework_selected: str
    model_name: str = "hyde_model"
    stage1_blueprint: str = ""
    final_output: str = ""


@app.post("/export/adl")
async def export_adl(req: ExportRequest):
    adl_content, error = generate_adl(
        stage1_blueprint=req.stage1_blueprint,
        final_output=req.final_output,
        framework_selected=req.framework_selected,
        model_name=req.model_name,
    )
    if error:
        raise HTTPException(status_code=422, detail=error)

    filename = safe_filename(req.model_name) + ".adl"
    return Response(
        content=adl_content.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/export/archimate")
async def export_archimate(req: ExportRequest):
    xml_content, error = generate_archimate(
        stage1_blueprint=req.stage1_blueprint,
        final_output=req.final_output,
        framework_selected=req.framework_selected,
        model_name=req.model_name,
    )
    if error:
        raise HTTPException(status_code=422, detail=error)

    filename = safe_filename(req.model_name) + ".archimate"
    return Response(
        content=xml_content.encode("utf-8"),
        media_type="application/xml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8010, reload=True)
