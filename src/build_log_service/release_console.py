from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_vector import BuildDiagnosticIndex, InfraiError
from .release_documents import BuildEvent, chunk_build_event


class CollectionRequest(BaseModel):
    collection: str = Field(min_length=1)
    dimension: int = Field(gt=0)


class BuildEventRequest(BaseModel):
    collection: str = Field(min_length=1)
    project: str = Field(min_length=1)
    release: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    status: str = Field(min_length=1)
    message: str = Field(min_length=1)
    embedding_model: str = "text-embedding-3-small"


class DiagnosticQuery(BaseModel):
    collection: str = Field(min_length=1)
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    embedding_model: str = "text-embedding-3-small"


class IngestResult(BaseModel):
    release: str
    outcome: str
    chunks_upserted: int


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    client = getattr(app.state, "index", None)
    if client:
        await client.close()


app = FastAPI(title="Build Diagnostic Index", lifespan=lifespan)


def get_index() -> BuildDiagnosticIndex:
    if not hasattr(app.state, "index"):
        app.state.index = BuildDiagnosticIndex()
    return app.state.index


def client_error(error: InfraiError) -> HTTPException:
    status = error.status_code if 400 <= error.status_code < 500 else 502
    return HTTPException(status_code=status, detail={"code": error.code, "message": str(error)})


@app.post("/collections")
async def create_collection(request: CollectionRequest) -> dict[str, str]:
    try:
        await get_index().create_collection(request.collection, request.dimension)
    except InfraiError as error:
        raise client_error(error) from error
    return {"collection": request.collection, "state": "ready"}


@app.post("/build-events", response_model=IngestResult)
async def ingest_build_event(request: BuildEventRequest) -> IngestResult:
    event = BuildEvent(
        project=request.project,
        release=request.release,
        stage=request.stage,
        status=request.status,
        message=request.message,
    )
    chunks = chunk_build_event(event)
    try:
        count = await get_index().ingest(request.collection, chunks, request.embedding_model)
    except InfraiError as error:
        raise client_error(error) from error
    return IngestResult(release=request.release, outcome=chunks[0].metadata["outcome"], chunks_upserted=count)


@app.post("/diagnostics")
async def find_diagnostics(request: DiagnosticQuery) -> dict[str, object]:
    try:
        matches = await get_index().search(
            request.collection, request.query, request.embedding_model, request.top_k
        )
    except InfraiError as error:
        raise client_error(error) from error
    return {"query": request.query, "matches": matches}

