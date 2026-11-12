# Tasks

## 1. Schema

- [ ] 1.1 Add a `Course` model (`id`, `owner_user_id` nullable, `title`, `status` default `active`, `created_at`) and `course_id` columns on `Concept` (non-null FK to courses, `ON DELETE CASCADE`) and `SessionState` (nullable) in `backend/app/db/models.py`. Verify by extending `backend/tests/test_db.py` for the new table and columns, and `python -m pytest -q` passes.

## 2. Ownership rules, data access and search filters

- [ ] 2.1 Create `backend/app/core/courses.py` with pure `can_view`, `can_modify` and `namespaced_concept_id(course_id, key)`. Verify with `backend/tests/test_courses.py`: owner sees and modifies; another user does neither; anyone sees a demo; nobody modifies a demo; two courses with key `introduction` give different ids.
- [ ] 2.2 In `backend/app/db/crud.py`, add `create_course`, `get_course`, `list_visible_courses(user_id)`, `set_active_course` (clears chat history and pending question), `delete_course_rows` (one transaction, design decision 9), and add a `course_id` argument to `get_all_learner_concepts` and `upsert_concept`. Verify with a throwaway-user script against the dev database after the reset in 4.2: two users each create a course; each lists only their own plus the demos; the script deletes its rows afterwards.
- [ ] 2.3 In `backend/app/core/retrieval.py`, make the filter builder accept several conditions, require `course_id` in `search_subject_kb`, and add `delete_course_vectors` and `delete_concept_vectors`. Verify with a unit test that the built filter contains `metadata.course_id` (and `metadata.concept_id` when given).

## 3. Remove biology and add the demo content

- [ ] 3.1 Delete `backend/seed_docs/`, `SEED_CONCEPTS` and the seeding `main()` in `backend/ingest.py`, keeping `ingest_docs`; make `ingest_docs` take a `course_id`, store it in chunk metadata, namespace concept ids and prerequisites, and delete a concept's existing points before adding new ones. Verify `python -c "import ingest"` works from `backend/` and the file no longer mentions any biology term.
- [ ] 3.2 Write the nine demo documents and a manifest under `backend/demo_courses/` (design decision 2). Verify by reading each document for accuracy before moving on, and that the manifest's prerequisites form a chain inside each course.
- [ ] 3.3 Write `backend/seed_demo.py`: create the three demo courses if missing (fixed ids, no owner) and ingest their documents with `ingest_docs`. Verify with a unit test of the manifest loader (no network), and later by running it twice in 4.2.
- [ ] 3.4 Replace biology examples in code comments, docstrings and test fixtures (`backend/app/core/tutor.py`, `learner.py`, `backend/app/db/crud.py`, `backend/tests/test_grading_tool.py`, `test_grade_update.py`) with neutral ones. Verify `grep -rniE "biology|chromosom|mitosis|meiosis" backend frontend/src` returns nothing (excluding `.venv`) and the tests pass.

## 4. Reset the dev environment

- [ ] 4.1 Ask the user for explicit confirmation before resetting: show what will be deleted (row counts of `learner_concept`, `attempts`, `sessions`, and point counts of `subjects_kb` and `user_box`). Do not continue without a clear yes.
- [ ] 4.2 Run `docker compose down -v && docker compose up -d`, start the backend once so tables and collections are created, then run `python seed_demo.py` twice. Verify `GET /courses?user_id=x` lists the three demos with three concepts each, and the `subjects_kb` point count is the same after each seed run.

## 5. Tutor scoped to the active course

- [ ] 5.1 Extract the setup shared by `take_turn` and `take_turn_stream` into one helper that loads the session, resolves the active course, returns the fixed "pick or create a course" reply when there is none (or it is no longer visible), and otherwise builds the messages and the run config with `user_id`, `user_message` and `course_id`. Verify with stubbed unit tests for the no-course reply (no agent built) and the normal path, and that both entry points call the helper.
- [ ] 5.2 Replace `SYSTEM_PROMPT` with `build_system_prompt(course_title)`. Verify with a unit test that the prompt contains the given title and no subject word.
- [ ] 5.3 Scope the tools (design decision 6): `search_kb`, `pose_question`, `get_learner_model`, `select_next_concept`. Verify with stubbed tests: search passes the active course id; `pose_question` rejects a concept from another course and records nothing; `get_learner_model` asks only for the active course.
- [ ] 5.4 Add the course filter to the passage search in `grade_and_update`, and update `backend/tests/test_grading_tool.py` for the new config key. Verify the grading tests pass and assert the search received the course id.
- [ ] 5.5 Make `select_next_concept` in `learner.py` take a `course_id` and pass it through. Verify with a stubbed test that it only sees the course's concepts.

## 6. API

- [ ] 6.1 Add `backend/app/api/routes/courses.py` with the five course endpoints from design decision 11 and register it in `main.py`. Verify with `curl` against a running backend using throwaway users: create, list (own plus demos), get, select (chat history becomes empty), 404 for another user's course, 403 when deleting a demo.
- [ ] 6.2 Add the optional `course_id` query parameter to `/progress/{user_id}`, defaulting to the active course, returning an empty list with none, and 404 for a course the user cannot see. Verify with `curl` for each case.
- [ ] 6.3 Change `/ingest` to require `user_id` and `course_id` and refuse unless the user owns the course (update `IngestRequest` in `schemas.py`). Verify a 403 for a demo and for another user's course, and that ingesting the same small document twice leaves each passage stored once.
- [ ] 6.4 Implement course deletion: vectors first, then `delete_course_rows`. Verify after deleting a course that was studied (one graded answer) that its concepts, progress rows, attempts and Qdrant points are all gone, and the owner has no active course.

## 7. Frontend

- [ ] 7.1 In `frontend/src/api.ts`, add `listCourses`, `createCourse`, `selectCourse`, `deleteCourse`, a `course_id` argument on `getProgress`, and `prereqs` and `course_id` on `ConceptProgress`. Verify `npm run build` passes.
- [ ] 7.2 In `App.tsx`, add a course picker in the header; changing it selects the course, then reloads progress and chat history. Verify in the browser that switching between two demos changes the concept list and empties the chat.
- [ ] 7.3 Make `Dashboard.tsx` draw its concept map from the `concepts` prop and delete `CONCEPT_IDS` and `CONCEPT_DETAILS`; with no active course, show the demo courses as cards and a "create course" form. Verify `npm run build` passes and, in the browser, a new user sees the demos, picking one shows its three concepts, and creating a course selects it.
- [ ] 7.4 In `ChatPanel.tsx`, show the "pick or create a course" prompt when there is no active course. Verify in the browser with a new user.

## 8. Integration check and docs

- [ ] 8.1 With a Gemini key, as a throwaway user: select Git Basics and chat. Verify the tutor names the course, teaches from its documents only, a posed question is stored with a `demo-git/...` concept id, and grading records an attempt. Delete the user's rows afterwards.
- [ ] 8.2 Verify isolation end to end: a second throwaway user cannot list, read, select, get progress for, ingest into or delete the first user's course, and their content searches never return its passages.
- [ ] 8.3 Update `CLAUDE.md`, `README.md` and `docs/PLAN.md`: no biology, the demo courses and their seed script, `course_id` in the run config, and the reset. Verify `grep -rniE "biology|chromosom|mitosis|meiosis"` over those files returns nothing.
- [ ] 8.4 Run `python -m pytest -q` from `backend/` and `npm run build` from `frontend/`; both pass.

## Workflow follow-up

- Archive `add-attempt-log` before archiving this change, so its specs land in `openspec/specs/` first.
- Review this change against its specs, then archive it with `/opsx:archive`.
- Start `add-course-upload` (docs/PLAN.md change 3) after this change is archived.
