# Spec Delta

## Purpose

Decides when a concept comes due for review after an answer, so what the student knows is revisited before it is forgotten and what they got wrong is revisited soon.

## ADDED Requirements

### Requirement: Passing lengthens the review interval
The system SHALL schedule the next review after a passed answer at the base interval multiplied by two for each additional consecutive pass beyond the first, with the base interval configured at 1 day.

#### Scenario: Consecutive passes
- **WHEN** a student's pass streak reaches 1, 2, 3 and 4
- **THEN** the next review is due in 1, 2, 4 and 8 days respectively

### Requirement: Failing schedules a short review
The system SHALL schedule the next review after a failed answer at a configured short interval, initially 0.05 days, and SHALL reset the pass streak to 0.

#### Scenario: Fail after a long streak
- **WHEN** a student with a streak of 4 fails an answer
- **THEN** the streak becomes 0 and the next review is due in about 72 minutes, not 8 days

#### Scenario: Fail on first attempt
- **WHEN** a student fails their first answer on a concept
- **THEN** the next review is due in about 72 minutes, sooner than the 1 day a first pass would give

### Requirement: Scheduling is repeatable
The system SHALL compute a review date only from the answer's result, the student's prior state and the time of grading, so identical inputs give identical dates.

#### Scenario: Same inputs twice
- **WHEN** the same prior state, quality and grading time are applied twice
- **THEN** both calculations give the same status, streak and next review date
