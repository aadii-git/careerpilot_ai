"""
CareerPilot AI — Memory Agent

Manages persistent user state in SQLite.
Reads and writes: career goals, progress, scores, topics, session history.
Acts as the single source of truth for user context across all agents.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from database.models import UserProfile
from database.sqlite import DatabaseManager
from services.progress_service import ProgressService
from utils.helpers import merge_skill_lists, now_iso

logger = logging.getLogger(__name__)


class MemoryAgent:
    """
    Persistent memory layer for CareerPilot AI.

    Reads and writes user state to SQLite, providing all other agents
    with the context they need to personalize their responses.
    """

    def __init__(self, db: DatabaseManager, user_id: int = 1) -> None:
        self._db = db
        self._user_id = user_id
        self._progress_svc = ProgressService(db)

    # ── User Profile ──────────────────────────────────────────────────────────

    def get_user(self) -> UserProfile:
        """Fetch (or create) the current user profile."""
        return self._db.get_or_create_user(self._user_id)

    def update_career_goal(self, goal: str) -> None:
        """Persist the user's career goal."""
        user = self.get_user()
        user.career_goal = goal
        self._db.update_user(user)
        logger.info("Updated career goal: %s", goal)

    def update_experience(self, experience: str) -> None:
        """Persist the user's self-described experience."""
        user = self.get_user()
        user.experience = experience
        self._db.update_user(user)

    def update_resume_text(self, text: str) -> None:
        """Persist extracted resume text."""
        user = self.get_user()
        user.resume_text = text
        self._db.update_user(user)

    def update_name(self, name: str) -> None:
        """Update the user's display name."""
        user = self.get_user()
        user.name = name
        self._db.update_user(user)

    # ── Skills ────────────────────────────────────────────────────────────────

    def add_strong_topics(self, topics: list[str]) -> None:
        """Add topics to the user's strong skills list."""
        user = self.get_user()
        user.strong_topics = merge_skill_lists(user.strong_topics, topics)
        self._db.update_user(user)

    def add_weak_topics(self, topics: list[str]) -> None:
        """Add topics to the user's weak skills list."""
        user = self.get_user()
        user.weak_topics = merge_skill_lists(user.weak_topics, topics)
        self._db.update_user(user)

    def sync_skill_topics_from_scores(self) -> None:
        """Auto-update strong/weak topics based on quiz score thresholds."""
        weak = self._progress_svc.get_weak_topics(self._user_id)
        strong = self._progress_svc.get_strong_topics(self._user_id)
        if weak:
            self.add_weak_topics(weak)
        if strong:
            self.add_strong_topics(strong)

    # ── Session Tracking ──────────────────────────────────────────────────────

    def record_session(self) -> int:
        """Update last_session timestamp and recalculate streak."""
        user = self.get_user()
        user.last_session = now_iso()
        self._db.update_user(user)
        streak = self._progress_svc.update_streak(self._user_id)
        logger.info("Session recorded. Streak: %d", streak)
        return streak

    def get_streak(self) -> int:
        """Return the current learning streak."""
        return self._progress_svc.calculate_streak(self._user_id)

    # ── Context Building ──────────────────────────────────────────────────────

    def get_full_context(self) -> dict[str, Any]:
        """
        Build a comprehensive context dict for use by other agents.

        Returns everything the orchestrator needs to route and personalize.
        """
        user = self.get_user()
        completed_lessons = self._db.get_completed_lessons(self._user_id)
        roadmap = self._db.get_roadmap(self._user_id)
        quiz_results = self._db.get_quiz_results(self._user_id, limit=50)
        avg_quiz = self._db.get_average_quiz_score(self._user_id)
        avg_interview = self._db.get_average_interview_score(self._user_id)
        streak = self.get_streak()

        quiz_scores_by_topic: dict[str, float] = {}
        for r in quiz_results:
            topic_scores = quiz_scores_by_topic.setdefault(r.topic, [])
            if isinstance(topic_scores, list):
                topic_scores.append(r.score)
        quiz_scores_by_topic = {
            k: round(sum(v) / len(v), 1) for k, v in quiz_scores_by_topic.items()
        }

        return {
            "user_id": user.id,
            "name": user.name,
            "career_goal": user.career_goal or "Not set",
            "experience": user.experience or "Not provided",
            "resume_text": user.resume_text,
            "strong_topics": user.strong_topics,
            "weak_topics": user.weak_topics,
            "learning_streak": streak,
            "completed_lessons": completed_lessons,
            "roadmap_topics": [r.topic for r in roadmap],
            "quiz_scores_by_topic": quiz_scores_by_topic,
            "average_quiz_score": avg_quiz,
            "average_interview_score": avg_interview,
            "last_session": user.last_session,
            "notes": user.notes,
        }

    def save_note(self, note: str) -> None:
        """Append a note to the user's session notes."""
        user = self.get_user()
        existing = user.notes or ""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        user.notes = f"{existing}\n[{timestamp}] {note}".strip()
        self._db.update_user(user)

    def get_personalization_summary(self) -> str:
        """Return a short string for injecting user context into prompts."""
        ctx = self.get_full_context()
        parts = [f"User: {ctx['name']}"]
        if ctx["career_goal"] != "Not set":
            parts.append(f"Career Goal: {ctx['career_goal']}")
        if ctx["completed_lessons"]:
            parts.append(f"Completed: {', '.join(ctx['completed_lessons'][-3:])}")
        if ctx["weak_topics"]:
            parts.append(f"Needs work on: {', '.join(ctx['weak_topics'][:3])}")
        if ctx["strong_topics"]:
            parts.append(f"Strong in: {', '.join(ctx['strong_topics'][:3])}")
        parts.append(f"Streak: {ctx['learning_streak']} days")
        return " | ".join(parts)
