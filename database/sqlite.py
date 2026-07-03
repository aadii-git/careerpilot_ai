"""
CareerPilot AI — SQLite Database Manager

Handles all database operations:
- Table creation on startup
- CRUD for users, roadmap, lessons, quiz results, interview results, chat history
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, Optional

from database.models import (
    ALL_DDL,
    ChatMessage,
    InterviewResult,
    LessonRecord,
    QuizResult,
    RoadmapItem,
    UserProfile,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Thread-safe SQLite database manager for CareerPilot AI."""

    def __init__(self, db_path: str = "careerpilot.db") -> None:
        self.db_path = db_path
        self._init_database()

    # ── Connection ────────────────────────────────────────────────────────────

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager that yields an auto-committing connection."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self) -> None:
        """Create all tables if they don't exist."""
        with self._get_connection() as conn:
            for ddl in ALL_DDL:
                conn.execute(ddl)
        logger.info("Database initialised at %s", self.db_path)

    # ── User CRUD ─────────────────────────────────────────────────────────────

    def get_or_create_user(self, user_id: int = 1, name: str = "Learner") -> UserProfile:
        """Fetch an existing user or create one if it doesn't exist."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if row:
                return self._row_to_user(row)
            # Create new user
            now = datetime.utcnow().isoformat()
            conn.execute(
                """INSERT INTO users (id, name, strong_topics, weak_topics,
                   learning_streak, created_at)
                   VALUES (?, ?, '[]', '[]', 0, ?)""",
                (user_id, name, now),
            )
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return self._row_to_user(row)

    def update_user(self, user: UserProfile) -> None:
        """Persist updated user profile fields."""
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE users SET
                    name = ?, career_goal = ?, experience = ?,
                    resume_text = ?, strong_topics = ?, weak_topics = ?,
                    notes = ?, learning_streak = ?, last_session = ?
                   WHERE id = ?""",
                (
                    user.name,
                    user.career_goal,
                    user.experience,
                    user.resume_text,
                    json.dumps(user.strong_topics),
                    json.dumps(user.weak_topics),
                    user.notes,
                    user.learning_streak,
                    user.last_session,
                    user.id,
                ),
            )

    def _row_to_user(self, row: sqlite3.Row) -> UserProfile:
        d = dict(row)
        d["strong_topics"] = json.loads(d.get("strong_topics") or "[]")
        d["weak_topics"] = json.loads(d.get("weak_topics") or "[]")
        return UserProfile(**d)

    # ── Roadmap CRUD ──────────────────────────────────────────────────────────

    def upsert_roadmap(self, items: list[RoadmapItem]) -> None:
        """Replace entire roadmap for a user."""
        if not items:
            return
        user_id = items[0].user_id
        with self._get_connection() as conn:
            conn.execute("DELETE FROM roadmap_items WHERE user_id = ?", (user_id,))
            conn.executemany(
                """INSERT INTO roadmap_items
                   (user_id, month, topic, description, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [
                    (i.user_id, i.month, i.topic, i.description, i.status, i.created_at)
                    for i in items
                ],
            )

    def get_roadmap(self, user_id: int) -> list[RoadmapItem]:
        """Return all roadmap items for a user ordered by month."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM roadmap_items WHERE user_id = ? ORDER BY month",
                (user_id,),
            ).fetchall()
        return [RoadmapItem(**dict(r)) for r in rows]

    def update_roadmap_item_status(self, item_id: int, status: str) -> None:
        """Update the status of a single roadmap item."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE roadmap_items SET status = ? WHERE id = ?", (status, item_id)
            )

    # ── Lesson CRUD ───────────────────────────────────────────────────────────

    def save_lesson(self, lesson: LessonRecord) -> int:
        """Insert a lesson record and return its ID."""
        with self._get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO lessons
                   (user_id, topic, stage, content, completed, completed_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    lesson.user_id,
                    lesson.topic,
                    lesson.stage,
                    lesson.content,
                    int(lesson.completed),
                    lesson.completed_at,
                    lesson.created_at,
                ),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def get_completed_lessons(self, user_id: int) -> list[str]:
        """Return list of distinct completed topics."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT topic FROM lessons WHERE user_id = ? AND completed = 1",
                (user_id,),
            ).fetchall()
        return [r["topic"] for r in rows]

    def get_lessons_for_topic(self, user_id: int, topic: str) -> list[LessonRecord]:
        """Return all lesson stages for a specific topic."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM lessons WHERE user_id = ? AND topic = ? ORDER BY created_at",
                (user_id, topic),
            ).fetchall()
        return [LessonRecord(**dict(r)) for r in rows]

    # ── Quiz CRUD ─────────────────────────────────────────────────────────────

    def save_quiz_result(self, result: QuizResult) -> None:
        """Store a quiz result."""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO quiz_results
                   (user_id, topic, difficulty, question_type, score, max_score, feedback, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    result.user_id,
                    result.topic,
                    result.difficulty,
                    result.question_type,
                    result.score,
                    result.max_score,
                    result.feedback,
                    result.created_at,
                ),
            )

    def get_quiz_results(self, user_id: int, limit: int = 100) -> list[QuizResult]:
        """Return recent quiz results for a user."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM quiz_results WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [QuizResult(**dict(r)) for r in rows]

    def get_average_quiz_score(self, user_id: int) -> float:
        """Calculate the user's overall average quiz score."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT AVG(score) as avg FROM quiz_results WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return round(row["avg"] or 0.0, 1)

    # ── Interview CRUD ────────────────────────────────────────────────────────

    def save_interview_result(self, result: InterviewResult) -> None:
        """Persist an interview result."""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO interview_results
                   (user_id, interview_type, question, answer,
                    communication, technical_knowledge, confidence,
                    problem_solving, overall_score, feedback,
                    strengths, improvements, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    result.user_id,
                    result.interview_type,
                    result.question,
                    result.answer,
                    result.communication,
                    result.technical_knowledge,
                    result.confidence,
                    result.problem_solving,
                    result.overall_score,
                    result.feedback,
                    result.strengths,
                    result.improvements,
                    result.created_at,
                ),
            )

    def get_interview_results(self, user_id: int, limit: int = 50) -> list[InterviewResult]:
        """Return recent interview results."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM interview_results WHERE user_id = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (user_id, limit),
            ).fetchall()
        return [InterviewResult(**dict(r)) for r in rows]

    def get_average_interview_score(self, user_id: int) -> float:
        """Overall average interview score."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT AVG(overall_score) as avg FROM interview_results WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return round(row["avg"] or 0.0, 1)

    # ── Chat History ──────────────────────────────────────────────────────────

    def save_chat_message(self, msg: ChatMessage) -> None:
        """Persist a chat message."""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO chat_history (user_id, agent, role, content, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (msg.user_id, msg.agent, msg.role, msg.content, msg.created_at),
            )

    def get_chat_history(
        self, user_id: int, agent: str, limit: int = 20
    ) -> list[ChatMessage]:
        """Return recent chat history for an agent."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM chat_history WHERE user_id = ? AND agent = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (user_id, agent, limit),
            ).fetchall()
        return [ChatMessage(**dict(r)) for r in reversed(rows)]

    def clear_chat_history(self, user_id: int, agent: str) -> None:
        """Clear chat history for a specific agent."""
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM chat_history WHERE user_id = ? AND agent = ?",
                (user_id, agent),
            )

    # ── Stats ─────────────────────────────────────────────────────────────────

    def get_dashboard_stats(self, user_id: int) -> dict[str, Any]:
        """Aggregate all key stats for the dashboard."""
        roadmap = self.get_roadmap(user_id)
        completed = [r for r in roadmap if r.status == "completed"]
        quiz_results = self.get_quiz_results(user_id, limit=200)

        return {
            "total_roadmap_items": len(roadmap),
            "completed_roadmap_items": len(completed),
            "roadmap_percentage": (
                round(len(completed) / len(roadmap) * 100, 1) if roadmap else 0.0
            ),
            "average_quiz_score": self.get_average_quiz_score(user_id),
            "average_interview_score": self.get_average_interview_score(user_id),
            "total_quiz_attempts": len(quiz_results),
            "completed_lessons": len(self.get_completed_lessons(user_id)),
        }
