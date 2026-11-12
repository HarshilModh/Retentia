# Tasks

## 1. Config and pure grading update

- [x] 1.1 Add `PASS_THRESHOLD = 0.6`, `BASE_FAIL_INTERVAL_DAYS = 0.05` and `GRADER_CONTEXT_CHARS = 3000` to `backend/app/config.py`; verify `python -c "from app.config import PASS_THRESHOLD, BASE_FAIL_INTERVAL_DAYS, GRADER_CONTEXT_CHARS"` runs from `backend/`.
- [x] 1.2 In `backend/app/core/learner.py`, add a pure function that takes the current state, quality, pass threshold and `now` and returns the new mastery, status, streak, next review, misconceptions and a pass flag, clamping quality to 0.0–1.0 and using the fail interval on a fail. Verify with the tests in 1.3.
- [x] 1.3 Add `backend/tests/test_grade_update.py` covering: first pass, pass raising a streak, fail resetting a streak, fail scheduling about 0.05 days out, quality 1.4 clamped to 1.0 and -0.2 to 0.0, score exactly 0.6 passing, 0.59 failing, and the same inputs giving the same output. Verify `python -m pytest -q` passes with no database running.

## 2. Attempts table and transactional write

- [x] 2.1 Add the `Attempt` model and a `question_posed_at` column on `SessionState` in `backend/app/db/models.py`, matching design decision 7 (including the `(user_id, concept_id, created_at)` index). Verify by extending `backend/tests/test_db.py` to assert the table, its columns and the new session column.
- [x] 2.2 In `backend/app/db/crud.py`, add one function that upserts the `learner_concept` row and inserts the attempt in a single session and commit. Verify with `docker compose up -d` and a script or test that calls it twice and finds one progress row and two attempt rows.
- [x] 2.3 Verify atomicity: make the attempt insert fail (for example a null in a non-null column) and confirm the progress row is unchanged afterward. Record the result in the task notes. (Result: a null question raised IntegrityError and the progress row kept mastery 0.64 / streak 2; counts stayed 1 progress row, 2 attempts.)
- [x] 2.4 Reset the dev database (`docker compose down -v && docker compose up -d`, then `python ingest.py`) and verify the backend starts and `GET /progress/<user>` returns the three concepts. (Done without the reset: the dev DB held real chat history and progress, so `ALTER TABLE sessions ADD COLUMN IF NOT EXISTS question_posed_at timestamptz` was run in place and `init_db()` created `attempts`. Backend start and `/progress` are checked in 5.1.)

## 3. Wire grading to the pure function and the log

- [x] 3.1 Rewrite `apply_grade` in `backend/app/core/learner.py` to read the current row, call the pure function, and call the new transactional write with the question, raw answer, quality, pass flag, misconception, response time and `hints_used = 0`. Verify by calling it twice against the dev database and querying the `attempts` table.
- [x] 3.2 In `pose_question` (`backend/app/core/tutor.py`), store `question_posed_at` when saving the pending question. Verify the column is set after a pose, and cleared with the pending question after grading.
- [x] 3.3 Compute response time in the grading path as the difference between now and `question_posed_at`, empty when it is missing. Verify with a unit test of the helper for 42 seconds and for a missing value.

## 4. Grade the student's own message

- [x] 4.1 Add `user_message` to `config["configurable"]` in both `take_turn` and `take_turn_stream` in `backend/app/core/tutor.py`. Verify both call sites by reading the diff; there must be no third place that builds this config.
- [x] 4.2 Remove the `answer` parameter from `grade_and_update`; read the message from `RunnableConfig`. Verify the tool's schema (`grade_and_update.args`) lists no `answer` field.
- [x] 4.3 In the same tool, retrieve passages with `search_subject_kb(question, concept_id=...)`, join and truncate to `GRADER_CONTEXT_CHARS`, and pass them to `grade_answer` as an optional reference; add the reference to the grader prompt in `learner.py`, falling back to summary-only when empty. Verify with a unit test of the prompt-building code using fake passages and an empty list.
- [x] 4.4 Wrap the grader call so a failure returns a short error message to the agent, writes no attempt, and leaves the question pending. Verify with a test that stubs the grader to raise and asserts no attempt row and an unchanged pending question.
- [x] 4.5 Update `SYSTEM_PROMPT` so it no longer tells the agent to pass an answer into the grading tool. Verify the prompt text and the tool description agree.

## 5. Integration check and docs

- [x] 5.1 With a Gemini key, run one live chat: ask for a concept, answer a question, then query `attempts` and confirm the stored answer equals the exact message typed, quality is between 0 and 1, and `response_ms` is set. Confirm `/progress/<user>` shows the updated mastery.
- [x] 5.2 Answer one question wrongly and confirm the concept's `next_review` is about 72 minutes out, not a day.
- [x] 5.3 Update `docs/PLAN.md` (response time is measured by the server; quality is clamped in code rather than bounded in the schema) and add the dev-database reset note to `CLAUDE.md`. Verify the two files no longer contradict the design.
- [x] 5.4 Run `python -m pytest -q` from `backend/` and `npm run build` from `frontend/`; both pass.

## Workflow follow-up

- Review the change against the specs, then archive it with `/opsx:archive`.
- Start `add-courses` (docs/PLAN.md change 2) only after this change is archived.
