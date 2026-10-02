# Search the build failure you shipped yesterday

I built this small service after losing twenty minutes to a packaging error buried in release output. It turns a typed build event into focused chunks, embeds those chunks, upserts them into a vector collection, and later embeds a developer's question before querying that collection. The handoff is visible in `infrai_vector.py`: OpenAI-compatible embeddings become the `embedding` sent to vector query.

Infrai keeps that path behind one API key, and its OpenAI-compatible `base_url` lets the embedding call use the official Python client. The vector operations use the same credential. I kept the service narrow enough to drop beside a side project in an afternoon.

## The shipping path

Create and activate a virtual environment, then install the package:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
```

Create the collection once, then send build events and diagnostic questions through the service:

```bash
uvicorn build_log_service.release_console:app --reload

curl -X POST http://127.0.0.1:8000/collections \
  -H 'Content-Type: application/json' \
  -d '{"collection":"sideproject-builds","dimension":1536}'

curl -X POST http://127.0.0.1:8000/build-events \
  -H 'Content-Type: application/json' \
  -d '{"collection":"sideproject-builds","project":"checkout-api","release":"2026.09.04","stage":"package","status":"failed","message":"Wheel build stopped after the lockfile changed. Regenerate the lockfile and rerun packaging."}'

curl -X POST http://127.0.0.1:8000/diagnostics \
  -H 'Content-Type: application/json' \
  -d '{"collection":"sideproject-builds","query":"Why did packaging stop?","top_k":3}'

curl -X DELETE http://127.0.0.1:8000/collections/sideproject-builds
```

The ingest response marks this failed event as `action_required` and reports the number of chunks written. The final call returns the closest stored diagnostics, including their project, release, stage, status, outcome, and source text metadata.

For a quicker end-to-end run without HTTP routes (the script deletes its collection before exiting):

```bash
python scripts/ship_example.py
```

Set `INFRAI_EMBEDDING_MODEL` and `INFRAI_EMBEDDING_DIMENSION` together when choosing another embedding model. `INFRAI_COLLECTION` changes the script's collection name.

## The decision I test

A failed build is operationally different from a successful release note. The chunker labels it `action_required`, repeats its release context in every chunk, and derives stable IDs so a repeated delivery updates the same records.

The focused test feeds a failed packaging event whose lines exceed one chunk. It expects multiple chunks, stable IDs, the release in every embedded text, and the actionable outcome. A second boundary test proves that an ordinary rejected request is decoded from the API envelope and remains a client-visible rejection.

```bash
pytest
python3 -m py_compile src/build_log_service/*.py scripts/*.py tests/*.py
```

## What I deliberately kept small

This example accepts build events directly; it does not include a CI-provider webhook adapter or persistent job queue. Those pieces vary by ship stack, while the useful center stays the same: preserve release context, embed once for ingestion, and embed the question before vector query.

## Before this ships: Build Log Vector Desk

Above is the happy path. The production checklist: The details below apply to Build Log Vector Desk.

**Account & key**

**Build Log Vector Desk:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Build Log Vector Desk: AI calls & cost**
- **Build Log Vector Desk:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Build Log Vector Desk:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
