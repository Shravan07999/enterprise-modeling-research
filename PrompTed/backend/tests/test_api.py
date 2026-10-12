from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

# NOTE: absolute imports are required so the dependency override below matches the
# exact `get_session` function object the routes were declared with. Relative
# imports (..main / ..database) load duplicate module copies whose override keys
# never match, silently redirecting test writes to the production database.db.
from main import app
from database import get_session, _ensure_column

# Setup in-memory database for testing
sqlite_file_name = "database_test.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    # Apply lightweight migrations so stale test databases gain new columns
    _ensure_column(engine, "executionhistory", "metrics_json TEXT")

def get_session_override():
    with Session(engine) as session:
        yield session

app.dependency_overrides[get_session] = get_session_override

client = TestClient(app)

def setup_module(module):
    create_db_and_tables()

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Prompt Management Tool API"}

def test_create_prompt():
    response = client.post(
        "/prompts/",
        json={
            "name": "Test Prompt",
            "description": "A test prompt",
            "template": "Hello {{name}}",
            "input_variables": "name"
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Prompt"
    assert data["id"] is not None

def test_read_prompts():
    response = client.get("/prompts/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

def test_execute_prompt():
    # First create a prompt
    response = client.post(
        "/prompts/",
        json={
            "name": "Exec Prompt",
            "template": "Hello {{name}}",
            "input_variables": "name"
        },
    )
    prompt_id = response.json()["id"]
    
    # Execute it
    response = client.post(
        "/execute/",
        json={
            "prompt_id": prompt_id,
            "inputs": {"name": "World"}
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "Hello World" in data["result"]
    # Telemetry: every execution must report latency/token metrics
    assert "metrics" in data
    assert "latency_seconds" in data["metrics"]
    assert "prompt_tokens" in data["metrics"]
    assert "completion_tokens" in data["metrics"]
