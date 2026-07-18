from sqlalchemy import Column, Integer,String,DateTime,Float,Boolean,ForeignKey
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
    chat_history = Column(JSONB, default=list, nullable=False)