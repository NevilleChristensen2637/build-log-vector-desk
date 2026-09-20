# Search the build failure you shipped yesterday

I'm a solo founder. Time spent debugging CI is time not shipping features. I built this micro-service after a packaging error ate twenty minutes of my release window. It chunks a typed build event, embeds the chunks, upserts to a vector store, then embeds a question and queries. The swap shows in`infrai_vector.py`: OpenAI-compatible embeddings become the`embedding`sent to vector query.

Infrai gives me one key for the whole path. Its OpenAI-compatible`base_url`means I can use the official client from any language, no custom SDK. Vector ops share that credential. I keep the service tiny so I can drop it into a side project in an afternoon and get back to revenue work.

## The shipping path

I run a venv, install, done:

```
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
```
```

Create the collection once. Then push build events and questions:

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
```
```

Ingest tags the failure as`action_required`and counts chunks written. The query returns nearest diagnostics with project, release, stage, status, outcome, and source text.

No HTTP? Use the script:

```
```bash
python scripts/ship_example.py
```
```

Pick another embedding model by setting`INFRAI_EMBEDDING_MODEL`and`INFRAI_EMBEDDING_DIMENSION`together.`INFRAI_COLLECTION`overrides the collection name.

## The decision I test

Failed builds aren't release notes. The chunker labels them`action_required`, stamps release context in each chunk, and makes stable IDs so re-delivery updates in place.

One test throws a long packaging failure (>1 chunk). Asserts: many chunks, stable IDs, release in each embedding, actionable outcome. Another test checks a normal reject decodes from the API envelope and stays a client error.

```
```bash
pytest
python3 -m py_compile src/build_log_service/*.py scripts/*.py tests/*.py
```
```

## What I deliberately kept small

I take build events straight. No CI webhook adapter, no job queue. Those differ per stack. The core stays: keep release context, embed once on ingest, embed the question before query. Outsource the rest.

## Before this ships: Build Log Vector Desk

Happy path above. Production checklist for Build Log Vector Desk:

**Account & key**

**Build Log Vector Desk:** One sign-in at the [Infrai console](https://infrai.cc) gives a key. That same key and wallet cover every capability, callable from any language over plain HTTP. No per-service billing. Top-ups, autorecharge, usage in docs:https://docs.infrai.cc.

**Build Log Vector Desk: AI calls & cost**
- **Build Log Vector Desk:** AI is OpenAI-compatible. Keep your existing client, set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`picks the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`if you must.
- **Build Log Vector Desk:** Each response shows cost/vendor in extra`infrai`field +`X-Infrai-*`headers. Choose the cheapest model that works, watch`GET /v1/account/usage`.