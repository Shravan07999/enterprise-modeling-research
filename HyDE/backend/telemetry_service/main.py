import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="HyDE Telemetry", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

METRICS_LOG_PATH = Path(__file__).parent / "metrics.log"

_write_lock = asyncio.Lock()


class LogEntry(BaseModel):
    stage_name: str
    latency_ms: float
    token_count: int = 0


class LogEntryResponse(BaseModel):
    timestamp: str
    stage_name: str
    latency_ms: float
    token_count: int


def _sync_append(line: str) -> None:
    with open(METRICS_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)


def _sync_read_all() -> list[dict]:
    if not METRICS_LOG_PATH.exists():
        return []
    entries: list[dict] = []
    with open(METRICS_LOG_PATH, "r", encoding="utf-8") as f:
        for raw_line in f:
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                entries.append(json.loads(stripped))
            except json.JSONDecodeError:
                continue
    return entries


async def append_log_entry(record: dict) -> None:
    line = json.dumps(record, ensure_ascii=False) + "\n"
    async with _write_lock:
        await asyncio.to_thread(_sync_append, line)


async def read_all_entries() -> list[dict]:
    return await asyncio.to_thread(_sync_read_all)


@app.post("/log", response_model=LogEntryResponse, status_code=201)
async def create_log(entry: LogEntry):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage_name": entry.stage_name,
        "latency_ms": entry.latency_ms,
        "token_count": entry.token_count,
    }
    await append_log_entry(record)
    return LogEntryResponse(**record)


@app.get("/metrics", response_model=list[LogEntryResponse])
async def get_metrics():
    return await read_all_entries()


@app.delete("/metrics", status_code=204)
async def clear_metrics():
    async with _write_lock:
        await asyncio.to_thread(lambda: METRICS_LOG_PATH.write_text("", encoding="utf-8"))
    return None


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "telemetry", "port": 8011}
