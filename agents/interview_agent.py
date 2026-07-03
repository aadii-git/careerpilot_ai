"""
CareerPilot AI — Interview Coach Agent

Conducts realistic mock interviews across multiple types:
Behavioral, Technical, Resume-Based, Coding, System Design.

Evaluates answers on 4 dimensions and provides detailed coaching feedback.
"""

from __future__ import annotations

import logging
from typing import Optional

from database.models import InterviewEvaluation, InterviewResult
from database.sqlite import DatabaseManager
from services.gemini_service import GeminiService
from utils.helpers import now_iso
from utils.prompts import (
    INTERVIEW_AGENT_SYSTEM,
    interview_evaluation_prompt,
    interview_question_prompt,
)

logger = logging.getLogger(__name__)


class InterviewAgent:
    """
    Conducts mock interviews and provides detailed coaching feedback.

    Generates contextual interview questions, evaluates answers on
    4 dimensions (Communication, Technical, Confidence, Problem Solving),
    and provides specific improvement suggestions.
    """

    def __init__(self, gemini: GeminiService, db: DatabaseManager) -> None:
        self._gemini = gemini
        self._db = db

    # ── Question Generation ───────────────────────────────────────────────────

    def generate_question(
        self,
        interview_type: str,
        career_goal: str,
        previous_questions: Optional[list[str]] = None,
        resume_summary: Optional[str] = None,
    ) -> dict:
        """
        Generate a single interview question.

        Args:
            interview_type: 'Behavioral', 'Technical', 'Resume-Based',
                            'Coding', or 'System Design'.
            career_goal: Target role for context.
            previous_questions: Already-asked questions to avoid repetition.
            resume_summary: Brief resume info for Resume-Based interviews.

        Returns:
            Dict with question, question_type, expected_topics, time_limit_minutes.
        """
        logger.info("Generating %s interview question for %s", interview_type, career_goal)

        prompt = interview_question_prompt(
            interview_type=interview_type,
            career_goal=career_goal,
            previous_questions=previous_questions,
            resume_summary=resume_summary,
        )

        data = self._gemini.generate_json(
            prompt, system_instruction=INTERVIEW_AGENT_SYSTEM
        )

        if isinstance(data, dict) and "question" in data:
            return data

        # Fallback question
        return self._fallback_question(interview_type, career_goal)

    def generate_opening_message(self, interview_type: str, career_goal: str) -> str:
        """Generate a professional interview opening statement."""
        prompt = f"""
You are starting a {interview_type} mock interview for a {career_goal} position.
Write a brief, professional opening message (2-3 sentences) to set the scene.
Be encouraging and professional. Tell the candidate what to expect.
"""
        return self._gemini.generate_text(
            prompt, system_instruction=INTERVIEW_AGENT_SYSTEM
        )

    # ── Answer Evaluation ─────────────────────────────────────────────────────

    def evaluate_answer(
        self,
        user_id: int,
        interview_type: str,
        career_goal: str,
        question: str,
        answer: str,
        save_result: bool = True,
    ) -> InterviewEvaluation:
        """
        Evaluate an interview answer across 4 dimensions.

        Args:
            user_id: The candidate's ID.
            interview_type: Type of interview question.
            career_goal: Target role for context.
            question: The interview question asked.
            answer: The candidate's answer.
            save_result: Whether to persist to SQLite.

        Returns:
            InterviewEvaluation with per-dimension scores and feedback.
        """
        logger.info(
            "Evaluating %s answer for user %d", interview_type, user_id
        )

        prompt = interview_evaluation_prompt(
            question=question,
            answer=answer,
            interview_type=interview_type,
            career_goal=career_goal,
        )

        data = self._gemini.generate_json(
            prompt, system_instruction=INTERVIEW_AGENT_SYSTEM
        )

        if not isinstance(data, dict):
            logger.error("Interview evaluation failed — invalid response")
            return self._fallback_evaluation()

        evaluation = InterviewEvaluation(
            communication=float(data.get("communication") or 5.0),
            technical_knowledge=float(data.get("technical_knowledge") or 5.0),
            confidence=float(data.get("confidence") or 5.0),
            problem_solving=float(data.get("problem_solving") or 5.0),
            overall_score=float(data.get("overall_score") or 5.0),
            strengths=data.get("strengths") or [],
            improvements=data.get("improvements") or [],
            feedback=data.get("feedback") or "",
        )

        if save_result:
            self._save_result(user_id, interview_type, question, answer, evaluation)

        return evaluation

    # ── Session Management ────────────────────────────────────────────────────

    def run_interview_session(
        self,
        user_id: int,
        interview_type: str,
        career_goal: str,
        qa_pairs: list[tuple[str, str]],
        resume_summary: Optional[str] = None,
    ) -> dict:
        """
        Evaluate a full interview session with multiple Q&A pairs.

        Args:
            user_id: Candidate's ID.
            interview_type: Type of interview.
            career_goal: Target role.
            qa_pairs: List of (question, answer) tuples.
            resume_summary: Optional resume context.

        Returns:
            Session summary with per-question evaluations and overall stats.
        """
        evaluations = []

        for question, answer in qa_pairs:
            if not answer.strip():
                continue
            evaluation = self.evaluate_answer(
                user_id=user_id,
                interview_type=interview_type,
                career_goal=career_goal,
                question=question,
                answer=answer,
                save_result=True,
            )
            evaluations.append(
                {
                    "question": question,
                    "answer": answer,
                    "evaluation": evaluation,
                }
            )

        if not evaluations:
            return {"error": "No answers to evaluate."}

        # Aggregate scores
        def avg(field: str) -> float:
            vals = [e["evaluation"].model_dump()[field] for e in evaluations
                    if e["evaluation"].model_dump()[field] is not None]
            return round(sum(vals) / len(vals), 1) if vals else 0.0

        session_summary = {
            "interview_type": interview_type,
            "total_questions": len(evaluations),
            "average_communication": avg("communication"),
            "average_technical": avg("technical_knowledge"),
            "average_confidence": avg("confidence"),
            "average_problem_solving": avg("problem_solving"),
            "average_overall": avg("overall_score"),
            "evaluations": evaluations,
            "session_feedback": self._generate_session_feedback(evaluations, interview_type, career_goal),
        }

        return session_summary

    def get_interview_tips(self, interview_type: str, career_goal: str) -> str:
        """Return tips for the specific interview type."""
        prompt = f"""
Provide 5 specific, actionable tips for a {interview_type} interview for a {career_goal} role.
Format as a numbered list. Be practical and specific — not generic advice.
"""
        return self._gemini.generate_text(
            prompt, system_instruction=INTERVIEW_AGENT_SYSTEM
        )

    def get_sample_answer(
        self, question: str, interview_type: str, career_goal: str
    ) -> str:
        """Generate a model answer for an interview question."""
        prompt = f"""
Provide a strong model answer for this {interview_type} interview question for a {career_goal} role.

Question: {question}

Write a complete, well-structured answer demonstrating best practices.
For behavioral questions, use the STAR method.
For technical questions, show step-by-step reasoning.
"""
        return self._gemini.generate_text(
            prompt, system_instruction=INTERVIEW_AGENT_SYSTEM
        )

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _save_result(
        self,
        user_id: int,
        interview_type: str,
        question: str,
        answer: str,
        evaluation: InterviewEvaluation,
    ) -> None:
        """Persist an interview result to SQLite."""
        result = InterviewResult(
            user_id=user_id,
            interview_type=interview_type,
            question=question,
            answer=answer[:2000],
            communication=evaluation.communication,
            technical_knowledge=evaluation.technical_knowledge,
            confidence=evaluation.confidence,
            problem_solving=evaluation.problem_solving,
            overall_score=evaluation.overall_score,
            feedback=evaluation.feedback,
            strengths=", ".join(evaluation.strengths),
            improvements=", ".join(evaluation.improvements),
            created_at=now_iso(),
        )
        self._db.save_interview_result(result)

    def _generate_session_feedback(
        self, evaluations: list[dict], interview_type: str, career_goal: str
    ) -> str:
        """Generate overall session feedback."""
        avg_overall = sum(
            e["evaluation"].overall_score for e in evaluations
        ) / len(evaluations)

        all_strengths = []
        all_improvements = []
        for e in evaluations:
            all_strengths.extend(e["evaluation"].strengths)
            all_improvements.extend(e["evaluation"].improvements)

        prompt = f"""
Summarize the performance of a candidate in a {interview_type} interview for {career_goal}.

Average Score: {avg_overall:.1f}/10
Common Strengths: {list(set(all_strengths))[:5]}
Areas to Improve: {list(set(all_improvements))[:5]}

Write a 2-paragraph encouraging but honest overall session feedback.
Include specific action items for the next practice session.
"""
        return self._gemini.generate_text(
            prompt, system_instruction=INTERVIEW_AGENT_SYSTEM
        )

    def _fallback_question(self, interview_type: str, career_goal: str) -> dict:
        """Return a fallback question when generation fails."""
        defaults = {
            "Behavioral": "Tell me about a time you solved a challenging technical problem.",
            "Technical": f"What are the key skills required for a {career_goal} role?",
            "Resume-Based": "Walk me through your most significant project.",
            "Coding": "Write a function to reverse a string in Python.",
            "System Design": "Design a URL shortener service at scale.",
        }
        return {
            "question": defaults.get(interview_type, "Tell me about yourself."),
            "question_type": interview_type,
            "expected_topics": ["Clear communication", "Technical accuracy"],
            "time_limit_minutes": 5,
        }

    def _fallback_evaluation(self) -> InterviewEvaluation:
        """Return a safe fallback evaluation when Gemini fails."""
        return InterviewEvaluation(
            communication=5.0,
            technical_knowledge=5.0,
            confidence=5.0,
            problem_solving=5.0,
            overall_score=5.0,
            strengths=["Answer provided"],
            improvements=["Please retry for detailed feedback"],
            feedback="Evaluation failed. Please check your API connection and try again.",
        )
