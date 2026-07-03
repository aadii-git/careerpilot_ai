"""
CareerPilot AI — Roadmap Agent

Generates and adapts personalized month-by-month learning roadmaps.
Persists items to SQLite and re-adapts based on quiz performance.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from database.models import RoadmapItem, RoadmapPlan
from database.sqlite import DatabaseManager
from services.gemini_service import GeminiService
from utils.helpers import now_iso
from utils.prompts import (
    ROADMAP_AGENT_SYSTEM,
    adapt_roadmap_prompt,
    roadmap_generation_prompt,
)

logger = logging.getLogger(__name__)


class RoadmapAgent:
    """
    Generates and adapts personalized learning roadmaps.

    Creates month-by-month plans tailored to the user's career goal,
    current skills, and performance metrics.
    """

    def __init__(self, gemini: GeminiService, db: DatabaseManager) -> None:
        self._gemini = gemini
        self._db = db

    # ── Generate ──────────────────────────────────────────────────────────────

    def generate_roadmap(
        self,
        user_id: int,
        career_goal: str,
        current_skills: list[str],
        missing_skills: list[str],
        total_months: int = 6,
        completed_topics: Optional[list[str]] = None,
    ) -> RoadmapPlan:
        """
        Generate a fresh learning roadmap and persist it.

        Args:
            user_id: User's database ID.
            career_goal: Target career role.
            current_skills: Skills the user already has.
            missing_skills: Skills they need to acquire.
            total_months: Duration of the roadmap.
            completed_topics: Topics already finished (for refresh).

        Returns:
            RoadmapPlan with all items.
        """
        logger.info("Generating %d-month roadmap for user %d", total_months, user_id)

        prompt = roadmap_generation_prompt(
            career_goal=career_goal,
            current_skills=current_skills,
            missing_skills=missing_skills,
            completed_topics=completed_topics,
            total_months=total_months,
        )

        data = self._gemini.generate_json(
            prompt, system_instruction=ROADMAP_AGENT_SYSTEM
        )

        if not isinstance(data, dict) or "items" not in data:
            logger.error("Roadmap generation failed — invalid response")
            return self._fallback_roadmap(user_id, career_goal, total_months)

        # Build RoadmapItem list
        items: list[RoadmapItem] = []
        for item_data in data["items"]:
            month_val = item_data.get("month")
            try:
                month = int(month_val) if month_val is not None else 1
            except (ValueError, TypeError):
                month = 1
            topic = item_data.get("topic") or "Unknown Topic"
            description = item_data.get("description") or ""

            # Mark already-completed topics
            status = "pending"
            if completed_topics and topic in completed_topics:
                status = "completed"

            items.append(
                RoadmapItem(
                    user_id=user_id,
                    month=max(1, min(24, int(month))),
                    topic=topic,
                    description=description,
                    status=status,
                    created_at=now_iso(),
                )
            )

        # Persist to database
        self._db.upsert_roadmap(items)
        logger.info("Roadmap saved: %d items", len(items))

        return RoadmapPlan(
            career_goal=career_goal,
            total_months=total_months,
            items=[i.model_dump() for i in items],
            summary=data.get("summary") or "",
        )

    # ── Adapt ─────────────────────────────────────────────────────────────────

    def adapt_roadmap(
        self,
        user_id: int,
        career_goal: str,
        quiz_scores: dict[str, float],
        completed_topics: list[str],
    ) -> RoadmapPlan:
        """
        Re-generate roadmap adapted to current performance.

        Topics with score < 60 get reinforcement; high scorers advance faster.
        """
        existing_items = self._db.get_roadmap(user_id)
        if not existing_items:
            logger.warning("No existing roadmap to adapt for user %d", user_id)
            return self._fallback_roadmap(user_id, career_goal, 6)

        existing_data = [i.model_dump() for i in existing_items]

        prompt = adapt_roadmap_prompt(
            original_roadmap=existing_data,
            quiz_scores=quiz_scores,
            completed_topics=completed_topics,
        )

        data = self._gemini.generate_json(
            prompt, system_instruction=ROADMAP_AGENT_SYSTEM
        )

        if not isinstance(data, dict) or "items" not in data:
            logger.warning("Roadmap adaptation failed; keeping original")
            return RoadmapPlan(
                career_goal=career_goal,
                total_months=len(existing_items),
                items=existing_data,
                summary="Roadmap adaptation failed. Using original plan.",
            )

        items: list[RoadmapItem] = []
        for item_data in data["items"]:
            month_val = item_data.get("month")
            try:
                month = int(month_val) if month_val is not None else 1
            except (ValueError, TypeError):
                month = 1
            topic = item_data.get("topic") or "Unknown"
            status = item_data.get("status") or "pending"

            if completed_topics and topic in completed_topics:
                status = "completed"

            items.append(
                RoadmapItem(
                    user_id=user_id,
                    month=max(1, min(24, int(month))),
                    topic=topic,
                    description=item_data.get("description") or "",
                    status=status,
                    created_at=now_iso(),
                )
            )

        self._db.upsert_roadmap(items)
        logger.info("Roadmap adapted: %d items", len(items))

        return RoadmapPlan(
            career_goal=career_goal,
            total_months=max(i.month for i in items) if items else 6,
            items=[i.model_dump() for i in items],
            summary=data.get("summary") or "Roadmap updated based on your progress.",
        )

    # ── Status Updates ────────────────────────────────────────────────────────

    def mark_topic_complete(self, user_id: int, topic: str) -> None:
        """Mark a roadmap topic as completed."""
        roadmap = self._db.get_roadmap(user_id)
        for item in roadmap:
            if item.topic.lower() == topic.lower() and item.id:
                self._db.update_roadmap_item_status(item.id, "completed")
                logger.info("Marked '%s' as completed", topic)
                return
        logger.warning("Topic '%s' not found in roadmap", topic)

    def mark_topic_in_progress(self, user_id: int, topic: str) -> None:
        """Mark a roadmap topic as in progress."""
        roadmap = self._db.get_roadmap(user_id)
        for item in roadmap:
            if item.topic.lower() == topic.lower() and item.id:
                self._db.update_roadmap_item_status(item.id, "in_progress")
                return

    def get_current_topic(self, user_id: int) -> Optional[RoadmapItem]:
        """Return the first in-progress or pending roadmap item."""
        roadmap = self._db.get_roadmap(user_id)
        # Prefer in_progress first
        for item in roadmap:
            if item.status == "in_progress":
                return item
        # Then first pending
        for item in roadmap:
            if item.status == "pending":
                return item
        return None

    def get_roadmap_summary(self, user_id: int) -> dict[str, Any]:
        """Return progress stats for the roadmap."""
        items = self._db.get_roadmap(user_id)
        total = len(items)
        completed = sum(1 for i in items if i.status == "completed")
        in_progress = sum(1 for i in items if i.status == "in_progress")
        pending = sum(1 for i in items if i.status == "pending")

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "percentage": round(completed / total * 100, 1) if total > 0 else 0.0,
        }

    # ── Fallback ──────────────────────────────────────────────────────────────

    def _fallback_roadmap(
        self, user_id: int, career_goal: str, total_months: int
    ) -> RoadmapPlan:
        """Generate a basic fallback roadmap when AI generation fails."""
        default_topics = [
            ("Python Fundamentals", "Master Python syntax, data structures, and OOP"),
            ("Git & Version Control", "Learn Git workflow for collaborative development"),
            ("Data Structures & Algorithms", "Core CS fundamentals for interviews"),
            ("Machine Learning Basics", "Supervised and unsupervised learning concepts"),
            ("Deep Learning", "Neural networks, CNNs, RNNs with PyTorch"),
            ("LLMs & AI Agents", "Large language models and agent architectures"),
        ]

        items = []
        for idx, (topic, desc) in enumerate(default_topics[:total_months], start=1):
            item = RoadmapItem(
                user_id=user_id,
                month=idx,
                topic=topic,
                description=desc,
                status="pending",
                created_at=now_iso(),
            )
            items.append(item)

        self._db.upsert_roadmap(items)
        return RoadmapPlan(
            career_goal=career_goal,
            total_months=total_months,
            items=[i.model_dump() for i in items],
            summary="Default roadmap generated. Please retry for a personalized plan.",
        )
