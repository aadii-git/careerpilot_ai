"""
CareerPilot AI — Learning Coach Agent

Interactive AI tutor that teaches topics through an 8-stage lesson flow:
Overview → Analogy → Code Example → Practice → Mini Project → Quiz → Reflection → Resources

Never dumps everything at once — teaches one stage at a time.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from database.models import LessonRecord
from database.sqlite import DatabaseManager
from services.gemini_service import GeminiService
from utils.helpers import now_iso
from config import LESSON_STAGES
from utils.prompts import (
    LEARNING_AGENT_SYSTEM,
    lesson_stage_prompt,
    next_lesson_recommendation_prompt,
)

logger = logging.getLogger(__name__)


class LearningAgent:
    """
    Interactive AI tutor delivering structured, staged lessons.

    Each lesson progresses through 8 stages. Progress is persisted
    so the user can resume where they left off.
    """

    def __init__(self, gemini: GeminiService, db: DatabaseManager) -> None:
        self._gemini = gemini
        self._db = db

    # ── Lesson Content ────────────────────────────────────────────────────────

    def get_lesson_stage(
        self,
        user_id: int,
        topic: str,
        stage: str,
        user_level: str = "intermediate",
    ) -> str:
        """
        Generate content for a specific lesson stage.

        Args:
            user_id: The learner's ID.
            topic: The topic being taught.
            stage: One of the 8 lesson stages.
            user_level: 'beginner', 'intermediate', or 'advanced'.

        Returns:
            Formatted lesson content as a markdown string.
        """
        if stage not in LESSON_STAGES:
            raise ValueError(f"Invalid stage '{stage}'. Must be one of: {LESSON_STAGES}")

        # Get previous stage content for context
        previous_content = self._get_previous_stage_content(user_id, topic, stage)

        prompt = lesson_stage_prompt(
            topic=topic,
            stage=stage,
            user_level=user_level,
            previous_content=previous_content,
        )

        logger.info("Generating lesson '%s' stage '%s' for user %d", topic, stage, user_id)
        content = self._gemini.generate_text(
            prompt, system_instruction=LEARNING_AGENT_SYSTEM
        )

        # Persist this stage
        self._save_lesson_stage(user_id, topic, stage, content)

        return content

    def teach_interactively(
        self,
        user_id: int,
        topic: str,
        user_message: str,
        stage: str,
        history: Optional[list[dict]] = None,
        user_level: str = "intermediate",
    ) -> str:
        """
        Handle an interactive Q&A within a lesson stage.

        Args:
            user_id: The learner's ID.
            topic: Current topic being taught.
            user_message: The student's question or response.
            stage: Current lesson stage.
            history: Conversation history for context.
            user_level: Student's level.

        Returns:
            The tutor's response.
        """
        system = f"""{LEARNING_AGENT_SYSTEM}

Current Topic: {topic}
Current Stage: {stage}
Student Level: {user_level}

You are in the middle of teaching this topic interactively.
Answer questions, provide clarification, and guide the student forward.
Keep responses focused and educational. Encourage curiosity."""

        messages = history or []

        return self._gemini.chat_with_history(
            messages=messages,
            new_message=user_message,
            system_instruction=system,
        )

    # ── Progress Management ───────────────────────────────────────────────────

    def complete_stage(self, user_id: int, topic: str, stage: str) -> None:
        """Mark a lesson stage as completed."""
        lessons = self._db.get_lessons_for_topic(user_id, topic)
        for lesson in lessons:
            if lesson.stage == stage and lesson.id:
                # Update via re-save (simplest approach with current schema)
                updated = LessonRecord(
                    id=lesson.id,
                    user_id=user_id,
                    topic=topic,
                    stage=stage,
                    content=lesson.content,
                    completed=True,
                    completed_at=now_iso(),
                    created_at=lesson.created_at,
                )
                self._db.save_lesson(updated)
                logger.info("Stage '%s/%s' marked complete", topic, stage)
                return

        # If not found, create a completed record
        self._save_lesson_stage(user_id, topic, stage, content="", completed=True)

    def get_current_stage(self, user_id: int, topic: str) -> str:
        """
        Determine which stage the user should be on for a topic.

        Returns the next incomplete stage, or 'Resources' if all done.
        """
        lessons = self._db.get_lessons_for_topic(user_id, topic)
        completed_stages = {l.stage for l in lessons if l.completed}

        for stage in LESSON_STAGES:
            if stage not in completed_stages:
                return stage

        return "Resources"  # All stages complete

    def is_topic_complete(self, user_id: int, topic: str) -> bool:
        """Return True if all lesson stages for a topic are completed."""
        lessons = self._db.get_lessons_for_topic(user_id, topic)
        completed_stages = {l.stage for l in lessons if l.completed}
        return all(stage in completed_stages for stage in LESSON_STAGES)

    def get_lesson_progress(self, user_id: int, topic: str) -> dict[str, bool]:
        """Return completion status for each lesson stage."""
        lessons = self._db.get_lessons_for_topic(user_id, topic)
        completed_stages = {l.stage for l in lessons if l.completed}
        return {stage: stage in completed_stages for stage in LESSON_STAGES}

    # ── Next Lesson ───────────────────────────────────────────────────────────

    def recommend_next_topic(
        self,
        user_id: int,
        career_goal: str,
        roadmap_topics: list[str],
        quiz_scores: dict[str, float],
    ) -> dict:
        """
        Recommend the best next topic to study.

        Args:
            user_id: The learner's ID.
            career_goal: Target career role.
            roadmap_topics: All topics in the user's roadmap.
            quiz_scores: Topic → average score mapping.

        Returns:
            Dict with next_topic, reason, estimated_hours, prerequisite_check.
        """
        completed = self._db.get_completed_lessons(user_id)

        prompt = next_lesson_recommendation_prompt(
            completed_topics=completed,
            quiz_scores=quiz_scores,
            career_goal=career_goal,
            roadmap_topics=roadmap_topics,
        )

        data = self._gemini.generate_json(
            prompt, system_instruction=LEARNING_AGENT_SYSTEM
        )

        if isinstance(data, dict):
            return data

        # Fallback: first incomplete roadmap topic
        for topic in roadmap_topics:
            if topic not in completed:
                return {
                    "next_topic": topic,
                    "reason": "Next topic in your roadmap",
                    "estimated_hours": 10,
                    "prerequisite_check": "None",
                }

        return {
            "next_topic": "Review and Practice",
            "reason": "You've completed all roadmap topics! Time to consolidate knowledge.",
            "estimated_hours": 5,
            "prerequisite_check": "None",
        }

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _save_lesson_stage(
        self,
        user_id: int,
        topic: str,
        stage: str,
        content: str,
        completed: bool = False,
    ) -> None:
        """Internal helper to persist a lesson stage."""
        lesson = LessonRecord(
            user_id=user_id,
            topic=topic,
            stage=stage,
            content=content,
            completed=completed,
            completed_at=now_iso() if completed else None,
            created_at=now_iso(),
        )
        self._db.save_lesson(lesson)

    def _get_previous_stage_content(
        self, user_id: int, topic: str, current_stage: str
    ) -> Optional[str]:
        """Get content from the previous lesson stage for context."""
        current_idx = LESSON_STAGES.index(current_stage) if current_stage in LESSON_STAGES else 0
        if current_idx == 0:
            return None

        prev_stage = LESSON_STAGES[current_idx - 1]
        lessons = self._db.get_lessons_for_topic(user_id, topic)
        for lesson in lessons:
            if lesson.stage == prev_stage and lesson.content:
                return lesson.content[:500]  # Limit context
        return None
