"""
CareerPilot AI — Orchestrator Agent

The central brain of the multi-agent system.
Routes user requests to the appropriate specialist agent,
maintains conversation context, and combines outputs.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from agents.career_agent import CareerAgent
from agents.interview_agent import InterviewAgent
from agents.learning_agent import LearningAgent
from agents.memory_agent import MemoryAgent
from agents.quiz_agent import QuizAgent
from agents.roadmap_agent import RoadmapAgent
from database.sqlite import DatabaseManager
from services.gemini_service import GeminiService
from utils.prompts import ORCHESTRATOR_SYSTEM

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Master orchestrator that coordinates all specialist agents.

    Responsibilities:
    - Initialise all sub-agents with shared dependencies
    - Route requests to the correct agent
    - Inject user memory context into every interaction
    - Combine outputs from multiple agents when needed
    - Maintain a clean public API for the Streamlit UI
    """

    def __init__(self, db_path: str = "careerpilot.db", user_id: int = 1) -> None:
        self._db = DatabaseManager(db_path)
        self._user_id = user_id

        # Shared Gemini service — one instance, all agents share it
        self._gemini = GeminiService()

        # Instantiate all agents
        self.memory = MemoryAgent(self._db, user_id)
        self.career = CareerAgent(self._gemini, self._db)
        self.roadmap = RoadmapAgent(self._gemini, self._db)
        self.learning = LearningAgent(self._gemini, self._db)
        self.quiz = QuizAgent(self._gemini, self._db)
        self.interview = InterviewAgent(self._gemini, self._db)

        logger.info("OrchestratorAgent initialised for user_id=%d", user_id)

    # ── Context ───────────────────────────────────────────────────────────────

    def get_context(self) -> dict[str, Any]:
        """Return full user context from MemoryAgent."""
        return self.memory.get_full_context()

    def get_user(self):
        """Return the current user profile."""
        return self.memory.get_user()

    # ── Career Flow ───────────────────────────────────────────────────────────

    def run_career_analysis(
        self,
        career_goal: str,
        experience: str,
        pdf_bytes: Optional[bytes] = None,
    ) -> dict[str, Any]:
        """
        Full career analysis flow.

        Optionally parses a resume, then runs CareerAgent analysis,
        generates a roadmap, and persists all results.

        Returns:
            Dict with keys: report, resume_analysis (optional), roadmap.
        """
        self.memory.update_career_goal(career_goal)
        self.memory.update_experience(experience)

        result: dict[str, Any] = {}

        if pdf_bytes:
            report, resume_analysis = self.career.analyze_with_resume(
                user_id=self._user_id,
                career_goal=career_goal,
                experience=experience,
                pdf_bytes=pdf_bytes,
            )
            result["resume_analysis"] = resume_analysis
        else:
            report = self.career.analyze_career(
                user_id=self._user_id,
                career_goal=career_goal,
                experience=experience,
            )

        result["report"] = report

        # Auto-generate roadmap from the analysis
        roadmap_plan = self.roadmap.generate_roadmap(
            user_id=self._user_id,
            career_goal=career_goal,
            current_skills=report.current_skills,
            missing_skills=report.missing_skills,
            total_months=6,
        )
        result["roadmap"] = roadmap_plan

        # Update memory with skill info
        self.memory.add_strong_topics(report.current_skills[:5])
        self.memory.add_weak_topics(report.missing_skills[:5])
        self.memory.record_session()

        return result

    # ── Learning Flow ─────────────────────────────────────────────────────────

    def start_lesson(
        self,
        topic: str,
        stage: str = "Overview",
        user_level: str = "intermediate",
    ) -> str:
        """
        Deliver a lesson stage to the user.

        Marks topic as in-progress in the roadmap.

        Returns:
            Formatted lesson content as markdown.
        """
        self.roadmap.mark_topic_in_progress(self._user_id, topic)
        content = self.learning.get_lesson_stage(
            user_id=self._user_id,
            topic=topic,
            stage=stage,
            user_level=user_level,
        )
        self.memory.record_session()
        return content

    def complete_lesson_stage(self, topic: str, stage: str) -> None:
        """Mark a lesson stage as complete and update roadmap if all done."""
        self.learning.complete_stage(self._user_id, topic, stage)
        if self.learning.is_topic_complete(self._user_id, topic):
            self.roadmap.mark_topic_complete(self._user_id, topic)
            logger.info("Topic '%s' fully completed!", topic)

    def get_lesson_progress(self, topic: str) -> dict[str, bool]:
        """Return stage-by-stage completion status for a topic."""
        return self.learning.get_lesson_progress(self._user_id, topic)

    def chat_with_tutor(
        self,
        topic: str,
        stage: str,
        user_message: str,
        history: Optional[list[dict]] = None,
        user_level: str = "intermediate",
    ) -> str:
        """Handle an interactive message within a lesson."""
        return self.learning.teach_interactively(
            user_id=self._user_id,
            topic=topic,
            user_message=user_message,
            stage=stage,
            history=history,
            user_level=user_level,
        )

    def get_next_topic_recommendation(self) -> dict:
        """Recommend the best next topic to study."""
        ctx = self.get_context()
        return self.learning.recommend_next_topic(
            user_id=self._user_id,
            career_goal=ctx["career_goal"],
            roadmap_topics=ctx["roadmap_topics"],
            quiz_scores=ctx["quiz_scores_by_topic"],
        )

    # ── Quiz Flow ─────────────────────────────────────────────────────────────

    def generate_quiz_question(
        self,
        topic: str,
        question_type: str = "MCQ",
        difficulty: str = "Medium",
    ):
        """Generate a single quiz question."""
        return self.quiz.generate_question(topic, question_type, difficulty)

    def evaluate_quiz_answer(
        self,
        topic: str,
        question,
        user_answer: str,
    ):
        """Evaluate a quiz answer and persist the result."""
        evaluation = self.quiz.evaluate_answer(
            user_id=self._user_id,
            topic=topic,
            question=question,
            user_answer=user_answer,
            save_result=True,
        )
        # Sync skill topics based on updated scores
        self.memory.sync_skill_topics_from_scores()
        self.memory.record_session()
        return evaluation

    # ── Interview Flow ────────────────────────────────────────────────────────

    def get_interview_question(
        self,
        interview_type: str,
        previous_questions: Optional[list[str]] = None,
    ) -> dict:
        """Generate the next interview question."""
        ctx = self.get_context()
        resume_summary = (
            ctx["resume_text"][:500] if ctx.get("resume_text") else None
        )
        return self.interview.generate_question(
            interview_type=interview_type,
            career_goal=ctx["career_goal"],
            previous_questions=previous_questions,
            resume_summary=resume_summary,
        )

    def evaluate_interview_answer(
        self,
        interview_type: str,
        question: str,
        answer: str,
    ):
        """Evaluate an interview answer and persist the result."""
        ctx = self.get_context()
        evaluation = self.interview.evaluate_answer(
            user_id=self._user_id,
            interview_type=interview_type,
            career_goal=ctx["career_goal"],
            question=question,
            answer=answer,
            save_result=True,
        )
        self.memory.record_session()
        return evaluation

    def get_interview_opening(self, interview_type: str) -> str:
        """Get an opening message for a mock interview session."""
        ctx = self.get_context()
        return self.interview.generate_opening_message(
            interview_type=interview_type,
            career_goal=ctx["career_goal"],
        )

    def get_sample_answer(self, question: str, interview_type: str) -> str:
        """Return a model answer for an interview question."""
        ctx = self.get_context()
        return self.interview.get_sample_answer(
            question=question,
            interview_type=interview_type,
            career_goal=ctx["career_goal"],
        )

    # ── Roadmap Flow ──────────────────────────────────────────────────────────

    def regenerate_roadmap(self, total_months: int = 6) -> Any:
        """Regenerate the roadmap based on current context."""
        ctx = self.get_context()
        return self.roadmap.generate_roadmap(
            user_id=self._user_id,
            career_goal=ctx["career_goal"],
            current_skills=ctx["strong_topics"],
            missing_skills=ctx["weak_topics"],
            total_months=total_months,
            completed_topics=ctx["completed_lessons"],
        )

    def adapt_roadmap(self) -> Any:
        """Adapt the roadmap based on recent quiz performance."""
        ctx = self.get_context()
        return self.roadmap.adapt_roadmap(
            user_id=self._user_id,
            career_goal=ctx["career_goal"],
            quiz_scores=ctx["quiz_scores_by_topic"],
            completed_topics=ctx["completed_lessons"],
        )

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def get_dashboard_data(self) -> dict[str, Any]:
        """
        Collect all data needed for the dashboard in one call.

        Returns:
            Comprehensive dict with stats, roadmap, and user profile.
        """
        ctx = self.get_context()
        stats = self._db.get_dashboard_stats(self._user_id)
        roadmap = self._db.get_roadmap(self._user_id)
        roadmap_summary = self.roadmap.get_roadmap_summary(self._user_id)

        return {
            **ctx,
            **stats,
            "roadmap": roadmap,
            "roadmap_summary": roadmap_summary,
        }

    # ── Free Chat ─────────────────────────────────────────────────────────────

    def chat(self, user_message: str, history: Optional[list[dict]] = None) -> str:
        """
        General-purpose chat with personalized context injected.

        Used for freeform questions not handled by a specific agent.
        """
        ctx_summary = self.memory.get_personalization_summary()
        system = f"{ORCHESTRATOR_SYSTEM}\n\nUser Context: {ctx_summary}"
        return self._gemini.chat_with_history(
            messages=history or [],
            new_message=user_message,
            system_instruction=system,
        )
