# Proposal

## Why

Retentia keeps one summary row per student per concept and no record of individual answers, so nothing can be replayed, audited or evaluated. The simulator and any later mastery model (docs/PLAN.md changes 5 and 6) need that history. Grading also has two defects: the agent supplies the text that gets graded, so it can paraphrase what the student wrote, and the grader sees only a one-line summary of the concept. A failed answer is also rescheduled for the same one day as a first pass.

## What Changes

- Add an append-only log with one row per graded attempt: the question, the student's raw answer, the quality score, pass/fail, any misconception, how long the student took, and what kind of step led to the question (empty until the next-step policy exists).
- Write the attempt and the progress update together, so one cannot exist without the other.
- Grade the exact message the student sent. The agent no longer passes the answer text to the grading tool.
- Give the grader the concept's retrieved course content, not only its summary.
- Treat any quality score outside 0.0 to 1.0 as the nearest bound.
- Schedule the next review of a failed attempt much sooner than a first pass (about 72 minutes instead of one day).
- Move the pass line (0.6) out of the grading code into configuration.
- Measure the student's response time on the server, from when the question was posed to when the answer arrives.
- **BREAKING** (dev only): the `sessions` table gains a column. There are no migrations, so the dev database must be reset once.

## Capabilities

### New Capabilities
- `attempt-log`: a durable, append-only record of every graded attempt, written atomically with the progress update.
- `answer-grading`: how a student's answer is graded: which text is graded, what the grader is given, and how the score is bounded and judged pass or fail.
- `review-scheduling`: when a concept is due for review after a pass or a fail.

### Modified Capabilities

None. `openspec/specs/` is empty; the existing behavior is captured here for the first time.

## Impact

- `backend/app/core/learner.py`: the grading update becomes a pure function; the grader accepts reference content; the pass line and fail interval come from config.
- `backend/app/core/tutor.py`: the grading tool reads the raw message from the run config and retrieves content; the question-posing tool records when it asked; both chat entry points pass the raw message.
- `backend/app/db/models.py`, `backend/app/db/crud.py`: new `attempts` table, new `sessions.question_posed_at` column, one transactional write for progress plus attempt.
- `backend/app/config.py`: pass threshold, fail interval, grader context size.
- `backend/tests/`: new tests for the pure update, the interval rule and the table shape.
- Docs: `docs/PLAN.md` and `CLAUDE.md` note that response time is measured by the server and that the dev database needs a reset.
- No API response shape changes and no frontend changes.
