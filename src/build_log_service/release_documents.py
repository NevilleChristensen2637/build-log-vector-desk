from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class BuildEvent:
    project: str
    release: str
    stage: str
    status: str
    message: str


@dataclass(frozen=True)
class DiagnosticChunk:
    chunk_id: str
    text: str
    metadata: dict[str, str]


def chunk_build_event(event: BuildEvent, max_chars: int = 700) -> list[DiagnosticChunk]:
    """Split on lines while preserving the release context in every vector."""
    if max_chars < 80:
        raise ValueError("max_chars must be at least 80")

    prefix = (
        f"Project: {event.project}\nRelease: {event.release}\n"
        f"Stage: {event.stage}\nStatus: {event.status}\n"
    )
    lines = [line.strip() for line in event.message.splitlines() if line.strip()]
    bodies: list[str] = []
    current = ""
    for line in lines or ["No diagnostic message was emitted."]:
        candidate = f"{current}\n{line}".strip()
        if current and len(prefix) + len(candidate) > max_chars:
            bodies.append(current)
            current = line
        else:
            current = candidate
    bodies.append(current)

    outcome = "action_required" if event.status.lower() in {"failed", "error"} else "informational"
    chunks: list[DiagnosticChunk] = []
    for index, body in enumerate(bodies):
        text = prefix + body
        identity = f"{event.project}:{event.release}:{event.stage}:{index}:{text}"
        chunks.append(
            DiagnosticChunk(
                chunk_id=sha256(identity.encode("utf-8")).hexdigest(),
                text=text,
                metadata={
                    "project": event.project,
                    "release": event.release,
                    "stage": event.stage,
                    "status": event.status,
                    "outcome": outcome,
                },
            )
        )
    return chunks

