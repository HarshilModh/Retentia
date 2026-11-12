# Design

## Context

Grading today runs through the `grade_and_update` agent tool ([tutor.py:77](backend/app/core/tutor.py:77)): the tool takes an `answer` string the LLM writes, calls `grade_answer`, then `apply_grade` reads the current row, computes the new values and upserts them ([learner.py:36](backend/app/core/learner.py:36)). `apply_grade` mixes calculation with database reads and writes, so it cannot be tested without Postgres. Each `crud` function opens its own session, so two writes are never one transaction. `take_turn` and `take_turn_stream` build the run config separately and both must change.

The database has no migrations: `init_db()` calls `create_all`, which creates missing tables but never adds columns to existing ones. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- One attempt row per graded answer, written in the same transaction as the progress update.
- The graded text is provably the student's message.
- The grading calculation is a pure function that tests and the future simulator can call without a database.

**Non-Goals:**
- Changing the mastery formula (EMA stays) or the thresholds other than the new fail interval.
- Choosing the next step, hints, or self-reported confidence.
- A migration system or data backfill for old progress rows.
- Streaming or UI changes.

## Decisions

**1. Split `apply_grade` into a pure part and a thin writer.**
A new pure function takes the current state, quality, the pass threshold and `now`, and returns the new mastery, status, streak, next review date, misconceptions and a pass flag. `apply_grade` becomes: read current row, call the pure function, write. Alternative: mock the database in tests. Rejected because it tests the mock, and the simulator (docs/PLAN.md change 5) needs the pure form anyway.

**2. One crud function writes progress and attempt in a single session.**
A new function opens one `SessionLocal`, upserts the `learner_concept` row and inserts the `attempts` row, then commits once. Alternative: two existing calls with compensating logic. Rejected because a crash between them leaves progress without history.

**3. The raw message travels in the run config, not in tool arguments.**
`take_turn` and `take_turn_stream` add `user_message` to `config["configurable"]` beside `user_id`. The grading tool reads it from `RunnableConfig` and exposes no `answer` parameter, so the LLM cannot supply or edit it. This is the same mechanism already used for `user_id` (CLAUDE.md rule 4). Alternative: validate that the agent's `answer` matches the message. Rejected as more code than removing the parameter.

**4. Response time is measured by the server.**
`pose_question` stores `question_posed_at` on the session row; grading computes the difference to `now`. docs/PLAN.md assumed the frontend would send it; server-side avoids a client change, cannot be spoofed by the client, and works for any future client. The measured time includes the rest of the agent turn after the question was posed (a few seconds of model latency), which is acceptable because the value is only stored in this change and drives no decision. If posed-at is missing, response time is empty.

**5. Retrieval for the grader happens in the tool, not in `learner.py`.**
The tool calls the existing content search with the question text, filtered to the concept, joins the passages, truncates to `GRADER_CONTEXT_CHARS` (proposed 3000) and passes them to `grade_answer` as an optional `reference` argument. This keeps `learner.py` free of vector-store imports and keeps imports working with no key. An empty result means summary-only grading.

**5a. Quality is clamped in code, not constrained in the schema.**
The pure grading update clamps quality to 0.0–1.0. docs/PLAN.md also mentioned bounding `Grade.quality` in the schema; that is dropped because JSON-schema bounds in Gemini structured output are not verified here and a rejected schema would break grading entirely. Clamping gives the same guarantee without that risk.

**6. Fail interval is `BASE_FAIL_INTERVAL_DAYS = 0.05`.**
It is a float number of days passed straight to `timedelta`. The pass path keeps `compute_next_review` unchanged. Alternative: also shorten the first-pass interval. Rejected as outside this change; the simulator will tune it.

**7. Attempts table shape.**
`attempts(id bigserial pk, user_id text, concept_id text fk concepts.id on delete cascade, question text, answer text, quality float, passed bool, misconception text null, action_type text null, hints_used int default 0, response_ms int null, created_at timestamptz default now())` with an index on `(user_id, concept_id, created_at)`. `action_type` is a plain string so the policy change can add values without a schema change.

**8. A grader failure is caught in the tool and reported to the agent.**
The tool wraps the grader call; on error it returns a short failure message and writes nothing, leaving the pending question in place so the student can resend. Alternative: let the exception propagate. Rejected because the outcome then depends on how the agent library handles tool errors.

## Risks / Trade-offs

- **Existing dev database lacks the new `sessions` column** → the first request after the change fails. Mitigation: reset the dev database once (`docker compose down -v`), documented in tasks and CLAUDE.md. No production data exists.
- **Response time includes agent latency** → a few seconds of noise. Mitigation: it is not used for decisions yet; revisit when it is.
- **Message that is not an answer gets graded** (the student asks "can you explain that?" and the agent calls the grader anyway) → a bogus low score is now logged permanently. Mitigation: unchanged from today's behavior but now visible in the log; the next-step policy change removes the agent's discretion over grading.
- **Longer grader prompt** → more input tokens per grade, a risk on the small Gemini free tier. Mitigation: the 3000-character cap.
- **Very short fail interval** → a concept can come due again within the same sitting. Intended; the simulator will show whether 0.05 days is right.
- **`on delete cascade` on attempts** → deleting a concept deletes its history. Acceptable until courses exist (docs/PLAN.md change 2) and deletion is defined.
