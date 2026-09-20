from build_log_service.release_documents import BuildEvent, chunk_build_event


def test_failed_release_becomes_actionable_chunks_with_stable_ids() -> None:
    event = BuildEvent(
        project="checkout-api",
        release="2026.09.04",
        stage="package",
        status="failed",
        message="Dependency resolution stopped.\nPin the conflicting package.\nPublish again after tests pass.",
    )

    first = chunk_build_event(event, max_chars=130)
    second = chunk_build_event(event, max_chars=130)

    assert len(first) > 1
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert all(chunk.metadata["outcome"] == "action_required" for chunk in first)
    assert all("Release: 2026.09.04" in chunk.text for chunk in first)

