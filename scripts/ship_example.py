import asyncio
import os

from build_log_service.infrai_vector import BuildDiagnosticIndex
from build_log_service.release_documents import BuildEvent, chunk_build_event


async def main() -> None:
    collection = os.environ.get("INFRAI_COLLECTION", "sideproject-builds")
    model = os.environ.get("INFRAI_EMBEDDING_MODEL", "text-embedding-3-small")
    dimension = int(os.environ.get("INFRAI_EMBEDDING_DIMENSION", "1536"))
    index = BuildDiagnosticIndex()
    created = False
    try:
        await index.create_collection(collection, dimension)
        created = True
        event = BuildEvent(
            project="checkout-api",
            release="2026.09.04",
            stage="package",
            status="failed",
            message="Wheel build stopped after the lockfile changed.\nRegenerate the lockfile and rerun packaging.",
        )
        count = await index.ingest(collection, chunk_build_event(event), model)
        matches = await index.search(collection, "Why did packaging stop?", model, top_k=3)
        print({"chunks_upserted": count, "diagnostics": matches})
    finally:
        try:
            if created:
                await index.delete_collection(collection)
        finally:
            await index.close()


if __name__ == "__main__":
    asyncio.run(main())
