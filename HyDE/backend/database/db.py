from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import Column, inspect, text as sa_text
from sqlalchemy.types import JSON, Text
from sqlmodel import Field, Session, SQLModel, create_engine

DATABASE_PATH = Path(__file__).parent / "hyde.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


class HydeInteraction(SQLModel, table=True):
    __tablename__ = "hyde_interactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    framework_selected: str = Field(nullable=False, index=True)
    user_query: str = Field(nullable=False)
    retrieved_source_pages: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=[]),
    )
    final_output: str = Field(default="", nullable=False)

    # Pipeline trace fields
    stage1_prompt: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    stage1_semantic_narrative: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    stage1_blueprint: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    stage2_query: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    stage2_chunk_count: int | None = Field(default=None, nullable=True)
    stage3_prompt: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )


# SQLite doesn't support IF NOT EXISTS on ALTER TABLE, so we diff manually.
def _migrate() -> None:
    columns = {c["name"] for c in inspect(engine).get_columns("hyde_interactions")}
    new_cols = [
        ("stage1_prompt", "TEXT"),
        ("stage1_semantic_narrative", "TEXT"),
        ("stage1_blueprint", "TEXT"),
        ("stage2_query", "TEXT"),
        ("stage2_chunk_count", "INTEGER"),
        ("stage3_prompt", "TEXT"),
    ]
    with engine.connect() as conn:
        for col, col_type in new_cols:
            if col not in columns:
                conn.execute(sa_text(f"ALTER TABLE hyde_interactions ADD COLUMN {col} {col_type}"))
        conn.commit()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    try:
        _migrate()
    except Exception:
        pass


def get_session():
    with Session(engine) as session:
        yield session


if __name__ == "__main__":
    init_db()
    print(f"db ready at {DATABASE_PATH}")

    with Session(engine) as session:
        rec = HydeInteraction(
            framework_selected="TOGAF",
            user_query="Test query",
            retrieved_source_pages=["page_1", "page_2"],
            final_output="Test output",
            stage1_prompt="test prompt",
            stage1_semantic_narrative="test narrative",
            stage1_blueprint="test blueprint",
            stage2_query="test query",
            stage2_chunk_count=3,
            stage3_prompt="test stage3 prompt",
        )
        session.add(rec)
        session.commit()
        session.refresh(rec)

        fetched = session.get(HydeInteraction, rec.id)
        assert fetched is not None
        assert fetched.stage1_semantic_narrative == "test narrative"
        assert fetched.stage2_chunk_count == 3

        session.delete(fetched)
        session.commit()
        print(f"smoke test passed (id={rec.id})")
