from sqlmodel import SQLModel, create_engine, Session

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=False, connect_args=connect_args)


def _ensure_column(target_engine, table: str, column_ddl: str) -> None:
    """Add a column if not present (SQLite table alteration fallback)."""
    try:
        with target_engine.connect() as conn:
            conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column_ddl}")
            conn.commit()
    except Exception:
        pass


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _ensure_column(engine, "executionhistory", "metrics_json TEXT")
    _ensure_column(engine, "exportlog", "prompt_tokens INTEGER")
    _ensure_column(engine, "exportlog", "completion_tokens INTEGER")


def get_session():
    with Session(engine) as session:
        yield session
