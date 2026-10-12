import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Tuple
from sqlmodel import Session, select
from database import get_session
from models import (
    Prompt,
    ExecutionHistory,
    ExecutionHistoryRead,
    AuditLog,
)
import json
import re
import os
import time
from sqlalchemy.orm import selectinload
from dotenv import load_dotenv
import openai

logger = logging.getLogger(__name__)

_available_models = [
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
]

_VISUAL_SCHEMA_INSTRUCTION = """
IMPORTANT: For visual modelling steps (Process, Business Architecture, ArchiMate, Zachman), you MUST append a JSON block at the VERY END of your response.
The block MUST follow this exact schema for compatibility with the visual engine:

```json
{
  "visual_flow": {
    "nodes": [
      { "id": "n1", "type": "actor|process|goal|system", "data": { "label": "NODE_NAME", "description": "Short details" } },
      { "id": "n2", "type": "actor|process|goal|system", "data": { "label": "NODE_NAME", "description": "Short details" } }
    ],
    "edges": [
      { "id": "e1-2", "source": "n1", "target": "n2", "label": "RELATIONSHIP" }
    ]
  }
}
```
"""


router = APIRouter(
    prefix="/execute",
    tags=["execute"],
)


class ExecutionRequest(BaseModel):
    prompt_id: int
    inputs: Dict[str, Any]


class ChainExecutionRequest(BaseModel):
    chain_id: int
    inputs: Dict[str, Any]


@router.post("/")
def execute_prompt(request: ExecutionRequest, session: Session = Depends(get_session)):
    logger.info("Executing prompt %s with inputs: %s", request.prompt_id, request.inputs)

    prompt = session.get(Prompt, request.prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    result_text, metrics = _execute_single_prompt_logic(prompt, request.inputs)

    history = ExecutionHistory(
        prompt_id=prompt.id,
        inputs=json.dumps(request.inputs),
        result=result_text,
        metrics_json=json.dumps(metrics),
    )
    session.add(history)
    session.commit()

    audit = AuditLog(
        user_id=1,
        action="Executed Prompt",
        target_type="prompt",
        target_id=prompt.id,
        details=f"Executed Pattern: {prompt.name}",
    )
    session.add(audit)
    session.commit()

    return {
        "id": history.id,
        "result": result_text,
        "inputs": request.inputs,
        "metrics": metrics,
        "created_at": history.created_at,
    }


@router.post("/chain")
def execute_chain(
    request: ChainExecutionRequest, session: Session = Depends(get_session)
):
    logger.info("Executing chain %s with inputs: %s", request.chain_id, request.inputs)

    from models import Chain

    chain = session.get(Chain, request.chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")

    steps = sorted(chain.steps, key=lambda s: s.order)
    context = request.inputs.copy()

    step_results = []
    step_metrics = []
    final_output = ""

    total_latency = 0.0
    total_prompt_tokens = 0
    total_completion_tokens = 0

    for step in steps:
        logger.debug("Step %s: Executing %s", step.order, step.prompt.name)
        step_inputs = {}

        if step.input_mapping:
            try:
                mapping = json.loads(step.input_mapping)
                for map_key, map_val in mapping.items():
                    if map_val in context:
                        step_inputs[map_key] = context[map_val]
                    else:
                        step_inputs[map_key] = map_val
            except Exception as e:
                logger.warning("Input mapping parse failure: %s", e)

        # Auto-inject all context keys that match prompt input variables
        if step.prompt.input_variables:
            needed_vars = [v.strip() for v in step.prompt.input_variables.split(",")]
            for var in needed_vars:
                if var not in step_inputs and var in context:
                    step_inputs[var] = context[var]

        # Execute
        result_text, step_metric = _execute_single_prompt_logic(step.prompt, step_inputs)

        total_latency += step_metric.get("latency_seconds") or 0.0
        total_prompt_tokens += max(step_metric.get("prompt_tokens") or 0, 0)
        total_completion_tokens += max(step_metric.get("completion_tokens") or 0, 0)

        # Post-processing
        result_text = result_text.strip()
        if result_text.startswith("```markdown") and result_text.endswith("```"):
            result_text = re.sub(r"^```markdown\s*", "", result_text)
            result_text = re.sub(r"\s*```$", "", result_text)
        elif result_text.startswith("```") and result_text.endswith("```"):
            result_text = re.sub(r"^```\s*", "", result_text)
            result_text = re.sub(r"\s*```$", "", result_text)

        # Update Context
        # TRANSIENT KEYS (for immediate next step)
        context["result"] = result_text
        context["previous_step_output"] = result_text

        # PERSISTENT KEYS: Store specifically if it is context/extraction
        low_name = step.prompt.name.lower()
        if "context" in low_name or "extraction" in low_name:
            context["context_extraction"] = result_text

        context[f"step_{step.order}_result"] = result_text

        step_type = "CRITIC" if step.is_critic else "GENERATION"

        step_results.append(
            {
                "step": step.order,
                "prompt_name": step.prompt.name,
                "type": step_type,
                "result": result_text,
            }
        )

        step_metrics.append(
            {
                "step": step.order,
                "prompt_name": step.prompt.name,
                "type": step_type,
                "model": step_metric.get("model"),
                "latency_seconds": step_metric.get("latency_seconds", 0.0),
                "prompt_tokens": step_metric.get("prompt_tokens", -1),
                "completion_tokens": step_metric.get("completion_tokens", -1),
            }
        )

        final_output += f"\n\n### Step {step.order}: {step.prompt.name} ({step_type})\n{result_text}"

    metrics_payload = {
        "steps": step_metrics,
        "totals": {
            "total_latency_seconds": round(total_latency, 3),
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
        },
    }

    # Save History
    first_prompt_id = steps[0].prompt_id if steps else 0
    history = ExecutionHistory(
        prompt_id=first_prompt_id,
        inputs=json.dumps(request.inputs),
        result=final_output,
        metrics_json=json.dumps(metrics_payload),
    )
    session.add(history)
    session.commit()

    # Audit
    audit = AuditLog(
        user_id=1,
        action="Executed Chain",
        target_type="chain",
        target_id=chain.id,
        details=f"Executed Framework {chain.framework}: {chain.name}",
    )
    session.add(audit)
    session.commit()

    return {
        "id": history.id,
        "result": final_output,
        "inputs": request.inputs,
        "steps": step_results,
        "metrics": metrics_payload,
        "created_at": history.created_at,
    }


def _execute_single_prompt_logic(prompt: Prompt, inputs: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    filled_template = prompt.template
    for key, value in inputs.items():
        pattern = re.compile(r"\{\{\s*" + re.escape(str(key)) + r"\s*\}\}")
        filled_template = pattern.sub(str(value), filled_template)

    metrics = {
        "latency_seconds": 0.0,
        "prompt_tokens": -1,
        "completion_tokens": -1,
        "model": "simulation",
    }

    load_dotenv(override=True)
    key = os.getenv("OPENAI_API_KEY")

    if not key or "your_key_here" in key:
        logger.info("OPENAI_API_KEY not configured. Running offline simulation.")
        sim_start = time.perf_counter()
        simulated = run_simulation(prompt.name, "Asset", filled_template)
        metrics["latency_seconds"] = round(time.perf_counter() - sim_start, 3)
        return simulated, metrics

    client = openai.OpenAI(api_key=key.strip())

    system_instruction = (
        "You are an expert Enterprise Architect. "
        "Provide detailed, comprehensive architectural models. "
        "Output MUST be in markdown. "
        "Follow the requested format strictly. "
        "Never wrap your entire response in additional markdown code blocks (backticks)."
    )

    low_name = prompt.name.lower()
    if any(
        k in low_name
        for k in [
            "process",
            "workflow",
            "layer",
            "matrix",
            "archimate",
            "relationship",
            "zachman",
            "goal",
            "model",
        ]
    ):
        system_instruction += _VISUAL_SCHEMA_INSTRUCTION

    success = False
    result_text = ""
    last_error = ""

    for model_name in _available_models:
        try:
            logger.debug("Attempting completion with model %s", model_name)
            messages = [
                {"role": "system", "content": system_instruction},
                {
                    "role": "user",
                    "content": f"Task: {prompt.name}\nContext: {filled_template}",
                },
            ]

            start = time.perf_counter()
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.2,
                top_p=0.95,
            )
            latency_seconds = round(time.perf_counter() - start, 3)

            if not response.choices:
                logger.warning("Model %s returned empty choices list", model_name)
                continue

            usage = getattr(response, "usage", None)
            prompt_tokens = (
                usage.prompt_tokens
                if usage is not None and usage.prompt_tokens is not None
                else -1
            )
            completion_tokens = (
                usage.completion_tokens
                if usage is not None and usage.completion_tokens is not None
                else -1
            )

            result_text = response.choices[0].message.content
            success = True
            metrics = {
                "latency_seconds": latency_seconds,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "model": model_name,
            }
            logger.info(
                "Model %s finished in %.2fs (%s in / %s out tokens)",
                model_name,
                latency_seconds,
                prompt_tokens,
                completion_tokens,
            )
            break
        except Exception as e:
            last_error = str(e)
            logger.warning("Model %s invocation failed: %s", model_name, last_error)
            continue

    if not success:
        logger.warning("All configured models failed (%s). Falling back to local simulation.", last_error)
        sim_start = time.perf_counter()
        simulation_data = run_simulation(prompt.name, "Asset", filled_template)
        metrics["latency_seconds"] = round(time.perf_counter() - sim_start, 3)
        result_text = f"> [!NOTE]\n> **Offline Simulation**: Live model execution unavailable. Generated using deterministic local architectural model synthesis.\n\n{simulation_data}"

    return result_text, metrics


def run_simulation(name: str, equipment: str, filled_template: str) -> str:
    name_low = name.lower()

    # Try to extract some context from any available input to make it feel less "generic"
    discovered_nodes = []

    # Attempt to find nouns or capitalized words as pseudo-nodes
    words = re.findall(r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)", filled_template)
    if words:
        discovered_nodes = list(
            set(
                [
                    w
                    for w in words
                    if len(w) > 3
                    and w
                    not in [
                        "Scenario",
                        "Analyze",
                        "Task",
                        "Context",
                        "Output",
                        "Nexus",
                        "Cargo",
                    ]
                ]
            )
        )

    def get_type(node_name: str) -> str:
        ln = node_name.lower()
        if any(
            x in ln
            for x in [
                "manager",
                "actor",
                "fleet",
                "hub",
                "stakeholder",
                "authority",
                "driver",
                "sponsor",
            ]
        ):
            return "actor"
        if any(
            x in ln
            for x in [
                "iot",
                "sensor",
                "controller",
                "system",
                "database",
                "app",
                "server",
                "nexus",
                "cargo",
            ]
        ):
            return "system"
        if any(
            x in ln for x in ["goal", "target", "objective", "reduction", "footprint"]
        ):
            return "goal"
        return "process"

    # Limit to 5 for simulation simplicity
    discovered_nodes = discovered_nodes[:5]

    if "context" in name_low or "extraction" in name_low:
        return json.dumps(
            {
                "actors": discovered_nodes
                if discovered_nodes
                else ["Executive Sponsor", "Operations Manager"],
                "goals": ["Optimize Performance", "Reduce Operational Risk"],
                "processes": ["Core Business Process", "Exception Handling"],
            },
            indent=2,
        )

    if "goal" in name_low:
        return f"### 4EM Goal Model (Simulated)\n- **Strategic Goal**: {discovered_nodes[0] if len(discovered_nodes) > 0 else 'Excellence'}\n- **Operational Goal**: {discovered_nodes[1] if len(discovered_nodes) > 1 else 'Efficiency'}"

    # Specific simulation for ArchiMate Layering
    if "archimate" in name_low and "layer" in name_low:
        # Sort nodes by type for better layering
        actors = [n for n in discovered_nodes if get_type(n) == "actor"]
        procs = [n for n in discovered_nodes if get_type(n) == "process"]
        systems = [n for n in discovered_nodes if get_type(n) == "system"]

        # Fallbacks
        n1 = actors[0] if actors else "Business Actor"
        n2 = procs[0] if procs else "Core Process"
        n3 = systems[0] if systems else "IoT Infrastructure"

        return f"""### ArchiMate Layering (Simulated)
This model maps the architecture into Business, Application, and Technology layers.

#### Identified Elements:
1.  **Business Layer**: {n1} - Human or organizational entities.
2.  **Application Layer**: {n2} - Logical process and software services.
3.  **Technology Layer**: {n3} - Physical devices and networks.

```json
{{
  "visual_flow": {{
    "nodes": [
      {{ "id": "b1", "type": "actor", "data": {{ "label": "{n1}", "description": "Key business stakeholder" }} }},
      {{ "id": "a1", "type": "process", "data": {{ "label": "{n2}", "description": "Operational workflow" }} }},
      {{ "id": "t1", "type": "system", "data": {{ "label": "{n3}", "description": "Technological realization" }} }}
    ],
    "edges": [
      {{ "id": "e1", "source": "b1", "target": "a1", "label": "Uses" }},
      {{ "id": "e2", "source": "a1", "target": "t1", "label": "Realized by" }}
    ]
  }}
}}
```
"""

    # Specific simulation for ArchiMate Relationship Mapping
    if "archimate" in name_low and "relationship" in name_low:
        systems = [n for n in discovered_nodes if get_type(n) == "system"]
        procs = [n for n in discovered_nodes if get_type(n) == "process"]

        n1 = procs[0] if procs else "Gateway Interface"
        n2 = systems[0] if systems else "Legacy DB"

        return f"""### ArchiMate Relationships (Simulated)
Detailed mapping of cross-layer dependencies.

```json
{{
  "visual_flow": {{
    "nodes": [
      {{ "id": "n1", "type": "process", "data": {{ "label": "{n1}", "description": "Operational Interface" }} }},
      {{ "id": "n2", "type": "system", "data": {{ "label": "{n2}", "description": "Backend realization" }} }}
    ],
    "edges": [
      {{ "id": "e1-2", "source": "n1", "target": "n2", "label": "Serving" }}
    ]
  }}
}}
```
"""

    if "process" in name_low or "workflow" in name_low:
        nlist = [n for n in discovered_nodes if get_type(n) == "process"]
        s1 = nlist[0] if len(nlist) > 0 else "Trigger Event"
        s2 = nlist[1] if len(nlist) > 1 else "Core Task"
        s3 = nlist[2] if len(nlist) > 2 else "Completion"
        return f"""### Process Model (Simulated)
Workflow generated based on scenario keywords.

```json
{{
  "visual_flow": {{
    "nodes": [
      {{ "id": "1", "type": "process", "data": {{ "label": "{s1}", "description": "Starting phase" }} }},
      {{ "id": "2", "type": "process", "data": {{ "label": "{s2}", "description": "Core analysis" }} }},
      {{ "id": "3", "type": "process", "data": {{ "label": "{s3}", "description": "Output generation" }} }}
    ],
    "edges": [
      {{ "id": "e1-2", "source": "1", "target": "2" }},
      {{ "id": "e2-3", "source": "2", "target": "3" }}
    ]
  }}
}}
```
"""

    if "zachman" in name_low and "matrix" in name_low:
        return """### Zachman Matrix (Simulated)
Classification across 6 interrogatives and 6 perspectives.

```json
{
  "visual_flow": {
    "nodes": [
      { "id": "z1", "type": "process", "data": { "label": "Executive View", "description": "Planner Perspective" } },
      { "id": "z2", "type": "process", "data": { "label": "Business View", "description": "Owner Perspective" } }
    ],
    "edges": [
      { "id": "ez1", "source": "z1", "target": "z2", "label": "Determines" }
    ]
  }
}
```
"""
    if "vision" in name_low:
        return "### TOGAF Vision (Simulated)\nStrategic alignment of IT with business goals. High-level roadmap for digital transformation."

    if "critic" in name_low:
        return "### Validation Report (Simulated)\n-  Model structure is sound.\n-  Suggestion: Detail cross-layer mappings for ArchiMate compliance."

    return (
        f"### Simulation Output for {name}\n"
        f"Generate architectural content for: {filled_template[:100]}...\n"
        f"(Simulated deterministic output)"
    )


@router.get("/history", response_model=List[ExecutionHistoryRead])
def get_history(session: Session = Depends(get_session)):
    statement = (
        select(ExecutionHistory)
        .order_by(ExecutionHistory.created_at.desc())
        .options(selectinload(ExecutionHistory.prompt))
    )
    history = session.exec(statement).all()

    results = []
    for h in history:
        results.append(
            ExecutionHistoryRead(
                id=h.id,
                prompt_id=h.prompt_id,
                inputs=h.inputs,
                result=h.result,
                created_at=h.created_at,
                prompt=h.prompt,
                metrics=json.loads(h.metrics_json) if h.metrics_json else None,
            )
        )
    return results
