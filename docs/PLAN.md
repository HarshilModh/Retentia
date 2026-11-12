# Retentia roadmap

This is the input for OpenSpec proposals. Each section under "Changes" is one OpenSpec
change, listed in build order. A section gives the reason, the scope, the design decisions
already made, and the acceptance criteria. The proposal, spec deltas and task list are
written from it when that change starts.

Threshold values in this document are starting points. The simulator (change 5) exists to
tune them.

## 1. Where the project is today

**Tracking**
- One row per student per concept in `learner_concept`: mastery, status, attempts, streak,
  misconceptions, last seen, next review. No history of individual attempts.
- Mastery is an exponential moving average of an LLM-assigned quality score
  (`learner.py: ema`, alpha 0.4, mastered at 0.7). It starts at 0.0, never decays, and has
  no measure of uncertainty.
- Scheduling is a doubling interval on the pass streak (`compute_next_review`). A fail and
  a first pass both schedule one day out.
- The grader (`grade_answer`) sees only the concept's one-line summary.
- `grade_and_update(answer)` takes the answer as an argument the agent writes, so the
  graded text is not guaranteed to be what the student typed.

**Deciding the next step**
- `select_next_concept` is a fixed cascade: most overdue review, then weakest in-progress
  concept, then the next concept whose prerequisites are mastered.
- It is an optional tool. The agent chooses whether to call it, and `pose_question`
  accepts any valid concept id, so prerequisites are not enforced.
- It returns a concept only. There is no action type, no reason and no stop condition.
- `/progress` does not return the next step, and the frontend does not show suggestions.

**Content**
- Three biology concepts in a straight line, typed by hand in `backend/ingest.py`.
- Concepts are global. Nothing ties a concept to a course or an owner.

**Tests**
- Unit tests for `ema` and `compute_next_review` only. No evaluation harness.

## 2. Target

1. A student uploads material and gets a private course: an outline of concepts with soft
   prerequisite links, generated from the upload and reviewed by the student.
2. Every attempt is logged with enough detail to replay and evaluate.
3. A deterministic policy picks one of five actions and a concept, with a one-line reason
   the student sees.
4. A simulator measures whether a policy helps, without calling an LLM.

## 3. Decisions already made

| Decision | Choice | Why |
|---|---|---|
| Who decides the next step | Rule-based policy in Python | The decision is arithmetic over scores and dates; it must be testable and explainable |
| Course visibility | Private to the uploader | Avoids permissions and sharing entirely |
| Prerequisites | Soft ordering hint, not a hard gate | Generated links are guesses |
| Mastery model | Keep EMA until the simulator shows BKT is better | Avoid replacing a model on assumption |
| Reasons shown to students | Templates filled by the policy | No LLM call, always consistent with the decision |
| Jev (TypeSafe decision model) | Not used for the next-step decision | It classifies text; its own listed limits include math and dates |
| Contextual bandits | Rejected for now | Needs a reward signal and volume the project does not have |
| IRT adaptive selection | Rejected for now | Needs a calibrated question bank; questions are generated on the fly |
| LLM decision step | Rejected | Non-deterministic, costs quota, hard to evaluate |
| FSRS | Deferred | A possible replacement for the interval rule once attempt history exists |

## 4. Changes

### Change 1: `add-attempt-log`

**Why.** Nothing later (simulator, BKT, any comparison) is possible without a record of
individual attempts, and grading must use the student's real words.

**Scope**
- New append-only `attempts` table: id, user id, concept id, question text, raw answer,
  quality, passed, misconception, action type (nullable until change 4), hints used
  (default 0), response time in ms (nullable), created at.
- `apply_grade` writes one attempt row in the same transaction as the `learner_concept`
  update.
- The grader receives the student's raw message. `take_turn` passes it through
  `RunnableConfig`; `grade_and_update` stops taking an `answer` argument from the LLM.
- The grader prompt includes retrieved course chunks for the concept, not only the summary.
- `Grade.quality` is bounded to 0.0–1.0 in the schema.
- A failed attempt schedules the next review sooner than a pass does
  (`BASE_FAIL_INTERVAL_DAYS`, proposed 0.05 days as in `BUILD_PLAN.md`).
- The pass line (currently a literal 0.6 in `apply_grade`) moves to `config.py`.
- The frontend sends response time with each answer. Hints stay at 0 until a hint feature
  exists.

**Acceptance**
- Grading an answer adds exactly one attempt row holding the raw message text.
- The agent cannot alter the text that is graded.
- A fail produces an earlier `next_review` than a first pass.
- Unit tests cover `apply_grade` for pass, fail, and first attempt.

**Out of scope.** Hints UI, self-reported confidence, any change to the mastery formula.

### Change 2: `add-courses`

**Why.** Concepts are global with hand-written ids, so two uploads would collide and
nothing can be private.

**Scope**
- New `courses` table: id, owner user id, title, status (`draft` or `active`), created at.
- `concepts` gains `course_id` and uses generated ids. Prerequisites reference concept ids
  within the same course.
- `sessions` gains the active `course_id`.
- Every chunk in Qdrant carries `course_id`; all content searches filter on it.
- `course_id` reaches tools through `RunnableConfig`, alongside `user_id`.
- `pose_question` accepts only concepts in the active course.
- The system prompt takes the course title; the word "biology" is removed.
- The biology seed becomes a demo script that creates one sample course for a given user.
- API: list my courses, get one course with its concepts, select the active course, delete
  a course (removing its concepts, learner rows, attempts and Qdrant points).
- `/progress` is scoped to a course.
- Qdrant points use deterministic ids so re-ingesting does not duplicate chunks.

**Acceptance**
- Two users with the same concept titles do not see each other's concepts, progress or
  search results.
- Deleting a course leaves no rows or vectors behind.
- The demo course behaves as the app does today.

**Out of scope.** Sharing, real authentication, migrations (reset the dev database).

### Change 3: `add-course-upload`

**Why.** The student should study their own material, in any subject.

**Flow**
1. Upload a file or paste text. Accepted: plain text, markdown, text-based PDF.
2. Extract text and split into chunks (reuse the existing splitter settings). Store chunks
   in Qdrant under a new course in `draft` status.
3. Extract an outline with one structured-output LLM call. Input: numbered chunks. Output:
   a list of concepts, each with title, summary, the indices of the chunks that support
   it, prerequisite concept references, and an order.
4. Validate the outline (rules below) and save it as draft concepts. Tag each chunk with
   its concept id.
5. The student reviews the outline: rename, edit summary, merge, delete, reorder.
6. The student confirms; the course becomes `active`.

**Validation rules**
- Target 5 to 15 concepts per document; reject and retry once outside 3 to 25.
- Every concept must cite at least one chunk; drop concepts that cite none.
- Prerequisite links must not form a cycle; drop the links that close a cycle.
- A prerequisite must come earlier in the order than the concept that needs it.
- Chunks no concept cites stay searchable at course level with no concept id.

**Limits (proposed)**
- Maximum upload 5 MB and roughly 60 chunks for a single extraction call. Above that,
  extract per section and merge duplicate concepts with a second call.
- Scanned PDFs, slides, images and audio are rejected with a clear message.

**Acceptance**
- Uploading a non-biology document yields a draft outline the student can edit and confirm.
- An outline with a cycle or an uncited concept is repaired before it is shown.
- After confirming, the tutor teaches and questions from the uploaded content only.
- Extraction is covered by tests that use a stubbed LLM response; no live calls in tests.

**Out of scope.** OCR, adding material to an existing course, regenerating an outline.

### Change 4: `add-next-step-policy`

**Why.** The next step is currently an optional tool call with no action type, reason or
stop condition.

**Interface.** One pure function: learner state for a course, session state and `now` go
in; a decision comes out. A decision holds an action, a concept id (absent for stop), a
reason string and the name of the rule that fired. Any policy implements this signature,
so alternatives can be compared in the simulator.

**Rules.** Checked in order; the first that matches wins.

| Order | Action | Fires when | Reason template |
|---|---|---|---|
| 1 | Stop | Session question budget reached, or nothing is due and nothing is left to learn | "You've done {n} questions. Good place to stop." |
| 2 | Revise prerequisite | Two fails in a row on a concept, and one of its prerequisites is below the mastery threshold | "{prereq} underpins {concept}, and it looks shaky." |
| 3 | Revise | A started concept is past its review date; at most {cap} per session | "Reviewing {concept}: last seen {days} days ago." |
| 4 | Check | Mastery between the low and high band with fewer than 3 attempts | "Quick check on {concept}: not enough answers yet to be sure." |
| 5 | Practice | An in-progress concept is below the mastery threshold | "{concept} is at {pct}%. A bit more practice." |
| 6 | Learn | The next unstarted concept in order, preferring those whose prerequisites are mastered | "{concept} is next, and you have what it builds on." |

**Starting values (in `config.py`).** Session budget 10 questions; review cap 4 per
session; uncertain band 0.4 to 0.8; mastery threshold 0.7.

**What each action means to the agent**
- Learn: teach from retrieved content, then pose one question.
- Practice: pose a question with brief feedback, no full re-teach.
- Revise: pose a recall question first, re-teach only on a fail.
- Check: pose one question with no teaching beforehand.
- Stop: summarise the session and do not pose a question.

**Enforcement**
- `take_turn` computes the decision before the agent runs and puts it in the system prompt.
- The agent cannot pose a question on a concept other than the decision's, unless the
  student explicitly asked for a different one. An override is logged with its own action
  type and the student is told which prerequisite they are skipping.
- `select_next_concept` as an agent tool is removed or reduced to reading the decision.
- Each attempt row records the action type that led to it.

**Surfacing**
- An endpoint returns the current decision for a course.
- The progress panel shows the action, the concept and the reason.
- The chat response carries the decision as structured data, not a string.

**Acceptance**
- Unit tests cover every rule, the ordering between rules, and the stop cases, using plain
  state objects with no database.
- The same state and `now` always produce the same decision.
- Every decision has a non-empty reason.

**Out of scope.** Tuning thresholds, time-based session limits, changing the mastery model.

### Change 5: `add-student-simulator`

**Why.** There is no way to tell whether one policy is better than another.

**Scope**
- A simulated student with hidden state per concept: known or not, a learning rate, slip
  and guess probabilities, and forgetting over simulated time. Learning a concept is
  slower while its prerequisites are unknown.
- A runner that advances a simulated clock, asks the policy for a decision, has the
  simulated student answer, and applies the same mastery update code the app uses. No
  LLM, no Postgres, no Qdrant.
- Synthetic courses of different shapes: a chain, a wide tree, a noisy graph with wrong
  prerequisite links.
- Baseline policies: random, curriculum order only, and the current cascade.
- Metrics: questions needed to master the course, true retention at day 30, questions
  spent on concepts already known, share of sessions ending in stop, and how far the
  app's mastery estimate is from the hidden truth.
- A command that runs all policies over a fixed set of seeds and prints a comparison table.

**Acceptance**
- A run with a fixed seed is reproducible.
- The rule-based policy beats random and curriculum-order on questions-to-mastery, or the
  result explains why not.
- The whole run finishes in seconds with no network access.

**Limit to state in the proposal.** The simulator tests policy logic against assumptions
about how students learn. It is not evidence about real students.

### Change 6: `replace-ema-with-bkt` (only if change 5 supports it)

**Why.** EMA starts at zero, cannot tell unknown from weak, and never decays.

**Scope**
- Bayesian Knowledge Tracing per concept with four parameters (prior, learn, slip, guess)
  held in `config.py`, replacing EMA as the mastery value.
- Uncertainty exposed as a simple flag from attempt count until something better is needed.
- Effective mastery used by the policy is discounted by time since the last review.
- The existing doubling interval stays for scheduling.

**Acceptance**
- In the simulator, the BKT estimate tracks hidden truth more closely than EMA, and the
  policy does no worse on questions-to-mastery and day-30 retention. If not, this change
  is abandoned and the reason recorded here.

## 5. Not planned

- FSRS scheduling, until attempt history exists and the interval rule is shown to be the
  weak point.
- Jev or another classifier for routing student messages (answer, question, topic change).
  Worth a look only if the agent's routing proves unreliable.
- Authentication, course sharing, Alembic migrations.
- OCR, slides, audio and video uploads.
- Self-reported confidence and a hints feature.

## 6. Open decisions

Each has a default the plan above assumes. Change the default here before the relevant
change starts.

| Question | Default assumed | Affects |
|---|---|---|
| Can a student override the suggested step? | Yes, with a notice about the skipped prerequisite | Change 4 |
| How long is a session? | 10 questions | Change 4 |
| Are questions always generated, or is there a fixed bank? | Always generated | Changes 3 and 5 |
| How large can an upload be? | 5 MB, about 60 chunks per extraction call | Change 3 |
| Can material be added to an existing course? | No, upload creates a new course | Change 3 |
| Is the app for real students yet? | No, a learning project | Auth and migrations stay out of scope |
