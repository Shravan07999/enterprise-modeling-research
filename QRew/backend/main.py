"""FastAPI application entrypoint and export endpoints."""

import sys
import os
import json
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

from pipeline import QRewPipeline
from database import init_db, save_run
from exporters.factory import get_exporter
from validators import validate_canonical, validate_adl_output, validate_archimate_output

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

engine = QRewPipeline()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QRewRequest(BaseModel):
    user_input: str
    framework_choice: str


class QRewResponse(BaseModel):
    run_id: str
    timestamp: str
    pipeline_strategy: str
    framework_target: str
    metrics: dict
    traces: dict


class ExportRequest(BaseModel):
    run_id: str
    format: str  # "adl" or "archimate"


class ExportStatusResponse(BaseModel):
    run_id: str
    framework: str
    canonical_model_available: bool
    formats_available: list
    validation_warnings: list


app = FastAPI(
    title="QRew API",
    description="Enterprise architecture query rewriter and diagram generator API.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.post("/api/qrew/run", response_model=QRewResponse)
def run_qrew(req: QRewRequest):
    framework = req.framework_choice.upper()
    try:
        payload = engine.run_qrew_pipeline(req.user_input, framework)
        save_run(payload)
        return QRewResponse(**payload)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Pipeline run failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail={"error": "Pipeline run failed", "detail": str(e)},
        )


@app.post("/api/qrew/export")
def export_model(req: ExportRequest):
    """Export canonical model to ADL or ArchiMate format."""
    # Load run from database
    from database import engine as db_engine
    from sqlmodel import Session, select
    from database import QRewRun

    with Session(db_engine) as session:
        run = session.exec(select(QRewRun).where(QRewRun.run_id == req.run_id)).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        traces = json.loads(run.traces_json)
        canonical_model = traces.get("canonical_model")
        if not canonical_model:
            if "elements" in traces and "relationships" in traces:
                canonical_model = traces
            else:
                raise HTTPException(status_code=400, detail="Canonical model not available for this run")

        framework = canonical_model.get("framework", "")
        # fallback framework
        if not framework:
            framework = canonical_model.get("metadata", {}).get("framework", "")
        
        format = req.format.lower()

        # Validate format matches framework
        if format == "adl" and framework != "4EM":
            raise HTTPException(status_code=400, detail=f"Format 'adl' not supported for framework '{framework}'")
        if format == "archimate" and framework != "BPMN":
            raise HTTPException(status_code=400, detail=f"Format 'archimate' not supported for framework '{framework}'")

        # Normalize canonical model entities against active schema
        from config import CANONICAL_TYPE_MAP_BPMN, CANONICAL_TYPE_MAP_4EM
        VALID_CANONICAL_TYPES = {
            "goal", "process", "actor", "org_unit", "role", "problem",
            "info_set", "product", "component", "feature", "tech_component",
            "concept", "attribute",
            "biz_actor", "biz_process", "biz_service", "biz_function",
            "biz_event", "biz_role", "biz_object",
            "app_component", "app_service", "app_function",
            "data_object", "artifact", "device", "node", "system_software",
            "tech_service", "tech_function", "tech_interface", "comm_network",
            "equipment", "facility", "junction", "grouping", "location",
            "driver", "stakeholder", "assessment", "principle", "requirement",
            "constraint", "outcome", "event", "gateway",
        }
        VALID_LAYERS = {"goals", "processes", "actors", "technical",
                        "business", "application", "technology",
                        "physical", "motivation", "implementation", None}
        type_map = CANONICAL_TYPE_MAP_4EM if framework == "4EM" else CANONICAL_TYPE_MAP_BPMN
        for elem in canonical_model.get("elements", []):
            ct = elem.get("canonicalType", "")
            if ct not in VALID_CANONICAL_TYPES:
                ft = elem.get("frameworkType", "")
                elem["canonicalType"] = type_map.get(ft, type_map.get(ct, "grouping"))
                logger.info(f"Sanitized canonicalType: '{ct}' -> '{elem['canonicalType']}' for '{elem.get('name')}'")
            if elem.get("layer") not in VALID_LAYERS:
                elem["layer"] = "business" if framework == "BPMN" else elem.get("submodel")

        validation = validate_canonical(canonical_model)
        if not validation.passed:
            raise HTTPException(status_code=500, detail={"error": "Invalid canonical model", "details": validation.errors})

        try:
            exporter = get_exporter(format)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        logger.info("export_requested", extra={"run_id": req.run_id, "format": format, "framework": framework})
        try:
            file_bytes = exporter.export(canonical_model)
        except Exception as e:
            logger.exception("Export serialization failed: %s", e)
            raise HTTPException(status_code=500, detail={"error": "Export serialization failed", "details": str(e)})

        if format == "adl":
            output_validation = validate_adl_output(file_bytes.decode("utf-8"))
        else:
            output_validation = validate_archimate_output(file_bytes)

        warnings = validation.warnings + output_validation.warnings
        filename = f"model.{format}"

        logger.info("export_completed", extra={
            "run_id": req.run_id,
            "format": format,
            "file_size_bytes": len(file_bytes),
            "warnings": warnings
        })

        # Return streaming response
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        if warnings:
            headers["X-Validation-Warnings"] = json.dumps(warnings)

        return StreamingResponse(
            iter([file_bytes]),
            media_type="application/octet-stream",
            headers=headers
        )


@app.get("/api/qrew/export/status/{run_id}", response_model=ExportStatusResponse)
def export_status(run_id: str):
    """Check export availability for a run."""
    from database import engine as db_engine
    from sqlmodel import Session, select
    from database import QRewRun

    with Session(db_engine) as session:
        run = session.exec(select(QRewRun).where(QRewRun.run_id == run_id)).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        traces = json.loads(run.traces_json)
        canonical_model = traces.get("canonical_model")

        if not canonical_model:
            return ExportStatusResponse(
                run_id=run_id,
                framework=run.framework_target,
                canonical_model_available=False,
                formats_available=[],
                validation_warnings=[]
            )

        framework = canonical_model.get("framework", "")
        formats = []
        if framework == "4EM":
            formats = ["adl"]
        elif framework == "BPMN":
            formats = ["archimate"]

        validation = validate_canonical(canonical_model)

        return ExportStatusResponse(
            run_id=run_id,
            framework=framework,
            canonical_model_available=True,
            formats_available=formats,
            validation_warnings=validation.warnings
        )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
