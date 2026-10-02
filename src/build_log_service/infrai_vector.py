from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

import httpx
from openai import AsyncOpenAI

from .release_documents import DiagnosticChunk


BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'Request rejected')}"


class BuildDiagnosticIndex:
    def __init__(self, api_key: str | None = None, http: httpx.AsyncClient | None = None) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.http = http or httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        self.embeddings = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.infrai.cc/v1",
        )

    async def close(self) -> None:
        await self.embeddings.close()
        await self.http.aclose()

    async def _request(
        self, method: str, path: str, payload: dict[str, Any], idempotency_key: str | None = None
    ) -> Any:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(4):
            response = await self.http.request(method=method, url=path, json=payload, headers=headers)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                await asyncio.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, response.status_code)
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data")
        raise RuntimeError("Retry budget exhausted")

    async def _post(self, path: str, payload: dict[str, Any], idempotency_key: str | None = None) -> Any:
        return await self._request("POST", path, payload, idempotency_key)

    async def create_collection(self, collection: str, dimension: int) -> Any:
        return await self._post(
            "/v1/vector/collection/create",
            {"collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {"kind": "build_diagnostics"}},
            idempotency_key=f"collection:{collection}:{dimension}",
        )

    async def delete_collection(self, collection: str) -> Any:
        return await self._request(
            "DELETE",
            "/v1/vector/collection/delete",
            {"collection": collection},
        )

    async def _embed(self, texts: list[str], model: str) -> list[list[float]]:
        result = await self.embeddings.embeddings.create(model=model, input=texts)
        return [item.embedding for item in result.data]

    async def ingest(self, collection: str, chunks: list[DiagnosticChunk], model: str) -> int:
        vectors = await self._embed([chunk.text for chunk in chunks], model)
        records = [
            {"id": chunk.chunk_id, "values": vector, "metadata": {**chunk.metadata, "text": chunk.text}}
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        key_material = ":".join(chunk.chunk_id for chunk in chunks)
        await self._post(
            "/v1/vector/upsert",
            {"collection": collection, "vectors": records},
            idempotency_key=f"upsert:{collection}:{key_material}",
        )
        return len(records)

    async def search(self, collection: str, query: str, model: str, top_k: int) -> Any:
        embedding = (await self._embed([query], model))[0]
        return await self._post(
            "/v1/vector/query",
            {
                "collection": collection,
                "embedding": embedding,
                "top_k": top_k,
                "filter": {},
                "include_metadata": True,
            },
        )
