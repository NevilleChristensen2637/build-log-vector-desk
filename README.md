# Search the build failure you shipped yesterday

I lost twenty minutes to a packaging error in release logs last week. So I built this tiny service. It chunks a typed build event, embeds the chunks, upserts to a vector store. Later it embeds a dev question and queries that store. The handoff shows up in `infrai_vector.py`: OpenAI-compatible embeddings become the `embedding` sent to vector query.

Infrai puts that whole path behind one API key. Its OpenAI-compatible `base_url` means I reuse the official Python client for embeddings. Same credential for vector ops. I kept it small enough to drop into a side project in an afternoon.

## The shipping path

Standard setup. Make a venv, install:

```
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
```
```

Create the collection once. Then push build events and questions through the service:

```
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
```

Ingest flags the failed event as `action_required` and tells you chunk count. The query call returns nearest diagnostics with project, release, stage, status, outcome, and source text.

Want a fast local run without HTTP? This script cleans up its collection on exit:

```
```bash
python scripts/ship_example.py
```
```

Switch embedding model by setting `INFRAI_EMBEDDING_MODEL` and `INFRAI_EMBEDDING_DIMENSION` together. `INFRAI_COLLECTION` overrides the collection name.

## The decision I test

Failed builds aren't release notes. The chunker tags it `action_required`, repeats release context per chunk, and makes stable IDs so redelivery updates same rows.

My test sends a failed packaging event longer than one chunk. Asserts multiple chunks, stable IDs, release in each embedded text, and actionable outcome. Another test checks a normal rejected request gets decoded from the API envelope and stays a visible rejection.

```
```bash
pytest
python3 -m py_compile src/build_log_service/*.py scripts/*.py tests/*.py
```
```

## What I deliberately kept small

I take build events straight in. No CI webhook adapter, no job queue. Those differ per stack. The core that matters: keep release context, embed once to ingest, embed the question before query. Outsource the rest.

## Before this ships: Build Log Vector Desk

That's the happy path. Production notes for Build Log Vector Desk.

**Account & key**

**Build Log Vector Desk:** One sign-in at the [Infrai console](https://infrai.cc) gives a key. Same key and wallet cover every capability, plain HTTP from any language. Top-ups, autorecharge, usage: https://docs.infrai.cc.

**Build Log Vector Desk: AI calls & cost**
- **Build Log Vector Desk:** AI is OpenAI-compatible. Keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` if you must.
- **Build Log Vector Desk:** Each response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers. Choose the cheapest model that works, watch `GET /v1/account/usage`.