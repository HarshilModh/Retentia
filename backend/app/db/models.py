from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Float, Boolean, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.session import Base


class Concept(Base):
    __tablename__ = "concepts"

    id = Column(String, primary_key=True)
    subject = Column(String, nullable=False)
    title = Column(String, nullable=False)
    summary = Column(String, nullable=True)
    prereqs = Column(JSONB, default=list, nullable=False)
    seq = Column(Integer, default=0, nullable=False)

class LearnerConcept(Base):
    __tablename__ = "learner_concept"

    user_id = Column(String, primary_key=True)
    concept_id = Column(String, ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)
    mastery = Column(Float, default=0.0, nullable=False)
    status = Column(String, default="not_started", nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    streak = Column(Integer, default=0, nullable=False)
    misconceptions = Column(JSONB, default=list, nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    next_review = Column(DateTime(timezone=True), nullable=True)

class SessionState(Base):
    __tablename__ = "sessions"

    user_id = Column(String, primary_key=True)
    current_concept_id = Column(String, nullable=True)
    pending_question = Column(String, nullable=True)
    # When pending_question was posed; used to measure how long the student
    # took to answer. Null when no question is pending or the time is unknown.
    question_posed_at = Column(DateTime(timezone=True), nullable=True)
    chat_history = Column(JSONB, default=list, nullable=False)


# Append-only log: one row per graded answer. Rows are never updated.
class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    concept_id = Column(String, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    quality = Column(Float, nullable=False)
    passed = Column(Boolean, nullable=False)
    misconception = Column(String, nullable=True)
    # Plain string so the next-step policy can add values without a schema
    # change. Null until a policy assigns one.
    action_type = Column(String, nullable=True)
    hints_used = Column(Integer, default=0, nullable=False)
    response_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_attempts_user_concept_created", "user_id", "concept_id", "created_at"),)