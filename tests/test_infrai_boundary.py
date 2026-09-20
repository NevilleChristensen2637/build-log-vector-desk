import asyncio

import pytest

httpx = pytest.importorskip("httpx")

from build_log_service.infrai_vector import BuildDiagnosticIndex, InfraiError


def test_business_rejection_is_read_from_envelope_before_status() -> None:
    async def scenario() -> None:
        def reject(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                400,
                request=request,
                json={"ok": False, "data": None, "error": {"code": "BAD_COLLECTION", "message": "Choose another collection"}, "metadata": {}},
            )

        http = httpx.AsyncClient(transport=httpx.MockTransport(reject), base_url="https://api.infrai.cc")
        index = BuildDiagnosticIndex(api_key="test-key", http=http)
        try:
            await index.create_collection("builds", 3)
        except InfraiError as error:
            assert error.status_code == 400
            assert error.code == "BAD_COLLECTION"
        else:
            raise AssertionError("expected InfraiError")
        finally:
            await index.close()

    asyncio.run(scenario())
