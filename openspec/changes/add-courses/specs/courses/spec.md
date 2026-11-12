# Spec Delta

## Purpose

Groups study material into courses, keeps each student's own courses private to them, offers a few shared demo courses, and tracks which course a student is currently studying.

## ADDED Requirements

### Requirement: Courses have an owner
The system SHALL record an owner for every course a student creates, and SHALL treat built-in demo courses as having no owner.

#### Scenario: Student creates a course
- **WHEN** a student creates a course titled "Organic Chemistry"
- **THEN** the course exists with that student as its owner and is listed in their courses

### Requirement: Own courses are private
The system SHALL show, return or act on a student-created course only for its owner, and SHALL respond to any other student exactly as if the course did not exist.

#### Scenario: Another student asks for the course
- **WHEN** student B requests, selects or deletes a course owned by student A
- **THEN** the system responds as if no such course exists, and nothing changes

#### Scenario: Listing courses
- **WHEN** a student lists their courses
- **THEN** the list contains the courses they own and the demo courses, and no course owned by anyone else

### Requirement: Demo courses are shared and read-only
The system SHALL provide built-in demo courses, visible to every student, that no student can rename, add material to or delete.

#### Scenario: Student tries to delete a demo course
- **WHEN** a student asks to delete a demo course
- **THEN** the request is refused with an explanation and the course is unchanged

#### Scenario: Progress on a demo course is personal
- **WHEN** two students study the same demo course
- **THEN** each sees only their own mastery and history for its concepts

### Requirement: Demo courses cover several subjects
The system SHALL ship with demo courses titled Git Basics, Intro Statistics and Basic Economics, each with at least three concepts linked by prerequisites, and SHALL contain no biology content.

#### Scenario: Fresh install
- **WHEN** the demo courses have been seeded into an empty system
- **THEN** listing courses shows Git Basics, Intro Statistics and Basic Economics, each with its concepts in prerequisite order

### Requirement: Each student has at most one active course
The system SHALL keep at most one active course per student, SHALL start every student with no active course, and SHALL only allow a course the student can see to become active.

#### Scenario: New student
- **WHEN** a student with no history opens the app
- **THEN** they have no active course and are offered the demo courses and the option to create one

#### Scenario: Selecting a demo course
- **WHEN** a student selects a demo course
- **THEN** it becomes their active course

### Requirement: Chat without an active course asks for one
The system SHALL reply to a chat message from a student with no active course with a fixed message asking them to pick or create a course, without calling the language model or changing any progress.

#### Scenario: Message before choosing a course
- **WHEN** a student with no active course sends "teach me something"
- **THEN** they receive the fixed message and no model call, question or attempt is made

### Requirement: Switching course starts a fresh conversation
The system SHALL clear the student's chat history and any pending question when their active course changes, and SHALL keep their progress in every course.

#### Scenario: Switch mid-question
- **WHEN** a question is pending and the student switches to another course
- **THEN** no question is pending, the chat history is empty, and their mastery in the previous course is unchanged

### Requirement: Deleting a course removes everything in it
The system SHALL, when an owner deletes their course, remove its concepts, the progress and attempt history for those concepts, and its stored content, and SHALL clear the active course of the owner if it was that course.

#### Scenario: Owner deletes a studied course
- **WHEN** the owner deletes a course they have studied
- **THEN** no concept, progress row, attempt record or stored content of that course remains
- **AND** the owner has no active course

### Requirement: Concepts in different courses never collide
The system SHALL allow two courses to contain concepts with the same title or the same caller-supplied key, and SHALL keep them as separate concepts.

#### Scenario: Two courses with an "Introduction" concept
- **WHEN** two courses each add a concept keyed "introduction"
- **THEN** both concepts exist, each in its own course, and progress on one does not affect the other
