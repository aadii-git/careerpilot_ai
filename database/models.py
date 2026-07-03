"""
CareerPilot AI — Pydantic Data Models and SQLite Schema Definitions

All domain models are defined here as Pydantic v2 BaseModel classes.
SQL table creation DDL strings are co-located with the models they represent.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# SQL Schema Strings
# ─────────────────────────────────────────────────────────────────────────────

USERS_DDL = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL DEFAULT 'Learner',
    career_goal     TEXT,
    experience      TEXT,
    resume_text     TEXT,
    strong_topics   TEXT    DEFAULT '[]',
    weak_topics     TEXT    DEFAULT '[]',
    notes           TEXT,
    learning_streak INTEGER DEFAULT 0,
    last_session    TEXT,
    created_at      TEXT    NOT NULL
);
"""

ROADMAP_ITEMS_DDL = """
CREATE TABLE IF NOT EXISTS roadmap_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    month       INTEGER NOT NULL,
    topic       TEXT    NOT NULL,
    description TEXT,
    status      TEXT    NOT NULL DEFAULT 'pending',
    created_at  TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

LESSONS_DDL = """
CREATE TABLE IF NOT EXISTS lessons (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    topic       TEXT    NOT NULL,
    stage       TEXT    NOT NULL,
    content     TEXT,
    completed   INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    created_at  TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

QUIZ_RESULTS_DDL = """
CREATE TABLE IF NOT EXISTS quiz_results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    topic       TEXT    NOT NULL,
    difficulty  TEXT    NOT NULL,
    question_type TEXT  NOT NULL,
    score       REAL    NOT NULL,
    max_score   REAL    NOT NULL DEFAULT 100.0,
    feedback    TEXT,
    created_at  TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

INTERVIEW_RESULTS_DDL = """
CREATE TABLE IF NOT EXISTS interview_results (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    interview_type      TEXT    NOT NULL,
    question            TEXT,
    answer              TEXT,
    communication       REAL,
    technical_knowledge REAL,
    confidence          REAL,
    problem_solving     REAL,
    overall_score       REAL,
    feedback            TEXT,
    strengths           TEXT,
    improvements        TEXT,
    created_at          TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

CHAT_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS chat_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    agent       TEXT    NOT NULL,
    role        TEXT    NOT NULL,
    content     TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

ALL_DDL: list[str] = [
    USERS_DDL,
    ROADMAP_ITEMS_DDL,
    LESSONS_DDL,
    QUIZ_RESULTS_DDL,
    INTERVIEW_RESULTS_DDL,
    CHAT_HISTORY_DDL,
]


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────


class UserProfile(BaseModel):
    """Represents a CareerPilot user profile."""

    id: Optional[int] = None
    name: str = "Learner"
    career_goal: Optional[str] = None
    experience: Optional[str] = None
    resume_text: Optional[str] = None
    strong_topics: list[str] = Field(default_factory=list)
    weak_topics: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    learning_streak: int = 0
    last_session: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class RoadmapItem(BaseModel):
    """A single item in the user's learning roadmap."""

    id: Optional[int] = None
    user_id: int
    month: int = Field(ge=1, le=24)
    topic: str
    description: Optional[str] = None
    status: str = "pending"  # pending | in_progress | completed
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"pending", "in_progress", "completed"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v


class LessonRecord(BaseModel):
    """Record of a lesson stage completed by the user."""

    id: Optional[int] = None
    user_id: int
    topic: str
    stage: str
    content: Optional[str] = None
    completed: bool = False
    completed_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class QuizResult(BaseModel):
    """Result of a quiz attempt."""

    id: Optional[int] = None
    user_id: int
    topic: str
    difficulty: str
    question_type: str
    score: float = Field(ge=0.0, le=100.0)
    max_score: float = 100.0
    feedback: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def percentage(self) -> float:
        """Return score as a percentage."""
        if self.max_score == 0:
            return 0.0
        return round((self.score / self.max_score) * 100, 1)


class InterviewResult(BaseModel):
    """Result of a single interview Q&A exchange."""

    id: Optional[int] = None
    user_id: int
    interview_type: str
    question: Optional[str] = None
    answer: Optional[str] = None
    communication: Optional[float] = None
    technical_knowledge: Optional[float] = None
    confidence: Optional[float] = None
    problem_solving: Optional[float] = None
    overall_score: Optional[float] = None
    feedback: Optional[str] = None
    strengths: Optional[str] = None
    improvements: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ChatMessage(BaseModel):
    """A single turn in a conversation with an agent."""

    id: Optional[int] = None
    user_id: int
    agent: str
    role: str  # "user" | "model"
    content: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SkillGapReport(BaseModel):
    """Output of the CareerAgent skill analysis."""

    career_goal: str = ""
    current_skills: list[str] = []
    missing_skills: list[str] = []
    readiness_percentage: float = 0.0
    recommended_projects: list[str] = []
    career_paths: list[str] = []
    summary: str = ""


class QuizQuestion(BaseModel):
    """A generated quiz question."""

    question_type: str = "MCQ"  # MCQ | Short Answer | Coding
    difficulty: str = "Medium"
    question: str = ""
    options: Optional[list[str]] = None  # For MCQ
    correct_answer: str = ""
    explanation: str = ""


class QuizEvaluation(BaseModel):
    """Result of evaluating a user's quiz answer."""

    score: float = 0.0  # 0-100
    is_correct: bool = False
    feedback: str = ""
    correct_answer: str = ""
    explanation: str = ""


class InterviewEvaluation(BaseModel):
    """Detailed scoring for one interview answer."""

    communication: float = 0.0  # 0-10
    technical_knowledge: float = 0.0  # 0-10
    confidence: float = 0.0  # 0-10
    problem_solving: float = 0.0  # 0-10
    overall_score: float = 0.0  # 0-10
    strengths: list[str] = []
    improvements: list[str] = []
    feedback: str = ""


class RoadmapPlan(BaseModel):
    """Full generated roadmap plan."""

    career_goal: str = ""
    total_months: int = 6
    items: list[dict[str, Any]] = []
    summary: str = ""
