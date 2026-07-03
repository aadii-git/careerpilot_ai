"""
CareerPilot AI — Career Coach Agent

Analyzes user's career goal, experience, and resume.
Produces: skill gap report, readiness score, career path recommendations.
"""

from __future__ import annotations

import logging
from typing import Optional

from database.models import SkillGapReport
from database.sqlite import DatabaseManager
from services.gemini_service import GeminiService
from services.resume_parser import ResumeParser
from utils.helpers import safe_parse_json
from utils.prompts import (
    CAREER_AGENT_SYSTEM,
    career_analysis_prompt,
    skill_gap_report_prompt,
)

logger = logging.getLogger(__name__)


class CareerAgent:
    """
    Analyzes careers and generates skill-gap reports.

    Coordinates with GeminiService for AI analysis and ResumeParser
    for PDF parsing when a resume is available.
    """

    def __init__(self, gemini: GeminiService, db: DatabaseManager) -> None:
        self._gemini = gemini
        self._db = db
        self._resume_parser = ResumeParser(gemini)

    # ── Main Analysis ─────────────────────────────────────────────────────────

    def analyze_career(
        self,
        user_id: int,
        career_goal: str,
        experience: str,
        resume_skills: Optional[list[str]] = None,
    ) -> SkillGapReport:
        """
        Perform comprehensive career analysis.

        Args:
            user_id: The user's database ID.
            career_goal: Target role (e.g., "AI Engineer").
            experience: User-described background and experience.
            resume_skills: Skills extracted from resume (if uploaded).

        Returns:
            SkillGapReport with current skills, gaps, readiness, and recommendations.
        """
        logger.info("Analyzing career for user %d: %s", user_id, career_goal)

        prompt = career_analysis_prompt(career_goal, experience, resume_skills)
        data = self._gemini.generate_json(
            prompt, system_instruction=CAREER_AGENT_SYSTEM
        )

        if not isinstance(data, dict):
            logger.error("Career analysis returned invalid data: %s", type(data))
            return self._fallback_report(career_goal)

        # Merge resume skills if not already in current_skills
        current = data.get("current_skills", [])
        if resume_skills:
            for skill in resume_skills:
                if skill.lower() not in [s.lower() for s in current]:
                    current.append(skill)

        report = SkillGapReport(
            career_goal=data.get("career_goal") or career_goal,
            current_skills=current or [],
            missing_skills=data.get("missing_skills") or [],
            readiness_percentage=float(data.get("readiness_percentage") or 0.0),
            recommended_projects=data.get("recommended_projects") or [],
            career_paths=data.get("career_paths") or [],
            summary=data.get("summary") or "",
        )

        # Persist results to user profile
        user = self._db.get_or_create_user(user_id)
        user.career_goal = career_goal
        user.experience = experience
        # Update weak topics from missing skills
        user.weak_topics = list(set(user.weak_topics + report.missing_skills[:5]))
        user.strong_topics = list(set(user.strong_topics + report.current_skills[:5]))
        self._db.update_user(user)

        logger.info(
            "Career analysis complete. Readiness: %.1f%%", report.readiness_percentage
        )
        return report

    def analyze_with_resume(
        self,
        user_id: int,
        career_goal: str,
        experience: str,
        pdf_bytes: bytes,
    ) -> tuple[SkillGapReport, "ResumeAnalysis"]:  # type: ignore[name-defined]
        """
        Full pipeline: parse resume → career analysis → gap report.

        Returns:
            Tuple of (SkillGapReport, ResumeAnalysis).
        """
        logger.info("Parsing resume for user %d", user_id)
        resume_analysis = self._resume_parser.parse_pdf_bytes(pdf_bytes, career_goal)

        # Persist resume text
        user = self._db.get_or_create_user(user_id)
        user.resume_text = resume_analysis.raw_text[:5000]
        self._db.update_user(user)

        report = self.analyze_career(
            user_id=user_id,
            career_goal=career_goal,
            experience=experience,
            resume_skills=resume_analysis.skills,
        )

        return report, resume_analysis

    # ── Detailed Gap Report ───────────────────────────────────────────────────

    def get_skill_gap_details(
        self, current_skills: list[str], career_goal: str
    ) -> dict:
        """
        Generate a detailed skill gap analysis with critical vs. nice-to-have gaps.

        Returns:
            Dict with critical_gaps, nice_to_have, timeline, immediate_actions.
        """
        prompt = skill_gap_report_prompt(current_skills, career_goal)
        data = self._gemini.generate_json(
            prompt, system_instruction=CAREER_AGENT_SYSTEM
        )
        if isinstance(data, dict):
            return data
        return {
            "critical_gaps": [],
            "nice_to_have": [],
            "timeline_estimate": "3-6 months",
            "immediate_actions": ["Start with Python fundamentals"],
        }

    def get_career_advice(self, question: str, user_context: str) -> str:
        """
        Answer a freeform career question with user context.

        Args:
            question: The user's career question.
            user_context: Personalization context from MemoryAgent.

        Returns:
            AI-generated career advice.
        """
        prompt = f"""
Context: {user_context}

Career Question: {question}

Provide specific, actionable career advice tailored to this user's situation.
Be encouraging but realistic. Include concrete next steps.
"""
        return self._gemini.generate_text(
            prompt, system_instruction=CAREER_AGENT_SYSTEM
        )

    # ── Fallback ──────────────────────────────────────────────────────────────

    def _fallback_report(self, career_goal: str) -> SkillGapReport:
        """Return a safe fallback report when AI generation fails."""
        return SkillGapReport(
            career_goal=career_goal,
            current_skills=["Unable to analyze — please try again"],
            missing_skills=[],
            readiness_percentage=0.0,
            recommended_projects=[],
            career_paths=[],
            summary="Analysis encountered an error. Please check your API key and try again.",
        )
