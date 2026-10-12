"""Persistence layer for pipeline runs using SQLModel and SQLite."""

import json
import os
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, create_engine, Session

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.join(_SCRIPT_DIR, "qrew.db")
_DB_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(_DB_URL, echo=False)


class QRewRun(SQLModel, table=True):
    __tablename__ = "qrew_runs"

    run_id: str = Field(primary_key=True)
    timestamp: str
    pipeline_strategy: str
    framework_target: str
    metrics_json: str = Field(default="{}")
    traces_json: str = Field(default="{}")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def init_db():
    SQLModel.metadata.create_all(engine)


def save_run(payload: dict):
    with Session(engine) as session:
        run = QRewRun(
            run_id=payload["run_id"],
            timestamp=payload["timestamp"],
            pipeline_strategy=payload["pipeline_strategy"],
            framework_target=payload["framework_target"],
            metrics_json=json.dumps(payload["metrics"]),
            traces_json=json.dumps(payload["traces"]),
        )
        session.add(run)
        session.commit()
