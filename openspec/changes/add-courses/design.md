# Design

## Context

See proposal.md for motivation. Facts that shape the approach:

- `concepts.id` is a global string primary key. `learner_concept` and `attempts` reference it with `ON DELETE CASCADE`.
- All current content and data is biology: three seed concepts, `backend/seed_docs/`, every progress row, chat session, Qdrant chunk and learner memory in the dev environment. The project no longer wants any of it.
- `init_db()` only creates missing tables; columns must be added by hand (CLAUDE.md, Known gaps). Since the dev data is being discarded anyway, a reset is the simplest way to get the new schema.
- `user_id` reaches tools through `RunnableConfig` (CLAUDE.md rule 4). Every chat turn already loads the session row.
- `frontend/src/components/Dashboard.tsx` hard-codes three biology concepts (`CONCEPT_IDS`, `CONCEPT_DETAILS` with icons and long descriptions).
- There is no auth: `user_id` is whatever the client sends. "Private" means every query is filtered by it.

## Goals / Non-Goals

**Goals:**
- Every concept, chunk and progress view belongs to one course; the tutor never crosses courses.
- No biology anywhere: code, comments, fixtures, docs or data.
- A new student has something to study immediately (the demo courses).
- Ownership checks live in one place, as pure functions that are easy to test.

**Non-Goals:**
- Uploading or generating courses (change 3). This change only creates empty courses and accepts material through the existing `/ingest`.
- Sharing student-created courses, roles, or real authentication.
- Per-course chat history; switching course clears it.
- Renaming courses or editing concepts through the API.
- Preserving any existing dev data.
- A Qdrant payload index on `course_id`; filtering works without one at this size.

## Decisions

**1. Demo courses are shared, read-only courses with no owner.**
`courses.owner_user_id` is nullable; `NULL` means built-in. Each demo has a fixed id: `demo-git`, `demo-stats`, `demo-econ`. Progress stays private because `learner_concept` is keyed by user. Alternative: copy the demos into each student's account. Rejected because every copy would re-embed the material (Gemini quota) and nothing about the demos is private.

**2. Demo content.** Three courses, three concepts each, prerequisites forming a chain. The documents are short (about 300–500 words each), written for this project, and stored as `backend/demo_courses/<course>/<concept>.md` with a small manifest giving titles, summaries, order and prerequisites.

| Course | Concepts, in prerequisite order |
|---|---|
| Git Basics | Commits → Branches → Merging |
| Intro Statistics | Averages (mean, median, mode) → Spread (range, variance, standard deviation) → The normal distribution |
| Basic Economics | Supply and demand → Market equilibrium → Price elasticity |

**3. Every concept id is namespaced by its course.**
Stored as `"{course_id}/{key}"`, where `key` is the manifest key (demos), the caller's id (`/ingest`) or a generated slug (change 3). Prerequisites are translated the same way, so they can only point inside the course. Student course ids are short random strings (`uuid4().hex[:12]`), never containing `/`. The id format is internal; nothing parses it. Alternative: a separate `(course_id, key)` composite key. Rejected because `learner_concept` and `attempts` would both need a second key column for no user-visible gain.

**4. Ownership rules are pure functions in a new `app/core/courses.py`.**
`can_view(course, user_id)` is true for the owner or when the owner is `None`; `can_modify(course, user_id)` is true only for the owner. Every route and tool loads the course, then asks these. A course that fails `can_view` is reported as 404, the same as a missing one, so ids cannot be probed. Alternative: filter in each SQL query. Rejected because the rule would be repeated in many places and harder to test.

**5. The active course lives on the session row and travels in the run config.**
`sessions.course_id` is nullable; `NULL` means no active course. `take_turn` and `take_turn_stream` resolve it once through a shared helper (the duplicated setup is extracted in this change). If it is null, missing or no longer visible, the turn returns the fixed "pick or create a course" reply without building the agent. Otherwise `course_id` goes into `config["configurable"]` next to `user_id` and `user_message`; tools read it from there, never from LLM arguments.

**6. Tools filter by course.**
- `search_kb`: always filters `metadata.course_id`, plus `concept_id` when given.
- `pose_question`: rejects a concept whose `course_id` is not the active course, listing valid ids.
- `get_learner_model`, `select_next_concept`: use `get_all_learner_concepts(user_id, course_id)`.
- `grade_and_update`: the pending question's concept is already in the active course; its passage search adds the course filter.
- `recall_persona`, `save_memory`: unchanged, user-level by design (spec: learner memories span courses).

**7. The system prompt is built per turn.**
`SYSTEM_PROMPT` becomes `build_system_prompt(course_title)`: "You are a personalized tutor for the course '{title}'…", with no subject word. A pure function, tested directly.

**8. Re-ingesting a concept replaces its chunks.**
Before adding chunks for a concept, delete the Qdrant points whose `metadata.concept_id` matches it (filtered by course). Each chunk's metadata gains `course_id`. This makes the demo seed safe to re-run. Alternative (docs/PLAN.md): deterministic point ids. Rejected because a shorter document would leave stale tail chunks behind.

**9. Course deletion order: vectors first, then one database transaction.**
Delete the course's Qdrant points by `metadata.course_id`, then in one transaction: clear `course_id`, `chat_history` and `pending_question` for sessions on that course, delete its concepts (cascading to `learner_concept` and `attempts`), delete the course. If the vector delete fails, nothing in Postgres changes. If Postgres fails afterwards, a retry completes it. Alternative: Postgres first. Rejected because a failure would leave orphaned vectors that nothing can find.

**10. Reset the dev data instead of migrating it.**
Everything stored is biology, so there is nothing to carry over. The reset is `docker compose down -v && docker compose up -d`, which recreates empty Postgres and Qdrant volumes; the app's startup creates the tables and collections, then `python seed_demo.py` loads the demos. This deletes all current progress, chats and learner memories, so the implementing task asks for explicit confirmation first. The biology seed (`SEED_CONCEPTS`, the seeding `main()` in `ingest.py`, `backend/seed_docs/`) is deleted; `ingest_docs` stays because `/ingest` uses it.

**11. API shape.** All take `user_id` like the existing routes (no auth yet).

| Method and path | Does |
|---|---|
| `GET /courses?user_id=` | Courses the user can see: owned ones plus the demos |
| `POST /courses` `{user_id, title}` | Creates an empty course owned by the user, status `active` |
| `GET /courses/{id}?user_id=` | One course and its concepts, 404 if not visible |
| `POST /courses/{id}/select` `{user_id}` | Makes it active; clears chat history and pending question |
| `DELETE /courses/{id}?user_id=` | Owner only; 403 for a demo; 404 if not visible |
| `GET /progress/{user_id}?course_id=` | Progress for that course, default the active one; empty with none |
| `POST /ingest` | Body gains `user_id` and `course_id`; 403 unless the user owns the course |

The `courses.status` column exists now (`active` | `draft`) so change 3 needs no schema change; only `active` is used here.

**12. Frontend.** The header gets a course `<select>` fed by `GET /courses`, demos marked as such; changing it calls select, then reloads progress and chat history. With no active course, the dashboard shows the demo courses as cards and a small "create course" form (title only); the chat panel shows the same prompt. `Dashboard.tsx` builds its concept map from the `concepts` it receives (title, summary, prereqs, seq) with one generic icon; `CONCEPT_IDS` and `CONCEPT_DETAILS` are deleted. `ConceptProgress` in `api.ts` gains `prereqs` and `course_id`.

## Risks / Trade-offs

- **The reset deletes all current dev progress, chats and memories** → asked for again before it runs; nothing in it is wanted (all biology).
- **A student's own course is empty until upload ships** → only `/ingest` can fill it. Accepted; the demos give students something to study meanwhile, and the empty-course state says so.
- **Demo documents are written by an LLM-assisted author** → factual errors would be taught. Mitigation: keep them short and on stable, well-known material; the task requires reading each one before seeding.
- **Seeding embeds nine documents** → a few Gemini embedding calls once per reset. Acceptable.
- **Switching course erases chat history** → accepted for simplicity; progress is kept.
- **No auth, so privacy depends on the client sending the right `user_id`** → unchanged risk, stated in CLAUDE.md; every query now filters on it, so adding auth later is one place.
