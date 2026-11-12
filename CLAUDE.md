# Retentia (repo: userBox)

A tutoring agent that tracks what each student knows and decides the next study step.
Today it is a three-concept biology demo. The goal is a subject-agnostic tutor: a student
uploads their own material, the app generates a private course from it, and a
deterministic policy picks the next step (learn, revise, practice, check, stop) with a
one-line reason.

**The roadmap is `docs/PLAN.md`. Read it before planning any change.**
`BUILD_PLAN.md` describes how v1 was built and is stale in places (it mentions OpenAI and
other values that changed). Where it disagrees with the code, the code is right.

## Stack

- Backend: FastAPI, LangGraph `create_react_agent`, LangChain, Gemini (`langchain-google-genai`)
- Data: PostgreSQL via SQLAlchemy 2 + psycopg 3; Qdrant via `langchain-qdrant`
- Frontend: Vite + React + TypeScript
- Specs: OpenSpec (CLI installed, not yet initialised in this repo)

## Commands

```bash
docker compose up -d                                  # Postgres on 5433, Qdrant on 6333
cd backend && . .venv/bin/activate
python -m pytest -q                                   # run from backend/ so `app` imports
python ingest.py                                      # seed the demo concepts
uvicorn main:app --reload --port 8000
cd frontend && npm run dev                            # npm run build = tsc --noEmit && vite build
```

## Where things are

| Path | What it holds |
|---|---|
| `backend/app/core/learner.py` | Mastery math, scheduling, next-concept selection, LLM grader |
| `backend/app/core/tutor.py` | The 7 agent tools, system prompt, `take_turn` and its streaming twin |
| `backend/app/core/retrieval.py` | Qdrant search over course content and per-student memories |
| `backend/app/db/models.py`, `crud.py` | Tables and all database access |
| `backend/ingest.py` | Chunking and the hard-coded demo concepts |
| `backend/app/api/routes/` | `/chat`, `/chat/stream`, `/progress`, `/ingest` |
| `frontend/src/components/` | Chat, dashboard and progress panels |

## Rules that must keep holding

1. **Numbers are computed in Python, never by the LLM.** Mastery, streaks, intervals and the
   next step come from deterministic code. The LLM grades an answer and writes prose.
2. **The decision is not the agent's.** The policy decides the next step; the agent carries
   it out. The agent must not be able to question a concept the policy did not select
   unless the student explicitly asked for it.
3. **Policy and mastery code are pure.** They take plain state and a `now` argument and
   return a result. No database calls and no `datetime.now()` inside them, so the
   simulator and unit tests can run them without Postgres or an API key.
4. **`user_id` and `course_id` reach tools through `RunnableConfig`,** never as arguments the
   LLM fills in.
5. **Every query is filtered by owner.** Courses are private to the student who uploaded
   them. This applies to Postgres and to Qdrant filters alike.
6. **Imports work with no API key.** LLM and embedding clients are built lazily inside
   functions.
7. **Qdrant metadata filters use the `metadata.` prefix** (`metadata.concept_id`). A bare key
   matches nothing and raises no error.

## Known gaps

- **No migrations.** `init_db()` only calls `create_all`, which creates missing tables but
  never alters existing ones. A new table appears on the next start. A new column does not:
  add it by hand with `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...` through
  `docker exec userbox-postgres psql -U userbox -d userbox`. The dev database holds real chat
  history and progress, so only reset it (`docker compose down -v && docker compose up -d`,
  then `python ingest.py`) for a change that cannot be made additively, and ask first.
  Alembic is out of scope until there is data worth keeping.
- **No auth.** `user_id` is a string the client sends. Privacy is only as strong as that
  until auth is added.
- **`take_turn` and `take_turn_stream` duplicate their setup.** Change both, or extract the
  shared part first.
- **Gemini free tier is small.** One chat turn costs several model calls. Tests and the
  simulator must not call the LLM.

## How to work in this repo

- **One OpenSpec change at a time,** in the order given in `docs/PLAN.md`. Do not combine
  changes or start one before the previous is archived.
- **Each proposal needs requirements with scenarios** and a task list small enough that
  every task is one sitting of work.
- **The developer is learning LangChain, LangGraph and RAG and writes the implementation
  code.** Default to explaining what to build and why, then reviewing what was written.
  Write implementation code only when asked.
- **Prefer the simplest thing that works.** `docs/PLAN.md` lists what was considered and
  rejected; do not reintroduce those without new evidence from the simulator.
