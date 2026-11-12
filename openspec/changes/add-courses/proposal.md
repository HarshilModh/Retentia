# Proposal

## Why

Concepts are global rows with hand-written ids, and every search, progress view and agent tool works over all of them. Two uploaded documents would collide, and nothing can be private to a student. The only content is a three-concept biology demo, which the project no longer wants. Course upload (docs/PLAN.md change 3) needs a place to put a student's own material, so this change introduces courses, scopes everything to the student's active course, and replaces the biology demo with a few subject-neutral demo courses.

## What Changes

- Add courses. A course has an owner, a title and a status. Courses a student creates are private to that student.
- Add three built-in **demo courses** with no owner, visible to every student and read-only: Git Basics, Intro Statistics and Basic Economics, three concepts each in a prerequisite chain. Progress on them is personal.
- **BREAKING**: remove all biology content: the seed concepts, `backend/seed_docs/`, the biology seeding in `ingest.py`, and biology examples in code comments and test fixtures. A new seed script loads the demo courses instead.
- Every concept belongs to exactly one course, and its id is namespaced by the course, so two courses can both have a concept called "Introduction".
- Each student has at most one **active course**, none at first. With no active course, chat replies with a fixed message asking the student to pick or create a course, without calling the model. Switching course clears the chat history and any pending question.
- Course content in the vector store carries its course, and every content search is filtered by it.
- New endpoints: list visible courses, get one course with its concepts, create an empty course, select the active course, delete a course I own. Deleting removes the course's concepts, progress, attempt history and stored content.
- **BREAKING**: `/progress/{user_id}` returns only the active course's concepts (or the course given as a query parameter), and an empty list with no active course. `/ingest` requires a course the caller owns.
- The tutor's instructions name the active course instead of a subject.
- The frontend gets a course picker, a "create course" form and empty states, and the dashboard draws its concept map from the API.
- **BREAKING** (dev data): the dev database and Qdrant are reset, because everything in them (progress, chats, learner memories, chunks) is biology. The reset asks for confirmation before it runs.
- Until upload ships (change 3), the only way to add material to a student's own course is `POST /ingest`.

## Capabilities

### New Capabilities
- `courses`: what a course is, who can see, select and delete it, the built-in demo courses, and the student's active course.
- `course-scoping`: everything the tutor does for a student (content search, questions, grading, progress, suggestions) stays inside the active course.

### Modified Capabilities

None. `openspec/specs/` is still empty: `add-attempt-log` has not been archived yet. Its `answer-grading` requirement that the grader receives "course content" is consistent with this change; the course filter is specified here under `course-scoping`.

## Impact

- `backend/app/db/models.py`, `crud.py`: new `courses` table; `concepts.course_id`; `sessions.course_id`; course-aware queries and a cascading delete.
- `backend/app/core/tutor.py`: active course loaded per turn and passed to tools through the run config; tools filter by it; system prompt built per course; fixed reply with no active course.
- `backend/app/core/retrieval.py`, `backend/ingest.py`: course filter on search; course metadata on chunks; re-ingesting a concept replaces its chunks; biology seed removed.
- New `backend/seed_demo.py` and `backend/demo_courses/` (nine short markdown documents written for this project).
- Removed: `backend/seed_docs/` (three biology documents).
- `backend/app/api/routes/`: new `courses.py`; `progress.py` and `ingest.py` scoped to a course.
- `backend/tests/`: fixtures and examples switched from biology to neutral subjects.
- `frontend/src/api.ts`, `App.tsx`, `components/Dashboard.tsx`, `ChatPanel.tsx`: course picker, create form, empty states and a data-driven dashboard; the hard-coded biology concepts are removed.
- Dev environment: one reset of Postgres and Qdrant, then `python seed_demo.py`.
- Docs: `CLAUDE.md`, `README.md` and `docs/PLAN.md` drop biology and describe the demo courses.
