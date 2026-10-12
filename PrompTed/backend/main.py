from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db_and_tables
from api import prompts, chains, execute, auth, analytics, export

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Prompt Management Tool API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(auth.router)
app.include_router(prompts.router)
app.include_router(chains.router)
app.include_router(execute.router)
app.include_router(analytics.router)
app.include_router(export.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Prompt Management Tool API"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
