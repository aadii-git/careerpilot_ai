"""
CareerPilot AI — Progress Service

Calculates learning streaks, skill mastery scores,
and aggregated statistics for the Progress dashboard.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from database.models import InterviewResult, QuizResult, RoadmapItem

logger = logging.getLogger(__name__)


class ProgressService:
    """
    Aggregates and calculates progress metrics for a user.

    Usage:
        svc = ProgressService(db_manager)
        streak = svc.calculate_streak(user_id)
        mastery = svc.get_skill_mastery(user_id)
    """

    def __init__(self, db_manager: "DatabaseManager") -> None:  # type: ignore[name-defined]
        self._db = db_manager

    # ── Streak ────────────────────────────────────────────────────────────────

    def calculate_streak(self, user_id: int) -> int:
        """
        Calculate the user's current daily learning streak.

        Streak = number of consecutive days with at least one activity
        (quiz attempt or lesson completed), ending today or yesterday.
        """
        try:
            quiz_results = self._db.get_quiz_results(user_id, limit=200)
            interview_results = self._db.get_interview_results(user_id, limit=100)

            activity_dates: set[date] = set()
            for q in quiz_results:
                try:
                    activity_dates.add(datetime.fromisoformat(q.created_at).date())
                except Exception:
                    pass
            for i in interview_results:
                try:
                    activity_dates.add(datetime.fromisoformat(i.created_at).date())
                except Exception:
                    pass

            if not activity_dates:
                return 0

            today = date.today()
            streak = 0
            current = today

            # Allow streak to start from yesterday if no activity today
            if current not in activity_dates:
                current = today - timedelta(days=1)

            while current in activity_dates:
                streak += 1
                current -= timedelta(days=1)

            return streak
        except Exception as exc:
            logger.error("Error calculating streak: %s", exc)
            return 0

    def update_streak(self, user_id: int) -> int:
        """Recalculate and persist the streak to the user profile."""
        user = self._db.get_or_create_user(user_id)
        streak = self.calculate_streak(user_id)
        user.learning_streak = streak
        user.last_session = datetime.utcnow().isoformat()
        self._db.update_user(user)
        return streak

    # ── Skill Mastery ─────────────────────────────────────────────────────────

    def get_skill_mastery(self, user_id: int) -> dict[str, float]:
        """
        Return per-topic average quiz score as a mastery proxy.

        Returns:
            Dict mapping topic → average score (0-100).
        """
        results = self._db.get_quiz_results(user_id, limit=500)
        if not results:
            return {}

        topic_scores: dict[str, list[float]] = {}
        for r in results:
            topic_scores.setdefault(r.topic, []).append(r.score)

        return {
            topic: round(sum(scores) / len(scores), 1)
            for topic, scores in topic_scores.items()
        }

    def get_weak_topics(self, user_id: int, threshold: float = 60.0) -> list[str]:
        """Return topics where mastery is below the threshold."""
        mastery = self.get_skill_mastery(user_id)
        return [t for t, s in mastery.items() if s < threshold]

    def get_strong_topics(self, user_id: int, threshold: float = 80.0) -> list[str]:
        """Return topics where mastery is above the threshold."""
        mastery = self.get_skill_mastery(user_id)
        return [t for t, s in mastery.items() if s >= threshold]

    # ── Quiz Analytics ────────────────────────────────────────────────────────

    def get_quiz_score_over_time(self, user_id: int) -> pd.DataFrame:
        """
        Return a DataFrame of quiz scores over time for charting.

        Columns: date, topic, score, difficulty
        """
        results = self._db.get_quiz_results(user_id, limit=200)
        if not results:
            return pd.DataFrame(columns=["date", "topic", "score", "difficulty"])

        records = []
        for r in results:
            try:
                dt = datetime.fromisoformat(r.created_at)
            except Exception:
                dt = datetime.utcnow()
            records.append(
                {
                    "date": dt.strftime("%Y-%m-%d"),
                    "topic": r.topic,
                    "score": r.score,
                    "difficulty": r.difficulty,
                }
            )

        return pd.DataFrame(records)

    def get_interview_scores_over_time(self, user_id: int) -> pd.DataFrame:
        """
        Return a DataFrame of interview overall scores over time.

        Columns: date, interview_type, overall_score, communication,
                 technical_knowledge, confidence, problem_solving
        """
        results = self._db.get_interview_results(user_id, limit=100)
        if not results:
            return pd.DataFrame(
                columns=["date", "interview_type", "overall_score",
                         "communication", "technical_knowledge",
                         "confidence", "problem_solving"]
            )

        records = []
        for r in results:
            if r.overall_score is None:
                continue
            try:
                dt = datetime.fromisoformat(r.created_at)
            except Exception:
                dt = datetime.utcnow()
            records.append(
                {
                    "date": dt.strftime("%Y-%m-%d"),
                    "interview_type": r.interview_type,
                    "overall_score": r.overall_score,
                    "communication": r.communication or 0,
                    "technical_knowledge": r.technical_knowledge or 0,
                    "confidence": r.confidence or 0,
                    "problem_solving": r.problem_solving or 0,
                }
            )

        return pd.DataFrame(records)

    def get_roadmap_progress_data(self, roadmap: list[RoadmapItem]) -> pd.DataFrame:
        """
        Convert roadmap items to a DataFrame for Gantt-style charting.

        Columns: month, topic, status
        """
        if not roadmap:
            return pd.DataFrame(columns=["month", "topic", "status"])

        return pd.DataFrame(
            [
                {"month": item.month, "topic": item.topic, "status": item.status}
                for item in roadmap
            ]
        )

    # ── Summary ───────────────────────────────────────────────────────────────

    def get_full_summary(self, user_id: int) -> dict[str, Any]:
        """Return a complete progress summary dict."""
        stats = self._db.get_dashboard_stats(user_id)
        mastery = self.get_skill_mastery(user_id)
        streak = self.calculate_streak(user_id)

        return {
            **stats,
            "streak": streak,
            "skill_mastery": mastery,
            "weak_topics": self.get_weak_topics(user_id),
            "strong_topics": self.get_strong_topics(user_id),
        }
