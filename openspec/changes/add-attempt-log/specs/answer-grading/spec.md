# Spec Delta

## Purpose

Defines how a student's answer is judged, so the score depends on what the student actually wrote and on the course material, not on how the tutoring agent restates it.

## ADDED Requirements

### Requirement: The student's own message is graded
The system SHALL grade the exact text of the message the student sent in the current turn, and SHALL NOT grade text supplied or altered by the tutoring agent.

#### Scenario: Agent paraphrases the answer
- **WHEN** the student sends "its when the cell splits in two" and the agent calls the grading step
- **THEN** the text graded and stored is "its when the cell splits in two"

### Requirement: The grader is given course content
The system SHALL give the grader the passages of the course material retrieved for the concept being asked about, in addition to the concept's summary, limited to a configured maximum length.

#### Scenario: Material exists for the concept
- **WHEN** a question about a concept is graded and course passages exist for it
- **THEN** the grader receives those passages along with the question and answer

#### Scenario: No passages found
- **WHEN** no course passages exist for the concept
- **THEN** grading proceeds using the concept's summary alone

### Requirement: Quality scores stay within range
The system SHALL treat a quality score below 0.0 as 0.0 and above 1.0 as 1.0 before it is used or stored.

#### Scenario: Grader returns an out-of-range score
- **WHEN** the grader returns a quality of 1.4
- **THEN** 1.0 is used for the mastery update and stored in the attempt record

### Requirement: Pass line is configurable
The system SHALL count an answer as passed when its quality is at or above a configured pass threshold, initially 0.6, which is separate from the mastery threshold.

#### Scenario: Score exactly at the line
- **WHEN** the quality is 0.6 and the pass threshold is 0.6
- **THEN** the answer counts as passed

#### Scenario: Score just below the line
- **WHEN** the quality is 0.59 and the pass threshold is 0.6
- **THEN** the answer counts as failed and the streak resets to 0

### Requirement: A grading failure changes nothing
The system SHALL leave progress and the pending question unchanged when grading cannot be completed, and SHALL tell the agent that grading failed.

#### Scenario: Grader call fails
- **WHEN** the grading service returns an error
- **THEN** no attempt record is written, mastery is unchanged, and the question remains pending
