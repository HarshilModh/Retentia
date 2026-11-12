# Spec Delta

## Purpose

Keeps a permanent, per-student record of every graded answer so progress can be audited, replayed and used to evaluate how well the tutor's decisions work.

## ADDED Requirements

### Requirement: Every graded attempt is recorded
The system SHALL store exactly one attempt record each time a student's answer is graded, holding the student, the concept, the question text, the student's answer text, the quality score, whether it passed, any misconception noted, and the time of grading.

#### Scenario: Answer is graded
- **WHEN** a student's answer to a pending question is graded
- **THEN** one new attempt record exists for that student and concept
- **AND** it holds the question as it was asked and the answer as the student typed it

#### Scenario: No question is pending
- **WHEN** a student sends a message and no question is pending
- **THEN** no attempt record is created

### Requirement: Attempt records are never changed
The system SHALL NOT edit or delete an attempt record once written, other than as part of deleting the student's data.

#### Scenario: Same concept answered repeatedly
- **WHEN** a student answers the same concept three times
- **THEN** three attempt records exist, each with its own score and time

### Requirement: Attempt and progress change together
The system SHALL apply the progress update and write the attempt record as one unit, so both exist or neither does.

#### Scenario: Write fails part-way
- **WHEN** saving the attempt record fails during grading
- **THEN** the student's mastery, streak, status and next review date are unchanged

### Requirement: Response time is recorded when known
The system SHALL record how long the student took to answer, measured from when the question was posed to when the answer was received, and SHALL leave it empty when the question's posing time is unknown.

#### Scenario: Question posed then answered
- **WHEN** a student answers 42 seconds after the question was posed
- **THEN** the attempt record shows a response time of about 42 seconds

#### Scenario: Posing time unknown
- **WHEN** a question was posed before response times were tracked
- **THEN** the attempt record's response time is empty and grading still succeeds

### Requirement: Step type and hints have defined defaults
The system SHALL store the kind of study step that led to the question, empty until a step policy supplies it, and the number of hints used, zero until a hint feature exists.

#### Scenario: Question posed with no policy
- **WHEN** an attempt is recorded and no study step was assigned
- **THEN** the step type is empty and hints used is 0

### Requirement: Attempts are private to the student
The system SHALL only return attempt records to the student who made them.

#### Scenario: Two students, same concept
- **WHEN** two students answer the same concept
- **THEN** each student's attempt records are separate and neither can be read through the other's identity
