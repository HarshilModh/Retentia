# userBox — Build Guide (Authoritative)

> **This is the file to follow when building userBox.** It reflects the **approved plan**:
> a LangGraph ReAct agent + 7 tools + curriculum, on **PostgreSQL + Qdrant**, built
> **strictly to spec** with **static-only verification** (no live LLM calls).
>
> ⚠️ `CLAUDE.md` and `DESIGN.md` describe the *earlier* SQLite + ChromaDB design and are
> **out of date**. Prefer this file. (`LEARN_RAG_TONIGHT.md` is conceptual background and
> still valid.)

---

## 1. Goal

A personalized RAG tutor that runs a **teach → check → grade → adapt** loop with short-term **conversational history**. Each `/chat`
turn runs a **LangGraph ReAct agent** that decides which tools to call. Tools do **dual
retrieval** — a shared **subject KB** (*what* to teach) + a per-learner **userBox** (*how*
to teach this person) — grade the learner, and write back deterministic **EMA mastery** +
**SM-2-lite** scheduling (with accelerated re-testing for failed items) and curriculum progress.

## 2. Locked decisions

1. Build **strictly** to this spec — no extra features/hardening beyond what's listed.
2. **No `OPENAI_API_KEY`** during the build — code must **import and start without a key**.
3. **Verification = static only**: imports/wiring, DB schema, deterministic math (EMA +
   SM-2-lite) via unit tests. The live `curl` flow is **documented, not run**.
4. Provider = OpenAI via `langchain-openai`; all models/constants come from `config.py`.

## 3. Datastore choice (this build)

| Role | Store | Library |
|------|-------|---------|
| Structured state | **PostgreSQL** | SQLAlchemy 2.x + `psycopg` (v3) |
| Vectors | **Qdrant** | `langchain-qdrant` + `qdrant-client` |

---

## 4. Stack & dependencies

`backend/requirements.txt`:
```
fastapi
uvicorn[standard]
python-dotenv
pydantic
langchain
langchain-core
langchain-openai
langchain-qdrant
langchain-text-splitters   # ⚠️ NOT pulled in transitively — list it explicitly
langgraph
qdrant-client
SQLAlchemy>=2
psycopg[binary]
```

`docker-compose.yml` (repo root) — `postgres:16` (user/pass/db = `userbox`) + `qdrant/qdrant`.

`backend/.env.example`:
```
OPENAI_API_KEY=sk-...
CHAT_MODEL=gpt-4o-mini
EMBED_MODEL=text-embedding-3-small
DATABASE_URL=postgresql+psycopg://userbox:userbox@localhost:5432/userbox
QDRANT_URL=http://localhost:6333
```

---

## 5. Architecture

```
POST /chat {user_id, message}
        │
        ▼
  tutor.take_turn ── loads session (pending Q? + chat history) ── builds system prompt
        │
        ▼
  LangGraph create_react_agent  (LLM picks tool order; recursion_limit cap)
        │  user_id injected via RunnableConfig (NOT a tool arg)
   ┌────┴───────────────────────────────────────────────┐
   ▼            ▼              ▼              ▼            ▼
 search_kb  recall_persona  save_memory  pose_question  grade_and_update
 (Qdrant    (Qdrant         (Qdrant      (PG sessions)  (LLM Grade →
  subject_kb) user_box)      user_box)                   EMA + SM-2-lite → PG)
        get_learner_model / select_next_concept   (PG learner state)
        │
        ▼
  returns {answer, tool_trace, mastery_change, suggestions}
```

The LLM only chooses tools and supplies a `quality` score. **Every number that affects
mastery or scheduling is computed in `learner.py`, in plain Python.**

---

## 6. File layout (`backend/app/`)

```
config.py     # env + constants; get_openai_api_key() reads the key LAZILY
db.py         # SQLAlchemy engine/Session/Base + ORM models + CRUD/upsert + init_db
schemas.py    # Pydantic: Grade (structured grading), ChatRequest, IngestDoc/IngestRequest
vectorstore.py# cached QdrantVectorStore singletons + ensure_collection (all lazy)
retrieval.py  # search_subject(query, concept_id?), recall_persona(user_id, query), save_memory
learner.py    # ema(), compute_next_review(streak), apply_grade(), select_next_concept(),
              #   grade_answer()  ← the only LLM call in this module
tutor.py      # 7 @tools, build_agent() (lazy), take_turn()
main.py       # FastAPI + CORS; lifespan startup = init_db + ensure collections; routes
ingest.py     # RecursiveCharacterTextSplitter(1000,150); seed concepts→PG, chunks→subject_kb
backend/seed_docs/   # chromosomes.md, mitosis.md, meiosis.md (filename == concept_id)
backend/tests/       # test_mastery.py, test_db.py
```

### 6.1 `config.py`
Constants: `CHAT_MODEL`, `EMBED_MODEL`, `EMBED_DIM=1536`, `DATABASE_URL`, `QDRANT_URL`,
`SUBJECT_KB_COLLECTION="subject_kb"`, `USER_BOX_COLLECTION="user_box"`, `RETRIEVAL_K=5`,
`PERSONA_K=3`, `MAX_AGENT_STEPS=6`, `MASTERY_ALPHA=0.4`, `MASTERY_THRESHOLD=0.7`,
`BASE_REVIEW_INTERVAL_DAYS=1`, `BASE_FAIL_INTERVAL_DAYS=0.05`, `CONSOLIDATION_THRESHOLD=10`.
**Do not read `OPENAI_API_KEY` at import.** Provide:
```python
def get_openai_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("set OPENAI_API_KEY")
    return key
```

### 6.2 `db.py` — PostgreSQL via SQLAlchemy 2.x
`engine = create_engine(DATABASE_URL, future=True)` (does **not** connect at import).
`SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)`.

ORM models (name the sessions model **`SessionState`**, table `"sessions"`, to avoid
confusion with SQLAlchemy's own Session):

- **concepts**: `id` PK(str), `subject`, `title`, `summary`, `prereqs` JSONB(list), `seq` int.
- **learner_concept**: composite PK `(user_id, concept_id)`; `mastery` float=0.0;
  `status` str='not_started'; `attempts` int=0; `streak` int=0; `misconceptions` JSONB(list);
  `last_seen` timestamptz; `next_review` timestamptz. (`concept_id` → FK `concepts.id`.)
- **sessions**: `user_id` PK; `current_concept_id`; `pending_question`; `chat_history` JSONB(list) (defaults to empty list `[]`).

`init_db()` = `Base.metadata.create_all(engine)` (idempotent, no Alembic).
CRUD helpers returning plain dicts: `upsert_concept`, `get_concepts`, `get_concept`,
`get_learner_concept`, `upsert_learner_concept(**fields)`, `get_all_learner_concepts(user_id)`
(LEFT JOIN concepts↔learner_concept, fill defaults for not-started), `get_session`,
`upsert_session(**fields)`.

### 6.3 `vectorstore.py` — Qdrant (all lazy via `lru_cache`)
```python
@lru_cache(1)
def _embeddings(): return OpenAIEmbeddings(model=EMBED_MODEL)   # built on first use only
@lru_cache(1)
def _client(): return QdrantClient(url=QDRANT_URL)

def ensure_collection(name):
    c = _client()
    if not c.collection_exists(name):
        c.create_collection(name, vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE))

@lru_cache(None)
def _store(name):
    ensure_collection(name)
    return QdrantVectorStore(client=_client(), collection_name=name, embedding=_embeddings())

def get_subject_kb(): return _store(SUBJECT_KB_COLLECTION)
def get_user_box():   return _store(USER_BOX_COLLECTION)
```
`ensure_collection` needs Qdrant but **not** a key (used at startup). `_store`/`_embeddings`
need a key, so they fire only during real ingest/chat — keeping no-key startup intact.

### 6.4 `retrieval.py`
⚠️ **`langchain-qdrant` stores metadata under the payload key `metadata`.** Filter on
`key=f"metadata.{field}"`:
```python
def _meta_filter(key, value):
    return Filter(must=[FieldCondition(key=f"metadata.{key}", match=MatchValue(value=value))])

def search_subject(query, concept_id=None, k=RETRIEVAL_K):
    flt = _meta_filter("concept_id", concept_id) if concept_id else None
    return get_subject_kb().similarity_search(query, k=k, filter=flt)

def recall_persona(user_id, query, k=PERSONA_K):
    return get_user_box().similarity_search(query, k=k, filter=_meta_filter("user_id", user_id))

def save_memory(user_id, text):
    # Save raw memory snippet with type metadata
    get_user_box().add_texts([text], metadatas=[{"user_id": user_id, "type": "snippet"}])
    
    # Memory Consolidation Check:
    # If the number of snippets for user_id in user_box exceeds CONSOLIDATION_THRESHOLD (10),
    # fetch all snippets for the user, invoke the LLM (lazy-loaded ChatOpenAI) to consolidate them 
    # into a unified markdown learner profile (overwriting previous profile), delete all raw snippets 
    # for this user from Qdrant, and save the new profile vector with metadata {"user_id": user_id, "type": "profile"}.
```

### 6.5 `learner.py` — deterministic core
```python
def ema(old, quality, alpha=MASTERY_ALPHA):
    return max(0.0, min(1.0, (1 - alpha) * old + alpha * quality))

def compute_next_review(streak):                 # SM-2-lite: 1, 2, 4, 8 ... days
    return BASE_REVIEW_INTERVAL_DAYS * 2 ** max(0, streak - 1)
```
`apply_grade(user_id, concept_id, quality, misconception=None)`:
- `new = ema(old, quality)`; `attempts += 1`; append misconception if any.
- `passed = quality >= 0.6` → `streak += 1` else `streak = 0`.
- `days = compute_next_review(streak)` if passed else `BASE_FAIL_INTERVAL_DAYS` (approx 1 hour for quick review).
- `status = "mastered" if new >= MASTERY_THRESHOLD else "learning"`.
- persist; return `{old_mastery, new_mastery, status, streak, next_review}`.

`select_next_concept(user_id)` priority: **due reviews → in-progress (lowest mastery) → not-started whose prereqs are all mastered, in `seq` order.**
- *Soft Prerequisite Lock*: Prerequisite checks are only applied to **not-started** concepts. Once a student has started a concept, a drop in a prerequisite's mastery does not lock them out, but instead generates a warning/suggestion to review the prereq.

`grade_answer(title, summary, question, answer) -> Grade`: the only LLM call — build
`ChatOpenAI(...).with_structured_output(Grade)` **inside the function** (lazy) and `.invoke`.

### 6.6 `tutor.py` — agent + tools
7 tools as `@tool`. Tools needing the learner take `config: RunnableConfig` and read
`user_id = config["configurable"]["user_id"]` — **never** a model-supplied arg (LangChain
hides the `config` param from the LLM's schema).

| Tool | Reads/Writes |
|------|--------------|
| `search_kb(query, concept_id?)` | Qdrant subject_kb |
| `recall_persona(query)` | Qdrant user_box (user_id from config) |
| `save_memory(text)` | Qdrant user_box |
| `get_learner_model()` | PG learner state |
| `pose_question(concept_id, text)` | PG sessions (sets pending_question) |
| `grade_and_update(concept_id, answer)` | LLM grade → `apply_grade` → PG; clears pending |
| `select_next_concept()` | PG learner state |

`build_agent()` imports `ChatOpenAI` + `create_react_agent` **inside** the function (lazy),
returns `create_react_agent(llm, TOOLS)`.

`take_turn(user_id, message)`:
- Load session (includes `pending_question` and `chat_history`).
- If `pending_question`, append it to the system prompt with an instruction to call `grade_and_update`.
- Construct input messages: `[SystemMessage(sys)] + chat_history + [HumanMessage(message)]` (keep message history capped at last 10 messages).
- `result = agent.invoke({"messages": messages}, config={"configurable":{"user_id":user_id}, "recursion_limit": 2*MAX_AGENT_STEPS+1})`.
- Append new `HumanMessage(message)` and tutor's final `AIMessage` response back to `chat_history` and persist session to DB.
- Walk `result["messages"]`: collect `tool_trace` from `AIMessage.tool_calls`; pull
  `mastery_change` from the `grade_and_update` `ToolMessage` and `suggestions` from
  `select_next_concept`. Return `{answer, tool_trace, mastery_change, suggestions}`.

### 6.7 `main.py`
Use the **`lifespan`** context manager (not `@app.on_event`) for startup: `init_db()` +
`ensure_collection(SUBJECT_KB_COLLECTION)` + `ensure_collection(USER_BOX_COLLECTION)`.
Routes: `GET /health` → `{"status":"ok"}`; `POST /chat` → `take_turn`;
`GET /progress/{user_id}` → `{concepts, due, next}`; `POST /ingest` → `ingest.ingest_docs(...)`.
Add permissive CORS.

### 6.8 `ingest.py`
`RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)`. Seed 3 concepts
(chromosomes seq0 no prereqs; mitosis seq1 prereq [chromosomes]; meiosis seq2 prereqs
[chromosomes, mitosis]). `ingest_docs(docs)` chunks each doc and `add_texts` into subject_kb
with metadata `{concept_id, source, chunk_index}`. `main()` = `init_db()` + seed + ingest
seed_docs. Runnable as `python -m app.ingest`.

---

## 7. Frontend (`frontend/`, Vite + React + TS) — last phase

One screen, three regions:
- **Progress panel** — concept list, mastery bars, status badges, "due"/"next up".
- **Tutor panel** — conversation, sources/agent-steps from `tool_trace` (collapsible),
  mastery-change display.
- **Controls** — `user_id` picker + ingest panel.

`src/api.ts` exposes `chat`, `getProgress` (and `ingest`) against
`import.meta.env.VITE_API_URL ?? 'http://localhost:8000'`. Build script:
`tsc --noEmit && vite build`.

---

## 8. Build order
1. `requirements.txt`, `docker-compose.yml`, `.env.example`, `seed_docs/`.
2. `config.py` → `db.py` → `schemas.py` → `vectorstore.py`.
3. `retrieval.py` → `ingest.py`.
4. `learner.py`.
5. `tutor.py`.
6. `main.py`.
7. `tests/` + static verification (§9).
8. Frontend.

---

## 9. Verification

### Static (run now — no key, no live services)
```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt pytest

# 1. import/wiring — must succeed with NO key and NO DB connection
env -u OPENAI_API_KEY -u DATABASE_URL -u QDRANT_URL python -c "import app.main; print('OK')"

# 2 & 3. math + DB-schema unit tests  (use `python -m pytest` from backend/ so `app` imports)
python -m pytest -q
```
Test expectations:
- `ema(0,1,0.4)==0.4`; clamps to [0,1]; repeated 1.0s converge >0.9; repeated 0.0s decay.
- `compute_next_review`: streak 1→1, 2→2, 3→4, 4→8; streak 0 floors to base.
- `Base.metadata.tables` contains `concepts`, `learner_concept`, `sessions` with expected
  columns; `learner_concept` PK == `{user_id, concept_id}`.

### Live teach→grade→adapt (DOCUMENTED ONLY — run later with a real key)
```bash
docker compose up -d
export DATABASE_URL=postgresql+psycopg://userbox:userbox@localhost:5432/userbox
export QDRANT_URL=http://localhost:6333
export OPENAI_API_KEY=sk-...
python -m app.ingest
uvicorn app.main:app --port 8000 &
curl -s localhost:8000/progress/alice
curl -s localhost:8000/chat -H 'content-type: application/json' \
  -d '{"user_id":"alice","message":"teach me about mitosis"}'
curl -s localhost:8000/chat -H 'content-type: application/json' \
  -d '{"user_id":"alice","message":"prophase, metaphase, anaphase, telophase"}'
curl -s localhost:8000/progress/alice
```
Expected: correct answers raise mastery (EMA) and push `next_review` out (SM-2-lite); wrong
answers keep mastery low, record a misconception, and schedule a near-term review.

---

## 10. Gotchas (learned the hard way)
- **`langchain-text-splitters` is not transitive** — add it to `requirements.txt` or
  `import RecursiveCharacterTextSplitter` fails.
- **Run tests with `python -m pytest` from `backend/`.** `tests/` has no `__init__.py`, so a
  bare `pytest` puts `tests/` (not `backend/`) on `sys.path` and `import app` fails.
- **Lazy clients everywhere.** Build `ChatOpenAI` / `OpenAIEmbeddings` / `QdrantClient`
  inside functions (or `lru_cache`d factories), never at import — that's what lets
  `import app.main` and `/health` work with no key. `create_engine` is safe at import (it
  doesn't connect).
- **Qdrant filter keys are prefixed `metadata.`** with `langchain-qdrant`.
- **Name the sessions ORM model `SessionState`** (not `Session`) to avoid shadowing.
- Use FastAPI **`lifespan`**, not the deprecated `@app.on_event("startup")`.

## 11. Out of scope
No auth, rate limiting, Alembic/migrations, extra endpoints, retry/backoff, or
integration/live tests beyond the single clear "missing `OPENAI_API_KEY`" error and the
static checks in §9.
