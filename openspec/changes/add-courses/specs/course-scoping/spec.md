# Spec Delta

## Purpose

Keeps everything the tutor does for a student inside that student's active course, so material, questions and progress from one course never leak into another.

## ADDED Requirements

### Requirement: Content search stays in the active course
The system SHALL return course content only from the student's active course, for both teaching and grading.

#### Scenario: Two courses cover similar topics
- **WHEN** a student whose active course is A asks about a topic that also appears in course B
- **THEN** only passages from course A are used

### Requirement: Questions are only posed on the active course
The system SHALL refuse to pose a question on a concept that is not in the student's active course, and SHALL tell the tutor which concepts are valid.

#### Scenario: Tutor names a concept from another course
- **WHEN** the tutor tries to question the student on a concept from a course that is not active
- **THEN** no question is recorded and the tutor is told the concept is not in the active course

### Requirement: Progress and suggestions are per course
The system SHALL compute the student's progress list and the suggested next concept from the active course's concepts only, unless another course the student can see is explicitly requested for progress, and SHALL return an empty progress list when there is no active course.

#### Scenario: Progress view
- **WHEN** a student views their progress
- **THEN** only concepts of their active course are listed

#### Scenario: No active course
- **WHEN** a student with no active course views their progress
- **THEN** the list is empty

#### Scenario: Progress for a named course
- **WHEN** a student requests progress for a specific course they can see
- **THEN** that course's concepts are listed with the student's progress on each

#### Scenario: Progress for a course they cannot see
- **WHEN** a student requests progress for another student's course
- **THEN** the system responds as if the course does not exist

### Requirement: The tutor is told which course it is teaching
The system SHALL name the active course in the tutor's instructions and SHALL NOT describe the tutor as specific to any subject.

#### Scenario: Active course is Git Basics
- **WHEN** the active course is "Git Basics"
- **THEN** the tutor's instructions name "Git Basics" and name no other subject

### Requirement: Learner memories span courses
The system SHALL keep observations about how a student learns (their preferences and recurring struggles) available in every course they study.

#### Scenario: Preference saved in one course
- **WHEN** the tutor saves "prefers short examples" while the student studies course A
- **THEN** that observation is available when the same student studies course B

### Requirement: Adding material requires an owned course
The system SHALL accept new course material only for a course the requesting student owns, and SHALL replace, not duplicate, a concept's stored content when that concept's material is added again.

#### Scenario: Re-adding a concept's material
- **WHEN** the same concept's material is added to a course twice
- **THEN** searches return each passage once

#### Scenario: Adding material to someone else's course
- **WHEN** a student adds material to a course they do not own, or to a demo course
- **THEN** the request is refused and nothing is stored
